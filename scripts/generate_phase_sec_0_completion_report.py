#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]

DOC_PATH = ROOT / "docs" / "security" / "phase_sec_0_emergency_response_draft.md"
BASELINE_PATH = ROOT / "config" / "security_phase_sec_0_baseline.json"
VALIDATION_PATH = ROOT / "exchange" / "logs" / "security_phase_sec_0_validation_result.json"

REPORT_JSON_PATH = ROOT / "exchange" / "logs" / "phase_sec_0_completion_report.json"
REPORT_MD_PATH = ROOT / "exchange" / "logs" / "phase_sec_0_completion_report.md"


NEXT_CANDIDATES = [
    "Phase-Sec 1 Emergency Freeze Flag Design",
    "Phase-Sec 2 Block Isolation Gate Design",
    "Phase-Sec 3 External Write Stop Gate Design",
    "Phase-Sec 4 Secret Rotation Checklist Design",
    "Phase-Sec 5 Backup Integrity Evidence Design",
    "Phase-Sec 6 Recovery Core Design",
]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def build_report() -> Dict[str, Any]:
    missing_files = [
        str(path.relative_to(ROOT))
        for path in [DOC_PATH, BASELINE_PATH, VALIDATION_PATH]
        if not path.exists()
    ]

    if missing_files:
        return {
            "phase_id": "PHASE_SEC_0",
            "status": "ABORT",
            "production_status": "NO_GO",
            "execution": "DRY_RUN",
            "reasons": [f"missing required files: {missing_files}"],
            "next_step": "restore_missing_phase_sec_0_files",
        }

    baseline = load_json(BASELINE_PATH)
    validation = load_json(VALIDATION_PATH)

    validation_status = validation.get("status")
    status = "PASS_DESIGN_ONLY" if validation_status == "PASS" else "FAIL"

    reasons = []
    if validation_status != "PASS":
        reasons.append(f"validation_status must be PASS, got {validation_status!r}")

    report = {
        "phase_id": "PHASE_SEC_0",
        "phase_name": "Security Emergency Response Baseline Draft",
        "status": status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "human_approval_required": baseline.get("human_approval_required"),
        "emergency_freeze_required": baseline.get("emergency_freeze_required"),
        "block_isolation_required": baseline.get("block_isolation_required"),
        "external_write_stop_required": baseline.get("external_write_stop_required"),
        "secret_rotation_required": baseline.get("secret_rotation_required"),
        "backup_protection_required": baseline.get("backup_protection_required"),
        "recovery_core_design_only": baseline.get("recovery_core_design_only"),
        "evidence_lock_required": baseline.get("evidence_lock_required"),
        "validation_status": validation_status,
        "restricted_operations": {
            "wordpress_write": "NO_GO",
            "wordpress_update": "NO_GO",
            "wordpress_delete": "NO_GO",
            "github_push": "NO_GO",
            "external_api_execution": "NO_GO",
            "automatic_recovery": "NO_GO",
            "automatic_rollback": "NO_GO",
            "automatic_connector_switching": "NO_GO",
            "vps_migration": "NO_GO",
            "modify_env": "NO_GO",
            "modify_secrets": "NO_GO",
            "production_deployment": "NO_GO"
        },
        "created_artifacts": [
            "docs/security/phase_sec_0_emergency_response_draft.md",
            "config/security_phase_sec_0_baseline.json",
            "scripts/validate_security_phase_sec_0_baseline.py",
            "tests/test_validate_security_phase_sec_0_baseline.py",
            "exchange/logs/security_phase_sec_0_validation_result.json"
        ],
        "next_candidates": NEXT_CANDIDATES,
        "reasons": reasons,
        "next_step": "phase_sec_1_or_manual_review" if status == "PASS_DESIGN_ONLY" else "fix_phase_sec_0_validation",
    }

    return report


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_markdown(path: Path, report: Dict[str, Any]) -> None:
    lines = [
        "# Phase-Sec 0 Completion Report",
        "",
        f"- Phase ID: {report.get('phase_id')}",
        f"- Phase Name: {report.get('phase_name')}",
        f"- Status: {report.get('status')}",
        f"- Production Status: {report.get('production_status')}",
        f"- Execution: {report.get('execution')}",
        f"- Human Approval Required: {report.get('human_approval_required')}",
        f"- Validation Status: {report.get('validation_status')}",
        "",
        "## Security Requirements",
        "",
        f"- Emergency Freeze Required: {report.get('emergency_freeze_required')}",
        f"- Block Isolation Required: {report.get('block_isolation_required')}",
        f"- External Write Stop Required: {report.get('external_write_stop_required')}",
        f"- Secret Rotation Required: {report.get('secret_rotation_required')}",
        f"- Backup Protection Required: {report.get('backup_protection_required')}",
        f"- Recovery Core Design Only: {report.get('recovery_core_design_only')}",
        f"- Evidence Lock Required: {report.get('evidence_lock_required')}",
        "",
        "## Restricted Operations",
        "",
    ]

    for key, value in report.get("restricted_operations", {}).items():
        lines.append(f"- {key}: {value}")

    lines.extend([
        "",
        "## Created Artifacts",
        "",
    ])

    for artifact in report.get("created_artifacts", []):
        lines.append(f"- {artifact}")

    lines.extend([
        "",
        "## Next Candidates",
        "",
    ])

    for candidate in report.get("next_candidates", []):
        lines.append(f"- {candidate}")

    lines.extend([
        "",
        "## Final Position",
        "",
        "Phase-Sec 0 is completed as DESIGN_ONLY.",
        "No production operation is allowed.",
        "No external write is allowed.",
        "No automatic recovery is allowed.",
        "Human approval remains required.",
        "",
    ])

    if report.get("reasons"):
        lines.extend(["## Reasons", ""])
        for reason in report["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    try:
        report = build_report()
    except Exception as exc:
        report = {
            "phase_id": "PHASE_SEC_0",
            "status": "ABORT",
            "production_status": "NO_GO",
            "execution": "DRY_RUN",
            "reasons": [f"report_exception: {exc}"],
            "next_step": "manual_review",
        }

    write_json(REPORT_JSON_PATH, report)
    write_markdown(REPORT_MD_PATH, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0 if report.get("status") == "PASS_DESIGN_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
