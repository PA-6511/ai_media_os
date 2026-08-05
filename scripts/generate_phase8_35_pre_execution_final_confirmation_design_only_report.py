#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_JSON = ROOT / "exchange/logs/phase8_35_pre_execution_final_confirmation_design_only_result.json"
REPORT_JSON = ROOT / "exchange/logs/phase8_35_pre_execution_final_confirmation_design_only_report.json"
REPORT_MD = ROOT / "exchange/logs/phase8_35_pre_execution_final_confirmation_design_only_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    result = _load(RESULT_JSON)

    report = {
        "phase": result.get("phase"),
        "phase_name": result.get("phase_name"),
        "final_status": result.get("final_status"),
        "production_status": result.get("production_status"),
        "execution": result.get("execution"),
        "design_only": bool(result.get("design_only", True)),
        "phase8_29_to_8_31_pack_status": result.get("phase8_29_to_8_31_pack_status"),
        "phase8_32_to_8_34_pack_status": result.get("phase8_32_to_8_34_pack_status"),
        "credentials_ready": bool(result.get("credentials_ready", False)),
        "credentials_not_ready": bool(result.get("credentials_not_ready", False)),
        "stop_required": bool(result.get("stop_required", False)),
        "execution_allowed": False,
        "wordpress_api_call_not_executed": not bool(result.get("wordpress_api_call_attempted", False)),
        "wordpress_write_not_executed": not bool(result.get("wordpress_write_executed", False)),
        "draft_creation_not_executed": not bool(result.get("wordpress_draft_created", False)),
        "actual_go_decision_issued": False,
        "handoff_evidence_generated_for_execution": False,
        "next_step": result.get("next_step"),
    }

    _write(REPORT_JSON, report)

    md = [
        "# Phase 8-35 Pre-execution Final Confirmation Report",
        "",
        "## Final",
        f"- final_status: {report['final_status']}",
        f"- phase8_29_to_8_31_pack_status: {report['phase8_29_to_8_31_pack_status']}",
        f"- phase8_32_to_8_34_pack_status: {report['phase8_32_to_8_34_pack_status']}",
        f"- credentials_ready: {report['credentials_ready']}",
        f"- credentials_not_ready: {report['credentials_not_ready']}",
        f"- stop_required: {report['stop_required']}",
        "",
        "## Safety",
        f"- production_status: {report['production_status']}",
        f"- execution: {report['execution']}",
        f"- DESIGN_ONLY: {report['design_only']}",
        f"- WordPress API call not executed: {report['wordpress_api_call_not_executed']}",
        f"- WordPress write not executed: {report['wordpress_write_not_executed']}",
        f"- draft creation not executed: {report['draft_creation_not_executed']}",
        f"- execution_allowed=false: {report['execution_allowed'] is False}",
        f"- actual_go_decision_issued=false: {report['actual_go_decision_issued'] is False}",
        f"- handoff_evidence_generated_for_execution=false: {report['handoff_evidence_generated_for_execution'] is False}",
        "",
        "## Next step",
        f"- {report['next_step']}",
    ]

    REPORT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
