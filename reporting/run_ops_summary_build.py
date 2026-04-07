from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from reporting.ops_summary_builder import build_ops_summary
from reporting.ops_summary_writer import DEFAULT_OPS_SUMMARY_JSON_PATH, write_ops_summary_json


def _render_pretty(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=" * 76)
    lines.append("AI Media OS Ops Summary")
    lines.append("=" * 76)
    lines.append(f"generated_at: {summary.get('generated_at')}")
    lines.append("")
    lines.append("Latest Artifacts")
    lines.append(f"- daily_report_json:     {summary.get('latest_daily_report_json')}")
    lines.append(f"- weekly_report_json:    {summary.get('latest_weekly_report_json')}")
    lines.append(f"- monthly_report_json:   {summary.get('latest_monthly_report_json')}")
    lines.append(f"- dashboard:             {summary.get('latest_dashboard')}")
    lines.append(f"- weekly_dashboard:      {summary.get('latest_weekly_dashboard')}")
    lines.append(f"- monthly_dashboard:     {summary.get('latest_monthly_dashboard')}")
    lines.append(f"- archive:               {summary.get('latest_archive')}")
    lines.append(f"- artifact_index:        {summary.get('latest_artifact_index')}")
    lines.append(f"- ops_portal:            {summary.get('latest_ops_portal')}")
    lines.append(f"- ops_home:              {summary.get('latest_ops_home')}")
    lines.append("")
    lines.append("Release Readiness")
    lines.append(f"- decision:              {summary.get('release_decision')}")
    lines.append(f"- recommended_action:    {summary.get('release_recommended_action')}")
    lines.append("")
    lines.append("Release Trend")
    lines.append(
        "- counts: "
        f"release={summary.get('trend_release_count', 0)} "
        f"review={summary.get('trend_review_count', 0)} "
        f"hold={summary.get('trend_hold_count', 0)}"
    )
    lines.append(f"- total_days:            {summary.get('trend_total_days', 0)}")
    lines.append(f"- latest_decision:       {summary.get('trend_latest_decision', 'N/A')}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="運用集約サマリーJSONを生成する")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OPS_SUMMARY_JSON_PATH,
        help=f"JSON 出力先 (default: {DEFAULT_OPS_SUMMARY_JSON_PATH})",
    )
    parser.add_argument(
        "--format",
        choices=["pretty", "json"],
        default="pretty",
        help="標準出力の形式 (pretty/json)",
    )
    args = parser.parse_args(argv)

    try:
        summary = build_ops_summary()
        output_path = write_ops_summary_json(summary, output_path=args.output)
        print(f"ops summary json: {output_path}")

        if args.format == "json":
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(_render_pretty(summary))

        return 0
    except Exception as exc:
        print(f"ops summary build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
