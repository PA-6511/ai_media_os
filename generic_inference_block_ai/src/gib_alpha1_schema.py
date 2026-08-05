"""
Lightweight JSON Schema validator for GIB-alpha1.

Supports a strict subset of JSON Schema:
  type, required, properties (with nested type / items), additionalProperties.

No external libraries are used.  This module performs validation only;
it never calls any network, filesystem (beyond reading schema files), or system API.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Map JSON Schema type names to Python types
_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string":  str,
    "array":   list,
    "boolean": bool,
    "object":  dict,
    "integer": int,
    "number":  (int, float),
}

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
INPUT_SCHEMAS_PATH  = _ROOT / "config" / "gib_alpha1_input_schemas.json"
OUTPUT_SCHEMAS_PATH = _ROOT / "config" / "gib_alpha1_output_schemas.json"


# ── core validator ────────────────────────────────────────────────────────────

def validate_value(value: Any, schema: dict[str, Any], path: str = "") -> list[str]:
    """Recursively validate *value* against *schema*.  Returns list of issue strings."""
    issues: list[str] = []
    prefix = f"{path}: " if path else ""

    # type check
    expected_type_name = schema.get("type")
    if expected_type_name is not None:
        expected = _TYPE_MAP.get(expected_type_name)
        if expected is None:
            issues.append(f"{prefix}unknown schema type '{expected_type_name}'")
        elif isinstance(value, bool) and expected_type_name in ("integer", "number"):
            # bool is a subclass of int in Python; reject it for numeric types explicitly
            issues.append(f"{prefix}expected {expected_type_name}, got bool")
        elif not isinstance(value, expected):
            issues.append(
                f"{prefix}expected {expected_type_name}, got {type(value).__name__}"
            )

    if not isinstance(value, dict):
        # array items check
        if isinstance(value, list) and "items" in schema:
            item_schema = schema["items"]
            for i, item in enumerate(value):
                issues.extend(validate_value(item, item_schema, f"{path}[{i}]"))
        return issues

    # object checks
    required_fields: list[str] = schema.get("required", [])
    for field in required_fields:
        if field not in value:
            issues.append(f"{prefix}missing required field '{field}'")

    properties: dict[str, Any] = schema.get("properties", {})
    for field, field_schema in properties.items():
        if field in value:
            issues.extend(validate_value(value[field], field_schema, f"{path}.{field}" if path else field))

    if schema.get("additionalProperties") is False:
        extra = set(value.keys()) - set(properties.keys())
        if extra:
            issues.append(f"{prefix}unexpected fields: {sorted(extra)}")

    return issues


def validate_object(data: Any, schema: dict[str, Any]) -> list[str]:
    """Top-level entry point; validates *data* against *schema*."""
    return validate_value(data, schema)


# ── schema file loading ───────────────────────────────────────────────────────

def load_schema_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Schema file root must be an object: {path}")
    return data


def load_input_schemas(path: Path | None = None) -> dict[str, Any]:
    return load_schema_file(path or INPUT_SCHEMAS_PATH)


def load_output_schemas(path: Path | None = None) -> dict[str, Any]:
    return load_schema_file(path or OUTPUT_SCHEMAS_PATH)


# ── convenience helpers ───────────────────────────────────────────────────────

def get_task_input_schema(task_type: str, input_schemas: dict[str, Any]) -> dict[str, Any]:
    schemas = input_schemas.get("task_schemas", {})
    if task_type not in schemas:
        raise KeyError(f"No input schema defined for task_type: {task_type}")
    return schemas[task_type]


def get_task_output_schema(task_type: str, output_schemas: dict[str, Any], blocked: bool = False) -> dict[str, Any]:
    if blocked:
        return output_schemas["blocked_output_schema"]
    schemas = output_schemas.get("task_schemas", {})
    if task_type not in schemas:
        raise KeyError(f"No output schema defined for task_type: {task_type}")
    return schemas[task_type]


def validate_task_input(task_type: str, data: Any, input_schemas: dict[str, Any]) -> list[str]:
    schema = get_task_input_schema(task_type, input_schemas)
    return validate_object(data, schema)


def validate_task_output(task_type: str, data: Any, output_schemas: dict[str, Any], blocked: bool = False) -> list[str]:
    schema = get_task_output_schema(task_type, output_schemas, blocked=blocked)
    return validate_object(data, schema)
