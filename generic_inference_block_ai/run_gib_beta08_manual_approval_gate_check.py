from __future__ import annotations

from generic_inference_block_ai.src.gib_beta08_validator import (
    validate_beta08_contract,
    write_beta08_validation_report,
)


def main() -> None:
    report_path = write_beta08_validation_report()
    report = validate_beta08_contract()

    print("GIB_BETA08_STATUS=" + report["final_status"])
    print("BETA_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("MANUAL_APPROVAL_REQUIRED=" + str(report["manual_approval_required"]).lower())
    print("APPROVAL_GRANTED=" + str(report["approval_granted"]).lower())
    print("REAL_LLM_CALL_ALLOWED=" + str(report["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(report["execution_allowed"]).lower())
    print("DENIED_SCENARIO_CALL_ALLOWED=" + str(report["denied_scenario"]["call_allowed"]).lower())
    print("APPROVED_SIM_SCENARIO_CALL_ALLOWED=" + str(report["approved_sim_scenario"]["call_allowed"]).lower())
    print("AUTO_CONNECT_TRIGGERED=" + str(report["auto_connect_triggered"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
