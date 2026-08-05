from __future__ import annotations

from generic_inference_block_ai.src.gib_beta06_validator import (
    validate_beta06_contract,
    write_beta06_validation_report,
)


def main() -> None:
    report_path = write_beta06_validation_report()
    report = validate_beta06_contract()

    print("GIB_BETA06_STATUS=" + report["final_status"])
    print("BETA_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("RUNTIME_TARGET=" + report["runtime_target"])
    print("GUARDRAILS_OK=" + str(report["guardrails_ok"]).lower())
    print("READY_CONDITIONS_OK=" + str(report["ready_conditions_ok"]).lower())
    print("READY_FOR_CONNECTING_STAGE=" + str(report["ready_for_connecting_stage"]).lower())
    print("NO_GENERATE_CALL_REQUIRED=" + str(report["no_generate_call_required"]).lower())
    print("LOCALHOST_ONLY_REQUIRED=" + str(report["localhost_only_required"]).lower())
    print("ALLOWLIST_ENFORCED=" + str(report["allowlist_enforced"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
