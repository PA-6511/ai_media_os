#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT_JSON = ROOT / "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_result.json"
DEFAULT_REPORT_JSON = ROOT / "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_report.json"
DEFAULT_REPORT_MD = ROOT / "exchange/logs/phase8_17_single_controlled_draft_creation_human_approval_handoff_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_sensitive_marker(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "authorization:",
        "bearer ",
        "basic ",
        "cookie:",
        "password=",
        "token=",
        "webhook=",
        "api_key=",
        "client_secret=",
    ]
    return any(marker in lowered for marker in markers)


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-17 Single Controlled Draft Creation Human Approval Handoff Report",
        "",
        "## Phase 8-17 summary",
        "- Design and handoff only. No WordPress execution is performed in this phase.",
        "",
        "## Final status",
        f"- final_status: {report.get('final_status')}",
        f"- handoff_status: {report.get('handoff_status')}",
        f"- previous Phase 8-16 final_status: {report.get('previous_final_status')}",
        f"- credentials_ready: {report.get('credentials_ready')}",
        f"- credentials_not_ready: {report.get('credentials_not_ready')}",
        f"- no_secret_leak_passed: {report.get('no_secret_leak_passed')}",
        f"- human_decision: {report.get('human_decision')}",
        f"- execution_allowed: {report.get('execution_allowed')}",
        "",
        "## Safety execution checks",
        f"- WordPress API call not executed: {report.get('wordpress_api_call_not_executed')}",
        f"- WordPress write not executed: {report.get('wordpress_write_not_executed')}",
        f"- draft creation not executed: {report.get('draft_creation_not_executed')}",
        f"- production remains NO_GO: {report.get('production_status') == 'NO_GO'}",
        "",
        "## Next step",
        f"- {report.get('next_step')}",
    ]
    return "\n".join(lines) + "\n"


def generate_phase8_17_single_controlled_draft_creation_human_approval_handoff_report(
    result_json_path: Path = DEFAULT_RESULT_JSON,
    output_json_path: Path = DEFAULT_REPORT_JSON,
    output_md_path: Path = DEFAULT_REPORT_MD,
) -> dict[str, Any]:
    result_json_path = Path(result_json_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    if not result_json_path.exists():
        report = {
            "phase": "8-17",
            "phase_name": "Single controlled draft creation human approval handoff",
            "final_status": "ABORT_POLICY_VIOLATION",
            "handoff_status": "ABORTED_POLICY_VIOLATION",
            "previous_final_status": None,
            "credentials_ready": False,
            "credentials_not_ready": False,
            "no_secret_leak_passed": False,
            "human_decision": None,
            "execution_allowed": False,
            "wordpress_api_call_not_executed": True,
            "wordpress_write_not_executed": True,
            "draft_creation_not_executed": True,
            "production_status": "NO_GO",
            "next_step": "abort_without_execution",
            "errors": ["missing_validator_result"],
            "generated_at": _now_iso(),
        }
    else:
        result = _load_json(result_json_path)
        report = {
            "phase": "8-17",
            "phase_name": "Single controlled draft creation human approval handoff",
            "final_status": result.get("final_status", "ABORT_POLICY_VIOLATION"),
            "handoff_status": result.get("handoff_status", "ABORTED_POLICY_VIOLATION"),
            "previous_final_status": result.get("previous_final_status"),
            "credentials_ready": bool(result.get("credentials_ready", False)),
            "credentials_not_ready": bool(result.get("credentials_not_ready", False)),
            "no_secret_leak_passed": bool(result.get("no_secret_leak_passed", False)),
            "human_decision": result.get("human_decision"),
            "execution_allowed": False,
            "wordpress_api_call_not_executed": not bool(result.get("wordpress_api_call_attempted", False)),
            "wordpress_write_not_executed": not bool(result.get("wordpress_write_executed", False)),
            "draft_creation_not_executed": not bool(result.get("wordpress_draft_created", False)),
            "production_status": result.get("production_status", "NO_GO"),
            "next_step": result.get("next_step", "abort_without_execution"),
            "errors": result.get("reasons", []),
            "generated_at": _now_iso(),
        }

    markdown = _build_markdown(report)
    if _contains_sensitive_marker(markdown):
        report["final_status"] = "ABORT_SECRET_LEAK_RISK"
        report["no_secret_leak_passed"] = False
        report["errors"] = list(report.get("errors", [])) + ["secret_like_content_detected_in_markdown"]
        markdown = _build_markdown(report)

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(markdown, encoding="utf-8")
    return report


def main() -> int:
    report = generate_phase8_17_single_controlled_draft_creation_human_approval_handoff_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    acceptable = {
        "PASS_HANDOFF_ONLY_CREDENTIALS_READY",
        "PASS_HANDOFF_ONLY_CREDENTIALS_NOT_READY",
        "WARN_REQUEST_FIX_NO_EXECUTION",
        "FAIL_REJECTED_BY_HUMAN_NO_EXECUTION",
        "ABORT_BY_HUMAN_NO_EXECUTION",
        "ABORT_UNKNOWN_DECISION_NO_EXECUTION",
    }
    return 0 if report.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
