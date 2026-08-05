from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "X-MANUAL-POSTING-READINESS-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_FINALIZATION_PACK_DIGEST = (
    "1caec5d697a00e5bae41f38ffec317a3"
    "0ff365e98e5d42697020d4ebf98ecd1c"
)

EXPECTED_APPROVAL_GATE_DIGEST = (
    "7a5bdcc215ddeb23c44010435806bfd0"
    "89658dd84f9508b83245c2b21b6310a9"
)

EXPECTED_REVIEW_DIGEST = (
    "d5112969c7ba2a6fa2f02f8da4e5d270"
    "1f8426d60d0355c2906d84d960f632ba"
)

EXPECTED_REPLACEMENT_PACK_DIGEST = (
    "7eae4a30876f6a411fef085c76ec10b3"
    "29b6d9d864fb534d11dcb90d9ba8cd4a"
)

EXPECTED_PUBLICATION_VERIFICATION_DIGEST = (
    "16e863ba32985294189c2f63314ddf6a"
    "ed7cf9a3ab3ed594568da35d9dba552c"
)

EXPECTED_WORDING_GATE_DIGEST = (
    "b52ca408c72095ea3b958bf28c044804"
    "c1f554ceda5f7b8fa7084539eda6ea8c"
)

FINAL_REVIEW_APPROVAL_REQUEST_ID = (
    "xr11-x-final-review-"
    "d5112969c7ba2a6fa2f02f8d"
)

MANUAL_POSTING_REQUEST_ID = (
    "xr11-x-manual-posting-"
    "1caec5d697a00e5bae41f38f"
)

EXPECTED_DRAFT_ID = (
    "xr11-x-draft-public-url-"
    "4842647be85ea1d60aab47fd"
)

EXPECTED_FINALIZATION_ID = (
    "xr11-x-finalized-local-"
    "4842647be85ea1d60aab47fd"
)

EXPECTED_TEXT_SHA = (
    "4842647be85ea1d60aab47fd159b85ee"
    "ef23c9632809a617fc2f49c21586e7af"
)

EXPECTED_PUBLIC_URL = (
    "https://hoshido.jp/2026/07/18/"
    "noa-senpai-wa-tomodachi-11-6ffa7a8d/"
)

EXPECTED_LITERAL_CHARACTER_COUNT = 160
EXPECTED_TCO_CHARACTER_COUNT = 117
EXPECTED_CHECK_COUNT = 12

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_"
    "MANUAL_X_POSTING_ONLY"
)

APPROVAL_SCOPE = (
    "ONE_MANUAL_X_POST_EXACT_FROZEN_TEXT_ONLY_"
    "PAID_PARTNERSHIP_DISCLOSURE_REQUIRED"
)

EXPECTED_FINAL_TEXT = (
    "【新刊】\n"
    "『のあ先輩はともだち。』"
    "第11巻が7月17日に配信開始📚\n"
    "\n"
    "著者：あきやまえんま\n"
    "出版社：集英社\n"
    "\n"
    "楽天Koboの配信情報・価格はこちら\n"
    "https://hoshido.jp/2026/07/18/"
    "noa-senpai-wa-tomodachi-11-6ffa7a8d/\n"
    "\n"
    "#のあ先輩はともだち "
    "#コミック新刊"
)

X_PAID_PARTNERSHIP_POLICY_URL = (
    "https://help.x.com/en/rules-and-policies/"
    "paid-partnerships-policy"
)

RAKUTEN_STEALTH_MARKETING_POLICY_URL = (
    "https://affiliate.rakuten.co.jp/guideline/"
    "stealth_marketing_regulation/"
)

CAA_STEALTH_MARKETING_QA_URL = (
    "https://www.caa.go.jp/policies/policy/"
    "representation/fair_labeling/faq/"
    "stealth_marketing/"
)


