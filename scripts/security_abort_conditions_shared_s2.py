#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "security_shared_abort_conditions_phase_s2.json"


def _load_shared_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("shared abort config must be a JSON object")
    return data


def _walk_items(node: Any, path: str = "") -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            next_path = f"{path}.{key}" if path else str(key)
            items.append((next_path, value))
            items.extend(_walk_items(value, next_path))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            next_path = f"{path}[{idx}]"
            items.append((next_path, value))
            items.extend(_walk_items(value, next_path))
    return items


def evaluate_shared_abort_conditions(
    data: dict[str, Any],
    config_path: Path = CONFIG_PATH,
) -> list[str]:
    conf = _load_shared_config(config_path)
    reasons: list[str] = []

    for key in conf.get("abort_if_true", []):
        if data.get(key) is True:
            reasons.append(f"{key}=true is prohibited")

    abort_if_equals = conf.get("abort_if_equals", {})
    if isinstance(abort_if_equals, dict):
        for key, expected in abort_if_equals.items():
            if data.get(key) == expected:
                reasons.append(f"{key}={expected} is prohibited")

    forbidden_unlock_keys = set(conf.get("forbidden_unlock_keys", []))
    forbidden_env_output_flag_keys = set(conf.get("forbidden_env_output_flag_keys", []))

    for path, value in _walk_items(data):
        key_name = path.split(".")[-1]
        lower_key = key_name.lower()

        if key_name in forbidden_unlock_keys and value not in (None, "", False, 0, []):
            reasons.append(f"forbidden unlock field detected: {path}")

        if "unlock" in lower_key and "token" in lower_key and value not in (None, "", False, 0, []):
            reasons.append(f"unlock token detected: {path}")

        if key_name in forbidden_env_output_flag_keys:
            reasons.append(f"forbidden env output flag detected: {path}")

    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped
