from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT / "config/new_release_article_batch_dry_run_policy.json"
)
VERIFICATION_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_verification_result.example.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_article_batch_dry_run_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_article_batch_dry_run_result.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_3_result.json"
REPORT_PATH = (
    ROOT / "reports/ls_new_batch_3_article_batch_dry_run_report.md"
)
SCRIPT_PATH = ROOT / "scripts/build_ls_new_batch_3.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_3_test_module",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ready_verification() -> dict:
    verification = load_json(VERIFICATION_PATH)
    item = verification["items"][0]

    item["verification_classification"] = (
        "READY_FOR_DRAFT"
    )
    item["classification_reasons"] = [
        "publisher_official_confirmed",
        "found_store_count=2",
        "confirmed_price_count=2",
        "verified_image_available",
    ]
    item["mismatches"] = []

    item["publisher_official"] = {
        "status": "CHECKED",
        "checked_at": "2026-07-10T12:00:00+09:00",
        "url": "https://publisher.example.jp/book",
        "title": "サンプル作品",
        "volume_label": "第1巻",
        "release_date": "2026-07-17",
    }

    item["stores"] = {
        "amazon": {
            "status": "FOUND",
            "checked_at": "2026-07-10T12:00:00+09:00",
            "url": "https://www.amazon.co.jp/dp/TEST001",
            "title": "サンプル作品",
            "volume_label": "第1巻",
            "release_date": "2026-07-17",
            "price_jpy": 770,
            "image_url": None,
        },
        "rakuten_kobo": {
            "status": "FOUND",
            "checked_at": "2026-07-10T12:00:00+09:00",
            "url": "https://books.rakuten.co.jp/rk/TEST001",
            "title": "サンプル作品",
            "volume_label": "第1巻",
            "release_date": "2026-07-17",
            "price_jpy": 770,
            "image_url": (
                "https://thumbnail.image.rakuten.co.jp/"
                "test-cover.jpg"
            ),
        },
        "dmm": {
            "status": "NOT_FOUND",
            "checked_at": "2026-07-10T12:00:00+09:00",
            "url": None,
            "title": None,
            "volume_label": None,
            "release_date": None,
            "price_jpy": None,
            "image_url": None,
        },
    }

    item["resolved_store_links"] = {
        "amazon": "https://www.amazon.co.jp/dp/TEST001",
        "rakuten_kobo": (
            "https://books.rakuten.co.jp/rk/TEST001"
        ),
        "dmm": None,
    }
    item["resolved_prices_jpy"] = {
        "amazon": 770,
        "rakuten_kobo": 770,
        "dmm": None,
    }
    item["resolved_image"] = {
        "source": "rakuten_kobo",
        "url": (
            "https://thumbnail.image.rakuten.co.jp/"
            "test-cover.jpg"
        ),
    }

    verification["classification_counts"] = {
        "READY_FOR_DRAFT": 1
    }
    verification["ready_for_draft_count"] = 1

    return verification


def build_output(verification: dict) -> dict:
    module = load_module()

    return module.build_output(
        verification=verification,
        request=load_json(REQUEST_PATH),
        policy=load_json(POLICY_PATH),
    )


