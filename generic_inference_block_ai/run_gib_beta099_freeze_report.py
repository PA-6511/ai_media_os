from __future__ import annotations

from generic_inference_block_ai.src.gib_beta099_freeze_report import (
    build_freeze_report,
    write_freeze_report,
)


def main() -> None:
    report_path = write_freeze_report()
    report = build_freeze_report()
    safety = report["safety_summary"]

    print("GIB_FREEZE_REPORT_STATUS=" + ("PASS" if report["all_pass"] else "FAIL"))
    print("REPORT_TYPE=" + report["report_type"])
    print("PHASE_COUNT=" + str(report["phase_count"]))
    print("REAL_LLM_CALL_ALLOWED=" + str(safety["real_llm_call_allowed"]).lower())
    print("EXECUTION_ALLOWED=" + str(safety["execution_allowed"]).lower())
    print("GENERATE_CALL_ALLOWED=" + str(safety["generate_call_allowed"]).lower())
    print("CHAT_CALL_ALLOWED=" + str(safety["chat_call_allowed"]).lower())
    print("CAN_EXECUTE_NOW=" + str(safety["can_execute_now"]).lower())
    print("RELEASE_RECOMMENDATION=" + report["release_recommendation"])
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
