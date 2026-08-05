from __future__ import annotations

from generic_inference_block_ai.src.gib_alpha2_validator import (
    validate_alpha2_contract,
    write_alpha2_validation_report,
)


def main() -> None:
    report_path = write_alpha2_validation_report()
    report = validate_alpha2_contract()
    print("GIB_ALPHA2_TEMPLATE_STATUS="    + report["final_status"])
    print("PRODUCTION_STATUS="             + report["production_status"])
    print("EXECUTION_ALLOWED="             + str(report["execution_allowed"]).lower())
    print("CREDENTIAL_ACCESS_ALLOWED="     + str(report["credential_access_allowed"]).lower())
    print("WORDPRESS_WRITE_ALLOWED="       + str(report["wordpress_write_allowed"]).lower())
    print("REAL_LLM_CALL_ALLOWED="         + str(report["real_llm_call_allowed"]).lower())
    print("TEMPLATE_CONFIG_VALID="         + str(report["template_config_valid"]).lower())
    print("ALL_SAMPLES_FULLY_VALID="       + str(report["all_samples_fully_valid"]).lower())
    print("TASK_TEMPLATE_COUNT="           + str(report["task_template_count"]))
    print("REPORT_PATH="                   + str(report_path))


if __name__ == "__main__":
    main()
