#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUTS = {
    "8-26": ROOT / "exchange/logs/phase8_26_credential_readiness_recheck_orchestration_design_only_result.json",
    "8-27": ROOT / "exchange/logs/phase8_27_final_no_go_go_decision_rule_design_only_result.json",
    "8-28": ROOT / "exchange/logs/phase8_28_final_pre_execution_handoff_evidence_design_only_result.json",
}

OUTPUT_JSON = ROOT / "exchange/logs/phase8_26_to_8_28_final_pre_execution_decision_pack_overall_report.json"
OUTPUT_MD = ROOT / "exchange/logs/phase8_26_to_8_28_final_pre_execution_decision_pack_overall_report.md"

PASS_STATUS = "PHASE8_26_TO_8_28_FINAL_PRE_EXECUTION_DECISION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
EXPECTED_PHASE_STATUS = {
    "8-26": "DESIGN_ONLY_CREDENTIAL_RECHECK_ORCHESTRATION_SPEC_READY_NO_EXECUTION",
    "8-27": "DESIGN_ONLY_FINAL_NO_GO_GO_DECISION_RULE_SPEC_READY_NO_EXECUTION",
    "8-28": "DESIGN_ONLY_FINAL_PRE_EXECUTION_HANDOFF_EVIDENCE_SPEC_READY_NO_EXECUTION",
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
    all_no_credential_actual_check = True

    for phase, path in INPUTS.items():
        if not path.exists():
            missing.append(phase)
            failed += 1
            continue

        payload = _load_json(path)
        phases.append({"phase": phase, "final_status": payload.get("final_status")})

        if payload.get("final_status") == EXPECTED_PHASE_STATUS[phase]:
            passed += 1
        else:
            failed += 1

        all_design_only = all_design_only and bool(payload.get("design_only", False))
        all_no_execution = all_no_execution and (payload.get("execution_allowed") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_api_call_attempted") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_write_executed") is False)
        all_no_execution = all_no_execution and (payload.get("wordpress_draft_created") is False)
        all_no_execution = all_no_execution and (payload.get("approve_draft_create_only_currently_allowed") is False)
        all_no_execution = all_no_execution and (payload.get("unlock_in_this_phase") is False)
        all_no_secret_leak = all_no_secret_leak and bool(payload.get("no_secret_leak_passed", False))
        all_no_credential_actual_check = all_no_credential_actual_check and (payload.get("credential_actual_check_executed") is False)
        all_no_credential_actual_check = all_no_credential_actual_check and (payload.get("os_environ_credential_read_executed") is False)
        all_no_credential_actual_check = all_no_credential_actual_check and (payload.get("actual_go_decision_issued") is False)
        all_no_credential_actual_check = all_no_credential_actual_check and (payload.get("handoff_evidence_generated_for_execution") is False)

    if missing:
        pack_status = "ABORT_MISSING_EVIDENCE"
    elif failed > 0:
        pack_status = "ABORT_POLICY_VIOLATION"
    elif all_design_only and all_no_execution and all_no_secret_leak and all_no_credential_actual_check:
        pack_status = PASS_STATUS
    else:
        pack_status = "ABORT_POLICY_VIOLATION"

    report = {
        "pack_name": "Phase 8-26〜8-28 Final pre-execution decision preparation pack",
        "pack_status": pack_status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "phase_count": 3,
        "passed_phase_count": passed,
        "failed_phase_count": failed,
        "phases": phases,
        "all_design_only": all_design_only,
        "all_no_execution": all_no_execution,
        "all_no_secret_leak": all_no_secret_leak,
        "all_no_credential_actual_check": all_no_credential_actual_check,
        "wordpress_api_call_attempted": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "credential_actual_check_executed": False,
        "os_environ_credential_read_executed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "actual_go_decision_issued": False,
        "handoff_evidence_generated_for_execution": False,
        "next_step": "phase8_16_equivalent_credential_readiness_recheck_or_final_preflight",
        "generated_at": _now_iso(),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Phase 8-26〜8-28 Final Pre-execution Decision Pack Overall Report",
        "",
        "## Final",
        f"- pack_status: {report['pack_status']}",
        "",
        "## Safety",
        f"- production_status: {report['production_status']}",
        f"- execution: {report['execution']}",
        f"- DESIGN_ONLY: {report['all_design_only']}",
        f"- credential actual check not executed: {report['credential_actual_check_executed'] is False}",
        f"- os.environ credential read not executed: {report['os_environ_credential_read_executed'] is False}",
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
    return 0 if pack_status == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
