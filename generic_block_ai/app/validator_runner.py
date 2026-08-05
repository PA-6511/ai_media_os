"""
validator_runner.py  –  Phase 3.5-17

templates に対して各 validator を実行し、結果 dict を返します。
外部通信・自動実行・export は一切行いません。
ファイル書き込みはこのモジュール内では行いません（呼び出し元の責任）。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .proposal_validator import validate_proposal
from .review_queue_validator import validate_review_queue
from .evidence_index_validator import validate_evidence_index


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_all_validators(base_path: Path) -> dict[str, Any]:
    """
    base_path 配下の雛形 JSON に対して全 validator を実行し、
    結果をまとめた dict を返す。ファイル書き込みは行わない。
    """
    results: list[dict[str, Any]] = []

    checks = [
        (
            "proposal",
            base_path / "reports" / "phase35_proposal_package_template.json",
            validate_proposal,
        ),
        (
            "review_queue",
            base_path / "reports" / "phase35_review_queue_template.json",
            validate_review_queue,
        ),
        (
            "evidence_index",
            base_path / "evidence" / "phase35_evidence_index_template.json",
            validate_evidence_index,
        ),
    ]

    for name, path, validator in checks:
        if not path.exists():
            results.append(
                {
                    "target": name,
                    "file": str(path),
                    "result": "SKIP",
                    "reason": "file not found",
                    "failed_checks": [],
                    "warnings": [],
                }
            )
            continue

        data = _load_json(path)
        vr = validator(data)
        results.append(
            {
                "target": name,
                "file": str(path.relative_to(base_path)),
                "result": vr.result,
                "failed_checks": vr.failed_checks,
                "warnings": vr.warnings,
            }
        )

    overall = "PASS"
    for r in results:
        if r["result"] == "FAIL":
            overall = "FAIL"
            break
        if r["result"] in ("WARN", "SKIP"):
            overall = "WARN"

    return {
        "_meta": {
            "phase": "3.5-17",
            "purpose": "validator_execution_report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "auto_execute_allowed": False,
            "requires_human_approval": True,
        },
        "overall_result": overall,
        "validations": results,
    }
