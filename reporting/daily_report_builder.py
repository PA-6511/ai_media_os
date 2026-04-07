from __future__ import annotations

# daily_report_builder.py
# ログ・DB から日次集計データを抽出して dict にまとめるビルダー。

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from monitoring.kpi_snapshot_reader import load_latest_kpi_snapshot


def attach_kpi_summary(report: dict[str, Any], snapshot: dict | None) -> dict[str, Any]:
    """最新KPI snapshotの要約を report に付与する。"""
    snap = snapshot or {}
    report["kpi_summary"] = {
        "generated_at": snap.get("generated_at"),
        "health_score": snap.get("health_score", "N/A"),
        "health_grade": snap.get("health_grade", "N/A"),
        "anomaly_overall": snap.get("anomaly_overall", "N/A"),
        "alert_total": snap.get("alert_total", 0),
        "retry_queued_count": snap.get("retry_queued_count", 0),
        "latest_archive": snap.get("latest_archive"),
    }
    return report


class DailyReportBuilder:
    """日次運用レポートを構築する。"""

    def __init__(self, target_date: datetime | None = None):
        """Initialize.

        Args:
            target_date: 集計対象日（デフォルト: 今日）
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc)
        self.target_date = target_date
        self.report_date: str = target_date.strftime("%Y%m%d")

    def build(self, project_root: Path) -> dict[str, Any]:
        """ログ・DB から日次データを集計して dict を返す。"""
        report: dict[str, Any] = {
            "report_date": self.report_date,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "success_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "draft_count": 0,
            "retry_queued_count": 0,
            "combined_count": 0,
            "price_only_count": 0,
            "release_only_count": 0,
            "failed_slugs": [],
            "skipped_slugs": [],
            "draft_slugs": [],
            "completion_rate": 0.0,
        }

        # 1. status report から success/skipped/failed を取得
        self._aggregate_status(project_root, report)

        # 2. combined_signal.log から combined/price_only/release_only を抽出
        self._aggregate_signal_types(project_root, report)

        # 3. retry queue の件数を取得
        self._aggregate_retry_queue(project_root, report)

        # 4. completion_rate を計算
        total = (
            report.get("success_count", 0)
            + report.get("skipped_count", 0)
            + report.get("failed_count", 0)
        )
        if total > 0:
            report["completion_rate"] = round(
                100.0 * report.get("success_count", 0) / total, 2
            )

        return report

    def _aggregate_status(self, project_root: Path, report: dict[str, Any]) -> None:
        """status report から統計を抽出。"""
        try:
            # pipelines/show_status_report の結果を参照するか、
            # data/post_status_tracking から直接読む。
            # 簡略版: post_status_tracking をスキャン
            tracking_path = project_root / "data" / "post_status_tracking"
            if not tracking_path.exists():
                return

            # JSON Lines 形式で保存されているはず
            success, skipped, failed, draft = 0, 0, 0, 0
            failed_slugs: list[str] = []
            skipped_slugs: list[str] = []
            draft_slugs: list[str] = []

            for line in tracking_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    status = entry.get("status", "unknown")
                    slug = entry.get("slug", "")

                    if status == "published":
                        success += 1
                    elif status == "skipped":
                        skipped += 1
                        if slug:
                            skipped_slugs.append(slug)
                    elif status == "failed":
                        failed += 1
                        if slug:
                            failed_slugs.append(slug)
                    elif status == "draft":
                        draft += 1
                        if slug:
                            draft_slugs.append(slug)
                except (json.JSONDecodeError, KeyError):
                    continue

            report["success_count"] = success
            report["skipped_count"] = skipped
            report["failed_count"] = failed
            report["draft_count"] = draft
            report["failed_slugs"] = failed_slugs[:50]  # 最大50件
            report["skipped_slugs"] = skipped_slugs[:50]
            report["draft_slugs"] = draft_slugs[:50]
        except Exception as exc:
            print(f"[warning] status 集計失敗: {exc}")

    def _aggregate_signal_types(self, project_root: Path, report: dict[str, Any]) -> None:
        """combined_signal.log から combined/price_only/release_only を抽出。"""
        try:
            log_path = project_root / "data" / "logs" / "combined_signal.log"
            if not log_path.exists():
                return

            combined, price_only, release_only = 0, 0, 0

            for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                # [BATCH_SUMMARY] や [COMBINED_SIGNAL] の行を探す
                if "[BATCH_SUMMARY]" in line:
                    # 集計行から取得
                    combined += self._extract_int_from_line(line, r"combined_count=(\d+)")
                    price_only += self._extract_int_from_line(line, r"price_only_count=(\d+)")
                    release_only += self._extract_int_from_line(line, r"release_only_count=(\d+)")

            report["combined_count"] = combined
            report["price_only_count"] = price_only
            report["release_only_count"] = release_only
        except Exception as exc:
            print(f"[warning] signal types 集計失敗: {exc}")

    def _aggregate_retry_queue(self, project_root: Path, report: dict[str, Any]) -> None:
        """retry queue の件数を集計。"""
        try:
            # pipelines/show_retry_queue の結果から取得
            # または retry_queue_store を直接参照
            queue_path = project_root / "data" / "retry_queue_store"
            if not queue_path.exists():
                report["retry_queued_count"] = 0
                return

            queued_count = 0
            for line in queue_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    status = entry.get("status", "")
                    if status == "queued":
                        queued_count += 1
                except (json.JSONDecodeError, KeyError):
                    continue

            report["retry_queued_count"] = queued_count
        except Exception as exc:
            print(f"[warning] retry queue 集計失敗: {exc}")

    @staticmethod
    def _extract_int_from_line(line: str, pattern: str) -> int:
        """正規表現でマッチした数字を抽出。"""
        m = re.search(pattern, line)
        return int(m.group(1)) if m else 0


def build_daily_report(
    target_date: datetime | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """日次レポートをビルドして返す。

    Args:
        target_date: 集計対象日
        project_root: プロジェクトルート

    Returns:
        レポート dict
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[1]

    builder = DailyReportBuilder(target_date=target_date)
    report = builder.build(project_root)
    return attach_kpi_summary(report, load_latest_kpi_snapshot())
