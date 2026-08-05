from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT / "config/new_release_wp_draft_preparation_policy.json"
)
SOURCE_PATH = (
    ROOT / "exchange/examples/"
    "new_release_article_ready_preview_result.example.json"
)
REVIEW_PATH = (
    ROOT / "exchange/examples/"
    "new_release_wp_draft_review_request.example.json"
)
OUTPUT_PATH = (
    ROOT / "exchange/examples/"
    "new_release_wp_draft_preparation.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_4_result.json"
REPORT_PATH = (
    ROOT / "reports/"
    "ls_new_batch_4_wp_draft_preparation_report.md"
)
BUILDER_PATH = ROOT / "scripts/build_ls_new_batch_4.py"
BLOCKED_RUNNER_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4_test_module",
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

    assert policy["phase_id"] == "LS-NEW-BATCH-4"
    assert boundary["credential_read_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["wordpress_publish_allowed"] is False
    assert boundary["execution_allowed"] is False
    assert boundary["production_status"] == "NO_GO"
    assert boundary["safety_state"] == "PREPARATION_ONLY"


def test_review_request_has_no_approval() -> None:
    review = load_json(REVIEW_PATH)

    assert review["review_status"] == "NOT_REVIEWED"
    assert review["approved_item_ids"] == []
    assert review["human_approval_issued"] is False
    assert review["approval_token"] is None
    assert review["reviewed_at"] is None


def test_preparation_package_contains_one_draft() -> None:
    package = load_json(OUTPUT_PATH)

    assert package["item_count"] == 1
    assert package["approval_gate"]["state"] == "NOT_APPROVED"
    assert package["approval_gate"]["execution_allowed"] is False

    item = package["items"][0]

    assert item["preparation_state"] == "PREPARED_NOT_APPROVED"
    assert item["draft_payload"]["status"] == "draft"
    assert item["wordpress_write_allowed"] is False
    assert item["execution_allowed"] is False


def test_category_id_remains_unresolved() -> None:
    package = load_json(OUTPUT_PATH)
    category = package["items"][0][
        "draft_payload"
    ]["category"]

    assert category["wordpress_category_id"] is None
    assert category["resolution_state"] == "PENDING_ID_LOOKUP"
    assert package["category_resolution"]["completed"] is False
    assert (
        package["category_resolution"][
            "wordpress_api_lookup_allowed"
        ]
        is False
    )


def test_html_validation_and_store_order() -> None:
    package = load_json(OUTPUT_PATH)
    item = package["items"][0]

    assert item["html_validation"]["link_count"] == 2
    assert item["html_validation"]["image_count"] == 1
    assert item["store_button_order"] == [
        "amazon",
        "rakuten_kobo",
    ]


def test_digests_and_idempotency_key_are_fixed() -> None:
    package = load_json(OUTPUT_PATH)
    item = package["items"][0]

    assert len(package["batch_digest_sha256"]) == 64
    assert len(item["payload_digest_sha256"]) == 64
    assert len(item["idempotency_key"]) == 64


def test_rebuilding_is_deterministic() -> None:
    builder = load_builder()

    policy = load_json(POLICY_PATH)
    source = load_json(SOURCE_PATH)
    review = load_json(REVIEW_PATH)

    first = builder.build_package(
        source=source,
        review=review,
        policy=policy,
    )
    second = builder.build_package(
        source=source,
        review=review,
        policy=policy,
    )

    first.pop("_review_validation_checks")
    second.pop("_review_validation_checks")

    assert first["batch_digest_sha256"] == second[
        "batch_digest_sha256"
    ]
    assert (
        first["items"][0]["payload_digest_sha256"]
        == second["items"][0]["payload_digest_sha256"]
    )


def test_execution_runner_is_always_blocked() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(BLOCKED_RUNNER_PATH),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    result = json.loads(completed.stderr)

    assert result["status"] == "BLOCKED_NOT_APPROVED"
    assert result["human_approval_issued"] is False
    assert result["credential_read_allowed"] is False
    assert result["wordpress_api_call_allowed"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_DRAFT_PREPARATION_NO_WORDPRESS_ACCESS"
    )
    assert result["approval_state"] == "NOT_APPROVED"
    assert result["human_approval_issued"] is False
    assert result["category_resolution_completed"] is False
    assert result["ready_for_human_review"] is True
    assert result["ready_for_ls_new_batch_4a"] is True
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "Credential read allowed: `false`" in report
    assert "WordPress API call allowed: `false`" in report
    assert "Execution allowed: `false`" in report
