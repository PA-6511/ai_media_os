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


SOURCE_FILES = {
    "phase_s4_validation_result": ROOT / "exchange" / "logs" / "security_block_ai_isolation_design_phase_s4_validation_result.json",
    "phase_s4_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_overall_result.json",
    "phase_s4_1_replay_result": ROOT / "exchange" / "logs" / "security_isolation_policy_dry_run_phase_s4_1_result.json",
    "phase_s4_1_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_1_overall_result.json",
    "phase_s4_2_replay_result": ROOT / "exchange" / "logs" / "security_isolation_event_simulation_phase_s4_2_result.json",
    "phase_s4_2_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_2_overall_result.json",
    "phase_s4_3_audit_result": ROOT / "exchange" / "logs" / "security_isolation_audit_design_review_phase_s4_3_result.json",
    "phase_s4_3_overall_result": ROOT / "exchange" / "logs" / "security_phase_s4_3_overall_result.json",
}

OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_overall_completion_report.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_overall_completion_report.md"


EXPECTED_STATUSES = {
    "phase_s4_validation_result": "PASS",
    "phase_s4_overall_result": "PASS",
    "phase_s4_1_replay_result": "PASS",
    "phase_s4_1_overall_result": "PASS_DRY_RUN_ONLY",
    "phase_s4_2_replay_result": "PASS",
    "phase_s4_2_overall_result": "PASS_DRY_RUN_ONLY",
    "phase_s4_3_audit_result": "PASS",
    "phase_s4_3_overall_result": "PASS_DRY_RUN_ONLY",
}

EXPECTED_FINAL_STATUSES = {
    "phase_s4_overall_result": "PASS_DESIGN_ONLY",
    "phase_s4_1_overall_result": "PASS_DRY_RUN_ONLY",
    "phase_s4_2_overall_result": "PASS_DRY_RUN_ONLY",
    "phase_s4_3_overall_result": "PASS_DRY_RUN_ONLY",
}


SUMMARY_FIELDS = [
    "phase_status",
    "execution",
    "production_status",
    "human_approval_required",
    "isolation_design_only",
    "isolation_recommendation_only",
    "simulation_only",
    "recommendation_only",
    "audit_view_only",
    "isolation_execution_allowed",
    "isolation_executed",
    "executor_action_allowed",
    "network_policy_applied",
    "container_stop_executed",
    "process_kill_executed",
    "firewall_applied",
    "scheduler_stop_executed",
    "wordpress_write_executed",
    "external_api_call_executed",
    "state_change_executed",
]


