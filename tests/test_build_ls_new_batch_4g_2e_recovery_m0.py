from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY = (
    ROOT
    / "config/"
    "new_release_wp_fresh_store_link_"
    "finalization_plan_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_store_link_"
    "finalization_plan_request.example.json"
)
APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m0_"
    "store_link_finalization_plan_approval.json"
)
PLAN = (
    ROOT
    / "exchange/plans/new_release/fresh/"
    "new-release-comic-20260703-001."
    "store_link_finalization_plan.json"
)
ARTICLE = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
CONTENT_REVIEW = (
    ROOT
    / "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_content_human_review.json"
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
    "ls_new_batch_4g_2e_recovery_m0_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_m0_"
    "store_link_finalization_plan_report.md"
)
BLOCKED = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_m0_blocked.py"
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


def test_policy_is_plan_only() -> None:
    policy = load(POLICY)
    boundary = policy[
        "execution_boundary"
    ]

    assert (
        boundary[
            "store_link_finalization_plan_creation_allowed"
        ]
        is True
    )
    assert (
        boundary[
            "final_affiliate_link_generation_allowed"
        ]
        is False
    )
    assert boundary["dmm_recheck_allowed"] is False
    assert (
        boundary["article_url_injection_allowed"]
        is False
    )
    assert (
        boundary["network_connection_allowed"]
        is False
    )


def test_approval_digest() -> None:
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
        == "FRESH_STORE_LINK_FINALIZATION_PLAN_APPROVED"
    )


def test_plan_digest() -> None:
    plan = load(PLAN)
    comparable = copy.deepcopy(
        plan
    )
    stored = comparable.pop(
        "store_link_finalization_plan_digest_sha256"
    )

    assert digest(comparable) == stored


def test_store_order_and_common_attributes() -> None:
    plan = load(PLAN)

    assert plan["store_order"] == [
        "amazon",
        "rakuten_kobo",
        "dmm_books",
    ]

    common = plan[
        "common_link_contract"
    ]

    assert common["scheme"] == "https"
    assert common["target"] == "_blank"
    assert common["required_rel_tokens"] == [
        "nofollow",
        "sponsored",
        "noopener",
    ]
    assert common["dummy_url_allowed"] is False
    assert common["placeholder_url_allowed"] is False


def test_amazon_plan() -> None:
    amazon = load(PLAN)["stores"]["amazon"]

    assert amazon["order"] == 1
    assert amazon["identifier"] == {
        "type": "ASIN",
        "value": "B0H3N7QK5K",
    }
    assert (
        amazon["verification_source"][
            "is_final_affiliate_link"
        ]
        is False
    )
    assert (
        amazon["finalization"]["final_affiliate_url"]
        is None
    )
    assert amazon["finalization"]["ready"] is False


def test_rakuten_plan() -> None:
    rakuten = load(PLAN)[
        "stores"
    ]["rakuten_kobo"]

    assert rakuten["order"] == 2
    assert (
        rakuten["identifier"]["value"]
        == "4972000159519"
    )
    assert (
        rakuten["finalization"][
            "required_final_host"
        ]
        == "hb.afl.rakuten.co.jp"
    )
    assert (
        rakuten["finalization"][
            "final_affiliate_url"
        ]
        is None
    )


def test_dmm_plan_and_recheck() -> None:
    dmm = load(PLAN)[
        "stores"
    ]["dmm_books"]

    assert dmm["order"] == 3
    assert dmm["identifier"] == {
        "type": "DMM_SERIES_ID",
        "value": "861056",
    }
    assert dmm["recheck"]["required"] is True
    assert dmm["recheck"]["completed"] is False
    assert (
        dmm["recheck"][
            "canonical_product_resolution_required"
        ]
        is True
    )
    assert (
        dmm["recheck"][
            "series_latest_alias_may_be_final_link"
        ]
        is False
    )
    assert (
        dmm["finalization"]["required_final_host"]
        == "al.dmm.com"
    )
    assert (
        dmm["finalization"]["final_affiliate_url"]
        is None
    )


