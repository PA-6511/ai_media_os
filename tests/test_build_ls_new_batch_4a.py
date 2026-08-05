from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT / "config/"
    "new_release_wp_category_review_gate_policy.json"
)
PACKAGE_PATH = (
    ROOT / "exchange/examples/"
    "new_release_wp_draft_preparation.example.json"
)
CATEGORY_REQUEST_PATH = (
    ROOT / "exchange/examples/"
    "new_release_wp_category_resolution_request.example.json"
)
REVIEW_REQUEST_PATH = (
    ROOT / "exchange/examples/"
    "new_release_wp_human_review_gate_request.example.json"
)
OUTPUT_PATH = (
    ROOT / "exchange/examples/"
    "new_release_wp_category_review_gate_package.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4a_result.json"
)
REPORT_PATH = (
    ROOT / "reports/"
    "ls_new_batch_4a_category_review_gate_report.md"
)
BUILDER_PATH = ROOT / "scripts/build_ls_new_batch_4a.py"
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4a_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4a_test_module",
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

    assert policy["phase_id"] == "LS-NEW-BATCH-4A"
    assert boundary["credential_read_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_category_lookup_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["wordpress_publish_allowed"] is False
    assert boundary["human_approval_issued"] is False
    assert boundary["execution_allowed"] is False
    assert boundary["production_status"] == "NO_GO"


def test_example_category_resolution_is_not_production_usable() -> None:
    request = load_json(CATEGORY_REQUEST_PATH)
    resolution = request["resolutions"][0]

    assert request["resolution_mode"] == "EXAMPLE_ONLY"
    assert resolution["resolution_source"] == "EXAMPLE_FIXTURE"
    assert 900000 <= resolution["wordpress_category_id"] <= 999999


def test_review_gate_begins_unreviewed() -> None:
    review = load_json(REVIEW_REQUEST_PATH)

    assert review["review_status"] == "NOT_REVIEWED"
    assert review["human_approval_issued"] is False
    assert review["approval_label"] is None
    assert review["approval_token"] is None

    item_review = review["item_reviews"][0]

    assert item_review["decision"] == "PENDING"
    assert all(
        value is False
        for value in item_review["checks"].values()
    )


def test_gate_package_resolves_example_category_only() -> None:
    gate_package = load_json(OUTPUT_PATH)
    item = gate_package["items"][0]
    category = item["draft_payload"]["category"]

    assert gate_package["resolution_mode"] == "EXAMPLE_ONLY"
    assert (
        gate_package["category_resolution"]["completed"]
        is True
    )
    assert (
        gate_package["category_resolution"][
            "category_ids_production_usable"
        ]
        is False
    )
    assert category["wordpress_category_id"] == 900001
    assert (
        category["resolution_state"]
        == "RESOLVED_EXAMPLE_ONLY"
    )
    assert category["production_usable"] is False
    assert item["wordpress_write_allowed"] is False
    assert item["execution_allowed"] is False


def test_resolved_digests_are_present_and_deterministic() -> None:
    builder = load_builder()

    policy = load_json(POLICY_PATH)
    package = load_json(PACKAGE_PATH)
    category_request = load_json(CATEGORY_REQUEST_PATH)
    review_request = load_json(REVIEW_REQUEST_PATH)

    first = builder.build_gate_package(
        package=copy.deepcopy(package),
        category_request=copy.deepcopy(category_request),
        review_request=copy.deepcopy(review_request),
        policy=policy,
    )
    second = builder.build_gate_package(
        package=copy.deepcopy(package),
        category_request=copy.deepcopy(category_request),
        review_request=copy.deepcopy(review_request),
        policy=policy,
    )

    assert len(first["resolved_package_digest_sha256"]) == 64
    assert (
        first["resolved_package_digest_sha256"]
        == second["resolved_package_digest_sha256"]
    )
    assert (
        first["items"][0][
            "resolved_payload_digest_sha256"
        ]
        == second["items"][0][
            "resolved_payload_digest_sha256"
        ]
    )


def test_tampered_source_batch_is_rejected() -> None:
    builder = load_builder()

    policy = load_json(POLICY_PATH)
    package = load_json(PACKAGE_PATH)
    package["items"][0]["draft_payload"]["title"] += "改変"

    try:
        builder.build_gate_package(
            package=package,
            category_request=load_json(
                CATEGORY_REQUEST_PATH
            ),
            review_request=load_json(
                REVIEW_REQUEST_PATH
            ),
            policy=policy,
        )
    except builder.ValidationError as exc:
        assert "batch digest verification failed" in str(exc)
    else:
        raise AssertionError("tampered package was accepted")


def test_review_digest_mismatch_is_rejected() -> None:
    builder = load_builder()

    review_request = load_json(REVIEW_REQUEST_PATH)
    review_request["item_reviews"][0][
        "source_payload_digest_sha256"
    ] = "0" * 64

    try:
        builder.build_gate_package(
            package=load_json(PACKAGE_PATH),
            category_request=load_json(
                CATEGORY_REQUEST_PATH
            ),
            review_request=review_request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "source payload digest mismatch" in str(exc)
    else:
        raise AssertionError("review digest mismatch was accepted")


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
        == "BLOCKED_REVIEW_NOT_COMPLETED"
    )
    assert result["human_approval_issued"] is False
    assert result["credential_read_allowed"] is False
    assert result["wordpress_api_call_allowed"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_CATEGORY_RESOLUTION_AND_"
        "REVIEW_GATE_NO_WORDPRESS_ACCESS"
    )
    assert result["resolution_mode"] == "EXAMPLE_ONLY"
    assert result["category_resolution_completed"] is True
    assert result["category_ids_production_usable"] is False
    assert result["human_review_state"] == "NOT_REVIEWED"
    assert result["human_approval_issued"] is False
    assert result["ready_for_human_review"] is True
    assert result["ready_for_ls_new_batch_4b"] is True
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "WordPress API call allowed: `false`" in report
    assert "WordPress write allowed: `false`" in report
    assert "Execution allowed: `false`" in report
