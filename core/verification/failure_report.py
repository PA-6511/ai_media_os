"""failure_report.py — 検証失敗レポートの生成."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.verification.verification_result import VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)


def build_verification_failure_report(
    results: list[VerificationResult],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """検証結果リストから失敗レポートを生成して返す。

    Args:
        results: VerificationResult のリスト。
        context: 追加コンテキスト（row_id, pipeline 名など）。

    Returns:
        失敗レポート dict。failures が空のときも同じ形式で返す。
    """
    failures = [r for r in results if r.is_failure]
    warnings = [r for r in results if r.status == VerificationStatus.WARNING]

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(results),
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": [r.to_dict() for r in failures],
        "warnings": [r.to_dict() for r in warnings],
        "context": context or {},
    }

    if failures:
        logger.error(
            "verification_failure_report generated: failures=%d checks=%d context=%s",
            len(failures),
            len(results),
            context or {},
        )
    elif warnings:
        logger.warning(
            "verification_warning_report generated: warnings=%d checks=%d context=%s",
            len(warnings),
            len(results),
            context or {},
        )
    else:
        logger.info(
            "verification_report generated: all_ok checks=%d context=%s",
            len(results),
            context or {},
        )

    return report
