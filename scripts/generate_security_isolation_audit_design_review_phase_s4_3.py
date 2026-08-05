#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CONFIG_PATH = ROOT / "config" / "security_isolation_audit_design_review_phase_s4_3.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_isolation_audit_design_review_phase_s4_3_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_isolation_audit_design_review_phase_s4_3_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json object required")
    return data


def _flatten_required_evidence(required_evidence_files: dict[str, list[str]]) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for phase_name, paths in required_evidence_files.items():
        for rel_path in paths:
            items.append((phase_name, rel_path))
    return items


def generate_security_isolation_audit_design_review_phase_s4_3(
    config_path: Path = CONFIG_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    config = _load_json(Path(config_path))

    abort_reasons: list[str] = []
    fail_reasons: list[str] = []
    warnings: list[str] = []

    config_required_checks = {
        "status": "DESIGN_ONLY",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "audit_view_only": True,
        "simulation_only": True,
        "recommendation_only": True,
        "isolation_execution_allowed": False,
        "executor_action_allowed": False,
    }
    for key, expected in config_required_checks.items():
        if config.get(key) != expected:
            abort_reasons.append(f"config.{key} must be {expected!r}")

    actions = config.get("actions", {})
    for key in [
        "auto_isolation_execute",
        "network_policy_apply",
        "container_stop_execute",
        "process_kill_execute",
        "firewall_apply",
        "scheduler_stop_execute",
        "wordpress_write_execute",
        "external_api_call_execute",
        "state_change_execute",
    ]:
        if actions.get(key) is True:
            abort_reasons.append(f"config.actions.{key}=true is prohibited")

    required_items = _flatten_required_evidence(config.get("required_evidence_files", {}))
    required_evidence_count = len(required_items)
    found_evidence_count = 0
    missing_evidence_files: list[str] = []

    phase_summaries: dict[str, dict[str, Any]] = {}
    violated_invariants: list[str] = []

    required_invariants = config.get("required_invariants", {})

    payload_map: dict[str, dict[str, Any]] = {}
    for phase_name, rel_path in required_items:
        path = ROOT / rel_path
        if not path.exists():
            missing_evidence_files.append(rel_path)
            continue
        found_evidence_count += 1

        try:
            payload = _load_json(path)
        except Exception as exc:
            fail_reasons.append(f"json_parse_failed: {rel_path}: {exc}")
            continue

        payload_map[rel_path] = payload
        phase_summaries.setdefault(phase_name, {})[rel_path] = {
            "phase_id": payload.get("phase_id"),
            "status": payload.get("final_status") or payload.get("replay_result") or payload.get("validator_result"),
        }

        for key, expected in required_invariants.items():
            if key in payload and payload.get(key) != expected:
                violated_invariants.append(
                    f"{rel_path}:{key} expected {expected!r} got {payload.get(key)!r}"
                )

        for forbidden_true_key in [
            "isolation_executed",
            "network_policy_applied",
            "container_stop_executed",
            "process_kill_executed",
            "firewall_applied",
            "scheduler_stop_executed",
            "wordpress_write_executed",
            "external_api_call_executed",
            "state_change_executed",
        ]:
            if payload.get(forbidden_true_key) is True:
                abort_reasons.append(f"{rel_path}:{forbidden_true_key}=true detected")

    missing_evidence_count = len(missing_evidence_files)

    rules = config.get("required_status_rules", {})
    phase_s4_overall = payload_map.get("exchange/logs/security_phase_s4_overall_result.json", {})
    phase_s4_1_overall = payload_map.get("exchange/logs/security_phase_s4_1_overall_result.json", {})
    phase_s4_2_overall = payload_map.get("exchange/logs/security_phase_s4_2_overall_result.json", {})

    if phase_s4_overall.get("final_status") != rules.get("phase_s4_overall_final_status"):
        fail_reasons.append("phase_s4_overall_final_status mismatch")
    if phase_s4_1_overall.get("final_status") != rules.get("phase_s4_1_overall_final_status"):
        fail_reasons.append("phase_s4_1_overall_final_status mismatch")
    if phase_s4_2_overall.get("final_status") != rules.get("phase_s4_2_overall_final_status"):
        fail_reasons.append("phase_s4_2_overall_final_status mismatch")

    phase_s4_2_result = payload_map.get("exchange/logs/security_isolation_event_simulation_phase_s4_2_result.json", {})
    s4_2_required_metrics = config.get("phase_s4_2_required_metrics", {})
    for key, expected in s4_2_required_metrics.items():
        actual = phase_s4_2_result.get(key)
        if actual != expected:
            fail_reasons.append(f"phase_s4_2 metric mismatch: {key} expected {expected!r} got {actual!r}")

    if abort_reasons:
        audit_result = "ABORT"
    elif missing_evidence_count > 0 or fail_reasons or violated_invariants:
        audit_result = "FAIL"
    elif warnings:
        audit_result = "WARN"
    else:
        audit_result = "PASS"

    if audit_result == "ABORT":
        final_status = "ABORT"
    elif audit_result == "PASS":
        final_status = "PASS_DRY_RUN_ONLY"
    else:
        final_status = "ISOLATION_AUDIT_REVIEW_REQUIRED"

    result = {
        "phase_id": "PHASE_S4_3",
        "phase_name": "isolation_audit_design_review",
        "phase_status": "DESIGN_ONLY",
        "audit_result": audit_result,
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "audit_view_only": True,
        "simulation_only": True,
        "recommendation_only": True,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "network_policy_applied": False,
        "container_stop_executed": False,
        "process_kill_executed": False,
        "firewall_applied": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "required_evidence_count": required_evidence_count,
        "found_evidence_count": found_evidence_count,
        "missing_evidence_count": missing_evidence_count,
        "missing_evidence_files": missing_evidence_files,
        "phase_summaries": phase_summaries,
        "violated_invariants": violated_invariants,
        "warnings": warnings,
        "fail_reasons": fail_reasons,
        "abort_reasons": abort_reasons,
        "timestamp": _now_iso(),
        "next_step": "phase_s4_3_human_design_review_signoff_keep_no_go",
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Isolation Audit Design Review Phase S-4.3 Result",
        "",
        f"- audit_result: {result.get('audit_result')}",
        f"- final_status: {result.get('final_status')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- audit_view_only: {result.get('audit_view_only')}",
        f"- simulation_only: {result.get('simulation_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- required_evidence_count: {result.get('required_evidence_count')}",
        f"- found_evidence_count: {result.get('found_evidence_count')}",
        f"- missing_evidence_count: {result.get('missing_evidence_count')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
        "",
        "## missing_evidence_files",
    ]
    lines.extend([f"- {item}" for item in missing_evidence_files] or ["- none"])
    lines.extend(["", "## violated_invariants"])
    lines.extend([f"- {item}" for item in violated_invariants] or ["- none"])
    lines.extend(["", "## fail_reasons"])
    lines.extend([f"- {item}" for item in fail_reasons] or ["- none"])
    lines.extend(["", "## abort_reasons"])
    lines.extend([f"- {item}" for item in abort_reasons] or ["- none"])
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_isolation_audit_design_review_phase_s4_3()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["audit_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
