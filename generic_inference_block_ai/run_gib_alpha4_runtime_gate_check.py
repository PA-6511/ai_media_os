from __future__ import annotations

from generic_inference_block_ai.src.gib_alpha4_validator import (
    validate_alpha4_contract,
    write_alpha4_validation_report,
)


def main() -> None:
    report_path = write_alpha4_validation_report()
    report = validate_alpha4_contract()

    flags = report["policy_flags"]
    print("GIB_ALPHA4_GATE_STATUS=" + report["final_status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("EXECUTION_MODE=" + report["execution_mode"])
    print("ACTIVE_RUNTIME_LOCK=" + report["active_runtime_lock"])
    print("MODEL_RUNTIME_ENABLED=" + str(flags["model_runtime_enabled"]).lower())
    print("REAL_LLM_CALL_ALLOWED=" + str(flags["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(flags["execution_allowed"]).lower())
    print("ALL_SCENARIOS_MATCH_EXPECTED=" + str(report["all_scenarios_match_expected"]).lower())
    print("HARD_BLOCK_FOR_NON_STUB_RUNTIME=" + str(report["hard_block_for_non_stub_runtime"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
