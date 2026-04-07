from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_WEEKLY_DASHBOARD_FILENAME = "weekly_dashboard_latest.html"


def write_weekly_dashboard(html: str, report_dir: Path | None = None) -> str:
    """週次ダッシュボード HTML を保存してファイルパスを返す。"""
    out_dir = report_dir or DEFAULT_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / DEFAULT_WEEKLY_DASHBOARD_FILENAME
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
