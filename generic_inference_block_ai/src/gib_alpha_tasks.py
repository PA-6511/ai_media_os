from __future__ import annotations

from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_policy import (
    load_json,
    REQUIRED_ALLOWED_TASK_TYPES,
)

REQUIRED_TASK_FIELDS: list[str] = [
    "description",
    "risk_level",
    "execution_effect",
    "input_contract",
    "output_contract",
]

ALLOWED_RISK_LEVELS: list[str] = ["low", "medium", "high"]


def validate_task_config(task_config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if task_config.get("schema_version") != "gib.alpha.tasks.v0.1":
        issues.append("schema_version must be gib.alpha.tasks.v0.1")

    tasks = task_config.get("tasks")
    if not isinstance(tasks, dict):
        return ["tasks must be an object"]

    configured_task_types = list(tasks.keys())
    if configured_task_types != REQUIRED_ALLOWED_TASK_TYPES:
        issues.append("tasks must match the fixed alpha task order and names")

    for task_type, definition in tasks.items():
        if not isinstance(definition, dict):
            issues.append(f"{task_type}: definition must be an object")
            continue
        for fname in REQUIRED_TASK_FIELDS:
            if fname not in definition:
                issues.append(f"{task_type}: missing field {fname}")
        if definition.get("risk_level") not in ALLOWED_RISK_LEVELS:
            issues.append(f"{task_type}: invalid risk_level")
        if definition.get("execution_effect") != "none":
            issues.append(f"{task_type}: execution_effect must be none")
        if not isinstance(definition.get("input_contract"), list):
            issues.append(f"{task_type}: input_contract must be a list")
        if not isinstance(definition.get("output_contract"), list):
            issues.append(f"{task_type}: output_contract must be a list")

    return issues


def load_and_validate_task_config(path: str | Path) -> dict[str, Any]:
    task_config = load_json(path)
    issues = validate_task_config(task_config)
    if issues:
        raise RuntimeError("GIB alpha task config validation failed: " + "; ".join(issues))
    return task_config


def get_task_definition(task_config: dict[str, Any], task_type: str) -> dict[str, Any]:
    tasks = task_config.get("tasks", {})
    if task_type not in tasks:
        raise ValueError(f"Unsupported task_type: {task_type}")
    return tasks[task_type]
