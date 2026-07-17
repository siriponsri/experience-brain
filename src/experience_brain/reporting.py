from __future__ import annotations

from html import escape
from pathlib import Path

from .config import Settings, load_settings
from .event_store import read_events
from .util import read_yaml
from .wiki import wiki_metrics, wiki_root


def build_report(root: Path) -> Path:
    settings = load_settings(root)
    if settings.condition == "c1":
        return _build_wiki_report(settings)
    return _build_lite_report(root)


def _build_lite_report(root: Path) -> Path:
    events = read_events(root)
    index = read_yaml(root / "memory" / "skills" / "index.yaml", {"skills": {}})
    skills = index.get("skills", {})
    rows = "".join(
        f"<tr><td>{escape(str(skill_id))}</td><td>{escape(str(entry.get('status')))}</td>"
        f"<td>{escape(str(entry.get('version')))}</td></tr>"
        for skill_id, entry in sorted(skills.items())
    )
    document = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Experience Brain Lite</title></head><body>"
        "<h1>Experience Brain Lite report</h1>"
        f"<p>Append-only events: {len(events)}</p><p>Skills: {len(skills)}</p>"
        "<table><thead><tr><th>Skill</th><th>Status</th><th>Version</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></body></html>"
    )
    destination = root / "reports" / "index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return destination


def _build_wiki_report(settings: Settings) -> Path:
    raw_index = read_yaml(wiki_root(settings) / "raw" / "index.yaml", {"sources": {}})
    index = read_yaml(wiki_root(settings) / "index.yaml", {"pages": {}, "lessons": {}})
    metrics = wiki_metrics(settings)
    document = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Experience Brain C1 Wiki</title></head><body>"
        "<h1>Experience Brain C1 Wiki report</h1>"
        f"<p>Run: {escape(settings.run_id)}</p>"
        f"<p>Immutable raw sources: {len(raw_index.get('sources', {}))}</p>"
        f"<p>Current pages: {len(index.get('pages', {}))}</p>"
        f"<p>Current lessons: {len(index.get('lessons', {}))}</p>"
        f"<p>Wiki maintenance operations: {metrics['maintenance_operations']}</p>"
        f"<p>Wiki maintenance input tokens: {metrics['maintenance_input_tokens']}</p>"
        f"<p>Wiki maintenance output tokens: {metrics['maintenance_output_tokens']}</p>"
        f"<p>Wiki maintenance total tokens: {metrics['maintenance_tokens']}</p>"
        f"<p>Background tokens (wiki maintenance): {metrics['maintenance_tokens']}</p>"
        f"<p>Fairness config hash: {escape(settings.fairness_fingerprint)}</p>"
        "</body></html>"
    )
    destination = settings.root / "reports" / f"c1_{settings.run_id}.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return destination
