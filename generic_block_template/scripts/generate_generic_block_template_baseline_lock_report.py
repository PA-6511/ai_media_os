#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
JSON_OUT = LOG_DIR / "generic_block_template_baseline_lock_report.json"
MD_OUT = LOG_DIR / "generic_block_template_baseline_lock_report.md"

GENERIC_REPORT_PATH = LOG_DIR / "generic_block_report.json"
OPS_DASHBOARD_PATH = LOG_DIR / "generic_block_ops_dashboard.json"
RANKING_PREVIEW_PATH = LOG_DIR / "ranking_dry_run_preview.json"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_load(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = _load_json(path)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _overall_status(statuses: List[str]) -> str:
    if any(s == "FAIL" for s in statuses):
        return "FAIL"
    if any(s == "WARN" for s in statuses):
        return "WARN"
    return "PASS"


def generate_baseline_lock_report() -> Dict[str, Any]:
    generic_report = _safe_load(GENERIC_REPORT_PATH)
    ops_dashboard = _safe_load(OPS_DASHBOARD_PATH)
    ranking_preview = _safe_load(RANKING_PREVIEW_PATH)

    missing = []
    for name, payload in (
        ("generic_block_report", generic_report),
        ("generic_block_ops_dashboard", ops_dashboard),
        ("ranking_dry_run_preview", ranking_preview),
    ):
        if payload is None:
            missing.append(name)

    statuses: List[str] = []
    if generic_report is None:
        statuses.append("FAIL")
    else:
        statuses.append(str(generic_report.get("status", "FAIL")))

    if ops_dashboard is None:
        statuses.append("FAIL")
    else:
        statuses.append(str(ops_dashboard.get("status", "FAIL")))
        statuses.append(str(ops_dashboard.get("filter_status", "FAIL")))

    if ranking_preview is None:
        statuses.append("FAIL")
    else:
        statuses.append(str(ranking_preview.get("status", "FAIL")))

    production_status_ok = all(
        (payload or {}).get("production_status") == "NO_GO"
        for payload in (generic_report, ops_dashboard, ranking_preview)
    )
    if not production_status_ok:
        statuses.append("FAIL")

    overall = _overall_status(statuses)

    lock_payload = {
        "status": overall,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_name": "generic_block_template_v1_ranking_dry_run_ops_dashboard",
        "baseline_locked": overall == "PASS",
        "production_status": "NO_GO",
        "checks": {
            "required_reports_present": len(missing) == 0,
            "missing_reports": missing,
            "generic_block_report_status": (generic_report or {}).get("status", "FAIL"),
            "ops_dashboard_status": (ops_dashboard or {}).get("status", "FAIL"),
            "ops_dashboard_filter_status": (ops_dashboard or {}).get("filter_status", "FAIL"),
            "ranking_preview_status": (ranking_preview or {}).get("status", "FAIL"),
            "production_status_no_go": production_status_ok,
            "external_api_called": bool((ranking_preview or {}).get("external_api_called", False)),
            "external_network_called": bool((ranking_preview or {}).get("external_network_called", False)),
        },
        "summary": {
            "visible_blocks": (ops_dashboard or {}).get("generated_blocks_filtered", []),
            "excluded_blocks": (ops_dashboard or {}).get("excluded_blocks", []),
            "ranking_top_item": ((ops_dashboard or {}).get("ranking_preview_top_item") or {}).get("title", ""),
            "ranking_input_source": (ops_dashboard or {}).get("ranking_input_source", ""),
        },
        "source_reports": {
            "generic_block_report": str(GENERIC_REPORT_PATH),
            "generic_block_ops_dashboard": str(OPS_DASHBOARD_PATH),
            "ranking_dry_run_preview": str(RANKING_PREVIEW_PATH),
        },
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(lock_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Generic Block Template Baseline Lock Report",
        "",
        f"- status: {lock_payload['status']}",
        f"- generated_at: {lock_payload['generated_at']}",
        f"- baseline_name: {lock_payload['baseline_name']}",
        f"- baseline_locked: {lock_payload['baseline_locked']}",
        f"- production_status: {lock_payload['production_status']}",
        "",
        "## Checks",
        f"- required_reports_present: {lock_payload['checks']['required_reports_present']}",
        f"- missing_reports: {', '.join(lock_payload['checks']['missing_reports']) or 'none'}",
        f"- generic_block_report_status: {lock_payload['checks']['generic_block_report_status']}",
        f"- ops_dashboard_status: {lock_payload['checks']['ops_dashboard_status']}",
        f"- ops_dashboard_filter_status: {lock_payload['checks']['ops_dashboard_filter_status']}",
        f"- ranking_preview_status: {lock_payload['checks']['ranking_preview_status']}",
        f"- production_status_no_go: {lock_payload['checks']['production_status_no_go']}",
        f"- external_api_called: {lock_payload['checks']['external_api_called']}",
        f"- external_network_called: {lock_payload['checks']['external_network_called']}",
        "",
        "## Summary",
        f"- visible_blocks: {', '.join(lock_payload['summary']['visible_blocks']) or 'none'}",
        f"- excluded_blocks: {', '.join(lock_payload['summary']['excluded_blocks']) or 'none'}",
        f"- ranking_top_item: {lock_payload['summary']['ranking_top_item'] or 'none'}",
        f"- ranking_input_source: {lock_payload['summary']['ranking_input_source'] or 'none'}",
    ]
    MD_OUT.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return lock_payload


def main() -> int:
    payload = generate_baseline_lock_report()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
