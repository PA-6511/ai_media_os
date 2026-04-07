from __future__ import annotations

import argparse
import json
import sys

from ops.release_readiness_history_reader import (
    format_release_readiness_history,
    load_release_readiness_history,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="release readiness 履歴を表示する",
        prog="python3 -m ops.run_release_readiness_history_show",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="表示件数 (default: 10)",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="JSON 形式で出力 (--format json と同義)",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=["text", "json"],
        default=None,
        metavar="FORMAT",
        help="出力形式: text/json。--json と同時指定時は --format を優先",
    )
    return parser


def _resolve_output_format(args: argparse.Namespace) -> str:
    if args.fmt is not None:
        return args.fmt
    if args.as_json:
        return "json"
    return "text"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    output_format = _resolve_output_format(args)
    rows = load_release_readiness_history(limit=args.limit)

    if output_format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(format_release_readiness_history(rows))

    return 0


if __name__ == "__main__":
    sys.exit(main())
