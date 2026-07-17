from __future__ import annotations

import argparse
from pathlib import Path

import streamlit as st

from .store import ensure_store, lint_store, read_events, read_experiences


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--root", default=".")
    parsed, _ = parser.parse_known_args()
    return parsed


def main() -> None:
    root = Path(_args().root).resolve()
    ensure_store(root)
    st.set_page_config(page_title="Experience Brain", layout="wide")
    st.title("Experience Brain")
    events = read_events(root)
    experiences = read_experiences(root)
    st.metric("Events", len(events))
    st.metric("Experiences", len(experiences))
    tab_events, tab_experiences, tab_review, tab_lint = st.tabs(
        ["Events", "Experiences", "Review", "Lint"]
    )
    with tab_events:
        st.dataframe([event.model_dump(mode="json") for event in events], use_container_width=True)
    with tab_experiences:
        st.dataframe(
            [experience.model_dump(mode="json") for experience in experiences],
            use_container_width=True,
        )
    with tab_review:
        latest = root / "reports" / "latest.md"
        st.markdown(latest.read_text(encoding="utf-8") if latest.exists() else "No report yet.")
    with tab_lint:
        errors = lint_store(root)
        if errors:
            st.error("\n".join(errors))
        else:
            st.success("lint passed")


if __name__ == "__main__":
    main()
