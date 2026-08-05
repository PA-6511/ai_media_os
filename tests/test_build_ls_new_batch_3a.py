from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT / "config/"
    "new_release_ready_preview_integration_policy.json"
)
READY_PATH = (
    ROOT / "exchange/examples/"
    "new_release_verification_ready.example.json"
)
OUTPUT_PATH = (
    ROOT / "exchange/examples/"
    "new_release_article_ready_preview_result.example.json"
)
X_REQUEST_PATH = (
    ROOT / "exchange/examples/"
    "x_fb_ready_preview_initialize_request.example.json"
)
X_NORMALIZED_PATH = (
    ROOT / "exchange/examples/"
    "x_fb_ready_preview_normalized.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_3a_result.json"
)
REPORT_PATH = (
    ROOT / "reports/"
    "ls_new_batch_3a_ready_preview_integration_report.md"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_policy_blocks_live_operations() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-3A"
    assert boundary["external_api_call_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["wordpress_publish_allowed"] is False
    assert boundary["x_api_call_allowed"] is False
    assert boundary["x_post_allowed"] is False
    assert boundary["production_status"] == "NO_GO"


def test_ready_fixture_has_one_ready_item() -> None:
    data = load_json(READY_PATH)

    assert data["record_count"] == 1
    assert data["ready_for_draft_count"] == 1
    assert data["classification_counts"] == {
        "READY_FOR_DRAFT": 1
    }


def test_article_output_has_one_generated_item() -> None:
    output = load_json(OUTPUT_PATH)
    generated = output["generated_items"][0]

    assert output["generated_item_count"] == 1
    assert output["skipped_item_count"] == 0
    assert (
        generated["article_payload"]["post_status"]
        == "draft"
    )
    assert generated["wordpress_write_allowed"] is False


def test_html_preview_exists_and_has_store_order() -> None:
    result = load_json(RESULT_PATH)
    preview_path = ROOT / result["html_preview_path"]

    assert preview_path.exists()

    content = preview_path.read_text(encoding="utf-8")

    assert "ebook-pr-disclosure" in content
    assert "ebook-price-card" in content
    assert "ebook-store-button" in content
    assert content.index("Amazon Kindle") < content.index(
        "楽天Kobo"
    )
    assert "<script" not in content.lower()


def test_x_feedback_initialization_is_valid() -> None:
    request = load_json(X_REQUEST_PATH)
    normalized = load_json(X_NORMALIZED_PATH)

    assert request["action"] == "INITIALIZE"
    assert "#" not in request["generated_text"]
    assert normalized["record_version"] == 1
    assert normalized["record_stage"] == "DRAFT_GENERATED"
    assert (
        normalized["execution_boundary"]["x_post_allowed"]
        is False
    )


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_READY_ITEM_INTEGRATION_PREVIEW_NO_LIVE_WRITE"
    )
    assert result["generated_item_count"] == 1
    assert result["skipped_item_count"] == 0
    assert len(result["preview_digest_sha256"]) == 64
    assert result["ready_for_ls_new_batch_4"] is True
    assert result["next_phase_execution_allowed"] is False
    assert "WordPress write allowed: `false`" in report
    assert "X posting allowed: `false`" in report
