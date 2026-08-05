#!/usr/bin/env python3
from pathlib import Path

from phase8_post_credentials_ready_pack_common import validate_post_credentials_ready_design_phase

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_23_post_credentials_ready_credential_revalidation_design_only_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_23_post_credentials_ready_credential_revalidation_design_only_request.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_23_post_credentials_ready_credential_revalidation_design_only_result.json"

PASS_STATUS = "DESIGN_ONLY_POST_CREDENTIALS_READY_REVALIDATION_SPEC_READY_NO_EXECUTION"


def main() -> int:
    result = validate_post_credentials_ready_design_phase(
        policy_path=DEFAULT_POLICY,
        request_path=DEFAULT_REQUEST,
        output_json_path=DEFAULT_OUTPUT,
        pass_status=PASS_STATUS,
        next_step_default="phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only",
        design_flags={
            "credential_revalidation_design_only": True,
            "final_execution_authorization_design_only": False,
            "one_shot_lock_design_only": False,
            "rollback_design_only": False,
            "post_run_evidence_design_only": False,
        },
    )
    print(result)
    return 0 if result.get("final_status") == PASS_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
