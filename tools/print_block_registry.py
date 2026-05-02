from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from shared.block_manifest_registry import load_block_registry


def _status_label(valid: bool) -> str:
    return "valid" if valid else "invalid"


def format_block_registry_report(registry: dict[str, Any]) -> str:
    blocks = sorted(registry.get("blocks", []), key=lambda item: str(item.get("block_id", "")))
    summary = registry.get("summary", {})

    lines: list[str] = ["BLOCK REGISTRY"]
    for block in blocks:
        block_id = str(block.get("block_id", "unknown"))
        risk_level = str(block.get("risk_level", "unknown"))
        status = _status_label(bool(block.get("valid", False)))
        lines.append(f"- {block_id} | {risk_level} | {status}")

    lines.extend(
        [
            "",
            "summary:",
            f"total: {int(summary.get('total', 0))}",
            f"valid: {int(summary.get('valid', 0))}",
            f"invalid: {int(summary.get('invalid', 0))}",
            f"warnings: {int(summary.get('warnings', 0))}",
            f"errors: {int(summary.get('errors', 0))}",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print block manifest registry report")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw registry data as JSON",
    )
    args = parser.parse_args(argv)

    root_path = Path(args.root).resolve()
    registry = load_block_registry(str(root_path))
    if args.json:
        print(json.dumps(registry, ensure_ascii=False, indent=2))
    else:
        print(format_block_registry_report(registry))
    return 0


if __name__ == "__main__":
    sys.exit(main())