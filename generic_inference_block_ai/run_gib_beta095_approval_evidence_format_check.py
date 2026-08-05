from __future__ import annotations

from generic_inference_block_ai.src.gib_beta095_validator import (
    validate_beta095_contract,
    write_beta095_validation_report,
)


def main() -> None:
    report_path = write_beta095_validation_report()
    report = validate_beta095_contract()

    print("GIB_BETA095_STATUS=" + report["final_status"])
    print("BETA_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("MANUAL_APPROVAL_REQUIRED=" + str(report["manual_approval_required"]).lower())
    print("REAL_LLM_CALL_ALLOWED=" + str(report["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(report["execution_allowed"]).lower())
    print("TOKEN_FORMAT_VALID=" + str(report["token_format_valid"]).lower())
    print("CHANGE_ID_FORMAT_VALID=" + str(report["change_id_format_valid"]).lower())
    print("SECRET_VALUE_HANDLING_ALLOWED=" + str(report["secret_value_handling_allowed"]).lower())
    print("BETA09_PREREQ_OK=" + str(report["beta09_prereq_ok"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
