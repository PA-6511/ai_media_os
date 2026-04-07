from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_OPS_GUI_PREVIEW_HTML_PATH = DEFAULT_REPORT_DIR / "ops_gui_preview_latest.html"


def write_ops_gui_preview_html(html: str, output_path: Path | None = None) -> str:
    path = output_path or DEFAULT_OPS_GUI_PREVIEW_HTML_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return str(path)