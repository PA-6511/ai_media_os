#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUTS = {
    "8-29": ROOT / "exchange/logs/phase8_29_credential_readiness_recheck_no_secret_leak_gate_result.json",
    "8-30": ROOT / "exchange/logs/phase8_30_final_preflight_before_single_controlled_draft_creation_result.json",
    "8-31": ROOT / "exchange/logs/phase8_31_human_execution_approval_validation_handoff_result.json",
}

OUTPUT_JSON = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"
OUTPUT_MD = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.md"

PASS_READY = "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_READY_NO_EXECUTION"
PASS_NOT_READY = "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_NOT_READY_NO_EXECUTION"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    phases = []
    missing = []
    passed = 0
    failed = 0
    all_no_execution = True
    all_no_secret_leak = True
    credentials_ready = False
    credentials_not_ready = False

    finals: dict[str, str | None] = {}

    for phase, path in INPUTS.items():
        if not path.exists():
            missing.append(phase)
            failed += 1
            continue

        payload = _load_json(path)
        final_status = payload.get("final_status")
        phases.append({"phase": phase, "final_status": final_status})
        finals[phase] = final_status

        all_no_execution = all_no_execution and (payload.get("execution_allowed") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_api_call_attempted") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_write_executed") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_draft_created") is False)
        all_no_execution = all_no_execution and (payload.get("approve_draft_create_only_currently_allowed") is False)
        all_no_execution = all_no_execution and (payload.get("unlock_in_this_phase") is False)

        all_no_secret_leak = all_no_secret_leak and bool(payload.get("no_secret_leak_passed", False))

        if phase == "8-29":
            credentials_ready = bool(payload.get("credentials_ready", False))
            credentials_not_ready = bool(payload.get("credentials_not_ready", False))

    if missing:
        pack_status = "ABORT_MISSING_EVIDENCE"
    elif any((status or "").startswith("ABORT") or "FAIL" in (status or "") for status in finals.values()):
        pack_status = "ABORT_POLICY_VIOLATION"
    elif finals.get("8-29") == "CREDENTIAL_RECHECK_READY_NO_SECRET_LEAK_NO_EXECUTION" and finals.get("8-30") == "FINAL_PREFLIGHT_READY_BUT_NO_EXECUTION" and finals.get("8-31") == "HUMAN_APPROVAL_VALID_FOR_NEXT_PHASE_READY_BUT_NOT_EXECUTED":
        pack_status = PASS_READY
        passed = 3
    elif finals.get("8-29") == "CREDENTIAL_RECHECK_NOT_READY_NO_SECRET_OUTPUT_NO_EXECUTION" and finals.get("8-30") == "FINAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION" and finals.get("8-31") == "HUMAN_APPROVAL_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION":
        pack_status = PASS_NOT_READY
        passed = 3
    else:
        pack_status = "ABORT_POLICY_VIOLATION"

    if pack_status.startswith("ABORT"):
        failed = max(1, 3 - passed)

    report = {
        "pack_name": "Phase 8-29〜8-31 Credential recheck / final preflight / human execution approval pack",
        "pack_status": pack_status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "phase_count": 3,
        "passed_phase_count": passed,
        "failed_phase_count": failed,
        "credentials_ready": credentials_ready,
        "credentials_not_ready": credentials_not_ready,
        "phases": phases,
        "all_no_execution": all_no_execution,
        "all_no_secret_leak": all_no_secret_leak,
        "wordpress_api_call_attempted": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "actual_go_decision_issued": False,
        "handoff_evidence_generated_for_execution": False,
        "next_step": "phase8_next_one_shot_execution_gate_after_full_recheck_and_human_confirmation",
        "generated_at": _now_iso(),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Phase 8-29〜8-31 Pre-execution Approval Pack Overall Report",
        "",
        "## Scope",
        "- credential recheck",
        "- final preflight",
        "- human execution approval",
        "",
        "## Final",
        f"- pack_status: {report['pack_status']}",
        f"- credentials_ready: {report['credentials_ready']}",
        f"- credentials_not_ready: {report['credentials_not_ready']}",
        "",
        "## Safety",
        f"- production_status: {report['production_status']}",
        f"- execution: {report['execution']}",
        f"- WordPress API call not executed: {not report['wordpress_api_call_attempted']}",
        f"- WordPress write not executed: {not report['wordpress_write_executed']}",
        f"- draft creation not executed: {not report['wordpress_draft_created']}",
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
    return 0 if report["pack_status"] in {PASS_READY, PASS_NOT_READY} else 2


if __name__ == "__main__":
    raise SystemExit(main())
