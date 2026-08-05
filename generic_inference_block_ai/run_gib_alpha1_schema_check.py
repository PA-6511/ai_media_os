from __future__ import annotations

from generic_inference_block_ai.src.gib_alpha1_validator import (
    validate_alpha1_contract,
    write_alpha1_validation_report,
)


def main() -> None:
    report_path = write_alpha1_validation_report()
    report = validate_alpha1_contract()
    cov = report["schema_coverage"]
    print("GIB_ALPHA1_SCHEMA_STATUS="   + report["final_status"])
    print("PRODUCTION_STATUS="           + report["production_status"])
    print("EXECUTION_ALLOWED="           + str(report["execution_allowed"]).lower())
    print("CREDENTIAL_ACCESS_ALLOWED="   + str(report["credential_access_allowed"]).lower())
    print("WORDPRESS_WRITE_ALLOWED="     + str(report["wordpress_write_allowed"]).lower())
    print("REAL_LLM_CALL_ALLOWED="       + str(report["real_llm_call_allowed"]).lower())
    print("SCHEMA_COVERAGE_COMPLETE="    + str(cov["coverage_complete"]).lower())
    print("ALL_SAMPLES_SCHEMA_VALID="    + str(report["all_samples_schema_valid"]).lower())
    print("REPORT_PATH="                 + str(report_path))


if __name__ == "__main__":
    main()
