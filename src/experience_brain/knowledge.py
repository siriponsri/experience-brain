from __future__ import annotations

import csv
import json
import mimetypes
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from .capture import redact_text, redact_value
from .models import (
    ExtractorMetadata,
    Knowledge,
    KnowledgeStatus,
    Provenance,
    Redaction,
    SourceLocation,
)
from .store import append_knowledge, current_knowledge, inbox_dir, read_knowledge

TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".csv",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".ps1",
    ".bat",
    ".sql",
    ".xml",
}
OFFICE_EXTENSIONS = {".pdf", ".docx", ".xlsx"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | OFFICE_EXTENSIONS
MAX_EXTRACT_CHARS = 120_000


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    extractor_name: str
    locations: list[SourceLocation]
    warnings: list[str]


@dataclass(frozen=True)
class ProcessedInboxFile:
    filename: str
    content_hash: str
    status: str
    duplicate_of: str | None = None
    knowledge_id: str | None = None
    error: str | None = None


def content_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def inbox_files(root: Path) -> list[Path]:
    base = inbox_dir(root)
    if not base.exists():
        return []
    return sorted(path for path in base.rglob("*") if path.is_file())


def relative_inbox_name(root: Path, path: Path) -> str:
    return path.resolve().relative_to(inbox_dir(root).resolve()).as_posix()


def _decode_bytes(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp874", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_text(path: Path) -> ExtractedContent:
    text = _decode_bytes(path)
    if path.suffix.casefold() == ".json":
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
        except json.JSONDecodeError:
            pass
    if path.suffix.casefold() == ".csv":
        rows: list[str] = []
        for row in csv.reader(text.splitlines()):
            rows.append(" | ".join(row))
        text = "\n".join(rows)
    line_count = max(1, len(text.splitlines()))
    return ExtractedContent(
        text=text,
        extractor_name="plain_text_registry",
        locations=[SourceLocation(line_start=1, line_end=line_count)],
        warnings=[],
    )


def _extract_pdf(path: Path) -> ExtractedContent:
    try:
        pypdf = import_module("pypdf")
    except ImportError:
        return ExtractedContent("", "pypdf_missing", [], ["needs pypdf"])
    reader = pypdf.PdfReader(str(path))
    pages: list[str] = []
    locations: list[SourceLocation] = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"[Page {index}]\n{page_text}")
            locations.append(SourceLocation(page=index))
    return ExtractedContent(
        text="\n\n".join(pages),
        extractor_name="pypdf",
        locations=locations,
        warnings=[] if pages else ["no extractable text found"],
    )


def _extract_docx(path: Path) -> ExtractedContent:
    try:
        docx = import_module("docx")
    except ImportError:
        return ExtractedContent("", "python_docx_missing", [], ["needs python-docx"])
    document = docx.Document(str(path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return ExtractedContent(
        text="\n".join(paragraphs),
        extractor_name="python-docx",
        locations=[SourceLocation(section="document")],
        warnings=[] if paragraphs else ["no extractable text found"],
    )


def _extract_xlsx(path: Path) -> ExtractedContent:
    try:
        openpyxl = import_module("openpyxl")
    except ImportError:
        return ExtractedContent("", "openpyxl_missing", [], ["needs openpyxl"])
    workbook = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    parts: list[str] = []
    locations: list[SourceLocation] = []
    for sheet in workbook.worksheets:
        lines: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            values = ["" if value is None else str(value) for value in row]
            if any(value.strip() for value in values):
                lines.append(" | ".join(values))
        if lines:
            parts.append(f"[Sheet {sheet.title}]\n" + "\n".join(lines))
            locations.append(SourceLocation(sheet=sheet.title))
    workbook.close()
    return ExtractedContent(
        text="\n\n".join(parts),
        extractor_name="openpyxl",
        locations=locations,
        warnings=[] if parts else ["no extractable cells found"],
    )


EXTRACTORS: dict[str, Callable[[Path], ExtractedContent]] = {
    **{extension: _extract_text for extension in TEXT_EXTENSIONS},
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".xlsx": _extract_xlsx,
}


def extract_inbox_file(root: Path, filename: str) -> dict[str, Any]:
    path = (inbox_dir(root) / filename).resolve()
    if not path.is_relative_to(inbox_dir(root).resolve()):
        raise ValueError("inbox filename must stay inside inbox/")
    extracted = _extract_path(path)
    text, redactions = redact_text(extracted.text, field_path="extracted_content")
    return {
        "filename": filename,
        "content_hash": content_hash(path),
        "extractor": extracted.extractor_name,
        "text": text,
        "redactions": [redaction.model_dump(mode="json") for redaction in redactions],
        "warnings": extracted.warnings,
        "locations": [
            location.model_dump(mode="json", exclude_none=True) for location in extracted.locations
        ],
    }


def _extract_path(path: Path) -> ExtractedContent:
    extractor = EXTRACTORS.get(path.suffix.casefold())
    if extractor is None:
        return ExtractedContent("", "none", [], ["unsupported file type"])
    extracted = extractor(path)
    text = extracted.text[:MAX_EXTRACT_CHARS]
    warnings = list(extracted.warnings)
    if len(extracted.text) > MAX_EXTRACT_CHARS:
        warnings.append(f"content truncated to {MAX_EXTRACT_CHARS} characters")
    return ExtractedContent(text, extracted.extractor_name, extracted.locations, warnings)


def _words(text: str) -> list[str]:
    stop = {
        "about",
        "after",
        "before",
        "from",
        "that",
        "this",
        "with",
        "what",
        "when",
        "where",
        "which",
        "have",
        "into",
        "will",
        "your",
    }
    found = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.casefold())
    unique: list[str] = []
    for word in found:
        if word not in stop and word not in unique:
            unique.append(word)
    return unique


def digest_text(title: str, text: str) -> tuple[str, list[str], str, list[str]]:
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    summary = " ".join(lines[:4])[:700] if lines else f"No extractable text found in {title}."
    facts = [line for line in lines if len(line) >= 12][:6]
    if not facts and summary:
        facts = [summary]
    tags = _words(f"{title} {text}")[:12]
    applicability = (
        "Use as external Knowledge only. It can inform planning, but it is not evidence "
        "that the Agent has tested the claim."
    )
    return summary, facts, applicability, tags


def _knowledge_id(source_hash: str, *, suffix: str = "") -> str:
    base = f"KNO-{source_hash[:12].upper()}"
    return f"{base}-{suffix}" if suffix else base


def _source_metadata(path: Path) -> tuple[str, str | None]:
    source_type = path.suffix.casefold().lstrip(".") or "unknown"
    mime_type = mimetypes.guess_type(path.name)[0]
    return source_type, mime_type


def _redact_digest(
    summary: str,
    key_facts: list[str],
    applicability: str,
    tags: list[str],
) -> tuple[str, list[str], str, list[str], list[Redaction]]:
    clean_summary, summary_redactions = redact_text(summary, field_path="summary")
    clean_facts_any, fact_redactions = redact_value(key_facts, field_path="key_facts")
    clean_applicability, applicability_redactions = redact_text(
        applicability, field_path="suggested_applicability"
    )
    clean_tags_any, tag_redactions = redact_value(tags, field_path="tags")
    return (
        clean_summary,
        cast(list[str], clean_facts_any),
        clean_applicability,
        cast(list[str], clean_tags_any),
        [*summary_redactions, *fact_redactions, *applicability_redactions, *tag_redactions],
    )


def make_knowledge_record(
    *,
    knowledge_id: str | None = None,
    title: str,
    summary: str,
    key_facts: list[str],
    suggested_applicability: str,
    tags: list[str],
    source_filename: str,
    source_content_hash: str,
    source_type: str,
    source_mime_type: str | None = None,
    project: str = "general",
    status: KnowledgeStatus = KnowledgeStatus.proposed,
    source_location: SourceLocation | None = None,
    extractor: ExtractorMetadata | None = None,
    provenance: Provenance | None = None,
    metadata: dict[str, Any] | None = None,
    supersedes: str | None = None,
    invalidates: str | None = None,
) -> Knowledge:
    clean_summary, clean_facts, clean_applicability, clean_tags, redactions = _redact_digest(
        summary, key_facts, suggested_applicability, tags
    )
    base_provenance = provenance or Provenance(source="knowledge_inbox")
    clean_extra, extra_redactions = redact_value(
        base_provenance.extra, field_path="provenance.extra"
    )
    clean_metadata, metadata_redactions = redact_value(metadata or {}, field_path="metadata")
    return Knowledge(
        id=knowledge_id or _knowledge_id(source_content_hash),
        project=project,
        source_project=project,
        status=status,
        title=title,
        summary=clean_summary,
        key_facts=clean_facts,
        suggested_applicability=clean_applicability,
        tags=clean_tags,
        source_filename=source_filename,
        source_content_hash=source_content_hash,
        source_type=source_type,
        source_mime_type=source_mime_type,
        source_location=source_location,
        extractor=extractor or ExtractorMetadata(name="agent_digest"),
        supersedes=supersedes,
        invalidates=invalidates,
        provenance=base_provenance.model_copy(
            update={
                "redactions": [
                    *base_provenance.redactions,
                    *redactions,
                    *extra_redactions,
                    *metadata_redactions,
                ],
                "extra": clean_extra,
            }
        ),
        metadata=cast(dict[str, Any], clean_metadata),
    )


def save_knowledge_digest(
    root: Path,
    *,
    title: str,
    summary: str,
    key_facts: list[str],
    suggested_applicability: str,
    tags: list[str],
    source_filename: str,
    source_content_hash: str,
    source_type: str,
    source_mime_type: str | None = None,
    project: str = "general",
    provenance: Provenance | None = None,
) -> Knowledge:
    knowledge = make_knowledge_record(
        title=title,
        summary=summary,
        key_facts=key_facts,
        suggested_applicability=suggested_applicability,
        tags=tags,
        source_filename=source_filename,
        source_content_hash=source_content_hash,
        source_type=source_type,
        source_mime_type=source_mime_type,
        project=project,
        provenance=provenance,
    )
    append_knowledge(root, knowledge)
    return knowledge


def _status_record(
    *,
    root: Path,
    path: Path,
    status: KnowledgeStatus,
    source_hash: str,
    warning: str,
    project: str,
    provenance: Provenance,
    knowledge_id: str | None = None,
    supersedes: str | None = None,
) -> Knowledge:
    source_type, mime_type = _source_metadata(path)
    relative = relative_inbox_name(root, path)
    knowledge = make_knowledge_record(
        knowledge_id=knowledge_id,
        title=path.name,
        summary=warning,
        key_facts=[],
        suggested_applicability="No reusable Knowledge was created from this source.",
        tags=[source_type, status.value],
        source_filename=relative,
        source_content_hash=source_hash,
        source_type=source_type,
        source_mime_type=mime_type,
        project=project,
        status=status,
        extractor=ExtractorMetadata(name="inbox_status", warnings=[warning]),
        provenance=provenance,
        supersedes=supersedes,
        metadata={"processing_status": status.value, "error": warning},
    )
    append_knowledge(root, knowledge)
    return knowledge


def process_inbox(
    root: Path,
    *,
    project: str = "general",
    provenance: Provenance | None = None,
    retry: bool = False,
) -> list[ProcessedInboxFile]:
    base_provenance = provenance or Provenance(source="knowledge_inbox")
    existing_by_hash = {
        knowledge.source_content_hash: knowledge for knowledge in read_knowledge(root)
    }
    processed: list[ProcessedInboxFile] = []
    for path in inbox_files(root):
        relative = relative_inbox_name(root, path)
        source_hash = content_hash(path)
        if source_hash in existing_by_hash:
            existing = existing_by_hash[source_hash]
            retryable = existing.status in {
                KnowledgeStatus.error,
                KnowledgeStatus.needs_extractor,
                KnowledgeStatus.unsupported,
            }
            if not retry or not retryable:
                processed.append(
                    ProcessedInboxFile(
                        filename=relative,
                        content_hash=source_hash,
                        status="duplicate",
                        duplicate_of=existing.id,
                    )
                )
                continue
            revision_suffix = datetime.now(UTC).strftime("REV-%Y%m%d%H%M%S%f")
            revision_id = _knowledge_id(source_hash, suffix=revision_suffix)
        else:
            existing = None
            revision_id = None
        source_type, mime_type = _source_metadata(path)
        if path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
            record = _status_record(
                root=root,
                path=path,
                status=KnowledgeStatus.unsupported,
                source_hash=source_hash,
                warning=f"No extractor is registered for {path.suffix or 'this file type'}.",
                project=project,
                provenance=base_provenance,
                knowledge_id=revision_id,
                supersedes=existing.id if existing else None,
            )
            existing_by_hash[source_hash] = record  # type: ignore[assignment]
            processed.append(
                ProcessedInboxFile(
                    relative, source_hash, record.status.value, knowledge_id=record.id
                )
            )
            continue
        try:
            extracted = _extract_path(path)
        except Exception as error:  # pragma: no cover - defensive path for corrupt files
            record = _status_record(
                root=root,
                path=path,
                status=KnowledgeStatus.error,
                source_hash=source_hash,
                warning=str(error),
                project=project,
                provenance=base_provenance,
                knowledge_id=revision_id,
                supersedes=existing.id if existing else None,
            )
            existing_by_hash[source_hash] = record  # type: ignore[assignment]
            processed.append(
                ProcessedInboxFile(
                    relative,
                    source_hash,
                    record.status.value,
                    knowledge_id=record.id,
                    error=str(error),
                )
            )
            continue
        if extracted.extractor_name.endswith("_missing"):
            record = _status_record(
                root=root,
                path=path,
                status=KnowledgeStatus.needs_extractor,
                source_hash=source_hash,
                warning=", ".join(extracted.warnings),
                project=project,
                provenance=base_provenance,
                knowledge_id=revision_id,
                supersedes=existing.id if existing else None,
            )
            existing_by_hash[source_hash] = record  # type: ignore[assignment]
            processed.append(
                ProcessedInboxFile(
                    relative, source_hash, record.status.value, knowledge_id=record.id
                )
            )
            continue
        text, content_redactions = redact_text(extracted.text, field_path="extracted_content")
        summary, facts, applicability, tags = digest_text(path.stem, text)
        prior_same_name = [
            knowledge
            for knowledge in read_knowledge(root)
            if knowledge.source_filename == relative
            and knowledge.source_content_hash != source_hash
        ]
        previous_revision = prior_same_name[-1].id if prior_same_name else None
        knowledge = make_knowledge_record(
            knowledge_id=revision_id,
            title=path.stem,
            summary=summary,
            key_facts=facts,
            suggested_applicability=applicability,
            tags=tags,
            source_filename=relative,
            source_content_hash=source_hash,
            source_type=source_type,
            source_mime_type=mime_type,
            project=project,
            source_location=extracted.locations[0] if extracted.locations else None,
            extractor=ExtractorMetadata(
                name=extracted.extractor_name,
                content_chars=len(text),
                content_lines=len(text.splitlines()),
                warnings=extracted.warnings,
            ),
            provenance=base_provenance.model_copy(
                update={
                    "redactions": [*base_provenance.redactions, *content_redactions],
                    "extra": {
                        **base_provenance.extra,
                        "memory_type": "Knowledge",
                        "source": "external_file",
                        "previous_source_revision": previous_revision,
                    },
                }
            ),
            metadata={
                "processing_status": KnowledgeStatus.proposed.value,
                "source_locations": [
                    location.model_dump(mode="json", exclude_none=True)
                    for location in extracted.locations
                ],
                "previous_source_revision": previous_revision,
            },
            supersedes=existing.id if existing else None,
        )
        append_knowledge(root, knowledge)
        existing_by_hash[source_hash] = knowledge  # type: ignore[assignment]
        processed.append(
            ProcessedInboxFile(
                relative, source_hash, knowledge.status.value, knowledge_id=knowledge.id
            )
        )
    return processed


def list_inbox_status(root: Path) -> list[dict[str, Any]]:
    records = read_knowledge(root)
    by_hash = {knowledge.source_content_hash: knowledge for knowledge in records}
    hash_counts: dict[str, int] = {}
    paths = inbox_files(root)
    for path in paths:
        hash_counts[content_hash(path)] = hash_counts.get(content_hash(path), 0) + 1
    statuses: list[dict[str, Any]] = []
    for path in paths:
        source_hash = content_hash(path)
        record = by_hash.get(source_hash)
        status = record.status.value if record else "new"
        duplicate_of = (
            record.id
            if record and record.source_filename != relative_inbox_name(root, path)
            else None
        )
        duplicate = "duplicate" if duplicate_of or hash_counts[source_hash] > 1 else "unique"
        mime_type = mimetypes.guess_type(path.name)[0]
        statuses.append(
            {
                "filename": relative_inbox_name(root, path),
                "type": path.suffix.casefold().lstrip(".") or "unknown",
                "mime_type": mime_type,
                "size": path.stat().st_size,
                "content_hash": source_hash,
                "processing_status": status,
                "duplicate_status": duplicate,
                "duplicate_of": duplicate_of,
                "uploaded_or_discovered_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=UTC
                ).isoformat(),
                "knowledge_id": record.id if record else None,
                "error": record.metadata.get("error") if record else None,
            }
        )
    return statuses


KnowledgeReviewAction = str


def review_knowledge(
    root: Path,
    knowledge_id: str,
    *,
    action: KnowledgeReviewAction,
    run_id: str | None = None,
) -> Knowledge:
    matches = [knowledge for knowledge in current_knowledge(root) if knowledge.id == knowledge_id]
    if not matches:
        raise ValueError(f"unknown or non-current knowledge: {knowledge_id}")
    current = matches[0]
    if action not in {"confirm", "invalidate", "retire"}:
        raise ValueError(f"unsupported Knowledge review action: {action}")
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d%H%M%S%f")
    digest = sha256(f"{knowledge_id}:{action}:{timestamp}".encode()).hexdigest()[:8].upper()
    revision_id = f"{knowledge_id}-REV-{timestamp}-{digest}"
    status = {
        "confirm": KnowledgeStatus.confirmed,
        "invalidate": KnowledgeStatus.invalidated,
        "retire": KnowledgeStatus.retired,
    }[action]
    payload = current.model_dump(
        mode="json",
        exclude={"payload_hash", "previous_hash", "record_hash", "ingested_at"},
    )
    reviewed = Knowledge.model_validate(
        payload
        | {
            "id": revision_id,
            "schema_version": current.schema_version,
            "updated_at": now.isoformat(),
            "status": status.value,
            "supersedes": current.id if action != "invalidate" else None,
            "invalidates": current.id if action == "invalidate" else None,
            "metadata": {
                **current.metadata,
                "review_action": action,
                "reviewed_knowledge_id": current.id,
            },
            "provenance": Provenance(
                agent="owner",
                experiment_id="EXP-03.2",
                run_id=run_id or f"RUN-{timestamp}",
                source="owner_dashboard",
                extra={
                    "memory_type": "Knowledge",
                    "review_action": action,
                    "source_record_hash": current.record_hash,
                    "source_knowledge_id": current.id,
                },
            ).model_dump(mode="json"),
        }
    )
    append_knowledge(root, reviewed)
    return reviewed
