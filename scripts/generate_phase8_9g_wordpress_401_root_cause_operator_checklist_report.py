#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT_JSON = ROOT / "exchange/logs/phase8_9g_wordpress_401_root_cause_operator_checklist_result.json"
DEFAULT_REPORT_JSON = ROOT / "exchange/logs/phase8_9g_wordpress_401_root_cause_operator_checklist_report.json"
DEFAULT_REPORT_MD = ROOT / "exchange/logs/phase8_9g_wordpress_401_root_cause_operator_checklist_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-9G WordPress 401 Root Cause Operator Checklist Report",
        "",
        "## Purpose",
        "- Fix the 401 investigation checklist in design-only form and avoid any WordPress execution.",
        "",
        "## Final status",
        f"- final_status: {report.get('final_status')}",
        f"- retry_consumed: {report.get('retry_consumed')}",
        f"- retry_allowed: {report.get('retry_allowed')}",
        f"- retry_limit: {report.get('retry_limit')}",
        f"- freeze_required: {report.get('freeze_required')}",
        f"- human_decision: {report.get('human_decision')}",
        f"- human_approval_valid: {report.get('human_approval_valid')}",
        "",
        "## Investigation focus",
    ]
    for item in report.get("investigation_focus", []):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Operator checklist",
        ]
    )
    for key, value in report.get("operator_checklist", {}).items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Safety flags",
            f"- wordpress_api_call_allowed: {report.get('wordpress_api_call_allowed')}",
            f"- wordpress_api_call_attempted: {report.get('wordpress_api_call_attempted')}",
            f"- wordpress_write_executed: {report.get('wordpress_write_executed')}",
            f"- wordpress_draft_created: {report.get('wordpress_draft_created')}",
            f"- publish_allowed: {report.get('publish_allowed')}",
            f"- update_allowed: {report.get('update_allowed')}",
            f"- delete_allowed: {report.get('delete_allowed')}",
            f"- export_allowed: {report.get('export_allowed')}",
            f"- secret_values_output: {report.get('secret_values_output')}",
            f"- secret_values_written: {report.get('secret_values_written')}",
            f"- secret_values_logged: {report.get('secret_values_logged')}",
            "",
            "## Next step",
            f"- {report.get('next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_phase8_9g_wordpress_401_root_cause_operator_checklist_report(
    result_json_path: Path = DEFAULT_RESULT_JSON,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    report_md_path: Path = DEFAULT_REPORT_MD,
) -> dict[str, Any]:
    result_json_path = Path(result_json_path)
    report_json_path = Path(report_json_path)
    report_md_path = Path(report_md_path)

    if not result_json_path.exists():
        report = {
            "phase": "8-9G",
            "phase_name": "wordpress 401 root cause operator checklist",
            "final_status": "ABORT_POLICY_VIOLATION",
            "retry_consumed": True,
            "retry_allowed": False,
            "retry_limit": 0,
            "freeze_required": True,
            "human_decision": None,
            "human_approval_valid": False,
            "wordpress_api_call_allowed": False,
            "wordpress_api_call_attempted": False,
            "wordpress_write_executed": False,
            "wordpress_draft_created": False,
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "export_allowed": False,
            "secret_values_output": False,
            "secret_values_written": False,
            "secret_values_logged": False,
            "operator_checklist": {},
            "investigation_focus": [],
            "previous_statuses": {},
            "next_step": "manual_freeze_investigation_without_execution",
            "errors": ["missing_validator_result"],
            "generated_at": _now_iso(),
        }
    else:
        result = _load_json(result_json_path)
        report = {
            "phase": "8-9G",
            "phase_name": "wordpress 401 root cause operator checklist",
            "final_status": result.get("final_status", "ABORT_POLICY_VIOLATION"),
            "retry_consumed": bool(result.get("retry_consumed", True)),
            "retry_allowed": bool(result.get("retry_allowed", False)),
            "retry_limit": int(result.get("retry_limit", 0)),
            "freeze_required": bool(result.get("freeze_required", True)),
            "human_decision": result.get("human_decision"),
            "human_approval_valid": bool(result.get("human_approval_valid", False)),
            "wordpress_api_call_allowed": False,
            "wordpress_api_call_attempted": bool(result.get("wordpress_api_call_attempted", False)),
            "wordpress_write_executed": bool(result.get("wordpress_write_executed", False)),
            "wordpress_draft_created": bool(result.get("wordpress_draft_created", False)),
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "export_allowed": False,
            "secret_values_output": False,
            "secret_values_written": False,
            "secret_values_logged": False,
            "operator_checklist": result.get("operator_checklist", {}),
            "investigation_focus": result.get("investigation_focus", []),
            "previous_statuses": result.get("previous_statuses", {}),
            "next_step": result.get("next_step", "manual_freeze_investigation_without_execution"),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "policy_violations": result.get("policy_violations", []),
            "secret_leak_findings": result.get("secret_leak_findings", []),
            "generated_at": _now_iso(),
        }

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(_build_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    report = generate_phase8_9g_wordpress_401_root_cause_operator_checklist_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    acceptable = {
        "WORDPRESS_401_ROOT_CAUSE_OPERATOR_CHECKLIST_READY_NO_EXECUTION",
        "REQUEST_FIX_NO_EXECUTION",
        "REJECTED_NO_EXECUTION",
        "ABORTED_NO_EXECUTION",
    }
    return 0 if report.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())