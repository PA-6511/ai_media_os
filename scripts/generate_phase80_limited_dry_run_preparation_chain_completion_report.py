#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "exchange" / "logs" / "phase79_limited_dry_run_final_go_no_go_planning_report.json"
DEFAULT_OUTPUT = ROOT / "exchange" / "logs" / "phase80_limited_dry_run_preparation_chain_completion_report.json"

EXPECTED_EVIDENCE = {
    "phase66_go_no_go_report_reference",
    "preparation_scope_statement",
    "target_files_manifest",
    "sandbox_scope_confirmation",
    "single_file_scope_confirmation",
    "dry_run_mode_confirmation",
    "non_execution_confirmation",
}

CHAIN_SPECS = [
    {
        "phase": "Phase 68",
        "file": "phase68_preparation_review_report.json",
        "input_file": "phase67_preparation_evidence_report.json",
        "package_type": "phase68_preparation_review_report",
        "status_field": "review_status",
        "controls_key": "review_controls",
        "evidence_key": "review_evidence_checks",
        "gate_key": "manual_review_gate",
        "expected_decision": "ALLOW_PHASE69_READINESS_REVIEW_ONLY",
        "readiness_key": "phase69_readiness",
        "readiness_status": "READY_FOR_PHASE69_READINESS_REVIEW_ONLY",
    },
    {
        "phase": "Phase 69",
        "file": "phase69_preparation_approval_report.json",
        "input_file": "phase68_preparation_review_report.json",
        "package_type": "phase69_preparation_approval_report",
        "status_field": "approval_status",
        "controls_key": "approval_controls",
        "evidence_key": "approval_evidence_checks",
        "gate_key": "manual_approval_gate",
        "expected_decision": "ALLOW_PHASE70_PLANNING_ONLY",
        "readiness_key": "phase70_readiness",
        "readiness_status": "READY_FOR_PHASE70_PLANNING_ONLY",
    },
    {
        "phase": "Phase 70",
        "file": "phase70_preparation_final_review_report.json",
        "input_file": "phase69_preparation_approval_report.json",
        "package_type": "phase70_preparation_final_review_report",
        "status_field": "final_review_status",
        "controls_key": "final_review_controls",
        "evidence_key": "final_review_evidence_checks",
        "gate_key": "manual_final_review_gate",
        "expected_decision": "ALLOW_PHASE71_PLANNING_ONLY",
        "readiness_key": "phase71_readiness",
        "readiness_status": "READY_FOR_PHASE71_PLANNING_ONLY",
    },
    {
        "phase": "Phase 71",
        "file": "phase71_preparation_final_approval_report.json",
        "input_file": "phase70_preparation_final_review_report.json",
        "package_type": "phase71_preparation_final_approval_report",
        "status_field": "final_approval_status",
        "controls_key": "final_approval_controls",
        "evidence_key": "final_approval_evidence_checks",
        "gate_key": "manual_final_approval_gate",
        "expected_decision": "ALLOW_PHASE72_PLANNING_ONLY",
        "readiness_key": "phase72_readiness",
        "readiness_status": "READY_FOR_PHASE72_PLANNING_ONLY",
    },
    {
        "phase": "Phase 72",
        "file": "phase72_preparation_final_signoff_report.json",
        "input_file": "phase71_preparation_final_approval_report.json",
        "package_type": "phase72_preparation_final_signoff_report",
        "status_field": "final_signoff_status",
        "controls_key": "final_signoff_controls",
        "evidence_key": "final_signoff_evidence_checks",
        "gate_key": "manual_final_signoff_gate",
        "expected_decision": "ALLOW_PHASE73_PLANNING_ONLY",
        "readiness_key": "phase73_readiness",
        "readiness_status": "READY_FOR_PHASE73_PLANNING_ONLY",
    },
    {
        "phase": "Phase 73",
        "file": "phase73_preparation_lock_report.json",
        "input_file": "phase72_preparation_final_signoff_report.json",
        "package_type": "phase73_preparation_lock_report",
        "status_field": "lock_status",
        "controls_key": "lock_controls",
        "evidence_key": "lock_evidence_checks",
        "gate_key": "manual_lock_gate",
        "expected_decision": "ALLOW_PHASE74_PLANNING_ONLY",
        "readiness_key": "phase74_readiness",
        "readiness_status": "READY_FOR_PHASE74_PLANNING_ONLY",
    },
    {
        "phase": "Phase 74",
        "file": "phase74_limited_dry_run_sandbox_plan_report.json",
        "input_file": "phase73_preparation_lock_report.json",
        "package_type": "phase74_limited_dry_run_sandbox_plan_report",
        "status_field": "sandbox_plan_status",
        "controls_key": "sandbox_plan_controls",
        "evidence_key": "sandbox_plan_evidence_checks",
        "gate_key": "manual_sandbox_plan_gate",
        "expected_decision": "ALLOW_PHASE75_PLANNING_ONLY",
        "readiness_key": "phase75_readiness",
        "readiness_status": "READY_FOR_PHASE75_PLANNING_ONLY",
    },
    {
        "phase": "Phase 75",
        "file": "phase75_limited_dry_run_fixture_plan_report.json",
        "input_file": "phase74_limited_dry_run_sandbox_plan_report.json",
        "package_type": "phase75_limited_dry_run_fixture_plan_report",
        "status_field": "fixture_plan_status",
        "controls_key": "fixture_plan_controls",
        "evidence_key": "fixture_plan_evidence_checks",
        "gate_key": "manual_fixture_plan_gate",
        "expected_decision": "ALLOW_PHASE76_PLANNING_ONLY",
        "readiness_key": "phase76_readiness",
        "readiness_status": "READY_FOR_PHASE76_PLANNING_ONLY",
    },
    {
        "phase": "Phase 76",
        "file": "phase76_limited_dry_run_rollback_plan_report.json",
        "input_file": "phase75_limited_dry_run_fixture_plan_report.json",
        "package_type": "phase76_limited_dry_run_rollback_plan_report",
        "status_field": "rollback_plan_status",
        "controls_key": "rollback_plan_controls",
        "evidence_key": "rollback_plan_evidence_checks",
        "gate_key": "manual_rollback_plan_gate",
        "expected_decision": "ALLOW_PHASE77_PLANNING_ONLY",
        "readiness_key": "phase77_readiness",
        "readiness_status": "READY_FOR_PHASE77_PLANNING_ONLY",
    },
    {
        "phase": "Phase 77",
        "file": "phase77_limited_dry_run_evidence_plan_report.json",
        "input_file": "phase76_limited_dry_run_rollback_plan_report.json",
        "package_type": "phase77_limited_dry_run_evidence_plan_report",
        "status_field": "evidence_plan_status",
        "controls_key": "evidence_plan_controls",
        "evidence_key": "evidence_plan_evidence_checks",
        "gate_key": "manual_evidence_plan_gate",
        "expected_decision": "ALLOW_PHASE78_PLANNING_ONLY",
        "readiness_key": "phase78_readiness",
        "readiness_status": "READY_FOR_PHASE78_PLANNING_ONLY",
    },
    {
        "phase": "Phase 78",
        "file": "phase78_limited_dry_run_operator_checklist_report.json",
        "input_file": "phase77_limited_dry_run_evidence_plan_report.json",
        "package_type": "phase78_limited_dry_run_operator_checklist_report",
        "status_field": "operator_checklist_status",
        "controls_key": "operator_checklist_controls",
        "evidence_key": "operator_checklist_evidence_checks",
        "gate_key": "manual_operator_checklist_gate",
        "expected_decision": "ALLOW_PHASE79_PLANNING_ONLY",
        "readiness_key": "phase79_readiness",
        "readiness_status": "READY_FOR_PHASE79_PLANNING_ONLY",
    },
    {
        "phase": "Phase 79",
        "file": "phase79_limited_dry_run_final_go_no_go_planning_report.json",
        "input_file": "phase78_limited_dry_run_operator_checklist_report.json",
        "package_type": "phase79_limited_dry_run_final_go_no_go_planning_report",
        "status_field": "final_go_no_go_planning_status",
        "controls_key": "final_go_no_go_planning_controls",
        "evidence_key": "final_go_no_go_planning_evidence_checks",
        "gate_key": "manual_final_go_no_go_planning_gate",
        "expected_decision": "ALLOW_PHASE80_PLANNING_ONLY",
        "readiness_key": "phase80_readiness",
        "readiness_status": "READY_FOR_PHASE80_PLANNING_ONLY",
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def abort_result(reason: str) -> dict:
    return {
        "package_type": "phase80_limited_dry_run_preparation_chain_completion_report_result",
        "phase": "Phase 80",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_report_common(report: dict, spec: dict) -> str | None:
    if report.get("phase") != spec["phase"]:
        return f"{spec['phase']} phase mismatch"
    if report.get("package_type") != spec["package_type"]:
        return f"{spec['phase']} package_type mismatch"
    if report.get("status") != "PASS":
        return f"{spec['phase']} status must be PASS"
    if report.get(spec["status_field"]) != "PASS":
        return f"{spec['phase']} {spec['status_field']} must be PASS"
    if report.get("mode") != "DRY_RUN":
        return f"{spec['phase']} mode must be DRY_RUN"
    if report.get("human_approval_required") is not True:
        return f"{spec['phase']} human_approval_required must be true"
    if report.get("can_execute") is not False:
        return f"{spec['phase']} can_execute must be false"
    if report.get("execute_allowed") is not False:
        return f"{spec['phase']} execute_allowed must be false"
    if report.get("max_files_to_execute") != 1:
        return f"{spec['phase']} max_files_to_execute must be 1"
    if report.get("sandbox_scope_required") is not True:
        return f"{spec['phase']} sandbox_scope_required must be true"
    if report.get("single_file_scope_required") is not True:
        return f"{spec['phase']} single_file_scope_required must be true"

    controls = report.get(spec["controls_key"], {})
    if controls.get("does_not_execute") is not True:
        return f"{spec['phase']} {spec['controls_key']}.does_not_execute must be true"

    evidence_checks = report.get(spec["evidence_key"], {})
    if evidence_checks.get("does_not_execute") is not True:
        return f"{spec['phase']} {spec['evidence_key']}.does_not_execute must be true"
    required_evidence = evidence_checks.get("required_evidence", [])
    if not EXPECTED_EVIDENCE.issubset(set(required_evidence)):
        return f"{spec['phase']} required_evidence is missing one or more required entries"

    gate = report.get(spec["gate_key"], {})
    if gate.get("does_not_execute") is not True:
        return f"{spec['phase']} {spec['gate_key']}.does_not_execute must be true"
    if spec["expected_decision"] not in gate.get("allowed_decisions", []):
        return f"{spec['phase']} {spec['gate_key']}.allowed_decisions missing {spec['expected_decision']}"
    if "REJECT" not in gate.get("allowed_decisions", []):
        return f"{spec['phase']} {spec['gate_key']}.allowed_decisions missing REJECT"

    readiness = report.get(spec["readiness_key"], {})
    if readiness.get("readiness_status") != spec["readiness_status"]:
        return f"{spec['phase']} {spec['readiness_key']}.readiness_status mismatch"
    if readiness.get("human_approval_required") is not True:
        return f"{spec['phase']} {spec['readiness_key']}.human_approval_required must be true"
    if readiness.get("can_execute") is not False:
        return f"{spec['phase']} {spec['readiness_key']}.can_execute must be false"
    if readiness.get("execute_allowed") is not False:
        return f"{spec['phase']} {spec['readiness_key']}.execute_allowed must be false"

    return None


def build_report(chain_reports: list[dict], logs_dir: Path) -> dict:
    io_list = []
    readiness_transitions = []
    boundary_details = []

    for spec, report in zip(CHAIN_SPECS, chain_reports):
        io_list.append(
            {
                "phase": spec["phase"],
                "input_json": str((logs_dir / spec["input_file"]).as_posix()),
                "output_json": str((logs_dir / spec["file"]).as_posix()),
            }
        )

        readiness = report.get(spec["readiness_key"], {})
        readiness_transitions.append(
            {
                "phase": spec["phase"],
                "readiness_key": spec["readiness_key"],
                "readiness_status": readiness.get("readiness_status"),
            }
        )

        boundary_details.append(
            {
                "phase": spec["phase"],
                "mode": report.get("mode"),
                "human_approval_required": report.get("human_approval_required"),
                "can_execute": report.get("can_execute"),
                "execute_allowed": report.get("execute_allowed"),
                "max_files_to_execute": report.get("max_files_to_execute"),
                "sandbox_scope_required": report.get("sandbox_scope_required"),
                "single_file_scope_required": report.get("single_file_scope_required"),
                "controls_does_not_execute": report.get(spec["controls_key"], {}).get("does_not_execute"),
                "evidence_checks_does_not_execute": report.get(spec["evidence_key"], {}).get("does_not_execute"),
                "manual_gate_does_not_execute": report.get(spec["gate_key"], {}).get("does_not_execute"),
                "manual_gate_allowed_decisions": report.get(spec["gate_key"], {}).get("allowed_decisions", []),
                "production_status": report.get("production_status"),
            }
        )

    all_checks_passed = len(chain_reports) == len(CHAIN_SPECS)

    return {
        "package_type": "phase80_limited_dry_run_preparation_chain_completion_report",
        "phase": "Phase 80",
        "title": "Phase 80 Limited Dry-Run Preparation Chain Completion Report",
        "status": "PASS" if all_checks_passed else "ABORT",
        "chain_completion_status": "PASS" if all_checks_passed else "ABORT",
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "chain_scope": "phase68_to_phase79_limited_dry_run_preparation_chain",
        "input_output_json_list": io_list,
        "pass_status_summary": {
            "total_phases": len(CHAIN_SPECS),
            "pass_count": len(CHAIN_SPECS),
            "all_passed": all_checks_passed,
        },
        "readiness_transitions": readiness_transitions,
        "safety_boundary_maintenance": {
            "dry_run_fixed": True,
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
            "max_files_to_execute": 1,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "controls_does_not_execute": True,
            "evidence_checks_does_not_execute": True,
            "manual_gate_does_not_execute": True,
            "production_status": "NO_GO",
            "details": boundary_details,
        },
        "unreleased_items": [
            "execution_not_allowed",
            "production_reflection_not_allowed",
            "auto_merge_not_allowed",
            "delete_operations_not_allowed",
            "production_deploy_not_allowed",
        ],
        "next_stage_go_no_go_conditions": [
            "all_phase68_to_phase79_reports_pass",
            "safety_boundary_maintenance_intact",
            "manual_gate_decision_is_allow_phase80_planning_only_or_reject",
            "execution_flags_remain_false_until_explicit_future_unlock",
        ],
        "manual_phase80_gate": {
            "gate_required": True,
            "allowed_decisions": [
                "ALLOW_PHASE80_PLANNING_ONLY",
                "REJECT",
            ],
            "does_not_execute": True,
            "status": "MANUAL_PHASE80_PLANNING_GATE_READY" if all_checks_passed else "ABORT",
        },
        "phase80_readiness": {
            "readiness_status": "READY_FOR_PHASE80_PLANNING_ONLY" if all_checks_passed else "NOT_READY",
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
        },
        "production_status": "NO_GO",
        "all_checks_passed": all_checks_passed,
        "next_step": "review_phase80_go_no_go_conditions_before_any_execution",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_phase80_limited_dry_run_preparation_chain_completion_report(
    input_path: Path | None = None,
    output_path: Path | None = None,
    overwrite: bool = False,
) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        return abort_result(f"required input file not found: {input_path}")
    if output_path.exists() and not overwrite:
        return abort_result(f"JSON report already exists: {output_path}")

    logs_dir = input_path.parent
    chain_reports = []

    for spec in CHAIN_SPECS:
        report_path = logs_dir / spec["file"]
        if not report_path.exists():
            return abort_result(f"required chain file not found: {report_path}")
        report = load_json(report_path)
        error = validate_report_common(report, spec)
        if error:
            return abort_result(error)
        chain_reports.append(report)

    report = build_report(chain_reports, logs_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "package_type": "phase80_limited_dry_run_preparation_chain_completion_report_result",
        "phase": "Phase 80",
        "status": report["status"],
        "chain_completion_status": report["chain_completion_status"],
        "report_generated": report["status"] == "PASS",
        "json_output": str(output_path),
        "production_status": "NO_GO",
        "phase80_readiness": report["phase80_readiness"]["readiness_status"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase80 limited dry-run preparation chain completion report")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input Phase79 report path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output Phase80 report path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    result = generate_phase80_limited_dry_run_preparation_chain_completion_report(
        args.input,
        args.output,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
