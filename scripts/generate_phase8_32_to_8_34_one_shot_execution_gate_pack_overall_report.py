#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUTS = {
    "8-32": ROOT / "exchange/logs/phase8_32_final_execution_gate_decision_design_only_result.json",
    "8-33": ROOT / "exchange/logs/phase8_33_one_shot_lock_enforcement_abort_condition_design_only_result.json",
    "8-34": ROOT / "exchange/logs/phase8_34_post_run_evidence_contract_rollback_trigger_design_only_result.json",
}

OUTPUT_JSON = ROOT / "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.json"
OUTPUT_MD = ROOT / "exchange/logs/phase8_32_to_8_34_one_shot_execution_gate_pack_overall_report.md"

PASS_STATUS = "PHASE8_32_TO_8_34_ONE_SHOT_EXECUTION_GATE_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"

EXPECTED_PASS = {
    "8-32": "DESIGN_ONLY_FINAL_EXECUTION_GATE_SPEC_READY_NO_EXECUTION",
    "8-33": "DESIGN_ONLY_ONE_SHOT_LOCK_ABORT_SPEC_READY_NO_EXECUTION",
    "8-34": "DESIGN_ONLY_POST_RUN_EVIDENCE_ROLLBACK_SPEC_READY_NO_EXECUTION",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    phases = []
    missing = []
    passed = 0
    failed = 0

    all_design_only = True
    all_no_execution = True
    all_no_secret_leak = True
    all_no_lock_operation = True
    all_no_rollback_execution = True

    previous_phase8_29_to_8_31_pack_status = None
    previous_credentials_ready = False
    previous_credentials_not_ready = False
    credentials_blocked_reason_recorded = False

    finals: dict[str, str | None] = {}

    for phase, path in INPUTS.items():
        if not path.exists():
            missing.append(phase)
            failed += 1
            continue

        payload = _load_json(path)
        final_status = payload.get("final_status")
        finals[phase] = final_status
        phases.append({"phase": phase, "final_status": final_status})

        if final_status == EXPECTED_PASS[phase]:
            passed += 1
        else:
            failed += 1

        all_design_only = all_design_only and bool(payload.get("design_only", False))
        all_no_execution = all_no_execution and (payload.get("execution_allowed") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_api_call_attempted") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_write_executed") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_draft_created") is False)

        all_no_secret_leak = all_no_secret_leak and bool(payload.get("no_secret_leak_passed", False))
        all_no_lock_operation = all_no_lock_operation and (payload.get("lock_created") is False)
        all_no_lock_operation = all_no_lock_operation and (payload.get("lock_released") is False)
        all_no_rollback_execution = all_no_rollback_execution and (payload.get("rollback_executed") is False)

        if previous_phase8_29_to_8_31_pack_status is None:
            previous_phase8_29_to_8_31_pack_status = payload.get("previous_phase8_29_to_8_31_pack_status")
            previous_credentials_ready = bool(payload.get("previous_credentials_ready", False))
            previous_credentials_not_ready = bool(payload.get("previous_credentials_not_ready", False))

        reasons = payload.get("reasons", [])
        if any("previous_credentials_not_ready_blocked_reason_recorded" in str(r) for r in reasons):
            credentials_blocked_reason_recorded = True

    if missing:
        pack_status = "ABORT_MISSING_EVIDENCE"
    elif any((status or "").startswith("ABORT") or "FAIL" in (status or "") or "WARN" in (status or "") for status in finals.values()):
        pack_status = "ABORT_POLICY_VIOLATION"
    elif all_design_only and all_no_execution and all_no_secret_leak and all_no_lock_operation and all_no_rollback_execution:
        pack_status = PASS_STATUS
    else:
        pack_status = "ABORT_POLICY_VIOLATION"

    report = {
        "pack_name": "Phase 8-32〜8-34 One-shot execution gate pack",
        "pack_status": pack_status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "phase_count": 3,
        "passed_phase_count": passed,
        "failed_phase_count": failed,
        "phases": phases,
        "previous_phase8_29_to_8_31_pack_status": previous_phase8_29_to_8_31_pack_status,
        "previous_credentials_ready": previous_credentials_ready,
        "previous_credentials_not_ready": previous_credentials_not_ready,
        "credentials_blocked_reason_recorded": credentials_blocked_reason_recorded,
        "all_design_only": all_design_only,
        "all_no_execution": all_no_execution,
        "all_no_secret_leak": all_no_secret_leak,
        "all_no_lock_operation": all_no_lock_operation,
        "all_no_rollback_execution": all_no_rollback_execution,
        "wordpress_api_call_attempted": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "actual_go_decision_issued": False,
        "handoff_evidence_generated_for_execution": False,
        "lock_created": False,
        "lock_released": False,
        "rollback_executed": False,
        "next_step": "phase8_35_final_pre_execution_confirmation_or_dry_run_handoff",
        "generated_at": _now_iso(),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Phase 8-32〜8-34 One-shot Execution Gate Pack Overall Report",
        "",
        "## Final",
        f"- pack_status: {report['pack_status']}",
        f"- previous credentials ready: {report['previous_credentials_ready']}",
        f"- previous credentials not ready: {report['previous_credentials_not_ready']}",
        f"- blocked reason recorded: {report['credentials_blocked_reason_recorded']}",
        "",
        "## Safety",
        f"- production_status: {report['production_status']}",
        f"- execution: {report['execution']}",
        f"- DESIGN_ONLY: {report['all_design_only']}",
        f"- WordPress API call not executed: {not report['wordpress_api_call_attempted']}",
        f"- WordPress write not executed: {not report['wordpress_write_executed']}",
        f"- draft creation not executed: {not report['wordpress_draft_created']}",
        f"- lock_created=false: {report['lock_created'] is False}",
        f"- rollback_executed=false: {report['rollback_executed'] is False}",
        f"- production remains NO_GO: {report['production_status'] == 'NO_GO'}",
        "",
        "## Counts",
        f"- phase_count: {report['phase_count']}",
        f"- passed_phase_count: {report['passed_phase_count']}",
        f"- failed_phase_count: {report['failed_phase_count']}",
        "",
        "## Next step",
        f"- {report['next_step']}",
    ]
    OUTPUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if pack_status == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
