from __future__ import annotations

from generic_inference_block_ai.src.gib_alpha45_validator import (
    validate_alpha45_contract,
    write_alpha45_validation_report,
)


def main() -> None:
    report_path = write_alpha45_validation_report()
    report = validate_alpha45_contract()
    guardrails = report["beta0_guardrails"]

    print("GIB_ALPHA45_STATUS=" + report["final_status"])
    print("DESIGN_STATUS=" + report["design_status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("BETA0_READY=" + str(report["beta0_ready"]).lower())
    print("CHECKLIST_VALID=" + str(report["checklist_valid"]).lower())
    print("ALL_DECISIONS_MADE=" + str(report["all_decisions_made"]).lower())
    print("MODEL_RUNTIME_ENABLED=" + str(guardrails["model_runtime_enabled"]).lower())
    print("REAL_LLM_CALL_ALLOWED=" + str(guardrails["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(guardrails["execution_allowed"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
