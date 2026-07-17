from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .consolidate import consolidate_session
from .retrieve import format_briefing, retrieve_experience

SERVER_NAME = "experience-brain"


def create_server(root: Path | str = ".") -> Any:
    resolved_root = Path(root).resolve()
    mcp = FastMCP(SERVER_NAME)

    @mcp.tool(name="process_session")
    def process_session(session_id: str | None = None) -> str:
        count, report = consolidate_session(resolved_root, session_id)
        return f"experiences created={count}\nreview report={report}"

    @mcp.tool(name="query_experience")
    def query_experience(question: str, project: str | None = None, limit: int = 5) -> str:
        return format_briefing(
            retrieve_experience(resolved_root, question, project=project, limit=limit)
        )

    @mcp.tool(name="review_latest")
    def review_latest() -> str:
        path = resolved_root / "reports" / "latest.md"
        if not path.exists():
            return "No review report found."
        return path.read_text(encoding="utf-8")

    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
