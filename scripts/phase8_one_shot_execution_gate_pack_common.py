#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASE816_RESULT = "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json"
PHASE816_REPORT = "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.json"
PHASE817_RESULT = "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_result.json"
PHASE817_REPORT = "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_report.json"
PACK1822_REPORT = "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.json"
PACK2325_REPORT = "exchange/logs/phase8_23_to_8_25_post_credentials_ready_preparation_pack_overall_report.json"
PACK2628_REPORT = "exchange/logs/phase8_26_to_8_28_final_pre_execution_decision_pack_overall_report.json"
PACK2931_REPORT = "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"

EXPECTED_1822 = "PHASE8_18_TO_8_22_PREPARATION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
EXPECTED_2325 = "PHASE8_23_TO_8_25_POST_CREDENTIALS_READY_PREPARATION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
EXPECTED_2628 = "PHASE8_26_TO_8_28_FINAL_PRE_EXECUTION_DECISION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"
EXPECTED_2931_READY = "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_READY_NO_EXECUTION"
EXPECTED_2931_NOT_READY = "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_NOT_READY_NO_EXECUTION"

GLOBAL_FALSE_FLAGS = {
    "execution_allowed": False,
    "wordpress_api_call_allowed": False,
    "wordpress_api_call_attempted": False,
    "wordpress_write_allowed": False,
    "wordpress_write_executed": False,
    "wordpress_draft_created": False,
    "publish_allowed": False,
    "update_allowed": False,
    "delete_allowed": False,
    "bulk_action_allowed": False,
    "export_allowed": False,
    "auto_post": False,
    "auto_update": False,
    "auto_delete": False,
    "auto_export": False,
    "approve_draft_create_only_currently_allowed": False,
    "unlock_in_this_phase": False,
    "executor_action_allowed": False,
    "actual_go_decision_issued": False,
    "handoff_evidence_generated_for_execution": False,
    "lock_created": False,
    "lock_released": False,
    "rollback_executed": False,
    "secret_values_output": False,
    "secret_values_written": False,
    "secret_values_logged": False,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_root(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def scan_value_strings(payload: Any, markers: list[str], findings: list[str], path: str = "root") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            scan_value_strings(value, markers, findings, f"{path}.{key}")
        return

    if isinstance(payload, list):
        for idx, value in enumerate(payload):
            scan_value_strings(value, markers, findings, f"{path}[{idx}]")
        return

    if isinstance(payload, str):
        lowered = payload.lower()
        if any(marker in lowered for marker in markers):
            findings.append(f"forbidden_value:{path}")


def required_evidence() -> list[str]:
    return [
        PHASE816_RESULT,
        PHASE816_REPORT,
        PHASE817_RESULT,
        PHASE817_REPORT,
        PACK1822_REPORT,
        PACK2325_REPORT,
        PACK2628_REPORT,
        PACK2931_REPORT,
    ]


def load_required_evidence(root: Path) -> tuple[bool, dict[str, Any], list[str]]:
    missing: list[str] = []
    payloads: dict[str, Any] = {}
    for rel in required_evidence():
        p = root / rel
        if not p.exists():
            missing.append(rel)
        elif p.suffix == ".json":
            payloads[rel] = load_json(p)
    return len(missing) == 0, payloads, missing


def validate_previous_evidence(payloads: dict[str, Any], violations: list[str]) -> dict[str, Any]:
    p816 = payloads.get(PHASE816_RESULT, {})
    p817 = payloads.get(PHASE817_RESULT, {})
    p1822 = payloads.get(PACK1822_REPORT, {})
    p2325 = payloads.get(PACK2325_REPORT, {})
    p2628 = payloads.get(PACK2628_REPORT, {})
    p2931 = payloads.get(PACK2931_REPORT, {})

    previous_status = p2931.get("pack_status")
    previous_ready = bool(p2931.get("credentials_ready", False))
    previous_not_ready = bool(p2931.get("credentials_not_ready", False))

    if p1822 and p1822.get("final_status") != EXPECTED_1822:
        violations.append("phase8_18_to_8_22 pack status is not accepted")
    if p2325 and p2325.get("pack_status") != EXPECTED_2325:
        violations.append("phase8_23_to_8_25 pack status is not accepted")
    if p2628 and p2628.get("pack_status") != EXPECTED_2628:
        violations.append("phase8_26_to_8_28 pack status is not accepted")

    if p2931 and previous_status not in {EXPECTED_2931_READY, EXPECTED_2931_NOT_READY}:
        violations.append("phase8_29_to_8_31 pack status is not accepted")

    return {
        "previous_phase8_16_final_status": p816.get("final_status"),
        "previous_phase8_17_final_status": p817.get("final_status"),
        "previous_phase8_18_to_8_22_pack_status": p1822.get("final_status"),
        "previous_phase8_23_to_8_25_pack_status": p2325.get("pack_status"),
        "previous_phase8_26_to_8_28_pack_status": p2628.get("pack_status"),
        "previous_phase8_29_to_8_31_pack_status": previous_status,
        "previous_credentials_ready": previous_ready,
        "previous_credentials_not_ready": previous_not_ready,
    }


def base_result(phase: str, phase_name: str) -> dict[str, Any]:
    return {
        "phase": phase,
        "phase_name": phase_name,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "design_only": True,
        "previous_evidence_found": False,
        "previous_phase8_16_final_status": None,
        "previous_phase8_17_final_status": None,
        "previous_phase8_18_to_8_22_pack_status": None,
        "previous_phase8_23_to_8_25_pack_status": None,
        "previous_phase8_26_to_8_28_pack_status": None,
        "previous_phase8_29_to_8_31_pack_status": None,
        "previous_credentials_ready": False,
        "previous_credentials_not_ready": False,
        "target_item_count": 1,
        **GLOBAL_FALSE_FLAGS,
        "no_secret_leak_passed": True,
        "reasons": [],
        "policy_violations": [],
        "secret_leak_findings": [],
        "next_step": "abort_without_execution",
    }


def build_phase_report(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": result.get("phase"),
        "phase_name": result.get("phase_name"),
        "final_status": result.get("final_status"),
        "production_status": result.get("production_status"),
        "execution": result.get("execution"),
        "design_only": bool(result.get("design_only", True)),
        "previous_evidence_found": bool(result.get("previous_evidence_found", False)),
        "previous_credentials_ready": bool(result.get("previous_credentials_ready", False)),
        "previous_credentials_not_ready": bool(result.get("previous_credentials_not_ready", False)),
        "execution_allowed": False,
        "wordpress_api_call_not_executed": not bool(result.get("wordpress_api_call_attempted", False)),
        "wordpress_write_not_executed": not bool(result.get("wordpress_write_executed", False)),
        "draft_creation_not_executed": not bool(result.get("wordpress_draft_created", False)),
        "actual_go_decision_issued": False,
        "handoff_evidence_generated_for_execution": False,
        "lock_created": False,
        "lock_released": False,
        "rollback_executed": False,
        "no_secret_values_output": result.get("secret_values_output") is False
        and result.get("secret_values_written") is False
        and result.get("secret_values_logged") is False,
        "next_step": result.get("next_step"),
        "generated_at": now_iso(),
    }


def build_phase_report_md(report: dict[str, Any], title: str) -> str:
    lines = [
        f"# {title}",
        "",
        "## Phase summary",
        "- This phase is design-only and does not execute WordPress operations.",
        "",
        "## Status",
        f"- final_status: {report.get('final_status')}",
        f"- production_status: {report.get('production_status')}",
        f"- execution: {report.get('execution')}",
        f"- design_only: {report.get('design_only')}",
        f"- previous_evidence_found: {report.get('previous_evidence_found')}",
        f"- previous credentials ready: {report.get('previous_credentials_ready')}",
        f"- previous credentials not ready: {report.get('previous_credentials_not_ready')}",
        "",
        "## Safety",
        f"- execution_allowed=false: {report.get('execution_allowed') is False}",
        f"- WordPress API call not executed: {report.get('wordpress_api_call_not_executed')}",
        f"- WordPress write not executed: {report.get('wordpress_write_not_executed')}",
        f"- draft creation not executed: {report.get('draft_creation_not_executed')}",
        f"- actual_go_decision_issued=false: {report.get('actual_go_decision_issued') is False}",
        f"- handoff_evidence_generated_for_execution=false: {report.get('handoff_evidence_generated_for_execution') is False}",
        f"- lock_created=false: {report.get('lock_created') is False}",
        f"- lock_released=false: {report.get('lock_released') is False}",
        f"- rollback_executed=false: {report.get('rollback_executed') is False}",
        f"- production remains NO_GO: {report.get('production_status') == 'NO_GO'}",
        f"- no secret values output: {report.get('no_secret_values_output')}",
        "",
        "## Next step",
        f"- {report.get('next_step')}",
    ]
    return "\n".join(lines) + "\n"
