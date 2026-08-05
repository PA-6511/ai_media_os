from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "input_registration_v2_policy.json"
)
OLD_APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_g_"
    "article_input_registration_approval.json"
)
V2_APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_g_"
    "article_input_registration_approval_v2.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "input_registration_request_v2.example.json"
)
INPUT = (
    ROOT
    / "exchange/inputs/new_release/fresh/"
    "new-release-comic-20260703-001.input.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_g_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_g_"
    "article_input_registration_report.md"
)
BUILDER = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_g_v2.py"
)
BLOCKED = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_g_v2_blocked.py"
)


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(value) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def module():
    spec = importlib.util.spec_from_file_location(
        "recovery_g_v2_builder",
        BUILDER,
    )
    assert spec is not None
    assert spec.loader is not None

    item = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(item)
    return item


def test_policy_revision_two() -> None:
    policy = load(POLICY)

    assert policy["policy_revision"] == 2
    assert (
        policy["operation_mode"]
        == (
            "APPROVED_FRESH_ARTICLE_INPUT_"
            "REGISTRATION_REISSUE_V2_ONLY"
        )
    )
    assert (
        policy["approval_contract"][
            "superseded_approval_must_be_preserved"
        ]
        is True
    )


def test_v2_approval_is_valid() -> None:
    approval = load(V2_APPROVAL)
    without_digest = copy.deepcopy(
        approval
    )
    stored = without_digest.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(without_digest) == stored
    assert approval["approval_revision"] == 2
    assert (
        approval["reissue_approval_label"]
        == (
            "FRESH_ARTICLE_INPUT_REGISTRATION_"
            "APPROVAL_REISSUE_APPROVED"
        )
    )
    assert (
        approval[
            "human_explicit_reissue_approval"
        ]
        is True
    )
    assert approval["execution_allowed"] is False


def test_old_approval_is_preserved() -> None:
    request = load(REQUEST)
    approval_v2 = load(V2_APPROVAL)

    assert OLD_APPROVAL.exists()
    assert (
        file_sha256(OLD_APPROVAL)
        == request[
            "superseded_approval_file_sha256"
        ]
    )
    assert (
        approval_v2["superseded_approval"][
            "preserved"
        ]
        is True
    )
    assert (
        approval_v2["superseded_approval"][
            "modified"
        ]
        is False
    )


def test_registration_identity() -> None:
    item = load(INPUT)

    assert (
        item["content_item_id"]
        == "new-release-comic-20260703-001"
    )
    assert item["work_title"] == "ダークギャザリング"
    assert item["volume_label"] == "第20巻"
    assert (
        item["article_title"]
        == "ダークギャザリング 第20巻｜配信開始"
    )
    assert item["release_date"] == "2026-07-03"
    assert item["author_name"] == "近藤憲一"
    assert item["publisher_name"] == "集英社"


def test_registration_has_no_categories() -> None:
    item = load(INPUT)

    assert "categories" not in item
    assert item["categories_initial_state"] == "ABSENT"
    assert (
        item[
            "production_category_id_payload_injected"
        ]
        is False
    )


def test_store_identifiers() -> None:
    item = load(INPUT)
    stores = item["store_links"]

    assert (
        stores["amazon"][
            "product_identifier"
        ]
        == "B0H3N7QK5K"
    )
    assert (
        stores["rakuten_kobo"][
            "product_identifier"
        ]
        == "4972000159519"
    )
    assert (
        stores["dmm_books"][
            "product_identifier"
        ]
        == "861056"
    )


def test_price_sources_are_rakuten_and_dmm() -> None:
    item = load(INPUT)
    price = item["price"]

    assert price["amount"] == 616
    assert price["currency"] == "JPY"
    assert set(
        price["verification_sources"]
    ) == {
        "rakuten_kobo",
        "dmm_books",
    }


def test_dmm_alias_recheck_required() -> None:
    item = load(INPUT)
    dmm = item["store_links"][
        "dmm_books"
    ]

    assert (
        dmm["url_kind"]
        == "SERIES_LATEST_ALIAS"
    )
    assert (
        dmm[
            "requires_recheck_before_payload_generation"
        ]
        is True
    )


def test_request_has_no_execution() -> None:
    request = load(REQUEST)

    assert request[
        "article_input_registration_requested"
    ] is True
    assert request[
        "human_review_completion_requested"
    ] is False
    assert request[
        "article_content_generation_requested"
    ] is False
    assert request[
        "fresh_payload_creation_requested"
    ] is False
    assert request[
        "payload_binding_requested"
    ] is False
    assert request[
        "production_category_id_payload_injection_requested"
    ] is False
    assert request[
        "wordpress_write_requested"
    ] is False
    assert request["execution_requested"] is False


def test_category_injection_is_rejected() -> None:
    builder = module()
    request = copy.deepcopy(
        load(REQUEST)
    )
    request["article_input"][
        "categories"
    ] = [10]

    try:
        builder.validate_article(
            request["article_input"],
            load(POLICY),
        )
    except builder.ValidationError as exc:
        assert "categories field" in str(exc)
    else:
        raise AssertionError(
            "categories field was accepted"
        )


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

    assert result[
        "superseded_approval_preserved"
    ] is True
    assert result[
        "human_review_complete"
    ] is False
    assert result[
        "fresh_payload_created"
    ] is False
    assert result[
        "production_category_id_payload_injected"
    ] is False
    assert result[
        "wordpress_write_performed"
    ] is False
    assert result["execution_allowed"] is False


def test_result_ready_for_human_review_only() -> None:
    result = load(RESULT)

    assert (
        result["status"]
        == (
            "PASS_FRESH_ARTICLE_INPUT_REGISTERED_"
            "NO_PAYLOAD_NO_NETWORK"
        )
    )
    assert result["approval_revision"] == 2
    assert result["approval_reissued"] is True
    assert (
        result["current_f_result_rebound"]
        is True
    )
    assert (
        result["superseded_approval_preserved"]
        is True
    )
    assert result[
        "article_input_registered"
    ] is True
    assert result["input_complete"] is True
    assert result[
        "human_review_complete"
    ] is False
    assert result[
        "fresh_payload_created"
    ] is False
    assert result[
        "production_category_id_payload_injected"
    ] is False
    assert result[
        "ready_for_fresh_article_input_human_review"
    ] is True
    assert result[
        "ready_for_article_content_generation"
    ] is False
    assert result["ready_for_execution"] is False


def test_report_confirms_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Approval revision: `2`" in report
    assert (
        "Superseded approval preserved: `true`"
        in report
    )
    assert (
        "Human review complete: `false`"
        in report
    )
    assert (
        "Fresh payload created: `false`"
        in report
    )
    assert (
        "Category ID injected: `false`"
        in report
    )
    assert (
        "WordPress write performed: `false`"
        in report
    )
