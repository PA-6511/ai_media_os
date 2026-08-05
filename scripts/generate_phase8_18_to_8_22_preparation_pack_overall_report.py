#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_REPORTS = {
    "8-18": ROOT / "exchange/logs/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_report.json",
    "8-19": ROOT / "exchange/logs/phase8_19_post_draft_creation_verification_design_only_report.json",
    "8-20": ROOT / "exchange/logs/phase8_20_first_draft_creation_completion_report_design_only_report.json",
    "8-21": ROOT / "exchange/logs/phase8_21_post_credentials_ready_rehandoff_design_only_report.json",
    "8-22": ROOT / "exchange/logs/phase8_22_immediate_pre_execution_freeze_abort_gate_design_only_report.json",
}
OUTPUT_JSON = ROOT / "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.json"
OUTPUT_MD = ROOT / "exchange/logs/phase8_18_to_8_22_preparation_pack_overall_report.md"
PASS_STATUS = "PHASE8_18_TO_8_22_PREPARATION_PACK_PASS_DESIGN_ONLY_NO_EXECUTION"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    phase_reports: dict[str, dict] = {}
    missing = []
    for phase, path in INPUT_REPORTS.items():
        if not path.exists():
            missing.append(phase)
        else:
            phase_reports[phase] = _load_json(path)

    all_pass = True
    no_execution = True
    for payload in phase_reports.values():
        if str(payload.get("final_status", "")).startswith("ABORT"):
            all_pass = False
        no_execution = no_execution and (payload.get("execution_allowed") is False)
        no_execution = no_execution and bool(payload.get("wordpress_api_call_not_executed", True))
        no_execution = no_execution and bool(payload.get("wordpress_write_not_executed", True))
        no_execution = no_execution and bool(payload.get("draft_creation_not_executed", True))

    if missing:
        final_status = "ABORT_MISSING_EVIDENCE"
    elif all_pass and no_execution:
        final_status = PASS_STATUS
    else:
        final_status = "ABORT_POLICY_VIOLATION"

    report = {
        "phase_pack": "8-18_to_8-22",
        "phase_pack_name": "First controlled draft creation preparation pack",
        "final_status": final_status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "phase_reports_found": sorted(list(phase_reports.keys())),
        "missing_phase_reports": missing,
        "generated_at": _now_iso(),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Phase 8-18 to 8-22 Preparation Pack Overall Report",
        "",
        "## Final status",
        f"- final_status: {report['final_status']}",
        "",
        "## Safety",
        f"- production_status: {report['production_status']}",
        f"- execution: {report['execution']}",
        f"- execution_allowed: {report['execution_allowed']}",
        f"- wordpress_api_call_allowed: {report['wordpress_api_call_allowed']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- wordpress_draft_created: {report['wordpress_draft_created']}",
        "",
        "## Coverage",
        f"- phase_reports_found: {', '.join(report['phase_reports_found'])}",
        f"- missing_phase_reports: {', '.join(report['missing_phase_reports']) if report['missing_phase_reports'] else 'none'}",
    ]
    OUTPUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if final_status == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
