from __future__ import annotations

from generic_inference_block_ai.src.gib_beta07_validator import (
    validate_beta07_contract,
    write_beta07_validation_report,
)


def main() -> None:
    report_path = write_beta07_validation_report()
    report = validate_beta07_contract()

    print("GIB_BETA07_STATUS=" + report["final_status"])
    print("BETA_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("REAL_LLM_CALL_ALLOWED=" + str(report["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(report["execution_allowed"]).lower())
    print("BASE_READY_CONDITIONS_OK=" + str(report["base_ready_conditions_ok"]).lower())
    print("SIMULATED_READY_CONDITIONS_OK=" + str(report["simulated_ready_conditions_ok"]).lower())
    print("AUTO_CONNECT_ON_READY=" + str(report["auto_connect_on_ready"]).lower())
    print("AUTO_CONNECT_TRIGGERED=" + str(report["auto_connect_triggered"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
