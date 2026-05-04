"""escalation.py — 検証失敗のエスカレーション処理."""
from __future__ import annotations

import logging
from typing import Any

from monitoring.slack_notifier import send_slack_block

logger = logging.getLogger(__name__)

# エスカレーション先（将来的に複数経路を追加可能）
_ESCALATION_CHANNELS = ["slack"]


def escalate_verification_failure(
    report: dict[str, Any],
    *,
    dry_run: bool = False,
) -> bool:
    """失敗レポートを受け取り、設定済みの経路へエスカレーションする。

    Args:
        report: build_verification_failure_report() が返した dict。
        dry_run: True の場合、実際の通知は送らずログのみ出力する。

    Returns:
        True: エスカレーション成功（または dry_run）
        False: 全経路で通知失敗
    """
    failure_count = report.get("failure_count", 0)
    warning_count = report.get("warning_count", 0)
    context = report.get("context", {})
    failures = report.get("failures", [])

    if failure_count == 0 and warning_count == 0:
        logger.debug("escalate_verification_failure called with no failures/warnings. skip.")
        return True

    level = "FAILURE" if failure_count > 0 else "WARNING"

    logger.error(
        "escalate_verification_failure: level=%s failures=%d warnings=%d context=%s",
        level,
        failure_count,
        warning_count,
        context,
    )

    if dry_run:
        logger.info("escalate_verification_failure: dry_run=True, skip notification")
        return True

    lines = [
        f"level: {level}",
        f"failure_count: {failure_count}",
        f"warning_count: {warning_count}",
        f"generated_at: {report.get('generated_at', '')}",
    ]
    if context:
        for k, v in context.items():
            lines.append(f"{k}: {v}")
    if failures:
        lines.append("failures:")
        for f in failures[:5]:
            lines.append(f"  - [{f.get('check_name', '')}] {f.get('message', '')}")
        if len(failures) > 5:
            lines.append(f"  ... and {len(failures) - 5} more")

    success = False
    try:
        send_slack_block(f"[ESCALATE] 検証失敗 ({level})", lines)
        success = True
    except Exception as e:
        logger.warning("escalate_verification_failure: Slack notification failed: %s", e)

    return success
