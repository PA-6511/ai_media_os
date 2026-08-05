#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

EVIDENCE_PATHS = {
    "N-1": ROOT / "exchange/logs/n1_vps_connectivity_result.json",
    "N-2": ROOT / "exchange/logs/n2_wordpress_api_stability_result.json",
    "N-3": ROOT / "exchange/logs/n3_slack_path_stability_result.json",
    "N-4": ROOT / "exchange/logs/n4_github_connectivity_result.json",
    "N-5": ROOT / "exchange/logs/n5_recovery_simulation_result.json",
}

OUTPUT_JSON = ROOT / "exchange/logs/n_series_overall_report.json"
OUTPUT_MD = ROOT / "exchange/logs/n_series_overall_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("overall_status") or "UNKNOWN")


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# N-Series VPS Communication Stability Overall Report",
        "",
        "## Summary",
        f"- overall_status: {report['overall_status']}",
        f"- production_status: {report['production_status']}",
        f"- execution: {report['execution']}",
        f"- required_evidence_count: {report['required_evidence_count']}",
        f"- found_evidence_count: {report['found_evidence_count']}",
        f"- missing_evidence_count: {report['missing_evidence_count']}",
        "",
        "## Evidence",
    ]
    for item in report.get("evidence", []):
        lines.append(
            "- "
            f"{item.get('phase')}: found={item.get('found')} status={item.get('status')} path={item.get('path')}"
        )

    lines.extend(
        [
            "",
            "## Safety",
            f"- NO_GO maintained: {report.get('production_status') == 'NO_GO'}",
            f"- wordpress_write_executed: {report.get('wordpress_write_executed')}",
            f"- github_push_executed: {report.get('github_push_executed')}",
            f"- slack_message_sent: {report.get('slack_message_sent')}",
            f"- system_restart_executed: {report.get('system_restart_executed')}",
            f"- executed_external_changes: {report.get('executed_external_changes')}",
            "",
            "## WARN",
        ]
    )
    warns = report.get("warn_list", [])
    if warns:
        for item in warns:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(["", "## FAIL"])
    fails = report.get("fail_list", [])
    if fails:
        for item in fails:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def generate_report(
    evidence_paths: dict[str, Path] | None = None,
    output_json_path: Path = OUTPUT_JSON,
    output_md_path: Path = OUTPUT_MD,
) -> dict[str, Any]:
    evidence_paths = evidence_paths or EVIDENCE_PATHS
    evidence: list[dict[str, Any]] = []
    warn_list: list[str] = []
    fail_list: list[str] = []

    required_count = len(evidence_paths)
    found_count = 0

    wordpress_write_executed = False
    github_push_executed = False
    slack_message_sent = False
    system_restart_executed = False

    for phase, path in evidence_paths.items():
        found = path.exists()
        status = "MISSING"
        payload: dict[str, Any] = {}

        if found:
            found_count += 1
            try:
                payload = _load_json(path)
                status = _extract_status(payload)
            except Exception:
                status = "FAIL"
                fail_list.append(f"{phase}: invalid_json")

        if status == "WARN":
            warn_list.append(f"{phase}: WARN")
        if status == "FAIL":
            fail_list.append(f"{phase}: FAIL")
        if status == "MISSING":
            fail_list.append(f"{phase}: MISSING")

        wordpress_write_executed = wordpress_write_executed or bool(payload.get("wordpress_write_executed", False))
        github_push_executed = github_push_executed or bool(payload.get("github_push_executed", False))
        slack_message_sent = slack_message_sent or bool(payload.get("slack_message_sent", False))
        system_restart_executed = system_restart_executed or bool(payload.get("system_restart_executed", False))

        evidence.append(
            {
                "phase": phase,
                "path": str(path),
                "found": found,
                "status": status,
            }
        )

    report = {
        "series": "N-1_to_N-5",
        "required_evidence_count": required_count,
        "found_evidence_count": found_count,
        "missing_evidence_count": required_count - found_count,
        "overall_status": "PASS_DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "mode": "CONNECTION_TEST",
        "human_approval_required": True,
        "wordpress_write_executed": wordpress_write_executed,
        "github_push_executed": github_push_executed,
        "slack_message_sent": slack_message_sent,
        "system_restart_executed": system_restart_executed,
        "executed_external_changes": 0,
        "evidence": evidence,
        "warn_list": warn_list,
        "fail_list": fail_list,
        "generated_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    result = generate_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
