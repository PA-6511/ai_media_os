from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ops.release_readiness_builder import build_release_readiness
from ops.release_readiness_writer import (
    DEFAULT_HISTORY_PATH,
    DEFAULT_JSON_PATH,
    DEFAULT_MD_PATH,
    append_release_readiness_history,
    write_release_readiness_json,
    write_release_readiness_md,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="運用リリース判定サマリーを生成する")
    parser.add_argument(
        "--format",
        choices=["pretty", "json"],
        default="pretty",
        help="標準出力の形式 (pretty/json)",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_PATH,
        help=f"JSON 出力先 (default: {DEFAULT_JSON_PATH})",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=DEFAULT_MD_PATH,
        help=f"Markdown 出力先 (default: {DEFAULT_MD_PATH})",
    )
    parser.add_argument(
        "--history-output",
        type=Path,
        default=DEFAULT_HISTORY_PATH,
        help=f"履歴 JSONL 出力先 (default: {DEFAULT_HISTORY_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        summary = build_release_readiness()
        json_path = write_release_readiness_json(summary, output_path=args.json_output)
        md_path = write_release_readiness_md(summary, output_path=args.md_output)
        history_path = append_release_readiness_history(summary, output_path=args.history_output)

        print(f"release readiness json: {json_path}")
        print(f"release readiness md:   {md_path}")
        print(f"release readiness history: {history_path}")

        if args.format == "json":
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print("=" * 72)
            print("AI Media OS Release Readiness")
            print("=" * 72)
            print(f"decision: {summary.get('decision')}")
            print(f"anomaly_overall: {summary.get('anomaly_overall')}")
            print(f"health: {summary.get('health_score')} ({summary.get('health_grade')})")
            print(f"retry_queued: {summary.get('retry_queued')}")
            print(f"integrity_overall: {summary.get('integrity_overall')}")
            print(f"latest_daily_report: {summary.get('latest_daily_report')}")
            print(f"latest_archive: {summary.get('latest_archive')}")
            print("reasons:")
            for reason in summary.get("reasons", []):
                print(f"- {reason}")
            print(f"recommended_action: {summary.get('recommended_action')}")

        decision = str(summary.get("decision", "review")).lower()
        if decision == "release":
            return 0
        if decision == "review":
            return 1
        return 2
    except Exception as exc:
        print(f"release readiness check failed: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
