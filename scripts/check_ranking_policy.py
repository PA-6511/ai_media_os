#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/ranking_policy.json"

REQUIRED_WEIGHTS = [
    "new_release_weight",
    "sale_weight",
    "author_weight",
    "publisher_weight",
]


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_policy(policy_path: Path = POLICY_PATH) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if not policy_path.exists():
        return {
            "status": "FAIL",
            "policy_path": str(policy_path),
            "errors": ["ranking_policy.json not found"],
            "warnings": [],
        }

    try:
        payload = _load_json(policy_path)
    except json.JSONDecodeError as exc:
        return {
            "status": "FAIL",
            "policy_path": str(policy_path),
            "errors": [f"invalid json: {exc}"],
            "warnings": [],
        }

    weights = payload.get("weights")
    if not isinstance(weights, dict):
        errors.append("weights must be an object")
        weights = {}

    total_weight = 0.0
    for key in REQUIRED_WEIGHTS:
        value = weights.get(key)
        if not isinstance(value, (int, float)):
            errors.append(f"missing or invalid weight: {key}")
            continue
        if value < 0:
            errors.append(f"weight must be >= 0: {key}")
        total_weight += float(value)

    if abs(total_weight - 1.0) > 1e-9:
        warnings.append(f"sum(weights) is {total_weight:.6f}, expected 1.0")

    formula = payload.get("score_formula")
    if not isinstance(formula, dict):
        errors.append("score_formula must be an object")
    else:
        expression = formula.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            errors.append("score_formula.expression must be non-empty string")

    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "status": status,
        "policy_path": str(policy_path),
        "errors": errors,
        "warnings": warnings,
        "checked_keys": REQUIRED_WEIGHTS,
        "execution": "validation_only",
    }


def main() -> int:
    result = check_policy()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
