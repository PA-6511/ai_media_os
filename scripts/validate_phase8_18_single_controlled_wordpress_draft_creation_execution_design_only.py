#!/usr/bin/env python3
from pathlib import Path

from phase8_design_only_pack_common import validate_design_only_phase

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_result.json"


def main() -> int:
    result = validate_design_only_phase(
        policy_path=DEFAULT_POLICY,
        request_path=DEFAULT_REQUEST,
        output_json_path=DEFAULT_OUTPUT_JSON,
        fallback_next_step="phase8_19_post_draft_creation_verification_design_only",
    )
    print(result)
    return 0 if result.get("final_status") == "DESIGN_ONLY_EXECUTION_SPEC_READY_NO_EXECUTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
