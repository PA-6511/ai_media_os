from __future__ import annotations

from generic_inference_block_ai.src.gib_beta05_validator import (
    validate_beta05_contract,
    write_beta05_validation_report,
)


def main() -> None:
    report_path = write_beta05_validation_report()
    report = validate_beta05_contract()

    print("GIB_BETA05_STATUS=" + report["final_status"])
    print("BETA_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("REAL_LLM_CALL_ALLOWED=" + str(report["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(report["execution_allowed"]).lower())
    print("OLLAMA_BINARY_FOUND=" + str(report["ollama_binary_found"]).lower())
    print("ALL_ENDPOINTS_VALID=" + str(report["all_endpoints_valid"]).lower())
    print("MODEL_ALLOWED=" + str(report["model_allowed"]).lower())
    print("GENERATE_API_CALLED=" + str(report["generate_api_called"]).lower())
    print("CHAT_API_CALLED=" + str(report["chat_api_called"]).lower())
    print("READY_FOR_CONNECTING_STAGE=" + str(report["ready_for_connecting_stage"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