PHASE_FLAG_KEYS = {
    "phase_s4_1_overall_result": [
        "isolation_execution_allowed",
        "isolation_executed",
        "executor_action_allowed",
        "network_policy_applied",
        "container_stop_executed",
        "process_kill_executed",
        "firewall_applied",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
    ],
    "phase_s4_2_overall_result": [
        "isolation_execution_allowed",
        "isolation_executed",
        "executor_action_allowed",
        "freeze_execution_allowed",
        "freeze_executed",
        "network_policy_applied",
        "container_stop_executed",
        "process_kill_executed",
        "firewall_applied",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
    ],
    "phase_s4_3_overall_result": [
        "isolation_execution_allowed",
        "isolation_executed",
        "network_policy_applied",
        "container_stop_executed",
        "process_kill_executed",
        "firewall_applied",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
    ],
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


def generate_security_phase_s4_overall_completion_report(
    source_files: dict[str, Path] | None = None,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    source_files = source_files or SOURCE_FILES

    missing_sources: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}
    for name, path in source_files.items():
        if not Path(path).exists():
            missing_sources.append(_normalize(Path(path)))
            continue
        payloads[name] = _load_json(Path(path))

    source_statuses = {
        name: str(
            payload.get("audit_result")
            or payload.get("replay_result")
            or payload.get("validator_result")
            or payload.get("final_status")
            or payload.get("status")
            or ""
        )
        for name, payload in payloads.items()
    }
    mismatched_statuses = {
        name: {"expected": expected, "actual": source_statuses.get(name)}
        for name, expected in EXPECTED_STATUSES.items()
        if source_statuses.get(name) != expected
    }

    all_sources_present = len(missing_sources) == 0
    all_statuses_match = len(mismatched_statuses) == 0

    phase_s4_1 = payloads.get("phase_s4_1_overall_result", {})
    phase_s4_2 = payloads.get("phase_s4_2_overall_result", {})
    phase_s4_3 = payloads.get("phase_s4_3_overall_result", {})
    phase_s4_3_audit = payloads.get("phase_s4_3_audit_result", {})

    summary = {
        "phase_s4_validation_result": payloads.get("phase_s4_validation_result", {}).get("final_status"),
        "phase_s4_overall_result": payloads.get("phase_s4_overall_result", {}).get("final_status"),
        "phase_s4_1_final_status": phase_s4_1.get("final_status"),
        "phase_s4_1_matched_expected_count": int(phase_s4_1.get("matched_expected_count", 0)),
        "phase_s4_1_mismatched_expected_count": int(phase_s4_1.get("mismatched_expected_count", 0)),
        "phase_s4_2_final_status": phase_s4_2.get("final_status"),
        "phase_s4_2_scenario_count": int(phase_s4_2.get("scenario_count", 0)),
        "phase_s4_2_matched_expected_count": int(phase_s4_2.get("matched_expected_count", 0)),
        "phase_s4_2_mismatched_expected_count": int(phase_s4_2.get("mismatched_expected_count", 0)),
        "phase_s4_3_final_status": phase_s4_3.get("final_status"),
        "phase_s4_3_required_evidence_count": int(phase_s4_3.get("required_evidence_count", 0)),
        "phase_s4_3_found_evidence_count": int(phase_s4_3.get("found_evidence_count", 0)),
        "phase_s4_3_missing_evidence_count": int(phase_s4_3.get("missing_evidence_count", 0)),
        "phase_s4_3_audit_result": phase_s4_3_audit.get("audit_result"),
    }

    def _flags_are_false(payload: dict[str, Any], keys: list[str]) -> bool:
        return all(payload.get(key) is False for key in keys)

    execution_flags_ok = (
        _flags_are_false(phase_s4_1, PHASE_FLAG_KEYS["phase_s4_1_overall_result"])
        and _flags_are_false(phase_s4_2, PHASE_FLAG_KEYS["phase_s4_2_overall_result"])
        and _flags_are_false(phase_s4_3, PHASE_FLAG_KEYS["phase_s4_3_overall_result"])
    )

    recommendations_ok = bool(phase_s4_1.get("isolation_recommendation_detected", False)) and bool(phase_s4_1.get("human_review_recommendation_detected", False)) and bool(phase_s4_2.get("isolation_recommendation_detected", False)) and bool(phase_s4_2.get("freeze_recommendation_detected", False)) and bool(phase_s4_2.get("human_review_recommendation_detected", False))

    completion_ready = (
        all_sources_present
        and all_statuses_match
        and execution_flags_ok
        and recommendations_ok
        and phase_s4_1.get("final_status") == "PASS_DRY_RUN_ONLY"
        and phase_s4_2.get("final_status") == "PASS_DRY_RUN_ONLY"
        and phase_s4_3.get("final_status") == "PASS_DRY_RUN_ONLY"
        and phase_s4_2.get("scenario_count") == 7
        and phase_s4_2.get("matched_expected_count") == 7
        and phase_s4_2.get("mismatched_expected_count") == 0
        and phase_s4_3.get("required_evidence_count") == 6
        and phase_s4_3.get("found_evidence_count") == 6
        and phase_s4_3.get("missing_evidence_count") == 0
    )

    if not all_sources_present:
        final_status = "S4_COMPLETION_REVIEW_REQUIRED"
    elif not all_statuses_match:
        final_status = "S4_COMPLETION_REVIEW_REQUIRED"
    elif completion_ready:
        final_status = "PASS_DRY_RUN_ONLY"
    else:
        final_status = "S4_COMPLETION_REVIEW_REQUIRED"

    result = {
        "package_type": "security_phase_s4_overall_completion_report",
        "phase_id": "PHASE_S4",
        "phase_name": "block_ai_isolation_design",
        "title": "Security Phase S-4 Overall Completion Report",
        "phase_status": "DESIGN_ONLY",
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "summary": summary,
        "safety_flags": {
            "isolation_design_only": bool(payloads.get("phase_s4_overall_result", {}).get("isolation_design_only", True)),
            "isolation_execution_allowed": False,
            "isolation_executed": False,
            "executor_action_allowed": False,
            "isolation_recommendation_only": True,
            "simulation_only": True,
            "recommendation_only": True,
            "audit_view_only": True,
            "network_policy_applied": False,
            "container_stop_executed": False,
            "process_kill_executed": False,
            "firewall_applied": False,
            "scheduler_stop_executed": False,
            "wordpress_write_executed": False,
            "external_api_call_executed": False,
            "state_change_executed": False,
        },
        "source_files": {name: _normalize(Path(path)) for name, path in source_files.items()},
        "source_statuses": source_statuses,
        "mismatched_statuses": mismatched_statuses,
        "missing_sources": missing_sources,
        "decision": {
            "result": "S-4 remains restricted to design / dry-run / simulation / audit only.",
            "production_release": "NOT_ALLOWED",
            "next_step": "Phase S-4.4 final isolation design gate or keep NO_GO",
        },
        "created_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    source_rows = "\n".join(f"| {name} | `{path}` | `{source_statuses.get(name, '')}` |" for name, path in result["source_files"].items())
    mismatched_lines = "\n".join(f"- {name}: expected `{item['expected']}` got `{item['actual']}`" for name, item in mismatched_statuses.items()) or "- なし"
    missing_lines = "\n".join(f"- {item}" for item in missing_sources) or "- なし"

    lines = [
        "# Security Phase S-4 Overall Completion Report",
        "",
        "## Final Status",
        "",
        f"- Completion status: `{result['final_status']}`",
        f"- Production status: `{result['production_status']}`",
        f"- Execution: `{result['execution']}`",
        f"- Human approval required: `{result['human_approval_required']}`",
        "",
        "## Summary",
        "",
        f"- S-4 validation result: `{summary.get('phase_s4_validation_result')}`",
        f"- S-4 overall result: `{summary.get('phase_s4_overall_result')}`",
        f"- S-4.1 final status: `{summary.get('phase_s4_1_final_status')}`",
        f"- S-4.1 matched / mismatched: `{summary.get('phase_s4_1_matched_expected_count')}` / `{summary.get('phase_s4_1_mismatched_expected_count')}`",
        f"- S-4.2 final status: `{summary.get('phase_s4_2_final_status')}`",
        f"- S-4.2 scenario count: `{summary.get('phase_s4_2_scenario_count')}`",
        f"- S-4.2 matched / mismatched: `{summary.get('phase_s4_2_matched_expected_count')}` / `{summary.get('phase_s4_2_mismatched_expected_count')}`",
        f"- S-4.3 final status: `{summary.get('phase_s4_3_final_status')}`",
        f"- S-4.3 evidence count: `{summary.get('phase_s4_3_found_evidence_count')}` / `{summary.get('phase_s4_3_required_evidence_count')}`",
        f"- S-4.3 missing evidence: `{summary.get('phase_s4_3_missing_evidence_count')}`",
        f"- S-4.3 audit result: `{summary.get('phase_s4_3_audit_result')}`",
        "",
        "## Safety Flags",
        "",
        "| Flag | Value |",
        "|---|---|",
    ]
    for key, value in result["safety_flags"].items():
        lines.append(f"| {key} | `{value}` |")
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
        f"`{result['decision']['result']}`",
        "",
        f"- Production release: `{result['decision']['production_release']}`",
        f"- Next step: `{result['decision']['next_step']}`",
        "",
        "## Important Note",
        "",
        "This report does not authorize isolation execution, network policy application, container stop, process kill, firewall application, scheduler stop, WordPress write, external API call, or state changes.",
        "",
        f"Created at: `{result['created_at']}`",
        "",
    ])
    output_md_path.write_text("\n".join(lines), encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_phase_s4_overall_completion_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["final_status"] == "PASS_DRY_RUN_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
