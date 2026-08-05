from __future__ import annotations

from generic_inference_block_ai.src.gib_alpha3_validator import (
    validate_alpha3_contract,
    write_alpha3_validation_report,
)


def main() -> None:
    report_path = write_alpha3_validation_report()
    report = validate_alpha3_contract()
    print("GIB_ALPHA3_RUNTIME_STATUS=" + report["final_status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("EXECUTION_ALLOWED=" + str(report["execution_allowed"]).lower())
    print("CREDENTIAL_ACCESS_ALLOWED=" + str(report["credential_access_allowed"]).lower())
    print("WORDPRESS_WRITE_ALLOWED=" + str(report["wordpress_write_allowed"]).lower())
    print("REAL_LLM_CALL_ALLOWED=" + str(report["real_llm_call_allowed"]).lower())
    print("ACTIVE_RUNTIME_LOCKED=" + report["active_runtime_locked"])
    print("ALL_SAMPLES_FULLY_VALID=" + str(report["all_samples_fully_valid"]).lower())
    print("ALL_SAMPLES_NO_RUNTIME_CALL=" + str(report["all_samples_no_runtime_call"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
