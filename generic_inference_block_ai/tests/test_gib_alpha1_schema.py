"""Unit tests for the GIB-alpha1 schema validator (pure logic, no I/O)."""
import pytest
from generic_inference_block_ai.src.gib_alpha1_schema import (
    validate_object,
    validate_task_input,
    validate_task_output,
    load_input_schemas,
    load_output_schemas,
)


# ── validate_object unit tests ────────────────────────────────────────────────

def test_valid_object_passes() -> None:
    schema = {
        "type": "object",
        "required": ["name", "count"],
        "properties": {
            "name":  {"type": "string"},
            "count": {"type": "integer"},
        },
        "additionalProperties": False,
    }
    assert validate_object({"name": "x", "count": 3}, schema) == []


def test_missing_required_field_reported() -> None:
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
        "additionalProperties": False,
    }
    issues = validate_object({}, schema)
    assert any("name" in i for i in issues)


def test_wrong_type_reported() -> None:
    schema = {
        "type": "object",
        "required": ["count"],
        "properties": {"count": {"type": "integer"}},
        "additionalProperties": False,
    }
    issues = validate_object({"count": "not-int"}, schema)
    assert any("count" in i for i in issues)


def test_extra_field_rejected_when_additional_false() -> None:
    schema = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
        "additionalProperties": False,
    }
    issues = validate_object({"name": "x", "extra": "y"}, schema)
    assert any("extra" in i for i in issues)


def test_array_items_type_checked() -> None:
    schema = {
        "type": "object",
        "required": ["tags"],
        "properties": {"tags": {"type": "array", "items": {"type": "string"}}},
        "additionalProperties": False,
    }
    assert validate_object({"tags": ["a", "b"]}, schema) == []
    issues = validate_object({"tags": ["a", 99]}, schema)
    assert issues  # 99 is not a string


def test_boolean_not_accepted_as_integer() -> None:
    schema = {
        "type": "object",
        "required": ["n"],
        "properties": {"n": {"type": "integer"}},
        "additionalProperties": False,
    }
    issues = validate_object({"n": True}, schema)
    assert issues


def test_boolean_field_accepted() -> None:
    schema = {
        "type": "object",
        "required": ["flag"],
        "properties": {"flag": {"type": "boolean"}},
        "additionalProperties": False,
    }
    assert validate_object({"flag": True}, schema) == []
    assert validate_object({"flag": False}, schema) == []


# ── schema coverage tests ─────────────────────────────────────────────────────

def test_all_task_types_have_input_schema() -> None:
    from generic_inference_block_ai.src.gib_alpha_policy import REQUIRED_ALLOWED_TASK_TYPES
    schemas = load_input_schemas()
    task_schemas = schemas.get("task_schemas", {})
    for task_type in REQUIRED_ALLOWED_TASK_TYPES:
        assert task_type in task_schemas, f"Missing input schema for {task_type}"


def test_all_task_types_have_output_schema() -> None:
    from generic_inference_block_ai.src.gib_alpha_policy import REQUIRED_ALLOWED_TASK_TYPES
    schemas = load_output_schemas()
    task_schemas = schemas.get("task_schemas", {})
    for task_type in REQUIRED_ALLOWED_TASK_TYPES:
        assert task_type in task_schemas, f"Missing output schema for {task_type}"


def test_blocked_output_schema_present() -> None:
    schemas = load_output_schemas()
    assert "blocked_output_schema" in schemas


# ── per-task contract tests ───────────────────────────────────────────────────

def test_phase_log_summary_valid_input() -> None:
    schemas = load_input_schemas()
    issues = validate_task_input(
        "phase_log_summary",
        {"phase_name": "P47", "status": "NO_GO", "log_excerpt": "ok"},
        schemas,
    )
    assert issues == []


def test_phase_log_summary_missing_field() -> None:
    schemas = load_input_schemas()
    issues = validate_task_input(
        "phase_log_summary",
        {"phase_name": "P47", "status": "NO_GO"},
        schemas,
    )
    assert any("log_excerpt" in i for i in issues)


def test_compliance_classify_valid_input() -> None:
    schemas = load_input_schemas()
    issues = validate_task_input(
        "compliance_classify",
        {"content_excerpt": "50% off", "context": "promo"},
        schemas,
    )
    assert issues == []


def test_compliance_classify_output_requires_boolean() -> None:
    schemas = load_output_schemas()
    from generic_inference_block_ai.src.gib_alpha1_schema import validate_task_output
    # Valid
    assert validate_task_output("compliance_classify", {
        "classification_label": "requires_human_review",
        "risk_notes": ["note"],
        "requires_human_review": True,
    }, schemas) == []
    # Invalid: string instead of bool
    issues = validate_task_output("compliance_classify", {
        "classification_label": "requires_human_review",
        "risk_notes": ["note"],
        "requires_human_review": "yes",
    }, schemas)
    assert issues


def test_article_outline_key_points_type() -> None:
    schemas = load_input_schemas()
    # key_points must be array
    issues = validate_task_input(
        "article_outline",
        {"topic": "t", "target_reader": "r", "key_points": "not-a-list"},
        schemas,
    )
    assert issues
