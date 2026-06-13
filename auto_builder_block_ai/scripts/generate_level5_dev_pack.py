#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
repo_root_str = str(REPO_ROOT)
if repo_root_str not in sys.path:
    sys.path.insert(0, repo_root_str)

from auto_builder_block_ai.src.level5_dev_pack_generator import generate_level5_dev_pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Level5 dry-run dev pack.")
    parser.add_argument("--phase-name", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--target-file", action="append", dest="target_files", required=True)
    parser.add_argument(
        "--validation-command",
        action="append",
        dest="validation_commands",
        required=True,
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = generate_level5_dev_pack(
        phase_name=args.phase_name,
        objective=args.objective,
        target_files=args.target_files,
        validation_commands=args.validation_commands,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())