#!/usr/bin/env python3
from pathlib import Path

from phase8_design_only_pack_common import build_design_only_report, build_design_only_report_markdown, load_json, write_json

ROOT = Path(__file__).resolve().parents[1]
RESULT_JSON = ROOT / "exchange/logs/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_result.json"
REPORT_JSON = ROOT / "exchange/logs/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_report.json"
REPORT_MD = ROOT / "exchange/logs/phase8_18_single_controlled_wordpress_draft_creation_execution_design_only_report.md"


def main() -> int:
    result = load_json(RESULT_JSON)
    report = build_design_only_report(result)
    write_json(REPORT_JSON, report)
    REPORT_MD.write_text(build_design_only_report_markdown(report), encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