class XManualPostingReadinessError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XManualPostingReadinessError(
            message
        )


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise XManualPostingReadinessError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    expected_digest: str,
    label: str,
) -> None:
    require(
        value.get(digest_field)
        == expected_digest,
        f"{label} recorded digest mismatch",
    )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == expected_digest,
        f"{label} canonical digest mismatch",
    )


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    try:
        descriptor = os.open(
            path,
            (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
            ),
            0o600,
        )
    except FileExistsError as exc:
        raise XManualPostingReadinessError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(
            descriptor,
            data,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_finalized_text(
    value: str,
) -> None:
    require(
        value == EXPECTED_FINAL_TEXT,
        "finalized X draft text mismatch",
    )

    require(
        hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()
        == EXPECTED_TEXT_SHA,
        "finalized X draft text SHA mismatch",
    )

    require(
        len(value)
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "finalized X draft character count mismatch",
    )

    require(
        value.count(
            EXPECTED_PUBLIC_URL
        )
        == 1,
        "finalized X draft public URL count mismatch",
    )

    require(
        "{{WORDPRESS_PUBLIC_URL}}"
        not in value,
        "public URL placeholder remains",
    )


def validate_execution_claim(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_X_DRAFT_FINAL_REVIEW_"
            "LOCAL_FINALIZATION_EXECUTION_CLAIM"
        ),
        "local finalization execution claim type mismatch",
    )

    require(
        value.get("approval_request_id")
        == FINAL_REVIEW_APPROVAL_REQUEST_ID,
        "local finalization request ID mismatch",
    )

    require(
        value.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "execution claim approval gate digest mismatch",
    )

    require(
        value.get(
            "source_review_digest_sha256"
        )
        == EXPECTED_REVIEW_DIGEST,
        "execution claim review digest mismatch",
    )

    require(
        value.get("source_x_draft_id")
        == EXPECTED_DRAFT_ID,
        "execution claim X draft ID mismatch",
    )

    require(
        value.get("source_text_sha256")
        == EXPECTED_TEXT_SHA,
        "execution claim text SHA mismatch",
    )

    require(
        value.get("finalization_id")
        == EXPECTED_FINALIZATION_ID,
        "execution claim finalization ID mismatch",
    )

    require(
        value.get("execution_claimed")
        is True,
        "local finalization was not claimed",
    )

    require(
        value.get("local_only")
        is True,
        "execution claim is not local-only",
    )

    require(
        value.get("x_post_allowed")
        is False,
        "execution claim permits X posting",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "execution claim permits rerun",
    )


def validate_consumption_lock(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R11_X_DRAFT_FINAL_REVIEW_"
            "APPROVAL_CONSUMPTION"
        ),
        "local finalization consumption lock type mismatch",
    )

    require(
        value.get("approval_request_id")
        == FINAL_REVIEW_APPROVAL_REQUEST_ID,
        "consumption request ID mismatch",
    )

    require(
        value.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "consumption approval gate digest mismatch",
    )

    require(
        value.get("approval_consumed")
        is True,
        "final review approval was not consumed",
    )

    require(
        value.get(
            "consumed_for_local_finalization"
        )
        is True,
        "approval was not consumed for local finalization",
    )

    require(
        value.get("x_post_allowed")
        is False,
        "consumption lock permits X posting",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "consumption lock permits rerun",
    )


