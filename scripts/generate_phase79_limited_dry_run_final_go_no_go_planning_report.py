#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "exchange" / "logs" / "phase78_limited_dry_run_operator_checklist_report.json"
DEFAULT_OUTPUT = ROOT / "exchange" / "logs" / "phase79_limited_dry_run_final_go_no_go_planning_report.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def abort_result(reason: str) -> dict:
    return {
        "package_type": "phase79_limited_dry_run_final_go_no_go_planning_report_result",
        "phase": "Phase 79",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_phase78_report(data: dict) -> dict | None:
    if data.get("phase") != "Phase 78":
        return abort_result("input phase must be 'Phase 78'")
    if data.get("package_type") != "phase78_limited_dry_run_operator_checklist_report":
        return abort_result("input package_type mismatch")
    if data.get("status") != "PASS":
        return abort_result("input status must be PASS")
    if data.get("operator_checklist_status") != "PASS":
        return abort_result("input operator_checklist_status must be PASS")
    if data.get("mode") != "DRY_RUN":
        return abort_result("mode must be DRY_RUN")
    if data.get("human_approval_required") is not True:
        return abort_result("human_approval_required must be true")
    if data.get("can_execute") is not False:
        return abort_result("can_execute must be false")
    if data.get("execute_allowed") is not False:
        return abort_result("execute_allowed must be false")
    if data.get("max_files_to_execute") != 1:
        return abort_result("max_files_to_execute must be 1")
    if data.get("sandbox_scope_required") is not True:
        return abort_result("sandbox_scope_required must be true")
    if data.get("single_file_scope_required") is not True:
        return abort_result("single_file_scope_required must be true")

    operator_checklist_package = data.get("operator_checklist_package", {})
    if operator_checklist_package.get("does_not_execute") is not True:
        return abort_result("operator_checklist_package.does_not_execute must be true")

    controls = data.get("operator_checklist_controls", {})
    if controls.get("does_not_execute") is not True:
        return abort_result("operator_checklist_controls.does_not_execute must be true")

    evidence_checks = data.get("operator_checklist_evidence_checks", {})
    if evidence_checks.get("does_not_execute") is not True:
        return abort_result("operator_checklist_evidence_checks.does_not_execute must be true")
    required_evidence = evidence_checks.get("required_evidence", [])
    expected_evidence = {
        "phase66_go_no_go_report_reference",
        "preparation_scope_statement",
        "target_files_manifest",
        "sandbox_scope_confirmation",
        "single_file_scope_confirmation",
        "dry_run_mode_confirmation",
        "non_execution_confirmation",
    }
    if not expected_evidence.issubset(set(required_evidence)):
        return abort_result("required_evidence is missing one or more required entries")

    gate = data.get("manual_operator_checklist_gate", {})
    if gate.get("does_not_execute") is not True:
        return abort_result("manual_operator_checklist_gate.does_not_execute must be true")
    if "ALLOW_PHASE79_PLANNING_ONLY" not in gate.get("allowed_decisions", []):
        return abort_result("manual_operator_checklist_gate.allowed_decisions missing ALLOW_PHASE79_PLANNING_ONLY")

    readiness = data.get("phase79_readiness", {})
    if readiness.get("readiness_status") != "READY_FOR_PHASE79_PLANNING_ONLY":
        return abort_result("phase79_readiness.readiness_status must be READY_FOR_PHASE79_PLANNING_ONLY")
    if readiness.get("human_approval_required") is not True:
        return abort_result("phase79_readiness.human_approval_required must be true")
    if readiness.get("can_execute") is not False:
        return abort_result("phase79_readiness.can_execute must be false")
    if readiness.get("execute_allowed") is not False:
        return abort_result("phase79_readiness.execute_allowed must be false")

    return None


def build_report(source: dict, input_path: Path) -> dict:
    evidence_checks = source["operator_checklist_evidence_checks"]

    checks = [
        {
            "check": "input_phase=Phase 78",
            "passed": source.get("phase") == "Phase 78",
            "actual": source.get("phase"),
        },
        {
            "check": "input_package_type=phase78_limited_dry_run_operator_checklist_report",
            "passed": source.get("package_type") == "phase78_limited_dry_run_operator_checklist_report",
            "actual": source.get("package_type"),
        },
        {
            "check": "input_status=PASS",
            "passed": source.get("status") == "PASS",
            "actual": source.get("status"),
        },
        {
            "check": "dry_run_fixed=true",
            "passed": source.get("mode") == "DRY_RUN",
            "actual": source.get("mode"),
        },
        {
            "check": "human_approval_required=true",
            "passed": source.get("human_approval_required") is True,
            "actual": source.get("human_approval_required"),
        },
        {
            "check": "can_execute=false",
            "passed": source.get("can_execute") is False,
            "actual": source.get("can_execute"),
        },
        {
            "check": "execute_allowed=false",
            "passed": source.get("execute_allowed") is False,
            "actual": source.get("execute_allowed"),
        },
        {
            "check": "max_files_to_execute=1",
            "passed": source.get("max_files_to_execute") == 1,
            "actual": source.get("max_files_to_execute"),
        },
        {
            "check": "sandbox_scope_required=true",
            "passed": source.get("sandbox_scope_required") is True,
            "actual": source.get("sandbox_scope_required"),
        },
        {
            "check": "single_file_scope_required=true",
            "passed": source.get("single_file_scope_required") is True,
            "actual": source.get("single_file_scope_required"),
        },
        {
            "check": "final_go_no_go_planning_controls_does_not_execute=true",
            "passed": source.get("operator_checklist_controls", {}).get("does_not_execute") is True,
            "actual": source.get("operator_checklist_controls", {}).get("does_not_execute"),
        },
        {
            "check": "final_go_no_go_planning_evidence_checks_does_not_execute=true",
            "passed": evidence_checks.get("does_not_execute") is True,
            "actual": evidence_checks.get("does_not_execute"),
        },
        {
            "check": "manual_final_go_no_go_planning_gate_does_not_execute=true",
            "passed": source.get("manual_operator_checklist_gate", {}).get("does_not_execute") is True,
            "actual": source.get("manual_operator_checklist_gate", {}).get("does_not_execute"),
        },
        {
            "check": "phase79_readiness_status=READY_FOR_PHASE79_PLANNING_ONLY",
            "passed": source.get("phase79_readiness", {}).get("readiness_status") == "READY_FOR_PHASE79_PLANNING_ONLY",
            "actual": source.get("phase79_readiness", {}).get("readiness_status"),
        },
    ]
    all_checks_passed = all(check["passed"] for check in checks)

    return {
        "package_type": "phase79_limited_dry_run_final_go_no_go_planning_report",
        "phase": "Phase 79",
        "title": "Phase 79 Limited Dry-Run Final GO/NO-GO Planning Report",
        "status": "PASS" if all_checks_passed else "ABORT",
        "final_go_no_go_planning_status": "PASS" if all_checks_passed else "ABORT",
        "source_report": normalize_path(input_path),
        "source_report_type": source.get("package_type"),
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "final_go_no_go_planning_package": {
            "package_scope": "limited_dry_run_final_go_no_go_planning_package_only",
            "does_not_execute": True,
            "final_go_no_go_planning_target": "phase78_limited_dry_run_operator_checklist_report",
            "status": "LIMITED_DRY_RUN_FINAL_GO_NO_GO_PLANNING_PACKAGE_READY" if all_checks_passed else "ABORT",
        },
        "final_go_no_go_planning_controls": {
            "controls_required": True,
            "dry_run_required": True,
            "human_approval_required": True,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "does_not_execute": True,
            "status": "LIMITED_DRY_RUN_FINAL_GO_NO_GO_PLANNING_CONTROLS_READY" if all_checks_passed else "ABORT",
        },
        "final_go_no_go_planning_evidence_checks": {
            "evidence_required": True,
            "required_evidence": evidence_checks.get("required_evidence", []),
            "missing_evidence_blocks_progress": True,
            "does_not_execute": True,
            "status": "LIMITED_DRY_RUN_FINAL_GO_NO_GO_PLANNING_EVIDENCE_CHECKS_READY" if all_checks_passed else "ABORT",
        },
        "manual_final_go_no_go_planning_gate": {
            "gate_required": True,
            "allowed_decisions": [
                "ALLOW_PHASE80_PLANNING_ONLY",
                "REJECT",
            ],
            "does_not_execute": True,
            "status": "MANUAL_LIMITED_DRY_RUN_FINAL_GO_NO_GO_PLANNING_GATE_READY" if all_checks_passed else "ABORT",
        },
        "phase80_readiness": {
            "readiness_status": "READY_FOR_PHASE80_PLANNING_ONLY" if all_checks_passed else "NOT_READY",
            "planning_package_scope": "limited_dry_run_next_phase_planning_package_only",
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
        },
        "production_status": "NO_GO",
        "checks": checks,
        "all_checks_passed": all_checks_passed,
        "next_step": "decide_whether_to_start_phase80_limited_dry_run_next_phase_planning_package",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_phase79_limited_dry_run_final_go_no_go_planning_report(
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

    source = load_json(input_path)
    validation_error = validate_phase78_report(source)
    if validation_error:
        return validation_error

    report = build_report(source, input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "package_type": "phase79_limited_dry_run_final_go_no_go_planning_report_result",
        "phase": "Phase 79",
        "status": report["status"],
        "final_go_no_go_planning_status": report["final_go_no_go_planning_status"],
        "report_generated": report["status"] == "PASS",
        "json_output": str(output_path),
        "production_status": "NO_GO",
        "phase80_readiness": report["phase80_readiness"]["readiness_status"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase79 limited dry-run final GO/NO-GO planning report")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input Phase78 report path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output Phase79 report path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    result = generate_phase79_limited_dry_run_final_go_no_go_planning_report(args.input, args.output, overwrite=args.overwrite)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
