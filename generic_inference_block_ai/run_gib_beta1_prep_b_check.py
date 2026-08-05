from __future__ import annotations

from generic_inference_block_ai.src.gib_beta1_prep_b_validator import (
    validate_beta1_prep_b_contract,
    write_beta1_prep_b_validation_report,
)


def main() -> None:
    output_path = write_beta1_prep_b_validation_report()
    report = validate_beta1_prep_b_contract()

    print("GIB_BETA1_PREP_B_STATUS=" + report["final_status"])
    print("REPORT_TYPE=" + report["report_type"])
    print("PHASE_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("OUTPUT_SCOPE=" + report["output_scope"])
    print("PREREQUISITES_OK=" + str(report["prerequisites_ok"]).lower())
    print("PROTOCOL_OK=" + str(report["protocol_ok"]).lower())
    print("NON_EXECUTION_OK=" + str(report["non_execution_ok"]).lower())
    print("REAL_LLM_CALL_ALLOWED=" + str(report["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(report["execution_allowed"]).lower())
    print("GENERATE_CALL_ALLOWED=" + str(report["generate_call_allowed"]).lower())
    print("CHAT_CALL_ALLOWED=" + str(report["chat_call_allowed"]).lower())
    print("CAN_EXECUTE_NOW=" + str(report["can_execute_now"]).lower())
    print("REPORT_PATH=" + str(output_path))


if __name__ == "__main__":
    main()
