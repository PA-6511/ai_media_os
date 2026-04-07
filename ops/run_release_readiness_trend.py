from __future__ import annotations

import argparse
import json
import sys

from ops.release_readiness_trend_builder import build_release_readiness_trend
from ops.release_readiness_trend_writer import (
    write_release_readiness_trend_json,
    write_release_readiness_trend_md,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="release readiness 日次履歴サマリーを生成する",
        prog="python3 -m ops.run_release_readiness_trend",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        metavar="N",
        help="集計対象の日数 (default: 7, 0以下で全件)",
    )
    parser.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        help="JSON も保存する",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=["pretty", "json"],
        default="pretty",
        help="標準出力の形式 (pretty/json)",
    )
    return parser


def _render_pretty(summary: dict) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("AI Media OS Release Readiness Trend")
    lines.append("=" * 72)
    lines.append(f"generated_at: {summary.get('generated_at')}")
    lines.append(f"total_days:   {summary.get('total_days')}")
    lines.append(f"latest_decision: {summary.get('latest_decision')}")
    lines.append("")
    lines.append(
        "counts: "
        f"release={summary.get('release_count', 0)} "
        f"review={summary.get('review_count', 0)} "
        f"hold={summary.get('hold_count', 0)}"
    )
    lines.append("")
    lines.append("Recent Days")

    rows = summary.get("recent_days") if isinstance(summary.get("recent_days"), list) else []
    if rows:
        for idx, row in enumerate(rows, start=1):
            lines.append(
                f"[{idx}] {row.get('date', 'N/A')} "
                f"decision={row.get('decision', 'N/A')} "
                f"health={row.get('health_score', 'N/A')} "
                f"anomaly={row.get('anomaly_overall', 'N/A')}"
            )
    else:
        lines.append("(no records)")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        summary = build_release_readiness_trend(limit_days=args.days)
        md_path = write_release_readiness_trend_md(summary)
        print(f"release readiness trend md: {md_path}")

        if args.emit_json:
            json_path = write_release_readiness_trend_json(summary)
            print(f"release readiness trend json: {json_path}")

        if args.fmt == "json":
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(_render_pretty(summary))

        return 0
    except Exception as exc:
        print(f"release readiness trend failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
