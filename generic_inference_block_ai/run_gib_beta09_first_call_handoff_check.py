from __future__ import annotations

from generic_inference_block_ai.src.gib_beta09_validator import (
    validate_beta09_contract,
    write_beta09_validation_report,
)


def main() -> None:
    report_path = write_beta09_validation_report()
    report = validate_beta09_contract()

    print("GIB_BETA09_STATUS=" + report["final_status"])
    print("BETA_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("MANUAL_APPROVAL_REQUIRED=" + str(report["manual_approval_required"]).lower())
    print("MANUAL_APPROVAL_GRANTED=" + str(report["manual_approval_granted"]).lower())
    print("TARGET_RUNTIME=" + report["target_runtime"])
    print("TARGET_MODEL=" + report["target_model"])
    print("PROMOTION_CONDITIONS_DOCUMENTED=" + str(report["promotion_conditions_documented"]).lower())
    print("CAN_EXECUTE_NOW=" + str(report["can_execute_now"]).lower())
    print("BLOCKED_REASONS=" + ",".join(report["blocked_reasons"]))
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
