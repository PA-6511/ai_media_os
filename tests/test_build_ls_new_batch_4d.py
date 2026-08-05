from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_read_only_category_discovery_policy.json"
)
SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_preexecution_package.example.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_discovery_request.example.json"
)
CATALOG_PATH = (
    ROOT
    / "exchange/examples/"
    "wordpress_category_catalog.fixture.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_discovery_result.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_4d_result.json"
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4d_read_only_category_discovery_report.md"
)
BUILDER_PATH = ROOT / "scripts/build_ls_new_batch_4d.py"
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4d_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4d_test_module",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_policy_identity_and_closed_boundary() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-4D"
    assert boundary["credential_read_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_category_lookup_allowed"] is False
    assert boundary["wordpress_database_read_allowed"] is False
    assert boundary["wordpress_database_write_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["execution_allowed"] is False
    assert boundary["production_status"] == "NO_GO"


def test_request_does_not_request_wordpress_access() -> None:
    request = load_json(REQUEST_PATH)

    assert request["discovery_mode"] == "LOCAL_FIXTURE_ONLY"
    assert request["production_lookup_requested"] is False
    assert request["credential_access_requested"] is False
    assert request["wordpress_access_requested"] is False


def test_source_production_category_id_remains_null() -> None:
    source = load_json(SOURCE_PATH)
    category = source["items"][0][
        "draft_payload"
    ]["category"]

    assert category["wordpress_category_id"] is None
    assert (
        category["resolution_state"]
        == "PENDING_PRODUCTION_MANUAL_VERIFICATION"
    )
    assert category["production_usable"] is False


def test_fixture_candidate_is_reserved_and_not_production() -> None:
    catalog = load_json(CATALOG_PATH)
    category = catalog["categories"][0]

    assert catalog["source_type"] == "LOCAL_FIXTURE"
    assert catalog["production_usable"] is False
    assert 990000 <= category["wordpress_category_id"] <= 999999


def test_discovery_result_matches_without_payload_injection() -> None:
    package = load_json(OUTPUT_PATH)
    summary = package["discovery_summary"]
    result = package["discovery_results"][0]
    item = package["item_discovery_links"][0]

    assert summary["all_categories_matched"] is True
    assert summary["fixture_candidates_present"] is True
    assert (
        summary["fixture_candidates_applied_to_payload"]
        is False
    )
    assert summary["production_category_ids_present"] is False
    assert result["match_state"] == "MATCHED_FIXTURE_ONLY"
    assert result["production_usable"] is False
    assert result["payload_injection_allowed"] is False
    assert item["source_wordpress_category_id"] is None
    assert item["production_payload_modified"] is False
    assert item["execution_allowed"] is False


def test_fixture_slug_mismatch_is_rejected() -> None:
    builder = load_builder()

    catalog = load_json(CATALOG_PATH)
    catalog["categories"][0][
        "category_slug"
    ] = "different-category"

    try:
        builder.build_package(
            source=load_json(SOURCE_PATH),
            request=load_json(REQUEST_PATH),
            catalog=catalog,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "fixture match not found" in str(exc)
    else:
        raise AssertionError(
            "fixture slug mismatch was accepted"
        )


def test_fixture_id_outside_reserved_range_is_rejected() -> None:
    builder = load_builder()

    catalog = load_json(CATALOG_PATH)
    catalog["categories"][0][
        "wordpress_category_id"
    ] = 123

    try:
        builder.build_package(
            source=load_json(SOURCE_PATH),
            request=load_json(REQUEST_PATH),
            catalog=catalog,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "outside reserved range" in str(exc)
    else:
        raise AssertionError(
            "non-reserved fixture ID was accepted"
        )


def test_tampered_source_is_rejected() -> None:
    builder = load_builder()

    source = load_json(SOURCE_PATH)
    source["items"][0]["draft_payload"]["title"] += "改変"

    try:
        builder.build_package(
            source=source,
            request=load_json(REQUEST_PATH),
            catalog=load_json(CATALOG_PATH),
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "pre-execution digest verification failed" in str(
            exc
        )
    else:
        raise AssertionError("tampered source was accepted")


def test_package_digest_is_deterministic() -> None:
    builder = load_builder()

    source = load_json(SOURCE_PATH)
    request = load_json(REQUEST_PATH)
    catalog = load_json(CATALOG_PATH)
    policy = load_json(POLICY_PATH)

    first = builder.build_package(
        source=copy.deepcopy(source),
        request=copy.deepcopy(request),
        catalog=copy.deepcopy(catalog),
        policy=policy,
    )
    second = builder.build_package(
        source=copy.deepcopy(source),
        request=copy.deepcopy(request),
        catalog=copy.deepcopy(catalog),
        policy=policy,
    )

    assert len(first["discovery_package_digest_sha256"]) == 64
    assert (
        first["discovery_package_digest_sha256"]
        == second["discovery_package_digest_sha256"]
    )


def test_execution_runner_remains_blocked() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(BLOCKED_PATH),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    result = json.loads(completed.stderr)

    assert (
        result["status"]
        == "BLOCKED_FIXTURE_DISCOVERY_NOT_PRODUCTION"
    )
    assert result["fixture_candidate_present"] is True
    assert result["fixture_candidate_applied_to_payload"] is False
    assert result["production_category_ids_present"] is False
    assert result["execution_approval_issued"] is False
    assert result["approval_token_present"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_READ_ONLY_CATEGORY_DISCOVERY_DESIGN_"
        "NO_WORDPRESS_ACCESS"
    )
    assert result["all_categories_matched"] is True
    assert result["fixture_candidates_present"] is True
    assert result["fixture_candidates_applied_to_payload"] is False
    assert result["production_category_ids_present"] is False
    assert result["production_category_ids_usable"] is False
    assert result["ready_for_ls_new_batch_4e"] is True
    assert result["ready_for_production_category_resolution"] is False
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "Credential read allowed: `false`" in report
    assert "WordPress API call allowed: `false`" in report
    assert "WordPress database read allowed: `false`" in report
    assert "WordPress write allowed: `false`" in report
    assert "Execution allowed: `false`" in report
