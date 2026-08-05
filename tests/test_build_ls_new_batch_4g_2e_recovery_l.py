from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "content_human_review_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "content_human_review_request.example.json"
)
APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_l_"
    "content_human_review_approval.json"
)
REVIEW = (
    ROOT
    / "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_content_human_review.json"
)
ARTICLE = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
CONSUMPTION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_consumption.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_l_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_l_"
    "content_human_review_report.md"
)
BLOCKED = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_l_blocked.py"
)


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_policy_is_review_only() -> None:
    policy = load(POLICY)

    assert (
        policy["execution_boundary"][
            "review_evidence_creation_allowed"
        ]
        is True
    )
    assert (
        policy["execution_boundary"][
            "generated_article_write_allowed"
        ]
        is False
    )
    assert (
        policy["execution_boundary"][
            "fresh_payload_creation_allowed"
        ]
        is False
    )


def test_review_approval_digest() -> None:
    approval = load(APPROVAL)
    comparable = copy.deepcopy(
        approval
    )
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval["human_explicit_approval"] is True
    assert (
        approval["approval_label"]
        == "FRESH_ARTICLE_CONTENT_HUMAN_REVIEW_APPROVED"
    )


def test_review_evidence_digest() -> None:
    review = load(REVIEW)
    comparable = copy.deepcopy(
        review
    )
    stored = comparable.pop(
        "human_review_digest_sha256"
    )

    assert digest(comparable) == stored


def test_generated_article_is_preserved() -> None:
    request = load(REQUEST)

    assert (
        file_sha256(ARTICLE)
        == request["source_bindings"][
            "generated_article_file_sha256"
        ]
    )


def test_consumption_evidence_is_preserved() -> None:
    request = load(REQUEST)

    assert (
        file_sha256(CONSUMPTION)
        == request["source_bindings"][
            "consumption_evidence_file_sha256"
        ]
    )

    evidence = load(CONSUMPTION)

    assert evidence["authorization_consumed"] is True
    assert evidence["authorization_reuse_allowed"] is False


def test_title_and_disclosure_are_approved() -> None:
    review = load(REVIEW)
    checks = review["review_checks"]

    assert checks["article_title_matches"] is True
    assert (
        checks[
            "disclosure_is_first_visible_component"
        ]
        is True
    )
    assert checks["disclosure_text_exact"] is True


def test_cover_is_approved() -> None:
    checks = load(REVIEW)["review_checks"]

    assert checks["single_cover_image"] is True
    assert checks["cover_alt_matches"] is True
    assert checks["cover_loading_lazy"] is True
    assert checks["cover_asset_url_present"] is True
    assert checks["anchor_elements_absent"] is True


def test_information_card_is_approved() -> None:
    checks = load(REVIEW)["review_checks"]

    for field in [
        "作品名",
        "価格",
        "作者",
        "出版社",
        "発売日",
    ]:
        assert (
            checks[
                f"information_field_{field}_matches"
            ]
            is True
        )

    assert (
        checks["information_card_order_matches"]
        is True
    )


def test_store_slots_are_non_clickable_and_ordered() -> None:
    checks = load(REVIEW)["review_checks"]

    assert checks["store_slot_count_is_three"] is True
    assert checks["store_slot_order_matches"] is True
    assert (
        checks["all_store_slots_aria_disabled"]
        is True
    )
    assert checks["anchor_elements_absent"] is True
    assert checks["href_attributes_absent"] is True


def test_store_and_dmm_urls_are_absent() -> None:
    checks = load(REVIEW)["review_checks"]

    assert checks["store_product_urls_absent"] is True
    assert checks["final_affiliate_urls_absent"] is True
    assert checks["dmm_url_absent"] is True


def test_unnecessary_and_legacy_content_is_absent() -> None:
    checks = load(REVIEW)["review_checks"]

    assert (
        checks[
            "unnecessary_and_legacy_content_absent"
        ]
        is True
    )
    assert checks["categories_field_absent"] is True


def test_review_decision_is_approved_no_change() -> None:
    review = load(REVIEW)

    assert review["human_review_complete"] is True
    assert (
        review["review_decision"]
        == "APPROVED_NO_CHANGE_REQUIRED"
    )
    assert review["no_change_required"] is True
    assert (
        review[
            "content_approved_for_store_link_finalization_gate"
        ]
        is True
    )
    assert (
        review[
            "content_approved_for_payload_generation"
        ]
        is False
    )


def test_production_boundary_remains_closed() -> None:
    result = load(RESULT)

    assert result["fresh_payload_created"] is False
    assert result["payload_binding_complete"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert result["network_connection_performed"] is False
    assert result["wordpress_write_performed"] is False
    assert result["wordpress_published"] is False
    assert result["execution_allowed"] is False
    assert result["production_status"] == "NO_GO"


def test_blocked_runner_returns_three() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(BLOCKED),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    blocked = json.loads(
        completed.stderr
    )

    assert (
        blocked[
            "generated_article_modification_allowed"
        ]
        is False
    )
    assert (
        blocked[
            "fresh_payload_creation_allowed"
        ]
        is False
    )
    assert blocked["wordpress_write_allowed"] is False


def test_result_ready_for_store_link_gate_only() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_FRESH_ARTICLE_CONTENT_HUMAN_REVIEW_"
        "APPROVED_NO_CHANGE_NO_PAYLOAD_NO_NETWORK"
    )
    assert result["human_review_complete"] is True
    assert (
        result["review_decision"]
        == "APPROVED_NO_CHANGE_REQUIRED"
    )
    assert (
        result[
            "ready_for_store_link_finalization_gate"
        ]
        is True
    )
    assert result["ready_for_dmm_recheck_gate"] is True
    assert (
        result[
            "ready_for_fresh_payload_generation"
        ]
        is False
    )
    assert result["ready_for_execution"] is False


def test_report_confirms_review_and_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Human review complete: `true`" in report
    assert (
        "Review decision: "
        "`APPROVED_NO_CHANGE_REQUIRED`"
        in report
    )
    assert "Generated article modified: `false`" in report
    assert "Payload created: `false`" in report
    assert "Production status: `NO_GO`" in report
