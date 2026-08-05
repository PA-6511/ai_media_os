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
    "one_shot_offline_generation_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "one_shot_offline_generation_execute_request.example.json"
)
APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_k_execute_now_approval.json"
)
OUTPUT = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
AUTHORIZATION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_authorization.json"
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
    "ls_new_batch_4g_2e_recovery_k_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_k_"
    "one_shot_offline_generation_report.md"
)
BUILDER = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_k.py"
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


def test_policy_is_one_shot_generation_only() -> None:
    policy = load(POLICY)

    assert (
        policy["operation_mode"]
        == (
            "EXPLICITLY_APPROVED_ONE_SHOT_OFFLINE_"
            "ARTICLE_CONTENT_GENERATION"
        )
    )
    assert (
        policy["output_contract"][
            "one_shot_creation_allowed"
        ]
        is True
    )
    assert (
        policy["output_contract"][
            "overwrite_allowed"
        ]
        is False
    )
    assert (
        policy["output_contract"][
            "second_creation_allowed"
        ]
        is False
    )


def test_execute_approval_digest() -> None:
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
        == (
            "FRESH_ARTICLE_ONE_SHOT_OFFLINE_"
            "GENERATION_EXECUTE_NOW_APPROVED"
        )
    )


def test_article_output_digest() -> None:
    article = load(OUTPUT)
    comparable = copy.deepcopy(
        article
    )
    stored = comparable.pop(
        "article_content_digest_sha256"
    )

    assert digest(comparable) == stored
    assert article["article_content_generated"] is True
    assert article["human_review_complete"] is False


def test_fixed_disclosure_is_first_visible_component() -> None:
    article = load(OUTPUT)
    content = article["content_html"]

    assert content.startswith(
        (
            '<div class="ebook-new-release-article" '
            'data-template-id="POST185_STANDARD_TEMPLATE_V1">\n'
            '  <p class="ebook-pr-disclosure">'
        )
    )
    assert (
        "【PR】本記事にはアフィリエイト広告を含みます。"
        "価格・配信状況は各ストアで確認してください。"
        in content
    )


def test_current_cover_is_rendered_unlinked() -> None:
    article = load(OUTPUT)
    content = article["content_html"]

    assert (
        "https://shop.r10s.jp/rakutenkobo-ebooks/"
        "cabinet/6485/2000020786485.jpg"
        in content
    )
    assert "ダークギャザリング 第20巻 書影" in content
    assert "<a " not in content.lower()
    assert "href=" not in content.lower()


def test_information_card_values() -> None:
    content = load(OUTPUT)["content_html"]

    for required in [
        "作品名：",
        "ダークギャザリング",
        "価格：",
        "616円（税込）",
        "作者：",
        "近藤憲一",
        "出版社：",
        "集英社",
        "発売日：",
        "2026-07-03",
    ]:
        assert required in content


def test_store_slots_are_non_clickable() -> None:
    content = load(OUTPUT)["content_html"]

    assert content.count("<span ") == 3
    assert content.count('aria-disabled="true"') == 3

    assert "ls-store-amazon" in content
    assert "ls-store-kobo" in content
    assert "ls-store-dmm" in content

    assert "Amazonで確認（リンク準備中）" in content
    assert "楽天Koboで確認（リンク準備中）" in content
    assert "DMMブックスで確認（再確認待ち）" in content


def test_no_store_or_dmm_urls() -> None:
    article = load(OUTPUT)
    serialized = json.dumps(
        article,
        ensure_ascii=False,
        sort_keys=True,
    )

    for forbidden in [
        "https://www.amazon.co.jp/dp/",
        "https://books.rakuten.co.jp/rk/",
        "https://book.dmm.com/",
        "https://al.dmm.com/",
        "https://hb.afl.rakuten.co.jp/",
    ]:
        assert forbidden not in serialized


def test_no_unsupported_content() -> None:
    content = load(OUTPUT)["content_html"]

    for forbidden in [
        "あらすじ",
        "ポイント還元",
        "割引",
        "キャンペーン",
        "在庫",
        "月曜日のたわわ",
        "比村奇石",
        "税込792円",
        "B0H6DQLPPB",
        "4071859",
    ]:
        assert forbidden not in content


def test_output_is_not_payload() -> None:
    article = load(OUTPUT)

    assert "categories" not in article
    assert article["categories_field_present"] is False
    assert article["fresh_payload_created"] is False
    assert article["payload_binding_complete"] is False
    assert (
        article[
            "production_category_id_payload_injected"
        ]
        is False
    )


def test_consumption_evidence_digest() -> None:
    evidence = load(CONSUMPTION)
    comparable = copy.deepcopy(
        evidence
    )
    stored = comparable.pop(
        "consumption_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert evidence["authorization_consumed"] is True
    assert evidence["consumption_is_authoritative"] is True
    assert evidence["single_use"] is True
    assert evidence["authorization_reuse_allowed"] is False
    assert evidence["second_generation_allowed"] is False


def test_consumption_binds_generated_output() -> None:
    evidence = load(CONSUMPTION)
    article = load(OUTPUT)

    assert (
        evidence["generated_content_file_sha256"]
        == file_sha256(OUTPUT)
    )
    assert (
        evidence[
            "generated_content_artifact_digest_sha256"
        ]
        == article[
            "article_content_digest_sha256"
        ]
    )


def test_source_authorization_is_preserved() -> None:
    request = load(REQUEST)
    authorization = load(AUTHORIZATION)

    assert (
        file_sha256(AUTHORIZATION)
        == request[
            "source_bindings"
        ]["authorization_file_sha256"]
    )
    assert authorization["authorization_consumed"] is False

    evidence = load(CONSUMPTION)

    assert evidence["source_authorization_modified"] is False
    assert evidence["authorization_consumed"] is True


def test_result_records_terminal_one_shot_state() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_FRESH_ARTICLE_CONTENT_GENERATED_"
        "OFFLINE_ONE_SHOT_AUTHORIZATION_CONSUMED_"
        "NO_PAYLOAD_NO_NETWORK"
    )
    assert result["article_content_generated"] is True
    assert result["content_output_exists"] is True
    assert result["authorization_consumed"] is True
    assert result["consumption_evidence_created"] is True
    assert result["authorization_reuse_allowed"] is False
    assert result["second_generation_allowed"] is False


def test_result_keeps_production_closed() -> None:
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
    assert result["http_request_performed"] is False
    assert result["wordpress_access_performed"] is False
    assert result["wordpress_write_performed"] is False
    assert result["wordpress_draft_created"] is False
    assert result["wordpress_published"] is False
    assert result["execution_allowed"] is False
    assert result["production_status"] == "NO_GO"


def test_rerun_is_blocked_without_changes() -> None:
    output_hash_before = file_sha256(
        OUTPUT
    )
    consumption_hash_before = file_sha256(
        CONSUMPTION
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--execute",
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
        blocked["status"]
        == (
            "BLOCKED_ONE_SHOT_AUTHORIZATION_"
            "ALREADY_CONSUMED"
        )
    )
    assert blocked["authorization_reuse_allowed"] is False
    assert blocked["second_generation_allowed"] is False

    assert file_sha256(OUTPUT) == output_hash_before
    assert (
        file_sha256(CONSUMPTION)
        == consumption_hash_before
    )


def test_report_confirms_human_review_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Article content generated: `true`" in report
    assert "Authorization consumed: `true`" in report
    assert "Source authorization modified: `false`" in report
    assert "Store URLs included: `false`" in report
    assert "Payload created: `false`" in report
    assert "Production status: `NO_GO`" in report
