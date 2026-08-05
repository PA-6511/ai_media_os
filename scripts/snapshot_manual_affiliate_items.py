#!/usr/bin/env python3
"""Generate manual affiliate snapshot for Phase 8-50B hardening."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "manual_affiliate_builder" / "manual_items.example.json"
DEFAULT_OUTPUT = ROOT / "exchange" / "logs" / "phase8_50_manual_affiliate_snapshot.json"


PHASE_8_51_LOCK = {
    "phase": "Phase 8-51-MIGRATION-SKELETON",
    "execution_state": "UNEXECUTED",
    "lock": "NOT_STARTED_LOCKED",
    "execution_allowed": False,
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_snapshot(data: Dict[str, Any]) -> Dict[str, Any]:
    items = data.get("items", [])
    digest_src = json.dumps(items, ensure_ascii=False, sort_keys=True)
    checksum = hashlib.sha256(digest_src.encode("utf-8")).hexdigest()

    return {
        "phase": "Phase 8-50B",
        "status": "SNAPSHOT_GENERATED_DRY_RUN_ONLY",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "amazon_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "publish_allowed": False,
        "approval_token_consumed": False,
        "item_count": len(items),
        "items": items,
        "checksum": checksum,
        "next_phase_lock_state": PHASE_8_51_LOCK,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate manual affiliate snapshot")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input manual item JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output snapshot path")
    args = parser.parse_args()

    try:
        data = load_json(Path(args.input))
        snapshot = build_snapshot(data)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "phase": "Phase 8-50B",
                    "execution_mode": "DRY_RUN_ONLY",
                    "production_status": "NO_GO",
                    "publish_allowed": False,
                    "output": str(output),
                    "item_count": snapshot["item_count"],
                    "next_phase": snapshot["next_phase_lock_state"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "phase": "Phase 8-50B",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
