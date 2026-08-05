#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "exchange" / "logs" / "phase71_preparation_final_approval_report.json"
DEFAULT_OUTPUT = ROOT / "exchange" / "logs" / "phase72_preparation_final_signoff_report.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def abort_result(reason: str) -> dict:
    return {
        "package_type": "phase72_preparation_final_signoff_report_result",
        "phase": "Phase 72",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_phase71_report(data: dict) -> dict | None:
    if data.get("phase") != "Phase 71":
        return abort_result("input phase must be 'Phase 71'")
    if data.get("package_type") != "phase71_preparation_final_approval_report":
        return abort_result("input package_type mismatch")
    if data.get("status") != "PASS":
        return abort_result("input status must be PASS")
    if data.get("final_approval_status") != "PASS":
        return abort_result("input final_approval_status must be PASS")
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

    final_approval_package = data.get("final_approval_package", {})
    if final_approval_package.get("does_not_execute") is not True:
        return abort_result("final_approval_package.does_not_execute must be true")

    controls = data.get("final_approval_controls", {})
    if controls.get("does_not_execute") is not True:
        return abort_result("final_approval_controls.does_not_execute must be true")

    evidence_checks = data.get("final_approval_evidence_checks", {})
    if evidence_checks.get("does_not_execute") is not True:
        return abort_result("final_approval_evidence_checks.does_not_execute must be true")
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

    gate = data.get("manual_final_approval_gate", {})
    if gate.get("does_not_execute") is not True:
        return abort_result("manual_final_approval_gate.does_not_execute must be true")
    if "ALLOW_PHASE72_PLANNING_ONLY" not in gate.get("allowed_decisions", []):
        return abort_result("manual_final_approval_gate.allowed_decisions missing ALLOW_PHASE72_PLANNING_ONLY")

    readiness = data.get("phase72_readiness", {})
    if readiness.get("readiness_status") != "READY_FOR_PHASE72_PLANNING_ONLY":
        return abort_result("phase72_readiness.readiness_status must be READY_FOR_PHASE72_PLANNING_ONLY")
    if readiness.get("human_approval_required") is not True:
        return abort_result("phase72_readiness.human_approval_required must be true")
    if readiness.get("can_execute") is not False:
        return abort_result("phase72_readiness.can_execute must be false")
    if readiness.get("execute_allowed") is not False:
        return abort_result("phase72_readiness.execute_allowed must be false")

    return None


def build_report(source: dict, input_path: Path) -> dict:
    evidence_checks = source["final_approval_evidence_checks"]

    checks = [
        {
            "check": "input_phase=Phase 71",
            "passed": source.get("phase") == "Phase 71",
            "actual": source.get("phase"),
        },
        {
            "check": "input_package_type=phase71_preparation_final_approval_report",
            "passed": source.get("package_type") == "phase71_preparation_final_approval_report",
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
            "check": "final_signoff_controls_does_not_execute=true",
            "passed": source.get("final_approval_controls", {}).get("does_not_execute") is True,
            "actual": source.get("final_approval_controls", {}).get("does_not_execute"),
        },
        {
            "check": "final_signoff_evidence_checks_does_not_execute=true",
            "passed": evidence_checks.get("does_not_execute") is True,
            "actual": evidence_checks.get("does_not_execute"),
        },
        {
            "check": "manual_final_signoff_gate_does_not_execute=true",
            "passed": source.get("manual_final_approval_gate", {}).get("does_not_execute") is True,
            "actual": source.get("manual_final_approval_gate", {}).get("does_not_execute"),
        },
        {
            "check": "phase72_readiness_status=READY_FOR_PHASE72_PLANNING_ONLY",
            "passed": source.get("phase72_readiness", {}).get("readiness_status") == "READY_FOR_PHASE72_PLANNING_ONLY",
            "actual": source.get("phase72_readiness", {}).get("readiness_status"),
        },
    ]
    all_checks_passed = all(check["passed"] for check in checks)

    return {
        "package_type": "phase72_preparation_final_signoff_report",
        "phase": "Phase 72",
        "title": "Phase 72 Limited Dry-Run Preparation Final Signoff Report",
        "status": "PASS" if all_checks_passed else "ABORT",
        "final_signoff_status": "PASS" if all_checks_passed else "ABORT",
        "source_report": normalize_path(input_path),
        "source_report_type": source.get("package_type"),
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "final_signoff_package": {
            "package_scope": "limited_dry_run_preparation_final_signoff_package_only",
            "does_not_execute": True,
            "final_signoff_target": "phase71_preparation_final_approval_report",
            "status": "PREPARATION_FINAL_SIGNOFF_PACKAGE_READY" if all_checks_passed else "ABORT",
        },
        "final_signoff_controls": {
            "controls_required": True,
            "dry_run_required": True,
            "human_approval_required": True,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "does_not_execute": True,
            "status": "PREPARATION_FINAL_SIGNOFF_CONTROLS_READY" if all_checks_passed else "ABORT",
        },
        "final_signoff_evidence_checks": {
            "evidence_required": True,
            "required_evidence": evidence_checks.get("required_evidence", []),
            "missing_evidence_blocks_progress": True,
            "does_not_execute": True,
            "status": "PREPARATION_FINAL_SIGNOFF_EVIDENCE_CHECKS_READY" if all_checks_passed else "ABORT",
        },
        "manual_final_signoff_gate": {
            "gate_required": True,
            "allowed_decisions": [
                "ALLOW_PHASE73_PLANNING_ONLY",
                "REJECT",
            ],
            "does_not_execute": True,
            "status": "MANUAL_PREPARATION_FINAL_SIGNOFF_GATE_READY" if all_checks_passed else "ABORT",
        },
        "phase73_readiness": {
            "readiness_status": "READY_FOR_PHASE73_PLANNING_ONLY" if all_checks_passed else "NOT_READY",
            "planning_package_scope": "limited_dry_run_preparation_planning_package_only",
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
        },
        "production_status": "NO_GO",
        "checks": checks,
        "all_checks_passed": all_checks_passed,
        "next_step": "decide_whether_to_start_phase73_limited_dry_run_preparation_planning_package",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_phase72_preparation_final_signoff_report(
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
    validation_error = validate_phase71_report(source)
    if validation_error:
        return validation_error

    report = build_report(source, input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "package_type": "phase72_preparation_final_signoff_report_result",
        "phase": "Phase 72",
        "status": report["status"],
        "final_signoff_status": report["final_signoff_status"],
        "report_generated": report["status"] == "PASS",
        "json_output": str(output_path),
        "production_status": "NO_GO",
        "phase73_readiness": report["phase73_readiness"]["readiness_status"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase72 preparation final signoff report")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input Phase71 report path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output Phase72 report path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    result = generate_phase72_preparation_final_signoff_report(args.input, args.output, overwrite=args.overwrite)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
