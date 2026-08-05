#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLOCKS_DIR = ROOT / "blocks"
LOG_DIR = ROOT / "logs"
SCAFFOLD_HISTORY_PATH = LOG_DIR / "scaffold_generation_history.json"


def _validate_name(name: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", name):
        raise ValueError("block_name must match ^[a-z][a-z0-9_]{2,63}$")
    return name


def _append_scaffold_history(entry: Dict[str, Any], history_path: Path = SCAFFOLD_HISTORY_PATH) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    else:
        history = []

    if not isinstance(history, list):
        history = []

    history.append(entry)
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def scaffold_block(block_name: str, blocks_dir: Path = DEFAULT_BLOCKS_DIR) -> Dict[str, Any]:
    block_name = _validate_name(block_name)
    target_dir = blocks_dir / block_name

    if target_dir.exists():
        result = {
            "status": "WARN",
            "reason": "block already exists",
            "block_name": block_name,
            "target_dir": str(target_dir),
            "scaffold_only": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _append_scaffold_history(result)
        return result

    target_dir.mkdir(parents=True, exist_ok=False)

    readme = target_dir / "README.md"
    run_py = target_dir / "run.py"

    readme.write_text(
        "\n".join(
            [
                f"# {block_name}",
                "",
                "Generated from generic_block_template v1.",
                "",
                "- scaffold only",
                "- DRY_RUN only",
                "- external API/network disabled",
                "- production_status is NO_GO",
                "",
                "Execution is not wired by default.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    run_py.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from datetime import datetime, timezone",
                "",
                "",
                "def run_block() -> dict:",
                "    return {",
                f"        \"block_id\": \"{block_name}\",",
                "        \"status\": \"WARN\",",
                "        \"mode\": \"DRY_RUN\",",
                "        \"production_status\": \"NO_GO\",",
                "        \"reason\": \"scaffold only; execution not enabled\",",
                "        \"created_at\": datetime.now(timezone.utc).isoformat(),",
                "    }",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = {
        "status": "PASS",
        "block_name": block_name,
        "target_dir": str(target_dir),
        "files": [str(readme), str(run_py)],
        "scaffold_only": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _append_scaffold_history(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new block from generic template")
    parser.add_argument("block_name", help="new block name")
    parser.add_argument("--blocks-dir", default=str(DEFAULT_BLOCKS_DIR), help="blocks base directory")
    args = parser.parse_args()

    try:
        result = scaffold_block(args.block_name, Path(args.blocks_dir))
    except ValueError as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
