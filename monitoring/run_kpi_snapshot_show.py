from __future__ import annotations

"""KPI スナップショット一覧表示コマンド。

使い方:
    python3 -m monitoring.run_kpi_snapshot_show
    python3 -m monitoring.run_kpi_snapshot_show --limit 5
    python3 -m monitoring.run_kpi_snapshot_show --json
    python3 -m monitoring.run_kpi_snapshot_show --format json --limit 5
    python3 -m monitoring.run_kpi_snapshot_show --format text --limit 5
    python3 -m monitoring.run_kpi_snapshot_show --all
    python3 -m monitoring.run_kpi_snapshot_show --all --format json
"""

import argparse
import json
import sys

from monitoring.kpi_snapshot_reader import (
    DEFAULT_KPI_SNAPSHOTS_PATH,
    format_kpi_snapshots,
    load_kpi_snapshots,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="KPI スナップショット一覧を表示する",
        prog="python3 -m monitoring.run_kpi_snapshot_show",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "例:\n"
            "  %(prog)s                        # 人間向け表示 (最新10件)\n"
            "  %(prog)s --limit 5              # 人間向け表示 (最新5件)\n"
            "  %(prog)s --json                 # JSON 出力\n"
            "  %(prog)s --format json          # JSON 出力 (--json と同義)\n"
            "  %(prog)s --format text --limit 3\n"
            "  %(prog)s --all --format json    # 全件 JSON 出力\n"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="表示件数 (default: 10、--all 指定時は無視)",
    )
    parser.add_argument(
        "--all",
        dest="show_all",
        action="store_true",
        help="全件表示 (--limit を無視)",
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
        help="出力形式: text (人間向け) または json (default: text)。--json と同時指定時は --format を優先",
    )
    return parser


def resolve_output_format(args: argparse.Namespace) -> str:
    """最終的な出力形式を "json" または "text" で返す。

    優先順位: --format > --json > デフォルト(text)
    --json と --format text を同時指定した場合は --format を優先し text を返す。
    """
    if args.fmt is not None:
        return args.fmt
    if args.as_json:
        return "json"
    return "text"


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    output_format = resolve_output_format(args)
    limit = 0 if args.show_all else args.limit

    snapshots = load_kpi_snapshots(limit=limit)

    if not DEFAULT_KPI_SNAPSHOTS_PATH.exists():
        print(
            f"KPI snapshots file not found: {DEFAULT_KPI_SNAPSHOTS_PATH}",
            file=sys.stderr,
        )
        print("Run `python3 -m monitoring.run_kpi_snapshot` to generate one.")
        return 0

    if output_format == "json":
        print(json.dumps(snapshots, ensure_ascii=False, indent=2))
    else:
        print(format_kpi_snapshots(snapshots))

    return 0


if __name__ == "__main__":
    sys.exit(main())
