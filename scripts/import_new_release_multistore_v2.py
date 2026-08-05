from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from src.new_release_multistore_input import import_multistore_csv, write_import_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import new release multi-store CSV V2 without external network access.")
    parser.add_argument("csv_path", help="Input CSV path")
    parser.add_argument("--repo-root", required=True, help="Artifact output root directory")
    parser.add_argument("--strict", action="store_true", help="Return exit code 3 when blocked rows are present")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = import_multistore_csv(args.csv_path)
        if result["structure_errors"]:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2

        artifacts = write_import_artifacts(result, args.repo_root)
        output = {
            **result,
            "artifacts": artifacts,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if args.strict and result["blocked_count"] > 0:
            return 3
        return 0
    except FileNotFoundError:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "message": "Input CSV file was not found.",
                    "wordpress_write_performed": False,
                    "wordpress_publish_performed": False,
                    "external_network_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "message": str(exc),
                    "wordpress_write_performed": False,
                    "wordpress_publish_performed": False,
                    "external_network_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())