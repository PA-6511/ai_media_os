#!/usr/bin/env python3
from pathlib import Path

from phase8_pre_execution_approval_pack_common import build_phase_report, build_phase_report_md, load_json, write_json

ROOT = Path(__file__).resolve().parents[1]
RESULT_JSON = ROOT / "exchange/logs/phase8_31_human_execution_approval_validation_handoff_result.json"
REPORT_JSON = ROOT / "exchange/logs/phase8_31_human_execution_approval_validation_handoff_report.json"
REPORT_MD = ROOT / "exchange/logs/phase8_31_human_execution_approval_validation_handoff_report.md"


def main() -> int:
    result = load_json(RESULT_JSON)
    report = build_phase_report(result)
    write_json(REPORT_JSON, report)
    REPORT_MD.write_text(
        build_phase_report_md(
            report,
            "Phase 8-31 Human execution approval validation handoff report",
        ),
        encoding="utf-8",
    )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
