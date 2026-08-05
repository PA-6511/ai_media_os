from __future__ import annotations

from generic_inference_block_ai.src.gib_beta1_prep_validator import (
    validate_beta1_prep_contract,
    write_beta1_prep_report,
)


def main() -> None:
    report_path = write_beta1_prep_report()
    report = validate_beta1_prep_contract()

    print("GIB_BETA1_PREP_STATUS=" + report["final_status"])
    print("PHASE_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("TARGET_RUNTIME=" + report["target_runtime"])
    print("TARGET_HOST=" + report["target_host"])
    print("TARGET_MODEL=" + report["target_model"])
    print("BETA099_PREREQ_OK=" + str(report["beta099_prereq_ok"]).lower())
    print("CONSTRAINTS_OK=" + str(report["constraints_ok"]).lower())
    print("REAL_LLM_CALL_ALLOWED=" + str(report["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(report["execution_allowed"]).lower())
    print("CAN_EXECUTE_NOW=" + str(report["can_execute_now"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
