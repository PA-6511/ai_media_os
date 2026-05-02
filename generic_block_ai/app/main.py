from __future__ import annotations

import argparse
import json
from pathlib import Path

from .block_runner import GenericBlockRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generic Block AI safe runner (Phase G-1)")
    parser.add_argument(
        "--manifest",
        default=str(Path(__file__).resolve().parents[1] / "block_manifest.json"),
        help="Path to block_manifest.json",
    )
    parser.add_argument(
        "--policy",
        default=str(Path(__file__).resolve().parents[1] / "config" / "policy.json"),
        help="Path to policy.json",
    )
    parser.add_argument(
        "--actions-json",
        default="[]",
        help="JSON array of requested actions",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requested_actions = json.loads(args.actions_json)
    if not isinstance(requested_actions, list):
        raise ValueError("--actions-json must be a JSON array")

    runner = GenericBlockRunner(Path(args.manifest), Path(args.policy))
    result = runner.run(requested_actions=requested_actions)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
