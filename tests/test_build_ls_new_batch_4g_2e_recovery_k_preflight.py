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
    "one_shot_offline_generation_preflight_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "one_shot_offline_generation_preflight_request.example.json"
)
APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_k_preflight_approval.json"
)
PLAN = (
    ROOT
    / "exchange/preflight/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_preflight.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_k_preflight_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_k_preflight_report.md"
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
OUTPUT = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
BLOCKED = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_k_preflight_blocked.py"
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


def test_policy_is_preflight_only() -> None:
    policy = load(POLICY)

    assert (
        policy["operation_mode"]
        == (
            "APPROVED_ONE_SHOT_OFFLINE_"
            "GENERATION_PREFLIGHT_ONLY"
        )
    )
    assert (
        policy["execution_boundary"][
            "preflight_plan_creation_allowed"
        ]
        is True
    )
    assert (
        policy["execution_boundary"][
            "article_content_generation_allowed"
        ]
        is False
    )
    assert (
        policy["execution_boundary"][
            "authorization_consumption_allowed"
        ]
        is False
    )


def test_preflight_approval_digest() -> None:
    approval = load(APPROVAL)
    comparable = copy.deepcopy(approval)
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval["human_explicit_approval"] is True
    assert approval["execution_allowed"] is False


def test_preflight_plan_digest() -> None:
    plan = load(PLAN)
    comparable = copy.deepcopy(plan)
    stored = comparable.pop(
        "preflight_plan_digest_sha256"
    )

    assert digest(comparable) == stored


def test_current_article_identity_is_fixed() -> None:
    identity = load(PLAN)["article_identity"]

    assert identity["work_title"] == "ダークギャザリング"
    assert identity["volume_label"] == "第20巻"
    assert identity["release_date"] == "2026-07-03"
    assert identity["author_name"] == "近藤憲一"
    assert identity["publisher_name"] == "集英社"


def test_fixed_disclosure_is_first() -> None:
    render = load(PLAN)["planned_render"]

    assert (
        render["component_order"][0]
        == "advertising_disclosure"
    )
    assert (
        render["advertising_disclosure"]["exact_text"]
        == (
            "【PR】本記事にはアフィリエイト広告を含みます。"
            "価格・配信状況は各ストアで確認してください。"
        )
    )


def test_current_cover_is_planned_without_anchor() -> None:
    cover = load(PLAN)["planned_render"]["cover"]

    assert cover["required"] is True
    assert cover["image_source"] == "rakuten_kobo"
    assert cover["verification_state"] == "VERIFIED"
    assert cover["anchor_element"] is False
    assert cover["href"] is None
    assert (
        cover["image_url"].startswith(
            "https://shop.r10s.jp/"
        )
    )


def test_information_card_order_and_values() -> None:
    card = load(PLAN)[
        "planned_render"
    ]["information_card"]

    assert [
        item["label"]
        for item in card["ordered_fields"]
    ] == [
        "作品名",
        "価格",
        "作者",
        "出版社",
        "発売日",
    ]

    assert [
        item["value"]
        for item in card["ordered_fields"]
    ] == [
        "ダークギャザリング",
        "616円（税込）",
        "近藤憲一",
        "集英社",
        "2026-07-03",
    ]

    assert card["volume_line_included"] is False


def test_store_slots_are_non_clickable_and_ordered() -> None:
    navigation = load(PLAN)[
        "planned_render"
    ]["store_navigation"]

    assert (
        navigation["render_mode"]
        == "RESERVED_NON_CLICKABLE_SLOTS_ONLY"
    )
    assert [
        slot["store_id"]
        for slot in navigation["slots"]
    ] == [
        "amazon",
        "rakuten_kobo",
        "dmm_books",
    ]

    for slot in navigation["slots"]:
        assert slot["render_element"] == "span"
        assert slot["href"] is None
        assert slot["url_included"] is False
        assert slot["aria_disabled"] is True


def test_no_store_urls_in_preflight_plan() -> None:
    serialized = json.dumps(
        load(PLAN),
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


def test_dmm_recheck_remains_pending() -> None:
    plan = load(PLAN)
    slots = plan[
        "planned_render"
    ]["store_navigation"]["slots"]
    dmm = slots[2]

    assert dmm["store_id"] == "dmm_books"
    assert dmm["latest_alias_recheck_required"] is True
    assert dmm["latest_alias_recheck_completed"] is False
    assert dmm["href"] is None


def test_authorization_is_preserved() -> None:
    request = load(REQUEST)
    binding = request[
        "source_bindings"
    ]

    assert (
        file_sha256(AUTHORIZATION)
        == binding[
            "authorization_file_sha256"
        ]
    )

    authorization = load(AUTHORIZATION)

    assert authorization["single_use"] is True
    assert authorization["authorization_consumed"] is False


def test_no_consumption_or_content_output() -> None:
    assert not CONSUMPTION.exists()
    assert not OUTPUT.exists()


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

    result = json.loads(
        completed.stderr
    )

    assert (
        result["preflight_plan_creation_allowed"]
        is True
    )
    assert result["article_content_generated"] is False
    assert result["authorization_consumed"] is False
    assert result["wordpress_write_performed"] is False
    assert result["execution_allowed"] is False


def test_result_requires_execute_now_confirmation() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_FRESH_ARTICLE_ONE_SHOT_OFFLINE_"
        "GENERATION_PREFLIGHT_NO_CONTENT_"
        "NO_AUTH_CONSUMPTION_NO_NETWORK"
    )
    assert result["all_source_digests_verified"] is True
    assert result["store_urls_included"] is False
    assert result["dmm_url_included"] is False
    assert result["authorization_consumed"] is False
    assert result["content_output_exists"] is False
    assert result["article_content_generated"] is False
    assert (
        result[
            "ready_for_recovery_k_execute_now_confirmation"
        ]
        is True
    )
    assert (
        result[
            "ready_for_one_shot_offline_article_content_generation"
        ]
        is False
    )
    assert result["ready_for_execution"] is False


def test_report_confirms_preflight_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Store URLs included: `false`" in report
    assert "DMM URL included: `false`" in report
    assert "Authorization consumed: `false`" in report
    assert "Content output exists: `false`" in report
    assert "Execution allowed: `false`" in report
