from __future__ import annotations

from html import escape
from pathlib import Path

from .event_store import read_events
from .util import read_yaml


def build_report(root: Path) -> Path:
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
