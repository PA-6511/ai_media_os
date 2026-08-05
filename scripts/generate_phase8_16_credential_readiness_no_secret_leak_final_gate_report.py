#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT_JSON = ROOT / "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json"
DEFAULT_REPORT_JSON = ROOT / "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.json"
DEFAULT_REPORT_MD = ROOT / "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_secret_like_content(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "authorization:",
        "bearer ",
        "basic ",
        "cookie:",
        "password=",
        "token=",
        "webhook=",
        "client_secret=",
        "api_key=",
    ]
    return any(marker in lowered for marker in markers)


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-16 Credential Readiness / No-Secret-Leak Final Gate Report",
        "",
        "## Phase 8-16 summary",
        "- Final pre-execution gate only. No WordPress API call and no write operation are executed.",
        "",
        "## Final status",
        f"- final_status: {report.get('final_status')}",
        f"- credentials_ready: {report.get('credentials_ready')}",
        f"- no_secret_leak_passed: {report.get('no_secret_leak_passed')}",
        "",
        "## Safety execution checks",
        f"- WordPress API call not executed: {report.get('wordpress_api_call_not_executed')}",
        f"- WordPress write not executed: {report.get('wordpress_write_not_executed')}",
        f"- draft creation not executed: {report.get('draft_creation_not_executed')}",
        f"- production remains NO_GO: {report.get('production_status') == 'NO_GO'}",
        "",
        "## Credential readiness by key",
    ]

    for item in report.get("credentials", []):
        lines.append(
            "- "
            f"{item.get('credential_key')}: "
            f"present={item.get('present')} non_empty={item.get('non_empty')} status={item.get('status')}"
        )

    lines.extend(
        [
            "",
            "## Next step",
            f"- {report.get('next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_phase8_16_credential_readiness_no_secret_leak_final_gate_report(
    result_json_path: Path = DEFAULT_RESULT_JSON,
    output_json_path: Path = DEFAULT_REPORT_JSON,
    output_md_path: Path = DEFAULT_REPORT_MD,
) -> dict[str, Any]:
    result_json_path = Path(result_json_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    if not result_json_path.exists():
        report = {
            "phase": "8-16",
            "phase_name": "Credential readiness / no-secret-leak final gate",
            "final_status": "ABORT_POLICY_VIOLATION",
            "credentials_ready": False,
            "no_secret_leak_passed": False,
            "wordpress_api_call_not_executed": True,
            "wordpress_write_not_executed": True,
            "draft_creation_not_executed": True,
            "production_status": "NO_GO",
            "next_step": "manual_credential_provisioning_or_env_fix_without_secret_output",
            "credentials": [],
            "errors": ["missing_validator_result"],
            "generated_at": _now_iso(),
        }
    else:
        result = _load_json(result_json_path)
        report = {
            "phase": "8-16",
            "phase_name": "Credential readiness / no-secret-leak final gate",
            "final_status": result.get("final_status", "ABORT_POLICY_VIOLATION"),
            "credentials_ready": bool(result.get("credentials_ready", False)),
            "no_secret_leak_passed": bool(result.get("no_secret_leak_passed", False)),
            "wordpress_api_call_not_executed": bool(result.get("wordpress_api_call_not_executed", True)),
            "wordpress_write_not_executed": bool(result.get("wordpress_write_not_executed", True)),
            "draft_creation_not_executed": bool(result.get("draft_creation_not_executed", True)),
            "production_status": result.get("production_status", "NO_GO"),
            "next_step": result.get(
                "next_step",
                "manual_credential_provisioning_or_env_fix_without_secret_output",
            ),
            "credentials": result.get("credentials", []),
            "errors": result.get("errors", []),
            "generated_at": _now_iso(),
        }

    markdown = _build_markdown(report)
    if _contains_secret_like_content(markdown):
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
    report = generate_phase8_16_credential_readiness_no_secret_leak_final_gate_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    acceptable = {
        "CREDENTIALS_READY_NO_SECRET_LEAK_PASS",
        "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
    }
    return 0 if report.get("final_status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
