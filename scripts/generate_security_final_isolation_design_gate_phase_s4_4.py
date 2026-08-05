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


CONFIG_PATH = ROOT / "config" / "security_final_isolation_design_gate_phase_s4_4.json"
SOURCE_FILES = {
    "phase_s4_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_overall_result.json",
    "phase_s4_completion_report": ROOT / "exchange" / "logs" / "security_phase_s4_overall_completion_report.json",
    "phase_s4_1_replay_result": ROOT / "exchange" / "logs" / "security_isolation_policy_dry_run_phase_s4_1_result.json",
    "phase_s4_1_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_1_overall_result.json",
    "phase_s4_2_replay_result": ROOT / "exchange" / "logs" / "security_isolation_event_simulation_phase_s4_2_result.json",
    "phase_s4_2_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_2_overall_result.json",
    "phase_s4_3_audit_result": ROOT / "exchange" / "logs" / "security_isolation_audit_design_review_phase_s4_3_result.json",
    "phase_s4_3_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_3_overall_result.json",
}
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_final_isolation_design_gate_phase_s4_4_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_final_isolation_design_gate_phase_s4_4_result.md"

EXPECTED_STATUSES = {
    "phase_s4_overall_result": "PASS",
    "phase_s4_completion_report": "PASS_DRY_RUN_ONLY",
    "phase_s4_1_replay_result": "PASS",
    "phase_s4_1_overall_result": "PASS_DRY_RUN_ONLY",
    "phase_s4_2_replay_result": "PASS",
    "phase_s4_2_overall_result": "PASS_DRY_RUN_ONLY",
    "phase_s4_3_audit_result": "PASS",
    "phase_s4_3_overall_result": "PASS_DRY_RUN_ONLY",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json object required")
    return data


def _normalize(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _status_of(payload: dict[str, Any]) -> str:
    return str(
        payload.get("gate_result")
        or payload.get("audit_result")
        or payload.get("replay_result")
        or payload.get("validator_result")
        or payload.get("final_status")
        or payload.get("status")
        or ""
    )


def generate_security_final_isolation_design_gate_phase_s4_4(
    config_path: Path = CONFIG_PATH,
    source_files: dict[str, Path] | None = None,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    config = _load_json(Path(config_path))
    source_files = source_files or SOURCE_FILES

    abort_reasons: list[str] = []
    fail_reasons: list[str] = []
    warnings: list[str] = []
    missing_evidence_files: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}
    required_evidence_files = config.get("required_evidence_files", {})
    required_evidence_paths: list[str] = []
    for paths in required_evidence_files.values():
        if isinstance(paths, list):
            required_evidence_paths.extend([str(path) for path in paths])

    required_evidence_count = len(required_evidence_paths)
    for rel_path in required_evidence_paths:
        path = ROOT / rel_path
        if not path.exists():
            missing_evidence_files.append(rel_path)
            continue
        try:
            payload = _load_json(path)
        except Exception as exc:
            fail_reasons.append(f"json_parse_failed: {rel_path}: {exc}")
            continue
        for name, source_path in source_files.items():
            if _normalize(Path(source_path)) == rel_path:
                payloads[name] = payload
                break

    found_evidence_count = len(required_evidence_paths) - len(missing_evidence_files) - sum(1 for item in fail_reasons if item.startswith("json_parse_failed:"))
    missing_evidence_count = len(missing_evidence_files)

    config_required_checks = {
        "phase_status": "DESIGN_ONLY",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "final_gate_only": True,
        "future_execution_allowed": False,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "executor_action_allowed": False,
    }
    for key, expected in config_required_checks.items():
        if config.get(key) != expected:
            abort_reasons.append(f"config.{key} must be {expected!r}")

    for key in [
        "network_policy_apply",
        "firewall_apply",
        "container_stop_execute",
        "process_kill_execute",
        "scheduler_stop_execute",
        "wordpress_write_execute",
        "external_api_call_execute",
        "state_change_execute",
        "auto_freeze_execute",
        "auto_revoke_execute",
        "auto_isolation_execute",
    ]:
        if config.get("actions", {}).get(key) is True:
            abort_reasons.append(f"config.actions.{key}=true is prohibited")

    required_invariants = config.get("required_invariants", {})
    for key, expected in required_invariants.items():
        if key in {"production_status", "execution", "human_approval_required", "final_gate_only", "future_execution_allowed", "isolation_execution_allowed", "isolation_executed", "executor_action_allowed", "network_policy_applied", "firewall_applied", "container_stop_executed", "process_kill_executed", "scheduler_stop_executed", "wordpress_write_executed", "external_api_call_executed", "state_change_executed", "auto_freeze_execute", "auto_revoke_execute", "auto_isolation_execute"}:
            continue

    source_statuses = {name: _status_of(payload) for name, payload in payloads.items()}
    mismatched_statuses = {
        name: {"expected": expected, "actual": source_statuses.get(name)}
        for name, expected in EXPECTED_STATUSES.items()
        if source_statuses.get(name) != expected
    }

    phase_s4_completion = payloads.get("phase_s4_completion_report", {})
    phase_s4_1_overall = payloads.get("phase_s4_1_overall_result", {})
    phase_s4_2_overall = payloads.get("phase_s4_2_overall_result", {})
    phase_s4_3_overall = payloads.get("phase_s4_3_overall_result", {})

    if phase_s4_completion.get("final_status") != "PASS_DRY_RUN_ONLY":
        fail_reasons.append("S-4 completion report final_status must be PASS_DRY_RUN_ONLY")
    if phase_s4_1_overall.get("final_status") != "PASS_DRY_RUN_ONLY":
        fail_reasons.append("S-4.1 overall final_status must be PASS_DRY_RUN_ONLY")
    if phase_s4_2_overall.get("final_status") != "PASS_DRY_RUN_ONLY":
        fail_reasons.append("S-4.2 overall final_status must be PASS_DRY_RUN_ONLY")
    if phase_s4_3_overall.get("final_status") != "PASS_DRY_RUN_ONLY":
        fail_reasons.append("S-4.3 overall final_status must be PASS_DRY_RUN_ONLY")

    s4_completion_verified = phase_s4_completion.get("final_status") == "PASS_DRY_RUN_ONLY" and phase_s4_completion.get("production_status") == "NO_GO" and phase_s4_completion.get("execution") == "DRY_RUN"

    future_execution_allowed = bool(config.get("future_execution_allowed", False))
    isolation_design_ready = bool(s4_completion_verified and not future_execution_allowed and missing_evidence_count == 0 and len(mismatched_statuses) == 0)

    gate_result: str
    if abort_reasons:
        gate_result = "ABORT"
    elif missing_evidence_count > 0 or fail_reasons or mismatched_statuses:
        gate_result = "FAIL"
    elif warnings:
        gate_result = "WARN"
    else:
        gate_result = "PASS"

    if gate_result == "PASS":
        final_status = "PASS_DESIGN_GATE_ONLY"
    elif gate_result == "ABORT":
        final_status = "ABORT"
    else:
        final_status = "DESIGN_GATE_REVIEW_REQUIRED"

    result = {
        "phase_id": "PHASE_S4_4",
        "phase_name": "final_isolation_design_gate",
        "phase_status": "DESIGN_ONLY",
        "gate_result": gate_result,
        "final_status": final_status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "final_gate_only": True,
        "s4_completion_verified": s4_completion_verified,
        "required_evidence_count": required_evidence_count,
        "found_evidence_count": found_evidence_count,
        "missing_evidence_count": missing_evidence_count,
        "missing_evidence_files": missing_evidence_files,
        "isolation_design_ready": isolation_design_ready,
        "future_execution_allowed": False,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "network_policy_applied": False,
        "firewall_applied": False,
        "container_stop_executed": False,
        "process_kill_executed": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "executor_action_allowed": False,
        "abort_reasons": abort_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "source_files": {name: _normalize(Path(path)) for name, path in source_files.items()},
        "source_statuses": source_statuses,
        "mismatched_statuses": mismatched_statuses,
        "next_step": "pause_before_execution_or_prepare_s5_design_only",
        "created_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    source_rows = "\n".join(f"| {name} | `{path}` | `{source_statuses.get(name, '')}` |" for name, path in result["source_files"].items())
    mismatched_lines = "\n".join(f"- {name}: expected `{item['expected']}` got `{item['actual']}`" for name, item in mismatched_statuses.items()) or "- なし"
    missing_lines = "\n".join(f"- {item}" for item in missing_evidence_files) or "- なし"

    lines = [
        "# Security Final Isolation Design Gate Phase S-4.4 Result",
        "",
        "## Final Status",
        "",
        f"- gate_result: `{result['gate_result']}`",
        f"- final_status: `{result['final_status']}`",
        f"- production_status: `{result['production_status']}`",
        f"- execution: `{result['execution']}`",
        f"- human_approval_required: `{result['human_approval_required']}`",
        f"- final_gate_only: `{result['final_gate_only']}`",
        f"- s4_completion_verified: `{result['s4_completion_verified']}`",
        f"- isolation_design_ready: `{result['isolation_design_ready']}`",
        f"- future_execution_allowed: `{result['future_execution_allowed']}`",
        "",
        "## Evidence",
        "",
        f"- required_evidence_count: `{result['required_evidence_count']}`",
        f"- found_evidence_count: `{result['found_evidence_count']}`",
        f"- missing_evidence_count: `{result['missing_evidence_count']}`",
        "",
        "## Safety Flags",
        "",
        "| Flag | Value |",
        "|---|---|",
    ]
    for key in [
        "isolation_execution_allowed",
        "isolation_executed",
        "network_policy_applied",
        "firewall_applied",
        "container_stop_executed",
        "process_kill_executed",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
        "executor_action_allowed",
    ]:
        lines.append(f"| {key} | `{result[key]}` |")
    lines.extend([
        "",
        "## Evidence Sources",
        "",
        "| Evidence | Path | Status |",
        "|---|---|---|",
        source_rows,
        "",
        "## Mismatched Statuses",
        mismatched_lines,
        "",
        "## Missing Sources",
        missing_lines,
        "",
        "## Decision",
        "",
        "`Final Isolation Design Gate is satisfied; keep NO_GO and do not execute.`",
        "",
        f"- Next step: `{result['next_step']}`",
        "",
        f"Created at: `{result['created_at']}`",
        "",
    ])
    output_md_path.write_text("\n".join(lines), encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_final_isolation_design_gate_phase_s4_4()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["gate_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
