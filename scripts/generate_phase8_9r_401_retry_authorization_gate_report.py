#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT_JSON = ROOT / "exchange/logs/phase8_9r_401_retry_authorization_gate_result.json"
DEFAULT_REPORT_JSON = ROOT / "exchange/logs/phase8_9r_401_retry_authorization_gate_report.json"
DEFAULT_REPORT_MD = ROOT / "exchange/logs/phase8_9r_401_retry_authorization_gate_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-9R 401 Retry Authorization Gate Report",
        "",
        "## Purpose",
        "- Confirm the prior 401 failure evidence and authorize only one retry, with no execution in this phase.",
        "",
        "## Final status",
        f"- final_status: {report.get('final_status')}",
        f"- retry_authorized: {report.get('retry_authorized')}",
        f"- retry_allowed: {report.get('retry_allowed')}",
        f"- retry_limit: {report.get('retry_limit')}",
        f"- previous_status: {report.get('previous_status')}",
        f"- previous_401_confirmed: {report.get('previous_401_confirmed')}",
        f"- previous_freeze_required: {report.get('previous_freeze_required')}",
        f"- human_decision: {report.get('human_decision')}",
        f"- human_approval_valid: {report.get('human_approval_valid')}",
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
    return "\n".join(lines) + "\n"


def generate_phase8_9r_401_retry_authorization_gate_report(
    result_json_path: Path = DEFAULT_RESULT_JSON,
    report_json_path: Path = DEFAULT_REPORT_JSON,
    report_md_path: Path = DEFAULT_REPORT_MD,
) -> dict[str, Any]:
    result_json_path = Path(result_json_path)
    report_json_path = Path(report_json_path)
    report_md_path = Path(report_md_path)

    if not result_json_path.exists():
        report = {
            "phase": "8-9R",
            "phase_name": "401 retry authorization gate",
            "final_status": "ABORT_POLICY_VIOLATION",
            "retry_authorized": False,
            "retry_allowed": True,
            "retry_limit": 1,
            "previous_status": None,
            "previous_401_confirmed": False,
            "previous_freeze_required": False,
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
            "next_step": "manual_401_cause_review_and_retry_block",
            "errors": ["missing_validator_result"],
            "generated_at": _now_iso(),
        }
    else:
        result = _load_json(result_json_path)
        report = {
            "phase": "8-9R",
            "phase_name": "401 retry authorization gate",
            "final_status": result.get("final_status", "ABORT_POLICY_VIOLATION"),
            "retry_authorized": bool(result.get("retry_authorized", False)),
            "retry_allowed": bool(result.get("retry_allowed", True)),
            "retry_limit": int(result.get("retry_limit", 1)),
            "previous_status": result.get("previous_status"),
            "previous_401_confirmed": bool(result.get("previous_401_confirmed", False)),
            "previous_freeze_required": bool(result.get("previous_freeze_required", False)),
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
            "next_step": result.get("next_step", "manual_401_cause_review_and_retry_block"),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "policy_violations": result.get("policy_violations", []),
            "secret_leak_findings": result.get("secret_leak_findings", []),
            "generated_at": _now_iso(),
        }

    output_md = _build_markdown(report)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(output_md, encoding="utf-8")
    return report


def main() -> int:
    report = generate_phase8_9r_401_retry_authorization_gate_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    acceptable = {
        "401_RETRY_AUTHORIZATION_GATE_READY_NO_EXECUTION",
        "REQUEST_FIX_NO_EXECUTION",
        "REJECTED_NO_EXECUTION",
        "ABORTED_NO_EXECUTION",
    }
    return 0 if report.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())