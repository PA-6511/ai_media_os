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
    "new_release_wp_production_category_preexecution_policy.json"
)
SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_human_review_decision_package.example.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_resolution_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_preexecution_package.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4c_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4c_production_category_preexecution_report.md"
)
BUILDER_PATH = ROOT / "scripts/build_ls_new_batch_4c.py"
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4c_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4c_test_module",
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

    assert policy["phase_id"] == "LS-NEW-BATCH-4C"
    assert boundary["credential_read_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_category_lookup_allowed"] is False
    assert boundary["wordpress_database_read_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["execution_approval_issued"] is False
    assert boundary["execution_allowed"] is False
    assert boundary["production_status"] == "NO_GO"


def test_request_begins_with_null_production_category() -> None:
    request = load_json(REQUEST_PATH)
    category = request["categories"][0]

    assert (
        request["resolution_status"]
        == "PENDING_MANUAL_VERIFICATION"
    )
    assert category["wordpress_category_id"] is None
    assert category["resolution_source"] is None
    assert category["verified_at"] is None
    assert category["evidence_note"] is None
    assert category["human_verification_confirmed"] is False
    assert request["execution_approval_issued"] is False
    assert request["approval_token"] is None


def test_source_is_reviewed_but_example_only() -> None:
    source = load_json(SOURCE_PATH)

    assert source["resolution_mode"] == "EXAMPLE_ONLY"
    assert source["category_ids_production_usable"] is False
    assert (
        source["human_review"][
            "human_review_approval_recorded"
        ]
        is True
    )
    assert (
        source["human_review"]["execution_approval_issued"]
        is False
    )


def test_output_removes_example_category_id() -> None:
    package = load_json(OUTPUT_PATH)
    category = package["items"][0][
        "draft_payload"
    ]["category"]

    assert category["wordpress_category_id"] is None
    assert (
        category["resolution_state"]
        == "PENDING_PRODUCTION_MANUAL_VERIFICATION"
    )
    assert category["resolution_source"] is None
    assert category["production_usable"] is False
    assert category["source_example_category_id_removed"] is True

    serialized = json.dumps(package, ensure_ascii=False)
    assert "900001" not in serialized


def test_preexecution_gate_remains_closed() -> None:
    package = load_json(OUTPUT_PATH)
    gate = package["preexecution_gate"]

    assert (
        gate["state"]
        == "BLOCKED_PENDING_PRODUCTION_CATEGORY_RESOLUTION"
    )
    assert gate["content_review_recorded"] is True
    assert gate["production_category_resolution_required"] is True
    assert gate["execution_approval_issued"] is False
    assert gate["approval_token"] is None
    assert gate["execution_allowed"] is False


def test_package_digest_is_deterministic() -> None:
    builder = load_builder()

    policy = load_json(POLICY_PATH)
    source = load_json(SOURCE_PATH)
    request = load_json(REQUEST_PATH)

    first = builder.build_package(
        source=copy.deepcopy(source),
        request=copy.deepcopy(request),
        policy=policy,
    )
    second = builder.build_package(
        source=copy.deepcopy(source),
        request=copy.deepcopy(request),
        policy=policy,
    )

    assert len(
        first["preexecution_package_digest_sha256"]
    ) == 64
    assert (
        first["preexecution_package_digest_sha256"]
        == second["preexecution_package_digest_sha256"]
    )
    assert (
        first["items"][0][
            "production_pending_payload_digest_sha256"
        ]
        == second["items"][0][
            "production_pending_payload_digest_sha256"
        ]
    )


def test_non_null_category_id_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["categories"][0][
        "wordpress_category_id"
    ] = 123

    try:
        builder.build_package(
            source=load_json(SOURCE_PATH),
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must begin null" in str(exc)
    else:
        raise AssertionError(
            "non-null production category ID was accepted"
        )


def test_tampered_source_is_rejected() -> None:
    builder = load_builder()

    source = load_json(SOURCE_PATH)
    source["items"][0]["draft_payload"]["title"] += "改変"

    try:
        builder.build_package(
            source=source,
            request=load_json(REQUEST_PATH),
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "review package digest verification failed" in str(
            exc
        )
    else:
        raise AssertionError("tampered source was accepted")


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
        == "BLOCKED_PENDING_PRODUCTION_CATEGORY_RESOLUTION"
    )
    assert result["example_category_ids_removed"] is True
    assert result["production_category_ids_present"] is False
    assert result["execution_approval_issued"] is False
    assert result["approval_token_present"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_PRODUCTION_CATEGORY_REQUEST_"
        "PREPARED_NO_WORDPRESS_ACCESS"
    )
    assert result["example_category_ids_removed"] is True
    assert result["production_category_ids_present"] is False
    assert (
        result["production_category_resolution_state"]
        == "PENDING_MANUAL_VERIFICATION"
    )
    assert result["execution_approval_issued"] is False
    assert result["approval_token_present"] is False
    assert result["ready_for_ls_new_batch_4d"] is True
    assert result["ready_for_production_pre_execution"] is False
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "WordPress API call allowed: `false`" in report
    assert "WordPress database read allowed: `false`" in report
    assert "WordPress write allowed: `false`" in report
    assert "Execution allowed: `false`" in report
