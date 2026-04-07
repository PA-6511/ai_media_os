from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GUI_GO_LIVE_CHECKLIST_PATH = BASE_DIR / "docs" / "gui_go_live_checklist_latest.md"


def write_gui_go_live_checklist_markdown(markdown: str, output_path: Path | None = None) -> str:
    path = output_path or DEFAULT_GUI_GO_LIVE_CHECKLIST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return str(path)