#!/usr/bin/env python3
from pathlib import Path

from phase8_final_pre_execution_decision_pack_common import validate_final_pre_execution_decision_phase

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_28_final_pre_execution_handoff_evidence_design_only_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_28_final_pre_execution_handoff_evidence_design_only_request.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_28_final_pre_execution_handoff_evidence_design_only_result.json"

PASS_STATUS = "DESIGN_ONLY_FINAL_PRE_EXECUTION_HANDOFF_EVIDENCE_SPEC_READY_NO_EXECUTION"


def main() -> int:
    result = validate_final_pre_execution_decision_phase(
        policy_path=DEFAULT_POLICY,
        request_path=DEFAULT_REQUEST,
        output_json_path=DEFAULT_OUTPUT,
        pass_status=PASS_STATUS,
        next_step_default="phase8_16_equivalent_credential_readiness_recheck_or_final_preflight",
        design_flags={
            "credential_recheck_orchestration_design_only": False,
            "final_no_go_go_decision_rule_design_only": False,
            "final_pre_execution_handoff_evidence_design_only": True,
        },
    )
    print(result)
    return 0 if result.get("final_status") == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
