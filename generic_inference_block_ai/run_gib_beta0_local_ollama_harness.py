from __future__ import annotations

from generic_inference_block_ai.src.gib_beta0_validator import (
    validate_beta0_contract,
    write_beta0_validation_report,
)


def main() -> None:
    report_path = write_beta0_validation_report()
    report = validate_beta0_contract()
    flags = report["safety_flags"]

    print("GIB_BETA0_STATUS=" + report["final_status"])
    print("BETA_STATUS=" + report["status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("RUNTIME_TARGET=" + report["runtime_target"])
    print("PROBE_WOULD_CALL=" + str(report["probe_would_call"]).lower())
    print("PROBE_BLOCKED_REASON=" + str(report["probe_blocked_reason"]))
    print("REAL_LLM_CALL_ALLOWED=" + str(flags["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(flags["execution_allowed"]).lower())
    print("ALPHA45_ALL_DECISIONS_MADE=" + str(report["alpha45_all_decisions_made"]).lower())
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
