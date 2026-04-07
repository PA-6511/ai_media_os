from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ops.archive_inspector import find_latest_archive, inspect_archive


def _print_summary(result: dict) -> None:
    summary = result.get("summary", {})
    entries = result.get("entries", [])

    print()
    print("=" * 70)
    print("アーカイブ検証結果")
    print("=" * 70)
    print(f"archive: {result.get('path', '')}")
    print(f"valid:   {result.get('is_valid', False)}")
    if result.get("bad_member"):
        print(f"bad member: {result.get('bad_member')}")
    print()
    print("◆ 集計")
    print(f"reports_count:      {summary.get('reports_count', 0)}")
    print(f"logs_count:         {summary.get('logs_count', 0)}")
    print(f"test_outputs_count: {summary.get('test_outputs_count', 0)}")
    print(f"db_count:           {summary.get('db_count', 0)}")
    print(f"total_entries:      {summary.get('total_entries', 0)}")
    print()
    print("◆ entries")
    for entry in entries:
        print(f"- {entry}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ops archive の中身を検証する")
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="検証対象 zip パス。未指定時は最新アーカイブを自動検出",
    )
    args = parser.parse_args(argv)

    try:
        archive_path = args.path if args.path is not None else find_latest_archive()
        result = inspect_archive(archive_path)
        _print_summary(result)
        return 0 if result.get("is_valid", False) else 1
    except Exception as exc:
        print(f"archive inspect failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
