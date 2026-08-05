#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUTS = {
    "8-23": ROOT / "exchange/logs/phase8_23_post_credentials_ready_credential_revalidation_design_only_result.json",
    "8-24": ROOT / "exchange/logs/phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only_result.json",
    "8-25": ROOT / "exchange/logs/phase8_25_one_shot_execution_lock_rollback_post_run_evidence_design_only_result.json",
}

OUTPUT_JSON = ROOT / "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.json"
OUTPUT_MD = ROOT / "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.md"

PASS_STATUS = "PHASE8_23_TO_8_25_POST_CREDENTIALS_READY_PREPARATION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
EXPECTED_PHASE_STATUS = {
    "8-23": "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION",
    "8-24": "DESIGN_ONLY_FINAL_EXECUTION_AUTHORIZATION_SPEC_READY_NO_EXECUTION",
    "8-25": "DESIGN_ONLY_ONE_SHOT_LOCK_ROLLBACK_EVIDENCE_SPEC_READY_NO_EXECUTION",
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

    for phase, path in INPUTS.items():
        if not path.exists():
            missing.append(phase)
            failed += 1
            continue
        payload = _load_json(path)
        phases.append(
            {
                "phase": phase,
                "final_status": payload.get("final_status"),
            }
        )

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

    if missing:
        pack_status = "ABORT_MISSING_EVIDENCE"
    elif failed > 0:
        pack_status = "ABORT_POLICY_VIOLATION"
    elif all_design_only and all_no_execution and all_no_secret_leak:
        pack_status = PASS_STATUS
    else:
        pack_status = "ABORT_POLICY_VIOLATION"

    report = {
        "pack_name": "Phase 8-23〜8-25 Post-credentials-ready controlled execution preparation pack",
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
        "wordpress_api_call_attempted": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "next_step": "phase8_16_equivalent_credential_readiness_recheck_then_final_pre_execution_human_gate",
        "generated_at": _now_iso(),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Phase 8-23〜8-25 Post-credentials-ready Preparation Pack Overall Report",
        "",
        "## Final",
        f"- pack_status: {report['pack_status']}",
        "",
        "## Safety",
        f"- production_status: {report['production_status']}",
        f"- execution: {report['execution']}",
        f"- DESIGN_ONLY: {report['all_design_only']}",
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
