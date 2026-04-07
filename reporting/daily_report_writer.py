# daily_report_writer.py
# レポート dict を JSON ・テキストで保存するライター。

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


VALID_REPORT_FORMATS: set[str] = {"txt", "json"}


def build_report_path(report_date: str, report_format: str, output_dir: Path) -> Path:
    """日付とフォーマットからレポートパスを構築する。"""
    normalized_format = report_format.lower()
    if normalized_format not in VALID_REPORT_FORMATS:
        raise ValueError(
            f"不正な format です: {report_format} (許可: {sorted(VALID_REPORT_FORMATS)})"
        )

    return output_dir / f"daily_report_{report_date}.{normalized_format}"


def list_available_report_dates(output_dir: Path) -> list[str]:
    """利用可能なレポート日付 (YYYYMMDD) を昇順で返す。"""
    if not output_dir.exists() or not output_dir.is_dir():
        return []

    dates: set[str] = set()
    for path in output_dir.glob("daily_report_*.txt"):
        name = path.name
        # daily_report_YYYYMMDD.txt の形式を対象にする
        if name.startswith("daily_report_") and name.endswith(".txt"):
            date_part = name[len("daily_report_") : -len(".txt")]
            if len(date_part) == 8 and date_part.isdigit():
                dates.add(date_part)

    for path in output_dir.glob("daily_report_*.json"):
        name = path.name
        if name.startswith("daily_report_") and name.endswith(".json"):
            date_part = name[len("daily_report_") : -len(".json")]
            if len(date_part) == 8 and date_part.isdigit():
                dates.add(date_part)

    return sorted(dates)


class DailyReportWriter:
    """日次レポートをファイルに書き込む。"""

    def __init__(self, output_dir: Path | None = None):
        """Initialize.

        Args:
            output_dir: 出力先ディレクトリ (デフォルト: data/reports)
        """
        if output_dir is None:
            output_dir = Path(__file__).resolve().parents[1] / "data" / "reports"
        self.output_dir = output_dir

    def write(self, report: dict[str, Any]) -> tuple[Path, Path]:
        """レポートを JSON とテキストで保存する。

        Args:
            report: レポート dict

        Returns:
            (JSON ファイルパス, テキストファイルパス)
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        report_date = report.get("report_date", "unknown")
        json_path = build_report_path(report_date, "json", self.output_dir)
        txt_path = build_report_path(report_date, "txt", self.output_dir)

        # JSON 保存
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # テキスト保存
        with txt_path.open("w", encoding="utf-8") as f:
            self._write_text_report(f, report)

        return json_path, txt_path

    @staticmethod
    def _write_text_report(fp: Any, report: dict[str, Any]) -> None:
        """テキスト形式でレポートを書き込む。"""
        report_date = report.get("report_date", "unknown")
        generated_at = report.get("generated_at", "")

        fp.write("=" * 70 + "\n")
        fp.write("日次運用レポート\n")
        fp.write("=" * 70 + "\n\n")

        fp.write(f"レポート日: {report_date}\n")
        fp.write(f"生成時刻:   {generated_at}\n\n")

        # ---- 処理統計 ----
        fp.write("-" * 70 + "\n")
        fp.write("◆ 処理統計\n")
        fp.write("-" * 70 + "\n")

        success = report.get("success_count", 0)
        skipped = report.get("skipped_count", 0)
        failed = report.get("failed_count", 0)
        total = success + skipped + failed

        fp.write(f"総処理件数:      {total:>5}\n")
        fp.write(f"  成功:         {success:>5}\n")
        fp.write(f"  スキップ:     {skipped:>5}\n")
        fp.write(f"  失敗:         {failed:>5}\n")
        fp.write(f"完了率:         {report.get('completion_rate', 0):>6.2f}%\n")
        fp.write(f"Draft 件数:     {report.get('draft_count', 0):>5}\n\n")

        # ---- 信号統計 ----
        fp.write("-" * 70 + "\n")
        fp.write("◆ 信号統計（price_changed / release_changed の内訳）\n")
        fp.write("-" * 70 + "\n")

        combined = report.get("combined_count", 0)
        price_only = report.get("price_only_count", 0)
        release_only = report.get("release_only_count", 0)
        signal_total = combined + price_only + release_only

        fp.write(f"総シグナル件数:  {signal_total:>5}\n")
        fp.write(f"  複合シグナル:  {combined:>5}\n")
        fp.write(f"  価格変動:      {price_only:>5}\n")
        fp.write(f"  新刊イベント:  {release_only:>5}\n\n")

        # ---- 処理保留件数 ----
        fp.write("-" * 70 + "\n")
        fp.write("◆ 処理保留\n")
        fp.write("-" * 70 + "\n")
        fp.write(f"Retry Queue: {report.get('retry_queued_count', 0):>5}\n\n")

        # ---- KPI summary ----
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

        # ---- 失敗件数 ----
        failed_slugs = report.get("failed_slugs", [])
        if failed_slugs:
            fp.write("-" * 70 + "\n")
            fp.write(f"◆ 失敗件数: {len(failed_slugs)}\n")
            fp.write("-" * 70 + "\n")
            for i, slug in enumerate(failed_slugs[:10], 1):
                fp.write(f"  {i:2}. {slug}\n")
            if len(failed_slugs) > 10:
                fp.write(f"  ... 他 {len(failed_slugs) - 10} 件\n")
            fp.write("\n")

        # ---- スキップ件数 ----
        skipped_slugs = report.get("skipped_slugs", [])
        if skipped_slugs:
            fp.write("-" * 70 + "\n")
            fp.write(f"◆ スキップ件数: {len(skipped_slugs)}\n")
            fp.write("-" * 70 + "\n")
            for i, slug in enumerate(skipped_slugs[:10], 1):
                fp.write(f"  {i:2}. {slug}\n")
            if len(skipped_slugs) > 10:
                fp.write(f"  ... 他 {len(skipped_slugs) - 10} 件\n")
            fp.write("\n")

        # ---- Draft 件数 ----
        draft_slugs = report.get("draft_slugs", [])
        if draft_slugs:
            fp.write("-" * 70 + "\n")
            fp.write(f"◆ Draft 件数: {len(draft_slugs)}\n")
            fp.write("-" * 70 + "\n")
            for i, slug in enumerate(draft_slugs[:10], 1):
                fp.write(f"  {i:2}. {slug}\n")
            if len(draft_slugs) > 10:
                fp.write(f"  ... 他 {len(draft_slugs) - 10} 件\n")
            fp.write("\n")

        fp.write("=" * 70 + "\n")


def write_daily_report(
    report: dict[str, Any],
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """レポートを保存する。

    Args:
        report: レポート dict
        output_dir: 出力先ディレクトリ

    Returns:
        (JSON ファイルパス, テキストファイルパス)
    """
    writer = DailyReportWriter(output_dir=output_dir)
    return writer.write(report)