def run_builder(
    verification_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--verification",
            str(verification_path),
            "--check-only",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_policy_identity_and_safety_boundary() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-3"
    assert (
        policy["policy_id"]
        == "NEW_RELEASE_ARTICLE_BATCH_DRY_RUN_POLICY_V1"
    )
    assert boundary["external_api_call_allowed"] is False
    assert boundary["web_scraping_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["wordpress_publish_allowed"] is False
    assert boundary["x_api_call_allowed"] is False
    assert boundary["x_post_allowed"] is False
    assert boundary["production_status"] == "NO_GO"
    assert boundary["safety_state"] == "DRY_RUN_ONLY"


def test_non_ready_example_is_safely_skipped() -> None:
    output = build_output(load_json(VERIFICATION_PATH))

    assert output["generated_item_count"] == 0
    assert output["skipped_item_count"] == 1
    assert (
        output["skipped_items"][0]["reason"]
        == "NOT_READY_FOR_DRAFT"
    )


def test_ready_item_generates_article_and_x_candidate() -> None:
    output = build_output(ready_verification())
    generated = output["generated_items"][0]

    assert output["generated_item_count"] == 1
    assert (
        generated["article_payload"]["post_status"]
        == "draft"
    )
    assert generated["wordpress_write_allowed"] is False
    assert generated["x_post_allowed"] is False
    assert (
        generated["x_candidate"][
            "requires_manual_review"
        ]
        is True
    )


def test_store_button_order_is_fixed() -> None:
    output = build_output(ready_verification())
    payload = output["generated_items"][0][
        "article_payload"
    ]

    assert payload["metadata"]["store_button_order"] == [
        "amazon",
        "rakuten_kobo",
    ]

    content = payload["content_html"]

    assert content.index("Amazon Kindle") < content.index(
        "楽天Kobo"
    )


def test_uncategorized_is_never_assigned() -> None:
    output = build_output(ready_verification())
    payload = output["generated_items"][0][
        "article_payload"
    ]

    assert payload["uncategorized_assigned"] is False
    assert payload["category_slug"] == "comic-new-release"


def test_missing_image_rejects_ready_item() -> None:
    verification = ready_verification()
    verification["items"][0]["resolved_image"]["url"] = None

    module = load_module()

    try:
        module.build_output(
            verification=verification,
            request=load_json(REQUEST_PATH),
            policy=load_json(POLICY_PATH),
        )
    except module.ValidationError as exc:
        assert "resolved_image.url is required" in str(exc)
    else:
        raise AssertionError("missing image was accepted")


def test_less_than_two_found_stores_is_rejected() -> None:
    verification = ready_verification()
    item = verification["items"][0]

    item["stores"]["rakuten_kobo"] = {
        "status": "NOT_FOUND",
        "checked_at": "2026-07-10T12:00:00+09:00",
        "url": None,
        "title": None,
        "volume_label": None,
        "release_date": None,
        "price_jpy": None,
        "image_url": None,
    }
    item["resolved_store_links"]["rakuten_kobo"] = None
    item["resolved_prices_jpy"]["rakuten_kobo"] = None

    module = load_module()

    try:
        module.build_output(
            verification=verification,
            request=load_json(REQUEST_PATH),
            policy=load_json(POLICY_PATH),
        )
    except module.ValidationError as exc:
        assert "at least two found stores" in str(exc)
    else:
        raise AssertionError("one-store item was accepted")


def test_unknown_price_is_not_rendered_as_zero() -> None:
    verification = ready_verification()
    verification["items"][0][
        "resolved_prices_jpy"
    ]["amazon"] = None

    output = build_output(verification)
    content = output["generated_items"][0][
        "article_payload"
    ]["content_html"]

    assert "価格は販売ページで確認" in content
    assert ">0円<" not in content


def test_html_values_are_escaped() -> None:
    verification = ready_verification()
    item = verification["items"][0]
    item["title"] = "<script>alert(1)</script>"

    output = build_output(verification)
    content = output["generated_items"][0][
        "article_payload"
    ]["content_html"]

    assert "<script>" not in content
    assert "&lt;script&gt;" in content


def test_x_candidate_has_no_hashtag_and_reserves_url() -> None:
    output = build_output(ready_verification())
    x_candidate = output["generated_items"][0][
        "x_candidate"
    ]

    assert "#" not in x_candidate[
        "candidate_text_without_url"
    ]
    assert x_candidate["reserved_url_characters"] == 23
    assert (
        x_candidate["character_count_without_url"]
        <= 257
    )
    assert x_candidate["automatic_post_allowed"] is False


def test_feedback_initialize_request_is_generated() -> None:
    output = build_output(ready_verification())
    request = output["generated_items"][0][
        "x_feedback_initialize_request"
    ]

    assert request["action"] == "INITIALIZE"
    assert request["wordpress_post_id"] is None
    assert request["template_id"] == "X_NEW_RELEASE_V1"
    assert "TITLE_FIRST" in request["wording_labels"]


def test_preview_digest_is_deterministic() -> None:
    first = build_output(ready_verification())
    second = build_output(ready_verification())

    first_digest = first["generated_items"][0][
        "preview_digest_sha256"
    ]
    second_digest = second["generated_items"][0][
        "preview_digest_sha256"
    ]

    assert first_digest == second_digest
    assert len(first_digest) == 64


def test_check_only_passes_without_live_write() -> None:
    completed = run_builder(VERIFICATION_PATH)

    assert completed.returncode == 0

    result = json.loads(completed.stdout)

    assert (
        result["status"]
        == "PASS_ARTICLE_BATCH_DRY_RUN_NO_LIVE_WRITE"
    )
    assert result["generated_item_count"] == 0
    assert result["wordpress_write_allowed"] is False
    assert result["x_post_allowed"] is False
    assert result["ready_for_ls_new_batch_4"] is True


def test_generated_evidence_is_complete() -> None:
    assert OUTPUT_PATH.exists()
    assert RESULT_PATH.exists()
    assert REPORT_PATH.exists()

    output = load_json(OUTPUT_PATH)
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert output["generated_item_count"] == 0
    assert output["skipped_item_count"] == 1
    assert (
        result["status"]
        == "PASS_ARTICLE_BATCH_DRY_RUN_NO_LIVE_WRITE"
    )
    assert result["ready_for_real_ready_item_dry_run"] is True
    assert result["next_phase_execution_allowed"] is False
    assert "WordPress write allowed: `false`" in report
    assert "X posting allowed: `false`" in report
