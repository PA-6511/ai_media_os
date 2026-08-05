#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "exchange" / "logs" / "phase67_preparation_evidence_report.json"
DEFAULT_OUTPUT = ROOT / "exchange" / "logs" / "phase68_preparation_review_report.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def abort_result(reason: str) -> dict:
    return {
        "package_type": "phase68_preparation_review_report_result",
        "phase": "Phase 68",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_phase67_report(data: dict) -> dict | None:
    if data.get("phase") != "67":
        return abort_result("input phase must be '67'")
    if data.get("report_type") != "limited_dry_run_preparation_evidence_package_report":
        return abort_result("input report_type mismatch")
    if data.get("human_approval_required") is not True:
        return abort_result("human_approval_required must be true")
    if data.get("can_execute") is not False:
        return abort_result("can_execute must be false")
    if data.get("execute_allowed") is not False:
        return abort_result("execute_allowed must be false")
    if data.get("readiness_status") != "READY_FOR_PHASE68_PLANNING_ONLY":
        return abort_result("readiness_status must be READY_FOR_PHASE68_PLANNING_ONLY")
    if data.get("selected_decision") != "ALLOW_PHASE68_PLANNING_ONLY":
        return abort_result("selected_decision must be ALLOW_PHASE68_PLANNING_ONLY")

    policy = data.get("policy_result", {})
    if policy.get("policy_status") != "PASS":
        return abort_result("policy_result.policy_status must be PASS")

    package = data.get("preparation_evidence_package", {})
    if package.get("mode") != "DRY_RUN":
        return abort_result("preparation_evidence_package.mode must be DRY_RUN")
    if package.get("human_approval_required") is not True:
        return abort_result("preparation_evidence_package.human_approval_required must be true")
    if package.get("can_execute") is not False:
        return abort_result("preparation_evidence_package.can_execute must be false")
    if package.get("execute_allowed") is not False:
        return abort_result("preparation_evidence_package.execute_allowed must be false")
    if package.get("max_files_to_execute") != 1:
        return abort_result("preparation_evidence_package.max_files_to_execute must be 1")
    if package.get("sandbox_scope_required") is not True:
        return abort_result("preparation_evidence_package.sandbox_scope_required must be true")
    if package.get("single_file_scope_required") is not True:
        return abort_result("preparation_evidence_package.single_file_scope_required must be true")

    controls = data.get("preparation_controls", {})
    if controls.get("preparation_controls_does_not_execute") is not True:
        return abort_result("preparation_controls_does_not_execute must be true")
    if controls.get("execute_allowed") is not False:
        return abort_result("preparation_controls.execute_allowed must be false")

    requirements = data.get("preparation_evidence_requirements", {})
    if requirements.get("preparation_evidence_does_not_execute") is not True:
        return abort_result("preparation_evidence_requirements does_not_execute must be true")
    required_evidence = requirements.get("required_evidence", [])
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

    gate = data.get("manual_preparation_gate", {})
    if gate.get("manual_preparation_gate_does_not_execute") is not True:
        return abort_result("manual_preparation_gate_does_not_execute must be true")
    if "ALLOW_PHASE68_PLANNING_ONLY" not in gate.get("allowed_decisions", []):
        return abort_result("manual_preparation_gate.allowed_decisions missing ALLOW_PHASE68_PLANNING_ONLY")

    return None


def build_report(source: dict, input_path: Path) -> dict:
    package = source["preparation_evidence_package"]
    controls = source["preparation_controls"]
    requirements = source["preparation_evidence_requirements"]
    gate = source["manual_preparation_gate"]

    checks = [
        {
            "check": "input_phase=67",
            "passed": source.get("phase") == "67",
            "actual": source.get("phase"),
        },
        {
            "check": "input_report_type=limited_dry_run_preparation_evidence_package_report",
            "passed": source.get("report_type") == "limited_dry_run_preparation_evidence_package_report",
            "actual": source.get("report_type"),
        },
        {
            "check": "policy_result.policy_status=PASS",
            "passed": source.get("policy_result", {}).get("policy_status") == "PASS",
            "actual": source.get("policy_result", {}).get("policy_status"),
        },
        {
            "check": "dry_run_fixed=true",
            "passed": package.get("mode") == "DRY_RUN",
            "actual": package.get("mode"),
        },
        {
            "check": "human_approval_required=true",
            "passed": source.get("human_approval_required") is True and package.get("human_approval_required") is True,
            "actual": {
                "root": source.get("human_approval_required"),
                "package": package.get("human_approval_required"),
            },
        },
        {
            "check": "can_execute=false",
            "passed": source.get("can_execute") is False and package.get("can_execute") is False,
            "actual": {
                "root": source.get("can_execute"),
                "package": package.get("can_execute"),
            },
        },
        {
            "check": "execute_allowed=false",
            "passed": source.get("execute_allowed") is False and package.get("execute_allowed") is False,
            "actual": {
                "root": source.get("execute_allowed"),
                "package": package.get("execute_allowed"),
            },
        },
        {
            "check": "max_files_to_execute=1",
            "passed": package.get("max_files_to_execute") == 1,
            "actual": package.get("max_files_to_execute"),
        },
        {
            "check": "sandbox_scope_required=true",
            "passed": package.get("sandbox_scope_required") is True,
            "actual": package.get("sandbox_scope_required"),
        },
        {
            "check": "single_file_scope_required=true",
            "passed": package.get("single_file_scope_required") is True,
            "actual": package.get("single_file_scope_required"),
        },
        {
            "check": "review_controls_does_not_execute=true",
            "passed": controls.get("preparation_controls_does_not_execute") is True,
            "actual": controls.get("preparation_controls_does_not_execute"),
        },
        {
            "check": "review_evidence_checks_does_not_execute=true",
            "passed": requirements.get("preparation_evidence_does_not_execute") is True,
            "actual": requirements.get("preparation_evidence_does_not_execute"),
        },
        {
            "check": "manual_review_gate_does_not_execute=true",
            "passed": gate.get("manual_preparation_gate_does_not_execute") is True,
            "actual": gate.get("manual_preparation_gate_does_not_execute"),
        },
    ]
    all_checks_passed = all(check["passed"] for check in checks)

    return {
        "package_type": "phase68_preparation_review_report",
        "phase": "Phase 68",
        "title": "Phase 68 Limited Dry-Run Preparation Review Report",
        "status": "PASS" if all_checks_passed else "ABORT",
        "review_status": "PASS" if all_checks_passed else "ABORT",
        "source_report": normalize_path(input_path),
        "source_report_type": source.get("report_type"),
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
        "review_package": {
            "package_scope": "limited_dry_run_preparation_review_package_only",
            "does_not_execute": True,
            "review_target": "phase67_preparation_evidence_report",
            "status": "PREPARATION_REVIEW_REPORT_READY" if all_checks_passed else "ABORT",
        },
        "review_controls": {
            "controls_required": True,
            "dry_run_required": True,
            "human_approval_required": True,
            "sandbox_scope_required": True,
            "single_file_scope_required": True,
            "does_not_execute": True,
            "status": "PREPARATION_REVIEW_CONTROLS_READY" if all_checks_passed else "ABORT",
        },
        "review_evidence_checks": {
            "evidence_required": True,
            "required_evidence": requirements.get("required_evidence", []),
            "missing_evidence_blocks_progress": True,
            "does_not_execute": True,
            "status": "PREPARATION_REVIEW_EVIDENCE_CHECKS_READY" if all_checks_passed else "ABORT",
        },
        "manual_review_gate": {
            "gate_required": True,
            "allowed_decisions": [
                "ALLOW_PHASE69_READINESS_REVIEW_ONLY",
                "REJECT",
            ],
            "does_not_execute": True,
            "status": "MANUAL_PREPARATION_REVIEW_GATE_READY" if all_checks_passed else "ABORT",
        },
        "phase69_readiness": {
            "readiness_status": "READY_FOR_PHASE69_READINESS_REVIEW_ONLY" if all_checks_passed else "NOT_READY",
            "approval_package_scope": "limited_dry_run_preparation_approval_package_only",
            "human_approval_required": True,
            "can_execute": False,
            "execute_allowed": False,
        },
        "production_status": "NO_GO",
        "checks": checks,
        "all_checks_passed": all_checks_passed,
        "next_step": "decide_whether_to_start_phase69_limited_dry_run_preparation_approval_package",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_phase68_preparation_review_report(
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
    validation_error = validate_phase67_report(source)
    if validation_error:
        return validation_error

    report = build_report(source, input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "package_type": "phase68_preparation_review_report_result",
        "phase": "Phase 68",
        "status": report["status"],
        "review_status": report["review_status"],
        "report_generated": report["status"] == "PASS",
        "json_output": str(output_path),
        "production_status": "NO_GO",
        "phase69_readiness": report["phase69_readiness"]["readiness_status"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase68 preparation review report")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input Phase67 report path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output Phase68 report path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    result = generate_phase68_preparation_review_report(args.input, args.output, overwrite=args.overwrite)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())