def validate_finalization_pack(
    value: dict[str, Any],
    *,
    finalized_text_path: Path,
) -> None:
    verify_digest(
        value,
        digest_field=(
            "x_draft_final_review_local_"
            "finalization_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_FINALIZATION_PACK_DIGEST
        ),
        label="local finalization pack",
    )

    require(
        value.get("status")
        == (
            "PASS_X_DRAFT_FINAL_REVIEW_"
            "LOCAL_FINALIZATION_ONE_SHOT"
        ),
        "local finalization status mismatch",
    )

    require(
        value.get("finalization_state")
        == (
            "FINALIZED_LOCAL_X_DRAFT_READY_FOR_"
            "SEPARATE_MANUAL_POSTING_REVIEW"
        ),
        "local finalization state mismatch",
    )

    require(
        value.get("finalization_id")
        == EXPECTED_FINALIZATION_ID,
        "local finalization ID mismatch",
    )

    require(
        value.get(
            "source_approval_gate_digest_sha256"
        )
        == EXPECTED_APPROVAL_GATE_DIGEST,
        "source approval gate digest mismatch",
    )

    require(
        value.get("source_review_digest_sha256")
        == EXPECTED_REVIEW_DIGEST,
        "source review digest mismatch",
    )

    require(
        value.get(
            "source_replacement_pack_digest_sha256"
        )
        == EXPECTED_REPLACEMENT_PACK_DIGEST,
        "source replacement digest mismatch",
    )

    require(
        value.get(
            "source_publication_verification_"
            "digest_sha256"
        )
        == EXPECTED_PUBLICATION_VERIFICATION_DIGEST,
        "source publication digest mismatch",
    )

    require(
        value.get(
            "source_wording_gate_digest_sha256"
        )
        == EXPECTED_WORDING_GATE_DIGEST,
        "source wording digest mismatch",
    )

    draft = value.get(
        "finalized_x_draft"
    )

    require(
        isinstance(draft, dict),
        "finalized X draft evidence is missing",
    )

    require(
        draft.get("draft_id")
        == EXPECTED_DRAFT_ID,
        "finalized X draft ID mismatch",
    )

    require(
        draft.get("finalization_id")
        == EXPECTED_FINALIZATION_ID,
        "finalized draft finalization ID mismatch",
    )

    require(
        draft.get("revision")
        == "FINAL_REVIEW_APPROVED_LOCAL_V1",
        "finalized X draft revision mismatch",
    )

    require(
        draft.get("text")
        == EXPECTED_FINAL_TEXT,
        "finalized X draft content mismatch",
    )

    require(
        draft.get("text_sha256")
        == EXPECTED_TEXT_SHA,
        "finalized X draft SHA mismatch",
    )

    require(
        Path(
            draft["text_path"]
        ).resolve()
        == finalized_text_path,
        "finalized X draft path mismatch",
    )

    require(
        draft.get(
            "literal_character_count"
        )
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "literal character count mismatch",
    )

    require(
        draft.get(
            "estimated_tco_character_count"
        )
        == EXPECTED_TCO_CHARACTER_COUNT,
        "estimated t.co count mismatch",
    )

    require(
        draft.get("public_url")
        == EXPECTED_PUBLIC_URL,
        "finalized public URL mismatch",
    )

    require(
        draft.get("wording_frozen")
        is True,
        "finalized wording is not frozen",
    )

    require(
        draft.get(
            "local_finalization_completed"
        )
        is True,
        "local finalization is incomplete",
    )

    require(
        value.get(
            "x_final_review_approval_consumed"
        )
        is True,
        "final review approval is not consumed",
    )

    require(
        value.get(
            "local_finalization_executed"
        )
        is True,
        "local finalization was not executed",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "local finalization pack permits rerun",
    )

    for field in (
        "x_post_approval_issued",
        "manual_x_posting_allowed",
        "x_post_execution_allowed",
        "normal_x_fb_write",
        "wordpress_api_call",
        "wordpress_write",
        "database_write",
        "workflow_write",
        "x_api_call",
        "x_post",
    ):
        require(
            value.get(field)
            is False,
            (
                "finalization pack records an "
                f"unexpected action: {field}"
            ),
        )

    require(
        value.get("production_status")
        == "NO_GO",
        "finalization production status mismatch",
    )


