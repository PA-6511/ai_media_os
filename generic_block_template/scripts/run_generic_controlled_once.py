#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs/generic_controlled_once_result.json"
CONTROLLED_POLICY = ROOT / "config/controlled_run_policy.json"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_sample_runner() -> Any:
    run_py = ROOT / "blocks/sample_block/run.py"
    spec = importlib.util.spec_from_file_location("generic_sample_block_run", run_py)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load sample block runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_once(target_block: str = "sample_block") -> Dict[str, Any]:
    policy = _load_json(CONTROLLED_POLICY)

    if target_block != "sample_block":
        result = {
            "status": "FAIL",
            "reason": "only sample_block is allowed in R-3 v1",
            "target_block": target_block,
            "mode": "DRY_RUN",
            "production_status": "NO_GO",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    if policy.get("dry_run_only") is not True:
        result = {
            "status": "FAIL",
            "reason": "controlled_run_policy.dry_run_only must be true",
            "target_block": target_block,
            "mode": "UNKNOWN",
            "production_status": "NO_GO",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    module = _load_sample_runner()
    payload = module.run_sample_block()
    payload.update(
        {
            "target_block": target_block,
            "run_type": "CONTROLLED_ONCE",
            "policy_enforced": True,
            "evidence_recorded": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    result = run_once("sample_block")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
