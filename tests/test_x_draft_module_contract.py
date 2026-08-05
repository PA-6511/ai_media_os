from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/x_draft_module_contract.json"
VALIDATOR_PATH = ROOT / "scripts/validate_x_draft_module_contract.py"


def load_contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_x_draft_module_contract",
        VALIDATOR_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_contract_json_is_valid() -> None:
    contract = load_contract()

    assert contract["schema_version"] == "1.0.0"
    assert contract["phase_id"] == "X-R1"
    assert contract["contract_id"] == "X_DRAFT_MODULE_CONTRACT_V1"


def test_contract_uses_existing_database_status_values() -> None:
    contract = load_contract()
    workflow = contract["workflow_mapping"]

    assert workflow["database_x_status_after_generation"] == "DRAFT"
    assert workflow["database_review_status_after_generation"] == "IN_REVIEW"
    assert (
        workflow["database_review_status_after_human_approval"]
        == "APPROVED"
    )
    assert workflow["database_x_status_after_manual_post"] == "POSTED"
    assert workflow["failure_x_status"] == "ERROR"


def test_contract_maps_x_feedback_stages_separately() -> None:
    contract = load_contract()
    workflow = contract["workflow_mapping"]

    assert workflow["x_feedback_stage_after_generation"] == "DRAFT_GENERATED"
    assert workflow["x_feedback_human_reviewed_stage"] == "HUMAN_REVIEWED"


def test_contract_requires_verified_wordpress_draft() -> None:
    contract = load_contract()
    sources = contract["input_contract"]["wordpress_success_sources"]

    assert {
        "id_field": "created_post_id",
        "status_field": "created_post_status",
        "required_status": "draft",
    } in sources

    assert {
        "id_field": "new_post_id",
        "status_field": "returned_post_status",
        "required_status": "draft",
    } in sources


def test_contract_requires_real_https_article_url() -> None:
    contract = load_contract()
    rule = contract["input_contract"]["field_rules"]["article_url"]

    assert rule["required_scheme"] == "https"
    assert rule["placeholder_forbidden"] is True


def test_generation_contract_requires_pr_and_280_limit() -> None:
    contract = load_contract()
    generation = contract["generation_contract"]
    template = "\n".join(generation["template_lines"])

    assert generation["maximum_character_count"] == 280
    assert generation["include_synopsis"] is False
    assert "#PR" in template
    assert "{article_url}" in template
    assert "{title}" in template


def test_contract_forbids_external_execution() -> None:
    contract = load_contract()
    boundary = contract["execution_boundary"]

    assert boundary["x_api_call_allowed"] is False
    assert boundary["x_post_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["external_api_call_allowed"] is False
    assert boundary["automatic_human_approval_allowed"] is False
    assert boundary["automatic_posted_transition_allowed"] is False
    assert boundary["production_status"] == "NO_GO"
    assert boundary["safety_state"] == "DRY_RUN_ONLY"


def test_contract_does_not_require_new_database_table() -> None:
    contract = load_contract()
    storage = contract["storage_contract"]

    assert storage["database_table_addition_required"] is False
    assert storage["workflow_history_required"] is True


def test_validator_accepts_fixed_contract() -> None:
    validator = load_validator()
    contract = load_contract()

    checks = validator.validate_contract(contract)

    assert "identity" in checks
    assert "input_contract" in checks
    assert "generation_contract" in checks
    assert "workflow_mapping" in checks
    assert "execution_boundary" in checks


@pytest.mark.parametrize(
    ("path", "invalid_value"),
    [
        (("execution_boundary", "x_post_allowed"), True),
        (("execution_boundary", "wordpress_write_allowed"), True),
        (("output_contract", "fixed_values", "x_status"), "POSTED"),
        (
            ("output_contract", "fixed_values", "review_status"),
            "HUMAN_REVIEWED",
        ),
        (
            ("workflow_mapping", "database_x_status_after_generation"),
            "GENERATED",
        ),
    ],
)
def test_validator_rejects_unsafe_or_invalid_contract(
    path: tuple[str, ...],
    invalid_value: object,
) -> None:
    validator = load_validator()
    contract = load_contract()

    target: dict[str, Any] = contract
    for key in path[:-1]:
        target = target[key]

    target[path[-1]] = invalid_value

    with pytest.raises(validator.ContractValidationError):
        validator.validate_contract(contract)