def build_checklist() -> list[dict[str, Any]]:
    return [
        {
            "check_id": "X_ACCOUNT_IDENTITY",
            "description": (
                "投稿対象のXアカウントを人間が確認する"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "RAKUTEN_RELATIONSHIP_CLASSIFICATION",
            "description": (
                "通常成果報酬のみで、商品提供・イベント・"
                "特別クーポン・個別投稿指示がないことを確認する"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "SPECIAL_CAMPAIGN_STOP_RULE",
            "description": (
                "特別施策に該当する場合は投稿せず、"
                "PR表記入り新Revisionへ戻す"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "FROZEN_TEXT_SHA",
            "description": (
                "貼付本文が固定SHAと完全一致する"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "PUBLIC_URL",
            "description": (
                "公開URLが投稿ID195の記事である"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "WORDPRESS_PUBLIC_STATUS",
            "description": (
                "WordPress記事がpublishかつHTTP 200である"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "X_PAID_PARTNERSHIP_DISCLOSURE",
            "description": (
                "X投稿画面でPaid Partnership開示をONにする"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "DISCLOSURE_VISIBLE_BEFORE_POST",
            "description": (
                "投稿前プレビューでPaid Partnership表示を確認する"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "TEXT_NOT_MODIFIED",
            "description": (
                "改行・URL・絵文字・ハッシュタグを変更しない"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "CHARACTER_COUNT",
            "description": (
                "t.co換算117文字で投稿上限内である"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "NO_AUTOMATION_OR_API",
            "description": (
                "X API・ブラウザ自動化を使用せず人間が操作する"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
        {
            "check_id": "POST_EVIDENCE_CAPTURE",
            "description": (
                "投稿後にURL・post ID・時刻・開示表示証跡を保存する"
            ),
            "human_decision": "PENDING",
            "blocking": True,
        },
    ]


def validate_pending_checklist(
    value: Any,
) -> None:
    require(
        isinstance(value, list),
        "manual posting checklist must be a list",
    )

    require(
        len(value)
        == EXPECTED_CHECK_COUNT,
        (
            "manual posting checklist must contain "
            f"{EXPECTED_CHECK_COUNT} checks"
        ),
    )

    expected_ids = {
        "X_ACCOUNT_IDENTITY",
        "RAKUTEN_RELATIONSHIP_CLASSIFICATION",
        "SPECIAL_CAMPAIGN_STOP_RULE",
        "FROZEN_TEXT_SHA",
        "PUBLIC_URL",
        "WORDPRESS_PUBLIC_STATUS",
        "X_PAID_PARTNERSHIP_DISCLOSURE",
        "DISCLOSURE_VISIBLE_BEFORE_POST",
        "TEXT_NOT_MODIFIED",
        "CHARACTER_COUNT",
        "NO_AUTOMATION_OR_API",
        "POST_EVIDENCE_CAPTURE",
    }

    actual_ids: set[str] = set()

    for item in value:
        require(
            isinstance(item, dict),
            "manual posting checklist item is invalid",
        )

        check_id = item.get(
            "check_id"
        )

        require(
            isinstance(check_id, str)
            and check_id,
            "manual posting check ID is missing",
        )

        require(
            item.get("human_decision")
            == "PENDING",
            (
                "manual posting checks must "
                "remain pending"
            ),
        )

        require(
            item.get("blocking")
            is True,
            "manual posting check must be blocking",
        )

        actual_ids.add(check_id)

    require(
        actual_ids == expected_ids,
        "manual posting checklist IDs mismatch",
    )


def build_evidence_template() -> dict[str, Any]:
    return {
        "schema_version": (
            "X_R11_MANUAL_POSTING_EVIDENCE_V1"
        ),
        "status": "PENDING_MANUAL_X_POST",
        "manual_posting_request_id": (
            MANUAL_POSTING_REQUEST_ID
        ),
        "finalization_id": (
            EXPECTED_FINALIZATION_ID
        ),
        "x_draft_id": EXPECTED_DRAFT_ID,
        "expected_text_sha256": (
            EXPECTED_TEXT_SHA
        ),
        "expected_public_url": (
            EXPECTED_PUBLIC_URL
        ),
        "expected_paid_partnership_disclosure": True,
        "posted_at_utc": None,
        "x_post_url": None,
        "x_post_id": None,
        "x_account_handle": None,
        "posting_surface": None,
        "actual_text_sha256": None,
        "paid_partnership_disclosure_enabled": None,
        "paid_partnership_label_visible": None,
        "screenshot_evidence_path": None,
        "human_verified_exact_text": None,
        "human_verified_public_url": None,
        "human_verified_post_visible": None,
        "normal_x_fb_registration_completed": False,
        "x_api_call": False,
        "credentials_recorded": False,
        "production_status": "NO_GO",
    }


def validate_pending_evidence_template(
    value: dict[str, Any],
) -> None:
    require(
        value.get("status")
        == "PENDING_MANUAL_X_POST",
        "manual evidence template status mismatch",
    )

    require(
        value.get(
            "manual_posting_request_id"
        )
        == MANUAL_POSTING_REQUEST_ID,
        "manual evidence request ID mismatch",
    )

    require(
        value.get(
            "expected_text_sha256"
        )
        == EXPECTED_TEXT_SHA,
        "manual evidence expected SHA mismatch",
    )

    require(
        value.get(
            "expected_paid_partnership_disclosure"
        )
        is True,
        "paid partnership disclosure is not required",
    )

    for field in (
        "posted_at_utc",
        "x_post_url",
        "x_post_id",
        "x_account_handle",
        "posting_surface",
        "actual_text_sha256",
        "paid_partnership_disclosure_enabled",
        "paid_partnership_label_visible",
        "screenshot_evidence_path",
        "human_verified_exact_text",
        "human_verified_public_url",
        "human_verified_post_visible",
    ):
        require(
            value.get(field) is None,
            (
                "manual evidence field must "
                f"remain empty before posting: {field}"
            ),
        )

    require(
        value.get(
            "normal_x_fb_registration_completed"
        )
        is False,
        "normal X-FB registration is already complete",
    )

    require(
        value.get("x_api_call")
        is False,
        "evidence template records X API use",
    )

    require(
        value.get("credentials_recorded")
        is False,
        "evidence template records credentials",
    )


def build_readiness_prep(
    *,
    production_database_path: Path,
    finalization_pack_path: Path,
    finalized_text_path: Path,
    execution_claim_path: Path,
    consumption_lock_path: Path,
    evidence_template_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    finalization_pack_path = (
        finalization_pack_path.resolve()
    )

    finalized_text_path = (
        finalized_text_path.resolve()
    )

    execution_claim_path = (
        execution_claim_path.resolve()
    )

    consumption_lock_path = (
        consumption_lock_path.resolve()
    )

    evidence_template_path = (
        evidence_template_path.resolve()
    )

    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    require(
        finalized_text_path.is_file(),
        "finalized X draft text is missing",
    )

    require(
        sha256_file(
            finalized_text_path
        )
        == EXPECTED_TEXT_SHA,
        "finalized X draft file SHA mismatch",
    )

    finalized_text = (
        finalized_text_path.read_text(
            encoding="utf-8"
        )
    )

    validate_finalized_text(
        finalized_text
    )

    finalization_pack = load_json(
        finalization_pack_path
    )

    validate_finalization_pack(
        finalization_pack,
        finalized_text_path=(
            finalized_text_path
        ),
    )

    execution_claim = load_json(
        execution_claim_path
    )

    validate_execution_claim(
        execution_claim
    )

    consumption_lock = load_json(
        consumption_lock_path
    )

    validate_consumption_lock(
        consumption_lock
    )

    require(
        not evidence_template_path.exists(),
        "manual evidence template already exists",
    )

    require(
        not output_path.exists(),
        "manual posting readiness pack already exists",
    )

    checklist = build_checklist()

    validate_pending_checklist(
        checklist
    )

    evidence_template = (
        build_evidence_template()
    )

    validate_pending_evidence_template(
        evidence_template
    )

    prepared_at = datetime.now(
        timezone.utc
    ).isoformat()

    atomic_create_json(
        evidence_template_path,
        evidence_template,
    )

    readiness_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_MANUAL_POSTING_"
            "READINESS_PREP_READY"
        ),
        "readiness_state": (
            "AWAITING_EXPLICIT_HUMAN_"
            "MANUAL_X_POSTING_DECISION"
        ),
        "prepared_at": prepared_at,
        "manual_posting_request_id": (
            MANUAL_POSTING_REQUEST_ID
        ),
        "source_finalization_pack_path": str(
            finalization_pack_path
        ),
        "source_finalization_pack_digest_sha256": (
            EXPECTED_FINALIZATION_PACK_DIGEST
        ),
        "source_execution_claim_path": str(
            execution_claim_path
        ),
        "source_consumption_lock_path": str(
            consumption_lock_path
        ),
        "finalized_x_draft": {
            "draft_id": EXPECTED_DRAFT_ID,
            "finalization_id": (
                EXPECTED_FINALIZATION_ID
            ),
            "revision": (
                "FINAL_REVIEW_APPROVED_LOCAL_V1"
            ),
            "text": finalized_text,
            "text_path": str(
                finalized_text_path
            ),
            "text_sha256": (
                EXPECTED_TEXT_SHA
            ),
            "literal_character_count": (
                EXPECTED_LITERAL_CHARACTER_COUNT
            ),
            "estimated_tco_character_count": (
                EXPECTED_TCO_CHARACTER_COUNT
            ),
            "public_url": EXPECTED_PUBLIC_URL,
            "wording_frozen": True,
        },
        "compliance_policy_snapshot": {
            "snapshot_date": "2026-07-18",
            "x_paid_partnership_policy_url": (
                X_PAID_PARTNERSHIP_POLICY_URL
            ),
            "rakuten_policy_url": (
                RAKUTEN_STEALTH_MARKETING_POLICY_URL
            ),
            "caa_qa_url": (
                CAA_STEALTH_MARKETING_QA_URL
            ),
            "affiliate_commission_route": True,
            "x_paid_partnership_policy_applicable": True,
            "x_paid_partnership_disclosure_required": True,
            "required_x_ui_setting": (
                "PAID_PARTNERSHIP_DISCLOSURE_ON"
            ),
            "required_pre_post_visible_state": (
                "PAID_PARTNERSHIP_LABEL_VISIBLE"
            ),
            "rakuten_basic_function_only_confirmation_required": True,
            "rakuten_special_campaign_stop_rule": True,
            "policy_recheck_required_before_posting": True,
        },
        "manual_posting_constraints": {
            "human_operation_only": True,
            "x_web_or_official_app_only": True,
            "exact_frozen_text_required": True,
            "text_edit_allowed": False,
            "url_edit_allowed": False,
            "hashtag_edit_allowed": False,
            "media_attachment_allowed": False,
            "x_paid_partnership_disclosure_required": True,
            "post_button_allowed_before_approval": False,
            "x_api_allowed": False,
            "browser_automation_allowed": False,
            "maximum_manual_post_count": 1,
            "stop_if_disclosure_unavailable": True,
            "stop_if_special_rakuten_campaign": True,
        },
        "manual_posting_checklist": (
            checklist
        ),
        "post_execution_evidence_template_path": str(
            evidence_template_path
        ),
        "approval_label_if_approved": (
            APPROVAL_LABEL
        ),
        "approval_scope_if_approved": (
            APPROVAL_SCOPE
        ),
        "human_decision": "PENDING",
        "manual_posting_review_required": True,
        "manual_posting_review_completed": False,
        "manual_posting_approval_issued": False,
        "manual_posting_approval_consumed": False,
        "manual_x_posting_allowed": False,
        "x_paid_partnership_disclosure_verified": False,
        "x_post_execution_allowed": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "browser_automation": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "MANUAL_X_POSTING_REVIEW_PENDING_"
            "PAID_PARTNERSHIP_DISCLOSURE_REQUIRED_"
            "ALL_X_EXECUTION_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-MANUAL-POSTING-"
            "EXPLICIT-APPROVAL-GATE"
        ),
    }

    readiness = {
        **readiness_payload,
        "x_manual_posting_readiness_"
        "prep_digest_sha256": (
            canonical_digest(
                readiness_payload
            )
        ),
    }

    atomic_create_json(
        output_path,
        readiness,
    )

    return readiness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--finalization-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--finalized-text",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--execution-claim",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--consumption-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--evidence-template",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = build_readiness_prep(
            production_database_path=(
                args.production_db
            ),
            finalization_pack_path=(
                args.finalization_pack
            ),
            finalized_text_path=(
                args.finalized_text
            ),
            execution_claim_path=(
                args.execution_claim
            ),
            consumption_lock_path=(
                args.consumption_lock
            ),
            evidence_template_path=(
                args.evidence_template
            ),
            output_path=args.output,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_MANUAL_POSTING_"
                        "READINESS_PREP"
                    ),
                    "error": str(exc),
                    "manual_posting_approval_issued": False,
                    "manual_x_posting_allowed": False,
                    "x_post_execution_allowed": False,
                    "x_api_call": False,
                    "x_post": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "readiness_state": (
                    result["readiness_state"]
                ),
                "manual_posting_request_id": (
                    result[
                        "manual_posting_request_id"
                    ]
                ),
                "x_draft_id": (
                    result[
                        "finalized_x_draft"
                    ]["draft_id"]
                ),
                "x_draft_text_sha256": (
                    result[
                        "finalized_x_draft"
                    ]["text_sha256"]
                ),
                "human_check_count": (
                    EXPECTED_CHECK_COUNT
                ),
                "human_decision": "PENDING",
                "x_paid_partnership_disclosure_required": True,
                "x_paid_partnership_disclosure_verified": False,
                "manual_posting_approval_issued": False,
                "manual_x_posting_allowed": False,
                "x_post_execution_allowed": False,
                "x_api_call": False,
                "x_post": False,
                "production_status": "NO_GO",
                "evidence_template_path": str(
                    args.evidence_template.resolve()
                ),
                "readiness_pack_path": str(
                    args.output.resolve()
                ),
                "readiness_digest_sha256": (
                    result[
                        "x_manual_posting_readiness_"
                        "prep_digest_sha256"
                    ]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
