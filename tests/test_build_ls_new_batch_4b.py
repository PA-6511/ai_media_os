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
    "new_release_wp_human_review_decision_policy.json"
)
SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_review_gate_package.example.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_human_review_decision_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_human_review_decision_package.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4b_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4b_human_review_decision_report.md"
)
BUILDER_PATH = ROOT / "scripts/build_ls_new_batch_4b.py"
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4b_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4b_test_module",
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

    assert policy["phase_id"] == "LS-NEW-BATCH-4B"
    assert boundary["human_review_recording_allowed"] is True
    assert boundary["credential_read_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["execution_approval_issued"] is False
    assert boundary["approval_token_generation_allowed"] is False
    assert boundary["execution_allowed"] is False
    assert boundary["production_status"] == "NO_GO"


def test_request_records_complete_review_without_execution() -> None:
    request = load_json(REQUEST_PATH)

    assert request["review_status"] == "COMPLETED"
    assert (
        request["overall_decision"]
        == "APPROVE_FOR_DRAFT_PRE_EXECUTION"
    )
    assert request["execution_approval_issued"] is False
    assert request["approval_token"] is None

    item_review = request["item_reviews"][0]

    assert all(item_review["checks"].values())
    assert (
        item_review["decision"]
        == "APPROVE_FOR_DRAFT_PRE_EXECUTION"
    )


def test_example_review_is_approved_but_not_executable() -> None:
    package = load_json(OUTPUT_PATH)
    review = package["human_review"]

    assert package["resolution_mode"] == "EXAMPLE_ONLY"
    assert package["category_ids_production_usable"] is False
    assert review["state"] == "COMPLETED"
    assert (
        review["effective_outcome"]
        == "REVIEW_APPROVED_EXAMPLE_ONLY_NOT_EXECUTABLE"
    )
    assert (
        review["review_label"]
        == "REVIEW_APPROVED_EXAMPLE_ONLY_NOT_EXECUTABLE"
    )
    assert review["human_review_approval_recorded"] is True
    assert review["execution_approval_issued"] is False
    assert review["approval_token"] is None
    assert review["execution_allowed"] is False


def test_reviewed_item_remains_non_executable() -> None:
    package = load_json(OUTPUT_PATH)
    item = package["items"][0]

    assert item["human_review_status"] == "COMPLETED"
    assert (
        item["human_review_decision"]
        == "APPROVE_FOR_DRAFT_PRE_EXECUTION"
    )
    assert all(item["human_review_checks"].values())
    assert item["execution_approval_issued"] is False
    assert item["approval_token"] is None
    assert item["credential_read_allowed"] is False
    assert item["wordpress_api_call_allowed"] is False
    assert item["wordpress_write_allowed"] is False
    assert item["execution_allowed"] is False


def test_review_package_digest_is_deterministic() -> None:
    builder = load_builder()

    policy = load_json(POLICY_PATH)
    source = load_json(SOURCE_PATH)
    request = load_json(REQUEST_PATH)

    first = builder.build_review_package(
        source=copy.deepcopy(source),
        request=copy.deepcopy(request),
        policy=policy,
    )
    second = builder.build_review_package(
        source=copy.deepcopy(source),
        request=copy.deepcopy(request),
        policy=policy,
    )

    assert len(first["review_package_digest_sha256"]) == 64
    assert (
        first["review_package_digest_sha256"]
        == second["review_package_digest_sha256"]
    )


def test_missing_approval_check_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["item_reviews"][0]["checks"]["prices"] = False

    try:
        builder.build_review_package(
            source=load_json(SOURCE_PATH),
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "all checks must be true" in str(exc)
    else:
        raise AssertionError(
            "approval with incomplete checks was accepted"
        )


def test_source_payload_digest_mismatch_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["item_reviews"][0][
        "source_resolved_payload_digest_sha256"
    ] = "0" * 64

    try:
        builder.build_review_package(
            source=load_json(SOURCE_PATH),
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "source resolved payload digest mismatch" in str(exc)
    else:
        raise AssertionError(
            "payload digest mismatch was accepted"
        )


def test_rejection_flow_is_recordable() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["item_reviews"][0]["decision"] = "REJECT"
    request["item_reviews"][0][
        "reviewer_note"
    ] = "価格表示の再確認が必要。"
    request["overall_decision"] = "REJECT"

    package = builder.build_review_package(
        source=load_json(SOURCE_PATH),
        request=request,
        policy=load_json(POLICY_PATH),
    )

    review = package["human_review"]

    assert review["effective_outcome"] == "REVIEW_REJECTED"
    assert review["review_label"] == "HUMAN_REVIEW_REJECTED"
    assert review["human_review_approval_recorded"] is False
    assert review["execution_allowed"] is False


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
        == "BLOCKED_EXAMPLE_CATEGORY_AND_"
        "NO_EXECUTION_APPROVAL"
    )
    assert result["human_review_approval_recorded"] is True
    assert result["category_ids_production_usable"] is False
    assert result["execution_approval_issued"] is False
    assert result["approval_token_present"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_HUMAN_REVIEW_RECORDED_"
        "NO_WORDPRESS_ACCESS"
    )
    assert (
        result["effective_outcome"]
        == "REVIEW_APPROVED_EXAMPLE_ONLY_NOT_EXECUTABLE"
    )
    assert result["human_review_approval_recorded"] is True
    assert result["execution_approval_issued"] is False
    assert result["approval_token_present"] is False
    assert result["ready_for_ls_new_batch_4c"] is True
    assert result["ready_for_production_pre_execution"] is False
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "WordPress API call allowed: `false`" in report
    assert "WordPress write allowed: `false`" in report
    assert "Execution allowed: `false`" in report
