from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DAILY_CHECKLIST_PATH = BASE_DIR / "docs" / "daily_checklist_latest.md"


def write_daily_checklist(markdown: str, output_path: Path | None = None) -> str:
    """Daily checklist Markdown を保存し、保存先を返す。"""
    path = output_path or DEFAULT_DAILY_CHECKLIST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return str(path)