from __future__ import annotations

from generic_inference_block_ai.src.gib_alpha_demo import (
    run_demo_no_execution,
    write_demo_report,
)


def main() -> None:
    report_path = write_demo_report()
    report = run_demo_no_execution()
    print("GIB_ALPHA_DEMO_STATUS=" + report["final_status"])
    print("PRODUCTION_STATUS=" + report["production_status"])
    print("EXECUTION_ALLOWED=" + str(report["execution_allowed"]).lower())
    print("REAL_LLM_CALL_ALLOWED=" + str(report["real_llm_call_allowed"]).lower())
    print("CREDENTIAL_ACCESS_ALLOWED=" + str(report["credential_access_allowed"]).lower())
    print("WORDPRESS_WRITE_ALLOWED=" + str(report["wordpress_write_allowed"]).lower())
    print("RESPONSE_COUNT=" + str(len(report["responses"])))
    print("REPORT_PATH=" + str(report_path))


if __name__ == "__main__":
    main()
