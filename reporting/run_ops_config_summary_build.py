from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reporting.ops_config_summary_builder import build_ops_config_summary
from reporting.ops_config_summary_writer import (
    DEFAULT_OPS_CONFIG_SUMMARY_JSON_PATH,
    write_ops_config_summary_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ops config summary JSON を生成する")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OPS_CONFIG_SUMMARY_JSON_PATH,
        help=f"JSON 出力先 (default: {DEFAULT_OPS_CONFIG_SUMMARY_JSON_PATH})",
    )
    args = parser.parse_args(argv)

    try:
        payload = build_ops_config_summary()
        output_path = write_ops_config_summary_json(payload, output_path=args.output)
        print(f"ops config summary generated: {output_path}")
        return 0
    except Exception as exc:
        print(f"ops config summary build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())