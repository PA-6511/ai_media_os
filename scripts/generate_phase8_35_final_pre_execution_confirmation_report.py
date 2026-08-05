#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_JSON = ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_result.json"
REPORT_JSON = ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.json"
REPORT_MD = ROOT / "exchange/logs/phase8_35_final_pre_execution_confirmation_report.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    result = load_json(RESULT_JSON)

    report = {
        "phase": result.get("phase"),
        "phase_name": result.get("phase_name"),
        "phase_status": result.get("phase_status"),
        "final_status": result.get("final_status"),
        "production_status": result.get("production_status"),
        "execution": result.get("execution"),
        "final_pre_execution_confirmation_executed": bool(result.get("final_pre_execution_confirmation_executed", False)),
        "previous_phase8_29_to_8_31_pack_status": result.get("previous_phase8_29_to_8_31_pack_status"),
        "previous_phase8_32_to_8_34_pack_status": result.get("previous_phase8_32_to_8_34_pack_status"),
        "credentials_ready": bool(result.get("credentials_ready", False)),
        "credentials_not_ready": bool(result.get("credentials_not_ready", False)),
        "execution_allowed": False,
        "wordpress_api_call_not_executed": not bool(result.get("wordpress_api_call_attempted", False)),
        "wordpress_write_not_executed": not bool(result.get("wordpress_write_executed", False)),
        "draft_creation_not_executed": not bool(result.get("wordpress_draft_created", False)),
        "actual_go_decision_issued": False,
        "handoff_evidence_generated_for_execution": False,
        "production_remains_no_go": result.get("production_status") == "NO_GO",
        "no_secret_values_output": result.get("secret_values_output") is False
        and result.get("secret_values_written") is False
        and result.get("secret_values_logged") is False,
        "next_step": result.get("next_step"),
    }

    write_json(REPORT_JSON, report)

    md = [
        "# Phase 8-35 Final Pre-execution Confirmation Report",
        "",
        "## Phase 8-35 summary",
        "- This phase confirms readiness before one-shot draft creation dry-run handoff.",
        "- This phase does not execute WordPress operations.",
        "",
        "## Final",
        f"- final_status: {report['final_status']}",
        f"- previous Phase 8-29〜8-31 pack status: {report['previous_phase8_29_to_8_31_pack_status']}",
        f"- previous Phase 8-32〜8-34 pack status: {report['previous_phase8_32_to_8_34_pack_status']}",
        f"- credentials_ready: {report['credentials_ready']}",
        f"- credentials_not_ready: {report['credentials_not_ready']}",
        "",
        "## Safety",
        f"- execution_allowed=false: {report['execution_allowed'] is False}",
        f"- WordPress API call not executed: {report['wordpress_api_call_not_executed']}",
        f"- WordPress write not executed: {report['wordpress_write_not_executed']}",
        f"- draft creation not executed: {report['draft_creation_not_executed']}",
        f"- actual_go_decision_issued=false: {report['actual_go_decision_issued'] is False}",
        f"- handoff_evidence_generated_for_execution=false: {report['handoff_evidence_generated_for_execution'] is False}",
        f"- production remains NO_GO: {report['production_remains_no_go']}",
        f"- no secret values output: {report['no_secret_values_output']}",
        "",
        "## Next step",
        f"- {report['next_step']}",
    ]

    REPORT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
