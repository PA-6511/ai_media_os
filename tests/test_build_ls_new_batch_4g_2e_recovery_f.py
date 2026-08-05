from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / "config/new_release_wp_fresh_payload_generation_input_gate_policy.json"
CONTRACT = ROOT / "config/new_release_wp_fresh_payload_generation_input_contract.json"
TEMPLATE = ROOT / "exchange/examples/new_release_wp_fresh_payload_generation_input.template.json"
REQUEST = ROOT / "exchange/examples/new_release_wp_fresh_payload_generation_input_gate_request.example.json"
RESULT = ROOT / "exchange/logs/ls_new_batch_4g_2e_recovery_f_result.json"
REPORT = ROOT / "reports/ls_new_batch_4g_2e_recovery_f_input_gate_report.md"
BUILDER = ROOT / "scripts/build_ls_new_batch_4g_2e_recovery_f.py"
BLOCKED = ROOT / "scripts/execute_ls_new_batch_4g_2e_recovery_f_blocked.py"


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def module():
    spec = importlib.util.spec_from_file_location(
        "recovery_f_builder",
        BUILDER,
    )
    assert spec is not None
    assert spec.loader is not None
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


def test_policy_fixes_input_contract_only() -> None:
    policy = load(POLICY)

    assert (
        policy["input_contract"]["contract_id"]
        == "FRESH_NEW_RELEASE_COMIC_DRAFT_INPUT_V1"
    )
    assert (
        policy["input_contract"]["fixed_wordpress_status"]
        == "draft"
    )
    assert (
        policy["execution_boundary"][
            "fresh_payload_creation_allowed"
        ]
        is False
    )


def test_contract_excludes_post185_and_category_values() -> None:
    contract = load(CONTRACT)

    assert contract["legacy_post185_reference_allowed"] is False
    assert contract["categories_initial_states_allowed"] == [
        "ABSENT",
        "EMPTY_LIST",
    ]
    assert (
        contract["categories_value_before_binding_allowed"]
        is False
    )
    assert contract["fresh_payload_created"] is False


def test_template_is_incomplete_and_non_executable() -> None:
    template = load(TEMPLATE)

    assert (
        template["document_role"]
        == "NON_EXECUTABLE_INCOMPLETE_INPUT_TEMPLATE"
    )
    assert template["input_complete"] is False
    assert template["human_review_complete"] is False
    assert template["wordpress_status"] == "draft"
    assert template["legacy_post185_reference"] is False
    assert "categories" not in template
    assert template["payload_generation_requested"] is False
    assert template["execution_allowed"] is False


def test_required_store_slots_exist() -> None:
    template = load(TEMPLATE)

    assert set(template["store_links"]) == {
        "amazon",
        "rakuten_kobo",
        "dmm_books",
    }

    for store in template["store_links"].values():
        assert store["url"] is None
        assert store["verification_state"] == "PENDING"


def test_request_has_no_execution() -> None:
    request = load(REQUEST)

    assert request["input_contract_fixation_requested"] is True
    assert request["article_input_registration_requested"] is False
    assert request["fresh_payload_creation_requested"] is False
    assert request["payload_binding_requested"] is False
    assert (
        request[
            "production_category_id_payload_injection_requested"
        ]
        is False
    )
    assert request["wordpress_write_requested"] is False
    assert request["execution_requested"] is False


def test_payload_generation_request_is_rejected() -> None:
    builder = module()
    request = copy.deepcopy(load(REQUEST))
    request["fresh_payload_creation_requested"] = True

    try:
        builder.validate_request_and_sources(
            request,
            load(POLICY),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "payload generation request was accepted"
        )


def test_wordpress_request_is_rejected() -> None:
    builder = module()
    request = copy.deepcopy(load(REQUEST))
    request["wordpress_access_requested"] = True

    try:
        builder.validate_request_and_sources(
            request,
            load(POLICY),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "WordPress request was accepted"
        )


def test_blocked_runner_returns_three() -> None:
    completed = subprocess.run(
        [sys.executable, str(BLOCKED)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3
    result = json.loads(completed.stderr)

    assert result["article_input_registered"] is False
    assert result["fresh_payload_created"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert result["wordpress_write_performed"] is False
    assert result["execution_allowed"] is False


def test_result_is_ready_for_input_registration_only() -> None:
    result = load(RESULT)

    assert (
        result["status"]
        == (
            "PASS_FRESH_PAYLOAD_GENERATION_"
            "INPUT_CONTRACT_FIXED_NO_PAYLOAD_NO_NETWORK"
        )
    )
    assert result["article_input_registered"] is False
    assert result["fresh_payload_created"] is False
    assert result["payload_binding_complete"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert (
        result[
            "ready_for_fresh_article_input_registration"
        ]
        is True
    )
    assert result["ready_for_fresh_payload_generation"] is False
    assert result["ready_for_execution"] is False


def test_report_confirms_no_payload() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "Article input registered: `false`" in report
    assert "Fresh payload created: `false`" in report
    assert "Category ID 10 injected: `false`" in report
    assert "WordPress write performed: `false`" in report
