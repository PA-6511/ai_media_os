from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = (
    ROOT / "config/"
    "new_release_wp_fresh_article_"
    "template_reconciliation_policy.json"
)
REQUEST = (
    ROOT / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "template_reconciliation_request.example.json"
)
CONTRACT = (
    ROOT / "config/"
    "new_release_wp_fresh_article_"
    "template_reconciliation_contract.json"
)
APPROVAL = (
    ROOT / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_k0_"
    "template_reconciliation_approval.json"
)
AUTHORIZATION = (
    ROOT / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_authorization.json"
)
CONSUMPTION = (
    ROOT / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_consumption.json"
)
OUTPUT = (
    ROOT / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
RESULT = (
    ROOT / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_k0_result.json"
)
REPORT = (
    ROOT / "reports/"
    "ls_new_batch_4g_2e_recovery_k0_"
    "template_reconciliation_report.md"
)
BLOCKED = (
    ROOT / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_k0_blocked.py"
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


def test_policy_is_reconciliation_only() -> None:
    policy = load(POLICY)

    assert (
        policy["operation_mode"]
        == (
            "APPROVED_TEMPLATE_RECONCILIATION_"
            "CONTRACT_FIXATION_ONLY"
        )
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


def test_approval_digest() -> None:
    approval = load(APPROVAL)
    without_digest = copy.deepcopy(approval)
    stored = without_digest.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(without_digest) == stored
    assert approval["human_explicit_approval"] is True
    assert (
        approval["authorization_consumption_allowed"]
        is False
    )


def test_contract_digest() -> None:
    contract = load(CONTRACT)
    without_digest = copy.deepcopy(contract)
    stored = without_digest.pop(
        "template_reconciliation_contract_digest_sha256"
    )

    assert digest(without_digest) == stored
    assert contract["template_artifact_resolved"] is True


def test_disclosure_exact_text() -> None:
    contract = load(CONTRACT)

    assert (
        contract["advertising_disclosure"]["exact_text"]
        == (
            "【PR】本記事にはアフィリエイト広告を含みます。"
            "価格・配信状況は各ストアで確認してください。"
        )
    )


def test_information_card_and_store_order() -> None:
    structure = load(CONTRACT)["resolved_structure"]

    assert structure["information_card_fields"] == [
        "作品名",
        "価格",
        "作者",
        "出版社",
        "発売日",
    ]
    assert structure["store_button_order"] == [
        "amazon",
        "rakuten_kobo",
        "dmm_books",
    ]


def test_legacy_data_and_urls_are_blocked() -> None:
    contract = load(CONTRACT)
    legacy = contract["legacy_exclusion"]

    assert (
        legacy[
            "post185_product_data_inheritance_allowed"
        ]
        is False
    )
    assert (
        legacy["post185_url_inheritance_allowed"]
        is False
    )
    assert legacy["snapshot_href_reuse_allowed"] is False


def test_link_rendering_is_blocked() -> None:
    links = load(CONTRACT)["link_rendering"]

    assert (
        links["final_affiliate_link_rendering_allowed"]
        is False
    )
    assert links["dmm_url_rendering_allowed"] is False
    assert links["dmm_latest_alias_recheck_completed"] is False


def test_authorization_is_preserved() -> None:
    request = load(REQUEST)
    authorization = load(AUTHORIZATION)

    assert (
        file_sha256(AUTHORIZATION)
        == request["source_authorization_file_sha256"]
    )
    assert authorization["authorization_consumed"] is False
    assert (
        authorization["authorized_next_phase_id"]
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K"
    )


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

    result = json.loads(completed.stderr)

    assert result["template_artifact_resolved"] is True
    assert result["article_content_generated"] is False
    assert result["authorization_consumed"] is False
    assert result["wordpress_write_performed"] is False


def test_result_ready_for_k_preflight_only() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_FRESH_ARTICLE_TEMPLATE_RECONCILIATION_"
        "FIXED_NO_CONTENT_NO_AUTH_CONSUMPTION_NO_NETWORK"
    )
    assert result["template_artifact_resolved"] is True
    assert result["authorization_consumed"] is False
    assert result["content_output_exists"] is False
    assert result["article_content_generated"] is False
    assert result["ready_for_recovery_k_preflight"] is True
    assert (
        result[
            "ready_for_one_shot_offline_article_content_generation"
        ]
        is False
    )
    assert result["ready_for_execution"] is False


def test_report_confirms_boundary() -> None:
    report = REPORT.read_text(encoding="utf-8")

    assert "Template resolved: `true`" in report
    assert "Authorization consumed: `false`" in report
    assert "Legacy product data inherited: `false`" in report
    assert "Content output exists: `false`" in report
    assert "Execution allowed: `false`" in report
