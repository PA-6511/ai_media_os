from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from reporting.run_daily_report import generate_daily_report


DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "reports"


def run_daily_report_hook(
    report_date: date | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """日次レポートを生成し、結果情報を返す。

    Scheduler から呼ばれることを想定し、例外は呼び出し元で処理する。

    Args:
        report_date: レポート対象日。未指定時は当日。
        output_dir: 出力ディレクトリ。未指定時は data/reports。

    Returns:
        実行結果 dict。
    """
    target_date = report_date or date.today()
    target_output_dir = output_dir or DEFAULT_REPORT_DIR

    report, json_path, txt_path = generate_daily_report(
        report_date=target_date,
        output_dir=target_output_dir,
    )

    return {
        "success": True,
        "report_date": report.get("report_date", target_date.strftime("%Y%m%d")),
        "json_path": str(json_path),
        "txt_path": str(txt_path),
        "output_dir": str(target_output_dir),
    }
