from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"


def _build_monthly_report_path(report_month: str, output_dir: Path, report_format: str) -> Path:
    return output_dir / f"monthly_report_{report_month}.{report_format}"


def write_monthly_report_json(report: dict[str, Any], output_dir: Path | None = None) -> str:
    """月次レポート JSON を保存してパス文字列を返す。"""
    output = output_dir or DEFAULT_REPORT_DIR
    output.mkdir(parents=True, exist_ok=True)

    report_month = str(report.get("report_month", "unknown"))
    path = _build_monthly_report_path(report_month, output, "json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _write_top_slug_lines(fp: Any, title: str, rows: list[dict[str, Any]]) -> None:
    fp.write("-" * 70 + "\n")
    fp.write(f"◆ {title}\n")
    fp.write("-" * 70 + "\n")
    if not rows:
        fp.write("  (なし)\n\n")
        return

    for i, row in enumerate(rows, 1):
        slug = str(row.get("slug", ""))
        count = int(row.get("count", 0))
        fp.write(f"  {i:2}. {slug} ({count})\n")
    fp.write("\n")


def write_monthly_report_txt(report: dict[str, Any], output_dir: Path | None = None) -> str:
    """月次レポート TXT を保存してパス文字列を返す。"""
    output = output_dir or DEFAULT_REPORT_DIR
    output.mkdir(parents=True, exist_ok=True)

    report_month = str(report.get("report_month", "unknown"))
    path = _build_monthly_report_path(report_month, output, "txt")

    with path.open("w", encoding="utf-8") as fp:
        fp.write("=" * 70 + "\n")
        fp.write("月次運用レポート\n")
        fp.write("=" * 70 + "\n\n")

        fp.write(f"レポート月:       {report_month}\n")
        fp.write(f"日次レポート数:   {int(report.get('daily_report_count', 0)):>5}\n\n")

        fp.write("-" * 70 + "\n")
        fp.write("◆ 処理統計\n")
        fp.write("-" * 70 + "\n")
        fp.write(f"成功合計:         {int(report.get('total_success_count', 0)):>6}\n")
        fp.write(f"スキップ合計:     {int(report.get('total_skipped_count', 0)):>6}\n")
        fp.write(f"失敗合計:         {int(report.get('total_failed_count', 0)):>6}\n")
        fp.write(f"Draft 合計:       {int(report.get('total_draft_count', 0)):>6}\n")
        fp.write(f"Retry Queue 合計: {int(report.get('total_retry_queued_count', 0)):>6}\n\n")

        fp.write("-" * 70 + "\n")
        fp.write("◆ 信号統計\n")
        fp.write("-" * 70 + "\n")
        fp.write(f"combined 合計:    {int(report.get('total_combined_count', 0)):>6}\n")
        fp.write(f"price_only 合計:  {int(report.get('total_price_only_count', 0)):>6}\n")
        fp.write(f"release_only 合計:{int(report.get('total_release_only_count', 0)):>6}\n\n")

        kpi = report.get("kpi_summary") or {}
        fp.write("-" * 70 + "\n")
        fp.write("◆ KPI Summary\n")
        fp.write("-" * 70 + "\n")
        fp.write(f"snapshot_generated_at: {kpi.get('generated_at', 'N/A')}\n")
        fp.write(
            f"health: {kpi.get('health_score', 'N/A')} ({kpi.get('health_grade', 'N/A')})\n"
        )
        fp.write(
            f"anomaly: {kpi.get('anomaly_overall', 'N/A')} alerts={kpi.get('alert_total', 0)}\n"
        )
        fp.write(f"retry_queued_count: {kpi.get('retry_queued_count', 0)}\n")
        fp.write(f"latest_archive: {kpi.get('latest_archive', 'N/A')}\n\n")

        _write_top_slug_lines(fp, "失敗の多い slug", report.get("top_failed_slugs", []))
        _write_top_slug_lines(fp, "スキップの多い slug", report.get("top_skipped_slugs", []))

        fp.write("=" * 70 + "\n")

    return str(path)
