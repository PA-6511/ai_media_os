#!/usr/bin/env python3
from pathlib import Path

from phase8_pre_execution_approval_pack_common import build_phase_report, build_phase_report_md, load_json, write_json

ROOT = Path(__file__).resolve().parents[1]
RESULT_JSON = ROOT / "exchange/logs/phase8_30_final_preflight_before_single_controlled_draft_creation_result.json"
REPORT_JSON = ROOT / "exchange/logs/phase8_30_final_preflight_before_single_controlled_draft_creation_report.json"
REPORT_MD = ROOT / "exchange/logs/phase8_30_final_preflight_before_single_controlled_draft_creation_report.md"


def main() -> int:
    result = load_json(RESULT_JSON)
    report = build_phase_report(result)
    write_json(REPORT_JSON, report)
    REPORT_MD.write_text(
        build_phase_report_md(
            report,
            "Phase 8-30 Final preflight before single controlled draft creation report",
        ),
        encoding="utf-8",
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
