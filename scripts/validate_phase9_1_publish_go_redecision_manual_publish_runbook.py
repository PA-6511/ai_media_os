#!/usr/bin/env python3
"""Validate Phase 9-1 runbook structure and NO_GO constraints."""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

INPUT_RUNBOOK = LOG_DIR / "phase9_1_publish_go_redecision_manual_publish_runbook.json"
INPUT_GENERATION = LOG_DIR / "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result.json"
OUT_VALIDATION = LOG_DIR / "phase9_1_publish_go_redecision_manual_publish_runbook_validation_result.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _abort(reason: str) -> int:
    result = {
        "package_type": "phase9_1_publish_go_redecision_manual_publish_runbook_validation_result",
        "phase": "Phase 9-1",
        "status": "ABORT",
        "reason": reason,
        "runbook_valid": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write(OUT_VALIDATION, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1


def main() -> int:
    if not INPUT_RUNBOOK.exists() or not INPUT_GENERATION.exists():
        return _abort("required phase9_1 files not found")

    runbook = _load(INPUT_RUNBOOK)
    generation = _load(INPUT_GENERATION)

    checks = [
        {
            "check": "generation_status=PASS",
            "passed": generation.get("status") == "PASS",
            "actual": generation.get("status"),
        },
        {
            "check": "runbook_status=PASS",
            "passed": runbook.get("status") == "PASS",
            "actual": runbook.get("status"),
        },
        {
            "check": "phase8_final_decision=KEEP_NO_GO",
            "passed": runbook.get("phase8_final_decision") == "KEEP_NO_GO",
            "actual": runbook.get("phase8_final_decision"),
        },
        {
            "check": "target_draft_id=110",
            "passed": runbook.get("target_draft_id") == 110,
            "actual": runbook.get("target_draft_id"),
        },
        {
            "check": "target_draft_status=draft",
            "passed": runbook.get("target_draft_status") == "draft",
            "actual": runbook.get("target_draft_status"),
        },
        {
            "check": "manual_publish_executable_now=false",
            "passed": runbook.get("manual_publish_executable_now") is False,
            "actual": runbook.get("manual_publish_executable_now"),
        },
        {
            "check": "publish_execution_started=false",
            "passed": runbook.get("publish_execution_started") is False,
            "actual": runbook.get("publish_execution_started"),
        },
        {
            "check": "wordpress_publish_execution=NO_GO",
            "passed": runbook.get("wordpress_publish_execution") == "NO_GO",
            "actual": runbook.get("wordpress_publish_execution"),
        },
        {
            "check": "wordpress_write_executed=false",
            "passed": runbook.get("wordpress_write_executed") is False,
            "actual": runbook.get("wordpress_write_executed"),
        },
        {
            "check": "fixed_manual_procedure_count>=10",
            "passed": isinstance(runbook.get("fixed_manual_procedure"), list)
            and len(runbook.get("fixed_manual_procedure", [])) >= 10,
            "actual": len(runbook.get("fixed_manual_procedure", []))
            if isinstance(runbook.get("fixed_manual_procedure"), list)
            else None,
        },
        {
            "check": "forbidden_in_phase9_1_count>=10",
            "passed": isinstance(runbook.get("forbidden_in_phase9_1"), list)
            and len(runbook.get("forbidden_in_phase9_1", [])) >= 10,
            "actual": len(runbook.get("forbidden_in_phase9_1", []))
            if isinstance(runbook.get("forbidden_in_phase9_1"), list)
            else None,
        },
        {
            "check": "next_step_defined",
            "passed": bool(runbook.get("next_step")),
            "actual": runbook.get("next_step"),
        },
    ]

    failed = [c for c in checks if not c["passed"]]
    all_passed = len(failed) == 0

    result = {
        "package_type": "phase9_1_publish_go_redecision_manual_publish_runbook_validation_result",
        "phase": "Phase 9-1",
        "status": "PASS" if all_passed else "ABORT",
        "reason": (
            "phase9_1 runbook validated with no-go and no-write constraints"
            if all_passed
            else f"validation failed: {[f['check'] for f in failed]}"
        ),
        "runbook_valid": all_passed,
        "target_draft_id": runbook.get("target_draft_id"),
        "target_draft_status": runbook.get("target_draft_status"),
        "decision": runbook.get("phase8_final_decision"),
        "publish_execution_started": runbook.get("publish_execution_started"),
        "wordpress_publish_execution": runbook.get("wordpress_publish_execution"),
        "wordpress_write_executed": runbook.get("wordpress_write_executed"),
        "checks": checks,
        "all_checks_passed": all_passed,
        "next_step": runbook.get("next_step"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write(OUT_VALIDATION, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