def test_verification_urls_are_sources_only() -> None:
    plan = load(PLAN)

    expected_hosts = {
        "amazon": "www.amazon.co.jp",
        "rakuten_kobo": "books.rakuten.co.jp",
        "dmm_books": "book.dmm.com",
    }

    for store_id, host in expected_hosts.items():
        source = plan[
            "stores"
        ][store_id]["verification_source"]

        assert source[
            "is_final_affiliate_link"
        ] is False
        assert (
            source["role"]
            == (
                "PRODUCT_VERIFICATION_SOURCE_"
                "NOT_FINAL_AFFILIATE_LINK"
            )
        )
        assert (
            urlparse(source["url"]).hostname
            == host
        )


def test_no_final_affiliate_links_generated() -> None:
    plan = load(PLAN)

    for store in plan["stores"].values():
        assert (
            store["finalization"][
                "final_affiliate_url"
            ]
            is None
        )
        assert store["finalization"]["ready"] is False

    state = plan["current_state"]

    assert (
        state["final_affiliate_links_generated"]
        is False
    )
    assert (
        state["final_affiliate_links_validated"]
        is False
    )
    assert (
        state[
            "final_affiliate_links_injected_into_article"
        ]
        is False
    )


def test_failure_and_hide_contract() -> None:
    failure = load(PLAN)[
        "failure_contract"
    ]

    assert (
        failure["all_store_links_unavailable"]
        == "BLOCK_PAYLOAD_GENERATION"
    )
    assert (
        failure[
            "partial_store_links_available"
        ]
        == (
            "REQUIRE_EXPLICIT_HUMAN_APPROVAL_"
            "BEFORE_PAYLOAD"
        )
    )
    assert (
        failure[
            "minimum_valid_final_link_count_for_future_payload"
        ]
        == 1
    )
    assert (
        failure[
            "unresolved_store_slot_rendering_allowed"
        ]
        is False
    )


def test_article_and_review_are_preserved() -> None:
    request = load(REQUEST)
    bindings = request[
        "source_bindings"
    ]

    assert (
        file_sha256(ARTICLE)
        == bindings[
            "generated_article_file_sha256"
        ]
    )
    assert (
        file_sha256(CONTENT_REVIEW)
        == bindings[
            "content_human_review_file_sha256"
        ]
    )
    assert (
        file_sha256(CONSUMPTION)
        == bindings[
            "consumption_evidence_file_sha256"
        ]
    )


def test_article_still_has_no_links() -> None:
    article = load(ARTICLE)
    content = article["content_html"]

    assert "<a " not in content.lower()
    assert "href=" not in content.lower()
    assert (
        article["store_navigation"][
            "verification_source_urls_included"
        ]
        is False
    )
    assert (
        article["store_navigation"][
            "final_affiliate_urls_included"
        ]
        is False
    )


def test_current_phase_has_no_network_or_payload() -> None:
    result = load(RESULT)

    assert (
        result["final_affiliate_links_generated"]
        is False
    )
    assert (
        result["dmm_latest_alias_recheck_completed"]
        is False
    )
    assert result["fresh_payload_created"] is False
    assert result["payload_binding_complete"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert (
        result["network_connection_performed"]
        is False
    )
    assert result["http_request_performed"] is False
    assert (
        result["wordpress_write_performed"]
        is False
    )
    assert result["execution_allowed"] is False


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
            "final_affiliate_link_generation_allowed"
        ]
        is False
    )
    assert blocked["dmm_recheck_allowed"] is False
    assert (
        blocked["article_url_injection_allowed"]
        is False
    )
    assert (
        blocked["network_connection_allowed"]
        is False
    )


def test_result_ready_for_dmm_authorization_only() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_FRESH_STORE_LINK_FINALIZATION_PLAN_"
        "FIXED_NO_LINK_GENERATION_NO_NETWORK"
    )
    assert (
        result[
            "ready_for_dmm_recheck_authorization"
        ]
        is True
    )
    assert (
        result["ready_for_actual_dmm_recheck"]
        is False
    )
    assert (
        result[
            "ready_for_final_affiliate_link_generation"
        ]
        is False
    )
    assert (
        result["ready_for_article_url_injection"]
        is False
    )
    assert (
        result["ready_for_fresh_payload_generation"]
        is False
    )
    assert result["ready_for_execution"] is False


def test_report_confirms_plan_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert (
        "Final link generated: `false`"
        in report
    )
    assert (
        "Latest-alias recheck completed: `false`"
        in report
    )
    assert (
        "Generated article modified: `false`"
        in report
    )
    assert "Network accessed: `false`" in report
    assert "Production status: `NO_GO`" in report
