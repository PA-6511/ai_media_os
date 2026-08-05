#!/usr/bin/env python3
from pathlib import Path

from phase8_post_credentials_ready_pack_common import build_phase_report, build_phase_report_md, load_json, write_json

ROOT = Path(__file__).resolve().parents[1]
RESULT_JSON = ROOT / "exchange/logs/phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only_result.json"
REPORT_JSON = ROOT / "exchange/logs/phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only_report.json"
REPORT_MD = ROOT / "exchange/logs/phase8_24_single_controlled_draft_creation_final_execution_authorization_design_only_report.md"


def main() -> int:
    result = load_json(RESULT_JSON)
    report = build_phase_report(result)
    write_json(REPORT_JSON, report)
    REPORT_MD.write_text(
        build_phase_report_md(
            report,
            "Phase 8-24 Single controlled draft creation final execution authorization design report",
        ),
        encoding="utf-8",
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
