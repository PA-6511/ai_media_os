from __future__ import annotations

from generic_inference_block_ai.src.gib_beta1_prep_audit_index import (
    build_beta1_prep_audit_index,
    write_beta1_prep_audit_index,
)


def main() -> None:
    output_path = write_beta1_prep_audit_index()
    report = build_beta1_prep_audit_index()

    continuity = report["guardrail_continuity"]

    print("GIB_BETA1_PREP_A_STATUS=" + report["final_status"])
    print("REPORT_TYPE=" + report["report_type"])
    print("PHASE=" + report["phase"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("REPORT_COUNT=" + str(report["report_count"]))
    print("REFERENCE_REPORTS_READY=" + str(report["reference_reports_ready"]).lower())
    print("ALL_REAL_LLM_CALL_ALLOWED_FALSE=" + str(continuity["all_real_llm_call_allowed_false"]).lower())
    print("ALL_EXECUTION_ALLOWED_FALSE=" + str(continuity["all_execution_allowed_false"]).lower())
    print("ALL_CAN_EXECUTE_NOW_FALSE=" + str(continuity["all_can_execute_now_false"]).lower())
    print("REPORT_PATH=" + str(output_path))


if __name__ == "__main__":
    main()
