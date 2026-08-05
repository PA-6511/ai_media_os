#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"

REQUIRED_FILES = [
    ROOT / "config/block_policy.json",
    ROOT / "config/approval_policy.json",
    ROOT / "config/controlled_run_policy.json",
    ROOT / "config/sale_flash_block_policy.json",
    ROOT / "blocks/sample_block/run.py",
    ROOT / "docs/runbooks/generic_block_runbook.md",
]


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_template(root: Path = ROOT) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"missing file: {path}")

    block_policy_path = root / "config/block_policy.json"
    approval_policy_path = root / "config/approval_policy.json"
    controlled_policy_path = root / "config/controlled_run_policy.json"
    sale_flash_policy_path = root / "config/sale_flash_block_policy.json"

    if block_policy_path.exists():
        try:
            block_policy = _load_json(block_policy_path)
            if block_policy.get("mode") != "DRY_RUN_ONLY":
                errors.append("block_policy.mode must be DRY_RUN_ONLY")
            if block_policy.get("production_status") != "NO_GO":
                errors.append("block_policy.production_status must be NO_GO")
            safety_flags = [
                "external_api_allowed",
                "external_network_allowed",
                "wordpress_allowed",
                "publish_allowed",
                "update_allowed",
                "delete_allowed",
                "export_allowed",
            ]
            for key in safety_flags:
                if block_policy.get(key) is not False:
                    errors.append(f"block_policy.{key} must be false")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid json block_policy: {exc}")

    if approval_policy_path.exists():
        try:
            approval_policy = _load_json(approval_policy_path)
            if approval_policy.get("allow_execute_when_pending") is not False:
                errors.append("approval_policy.allow_execute_when_pending must be false")
            if approval_policy.get("allow_execute_when_rejected") is not False:
                errors.append("approval_policy.allow_execute_when_rejected must be false")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid json approval_policy: {exc}")

    if controlled_policy_path.exists():
        try:
            controlled_policy = _load_json(controlled_policy_path)
            if controlled_policy.get("dry_run_only") is not True:
                errors.append("controlled_run_policy.dry_run_only must be true")
            if controlled_policy.get("enforce_sample_block_only") is not True:
                errors.append("controlled_run_policy.enforce_sample_block_only must be true")
            allowed = controlled_policy.get("allowed_target_blocks", [])
            if allowed != ["sample_block"]:
                warnings.append("allowed_target_blocks should be exactly ['sample_block']")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid json controlled_run_policy: {exc}")

    if sale_flash_policy_path.exists():
        try:
            sale_flash_policy = _load_json(sale_flash_policy_path)
            if sale_flash_policy.get("block_id") != "sale_flash_block":
                errors.append("sale_flash_block_policy.block_id must be sale_flash_block")
            if sale_flash_policy.get("lifecycle_phase") != "DESIGN_POLICY_ONLY":
                errors.append("sale_flash_block_policy.lifecycle_phase must be DESIGN_POLICY_ONLY")
            if sale_flash_policy.get("execution_enabled") is not False:
                errors.append("sale_flash_block_policy.execution_enabled must be false")
            if sale_flash_policy.get("dry_run_only") is not True:
                errors.append("sale_flash_block_policy.dry_run_only must be true")
            if sale_flash_policy.get("production_status") != "NO_GO":
                errors.append("sale_flash_block_policy.production_status must be NO_GO")

            safety_flags = [
                "external_api_allowed",
                "external_network_allowed",
                "wordpress_allowed",
                "publish_allowed",
                "update_allowed",
                "delete_allowed",
                "export_allowed",
            ]
            for key in safety_flags:
                if sale_flash_policy.get(key) is not False:
                    errors.append(f"sale_flash_block_policy.{key} must be false")
        except json.JSONDecodeError as exc:
            errors.append(f"invalid json sale_flash_block_policy: {exc}")

    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "status": status,
        "template_root": str(root),
        "errors": errors,
        "warnings": warnings,
        "checked_files": [str(p) for p in REQUIRED_FILES],
    }


def main() -> int:
    result = check_template()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
