#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


VALIDATION_RESULT_PATH = ROOT / "exchange" / "logs" / "security_block_ai_isolation_design_phase_s4_validation_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_overall_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_overall_result.md"


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON object required")
    return data


def generate_security_phase_s4_overall_result(
    validation_result_path: Path = VALIDATION_RESULT_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict:
    validation = _load_json(Path(validation_result_path))
    validator_result = validation.get("validator_result")

    if validator_result == "ABORT":
        final_status = "ABORT"
    elif validator_result == "PASS":
        final_status = "PASS_DESIGN_ONLY"
    elif validator_result in {"WARN", "FAIL"}:
        final_status = "ISOLATION_DESIGN_REVIEW_REQUIRED"
    else:
        final_status = "ISOLATION_DESIGN_REVIEW_REQUIRED"

    result = {
        "phase_id": "PHASE_S4",
        "phase_name": "block_ai_isolation_design",
        "phase_status": "DESIGN_ONLY",
        "validator_result": validator_result,
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "isolation_design_only": True,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "executor_action_allowed": False,
        "s3_2_audit_verified": bool(validation.get("s3_2_audit_verified", False)),
        "next_step": "phase_s4_1_isolation_policy_dry_run_validation",
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Phase S-4 Overall Result",
        "",
        f"- validator_result: {result.get('validator_result')}",
        f"- final_status: {result.get('final_status')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- isolation_design_only: {result.get('isolation_design_only')}",
        f"- isolation_execution_allowed: {result.get('isolation_execution_allowed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- s3_2_audit_verified: {result.get('s3_2_audit_verified')}",
        f"- next_step: {result.get('next_step')}",
    ]
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = generate_security_phase_s4_overall_result()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["final_status"] in {"PASS_DESIGN_ONLY", "ISOLATION_DESIGN_REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
