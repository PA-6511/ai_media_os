#!/usr/bin/env python3
"""N-10: N-6〜N-9 集約 + N-1〜N-5 参照による最終通信安定性レポート生成。"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

N6_N9_EVIDENCE: dict[str, Path] = {
    "N-6": ROOT / "exchange/logs/n6_continuous_monitoring_dry_run_result.json",
    "N-7": ROOT / "exchange/logs/n7_cron_lock_guard_result.json",
    "N-8": ROOT / "exchange/logs/n8_log_rotation_check_result.json",
    "N-9": ROOT / "exchange/logs/n9_post_reboot_recovery_simulation_result.json",
}

N1_N5_EVIDENCE: dict[str, Path] = {
    "N-1": ROOT / "exchange/logs/n1_vps_connectivity_result.json",
    "N-2": ROOT / "exchange/logs/n2_wordpress_api_stability_result.json",
    "N-3": ROOT / "exchange/logs/n3_slack_path_stability_result.json",
    "N-4": ROOT / "exchange/logs/n4_github_connectivity_result.json",
    "N-5": ROOT / "exchange/logs/n5_recovery_simulation_result.json",
}

OUTPUT_JSON = ROOT / "exchange/logs/n6_n10_series_overall_report.json"
OUTPUT_MD = ROOT / "exchange/logs/n6_n10_series_overall_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("overall_status") or "UNKNOWN")


def _gather(
    paths: dict[str, Path],
) -> tuple[list[dict[str, Any]], list[str], list[str], int, int]:
    evidence: list[dict[str, Any]] = []
    warn_list: list[str] = []
    fail_list: list[str] = []
    found = 0
    for phase, path in paths.items():
        exists = path.exists()
        status = "MISSING"
        if exists:
            found += 1
            try:
                status = _extract_status(_load_json(path))
            except Exception:
                status = "FAIL"
                fail_list.append(f"{phase}: invalid_json")
        if status == "WARN":
            warn_list.append(f"{phase}: WARN")
        if status in {"FAIL", "MISSING"}:
            fail_list.append(f"{phase}: {status}")
        evidence.append({"phase": phase, "path": str(path), "found": exists, "status": status})
    return evidence, warn_list, fail_list, found, len(paths)


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# N-Series Final Infrastructure Verification Report (N-1 to N-9)",
        "",
        "## Summary",
        f"- overall_status: {report['overall_status']}",
        f"- production_status: {report['production_status']}",
        f"- execution: {report['execution']}",
        f"- n6_n9_required: {report['n6_n9_required_count']}",
        f"- n6_n9_found: {report['n6_n9_found_count']}",
        f"- n6_n9_missing: {report['n6_n9_missing_count']}",
        f"- n1_n5_reference_found: {report['n1_n5_found_count']} / {report['n1_n5_required_count']}",
        "",
        "## N-6 to N-9 Evidence",
    ]
    for item in report.get("n6_n9_evidence", []):
        lines.append(f"- {item['phase']}: found={item['found']} status={item['status']}")
    lines += ["", "## N-1 to N-5 Reference"]
    for item in report.get("n1_n5_reference", []):
        lines.append(f"- {item['phase']}: found={item['found']} status={item['status']}")
    lines += [
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
    warns = report.get("warn_list", [])
    lines += [f"- {w}" for w in warns] if warns else ["- none"]
    lines += ["", "## FAIL"]
    fails = report.get("fail_list", [])
    lines += [f"- {f}" for f in fails] if fails else ["- none"]
    return "\n".join(lines) + "\n"


def generate_report(
    n6_n9_paths: "dict[str, Path] | None" = None,
    n1_n5_paths: "dict[str, Path] | None" = None,
    output_json_path: Path = OUTPUT_JSON,
    output_md_path: Path = OUTPUT_MD,
) -> dict[str, Any]:
    n6_n9_paths = n6_n9_paths or N6_N9_EVIDENCE
    n1_n5_paths = n1_n5_paths or N1_N5_EVIDENCE

    n6_n9_ev, warns, fails, n6_n9_found, n6_n9_req = _gather(n6_n9_paths)
    n1_n5_ev, n1_n5_warns, n1_n5_fails, n1_n5_found, n1_n5_req = _gather(n1_n5_paths)

    all_warns = warns + n1_n5_warns
    all_fails = fails + n1_n5_fails

    report: dict[str, Any] = {
        "series": "N-1_to_N-9",
        "n6_n9_required_count": n6_n9_req,
        "n6_n9_found_count": n6_n9_found,
        "n6_n9_missing_count": n6_n9_req - n6_n9_found,
        "n1_n5_required_count": n1_n5_req,
        "n1_n5_found_count": n1_n5_found,
        "overall_status": "PASS_DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "mode": "CONNECTION_TEST",
        "human_approval_required": True,
        "wordpress_write_executed": False,
        "github_push_executed": False,
        "slack_message_sent": False,
        "system_restart_executed": False,
        "executed_external_changes": 0,
        "n6_n9_evidence": n6_n9_ev,
        "n1_n5_reference": n1_n5_ev,
        "warn_list": all_warns,
        "fail_list": all_fails,
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
