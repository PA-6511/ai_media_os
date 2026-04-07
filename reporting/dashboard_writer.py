from __future__ import annotations

# dashboard_writer.py
# 生成済み HTML を data/reports/dashboard_latest.html に保存する。

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_DASHBOARD_FILENAME = "dashboard_latest.html"


def write_dashboard(html: str, report_dir: Path | None = None) -> str:
    """ダッシュボード HTML を保存してファイルパスを返す。"""
    out_dir = report_dir or DEFAULT_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / DEFAULT_DASHBOARD_FILENAME
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)
