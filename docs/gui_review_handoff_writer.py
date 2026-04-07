from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GUI_REVIEW_HANDOFF_PATH = BASE_DIR / "docs" / "gui_review_handoff_latest.md"


def write_gui_review_handoff_markdown(md: str, output_path: Path | None = None) -> str:
    path = output_path or DEFAULT_GUI_REVIEW_HANDOFF_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")
    return str(path)
