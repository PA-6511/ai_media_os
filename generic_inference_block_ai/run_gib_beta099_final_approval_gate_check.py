from __future__ import annotations

from generic_inference_block_ai.src.gib_beta099_validator import (
    validate_beta099_contract,
    write_beta099_validation_report,
)


def main() -> None:
    report_path = write_beta099_validation_report()
    report = validate_beta099_contract()

    print("GIB_BETA099_STATUS=" + report["final_status"])
    print("BETA_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("FINAL_APPROVAL_REQUIRED=" + str(report["final_approval_required"]).lower())
    print("FINAL_APPROVAL_GRANTED=" + str(report["final_approval_granted"]).lower())
    print("TARGET_RUNTIME=" + report["target_runtime"])
    print("TARGET_MODEL=" + report["target_model"])
    print("SWITCH_CONDITIONS_OK=" + str(report["switch_conditions_ok"]).lower())
    print("DENIED_SCENARIO_CALL_ALLOWED=" + str(report["denied_scenario"]["call_allowed"]).lower())
    print("APPROVED_SIM_SCENARIO_CALL_ALLOWED=" + str(report["approved_sim_scenario"]["call_allowed"]).lower())
    print("CAN_EXECUTE_NOW=" + str(report["can_execute_now"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
