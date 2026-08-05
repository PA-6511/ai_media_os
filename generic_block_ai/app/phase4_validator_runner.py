"""
phase4_validator_runner.py  –  Phase 4-6

Phase 4 の JSON 成果物に対して validator を実行し、結果 dict を返します。
外部通信・自動実行・export は一切行いません。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .connection_test_result_validator import validate_connection_test_result
from .handoff_payload_validator import validate_handoff_payload


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_phase4_validators(base_path: Path) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    checks = [
        (
            "handoff_payload",
            base_path / "reports" / "phase4_2_decision_package_handoff_payload.json",
            validate_handoff_payload,
        ),
        (
            "connection_test_report",
            base_path / "reports" / "phase4_3_limited_connection_test_report.json",
            validate_connection_test_result,
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
        validation = validator(data)
        results.append(
            {
                "target": name,
                "file": str(path.relative_to(base_path)),
                "result": validation.result,
                "failed_checks": validation.failed_checks,
                "warnings": validation.warnings,
            }
        )

    overall = "PASS"
    for result in results:
        if result["result"] == "FAIL":
            overall = "FAIL"
            break
        if result["result"] in ("WARN", "SKIP"):
            overall = "WARN"

    return {
        "_meta": {
            "phase": "4-6",
            "purpose": "phase4_pass_evidence",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "operation_mode": "OBSERVE",
            "connection_test_mode": True,
            "connection_scope": "decision_package_handoff_only",
            "execution": "dry_run",
            "requires_human_approval": True,
            "auto_execute_allowed": False,
            "production_status": "NO_GO",
        },
        "overall_result": overall,
        "validations": results,
    }
