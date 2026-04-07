from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ops.recovery_summary_builder import build_recovery_summary, format_recovery_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="復旧用の一次確認サマリーを表示する")
    parser.add_argument(
        "--format",
        choices=["pretty", "json"],
        default="pretty",
        help="出力形式 (pretty/json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="出力先ファイル。未指定なら標準出力のみ",
    )
    args = parser.parse_args(argv)

    try:
        summary = build_recovery_summary()
        if args.format == "json":
            rendered = json.dumps(summary, ensure_ascii=False, indent=2)
        else:
            rendered = format_recovery_summary(summary)

        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
            print(f"recovery summary written: {args.output}")

        print(rendered)
        return 0
    except Exception as exc:
        print(f"recovery check failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())