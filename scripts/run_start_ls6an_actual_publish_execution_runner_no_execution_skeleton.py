#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_READY = "LS6AN_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_SKELETON_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="exchange/runtime/start_ls6an_actual_publish_execution_runner_no_execution_skeleton_result.json",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_no_execution_runner_blueprint() -> dict[str, Any]:
    return {
        "runner_name": "start_ls6an_actual_publish_execution_runner_no_execution_skeleton",
        "execution_enabled": False,
        "network_call_enabled": False,
        "credential_read_enabled": False,
        "publish_enabled": False,
        "wordpress_write_enabled": False,
        "authorization_header_enabled": False,
        "requires_explicit_execute_now": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }


def main() -> int:
    args = parse_args()
    result = {
        "phase": "LS-6AN",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_SKELETON",
        "status": STATUS_READY,
        "blueprint": build_no_execution_runner_blueprint(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
