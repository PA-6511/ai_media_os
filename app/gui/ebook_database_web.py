from __future__ import annotations

import html
import json
import logging
import os
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlencode
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.db.models import WorkflowApprovalRequest
from app.db.read_only_session import ReadOnlySessionLocal
from app.services.ebook_dashboard_service import EbookDashboardService
from app.gui.ebook_database_view_model import (
    EbookDatabaseQuery,
    EbookDatabaseViewModel,
)


DATABASE_SEARCH_PER_PAGE = 200
LOGGER = logging.getLogger(__name__)
DATABASE_SEARCH_FILTER_PARAMETERS = {
    "keyword",
    "release_date_from",
    "release_date_to",
    "item_type",
    "store_name",
    "workflow_status",
    "review_status",
    "wordpress_status",
    "include_excluded",
    "excluded_only",
    "missing_price",
    "missing_affiliate",
    "affiliate_status",
    "amazon_affiliate_status",
    "rakuten_kobo_affiliate_status",
    "dmm_affiliate_status",
    "summary_date",
}


@dataclass(frozen=True)
class DatabaseSearchPageState:
    keyword: str = ""
    release_date_from: str = ""
    release_date_to: str = ""
    item_type: str = ""
    store_name: str = ""
    workflow_status: str = ""
    review_status: str = ""
    wordpress_status: str = ""
    include_excluded: bool = False
    excluded_only: bool = False
    missing_price: bool = False
    missing_affiliate: bool = False
    affiliate_status: str = "all"
    amazon_affiliate_status: str = "all"
    rakuten_kobo_affiliate_status: str = "all"
    dmm_affiliate_status: str = "all"
    summary_date: str = ""
    page: int = 1


@dataclass(frozen=True)
class WordPressCategoryPageContext:
    categories: list[Any]
    item_states: dict[str, dict[str, Any]]
    error: str = ""


@dataclass(frozen=True)
class DatabaseSearchPageContext:
    raw_query: str
    params: dict[str, list[str]]
    state: DatabaseSearchPageState
    rows: list[dict[str, Any]]
    total_count: int
    total_pages: int
    current_page: int
    display_start: int
    display_end: int
    numeric_page_controls: str
    error: str
    dashboard: dict[str, Any]
    setting_views: dict[str, Any]
    dmm_destination_profiles: dict[str, Any]
    pending_approvals: dict[str, dict[str, Any]]
    approved_approvals: dict[str, dict[str, Any]]
    wordpress_execution_states: dict[str, dict[str, Any]]
    wordpress_schedule_states: dict[str, dict[str, Any]]
    supplement_cancellation_previews: dict[str, Any]
    wordpress_categories: list[Any]
    wordpress_context_error: str
    csrf_token: str
    notices: dict[str, str]
    daily_summary_snapshot: Any
    daily_summary_selections: dict[str, str]
    daily_summary_error_code: str


@dataclass(frozen=True)
class AffiliateSettingDisplay:
    service_name: str
    masked_affiliate_id: str
    configured: bool
    enabled: bool
    updated_at: str
    source: str
    url_template_configured: bool


@dataclass(frozen=True)
class DmmDestinationProfileDisplay:
    provider: str
    destination_type: str
    destination_key: str
    display_name: str
    masked_affiliate_id: str
    configured: bool
    active: bool
    channel: str
    channel_id: str


def _escape(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _mask_affiliate_id(value: str | None) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return "未登録"
    if len(normalized) <= 4:
        return "*" * len(normalized)
    if len(normalized) <= 8:
        return normalized[:2] + "*" * (len(normalized) - 4) + normalized[-2:]
    return normalized[:3] + "*" * (len(normalized) - 6) + normalized[-3:]


from app.services.workflow_action_service import get_workflow_action_token

STATUS_LABELS = {
    "NEW": "新規",
    "REVIEW": "レビュー中",
    "READY": "準備完了",
    "SCHEDULED": "予約済",
    "PUBLISHED": "公開済",
    "HOLD": "保留",
    "ERROR": "エラー",
    "NOT_CREATED": "未作成",
    "DRAFT": "下書き",
    "POSTED": "投稿済",
    "UNCHECKED": "未確認",
    "MISSING": "未取得",
    "IN_REVIEW": "確認中",
    "APPROVED": "承認済",
    "REJECTED": "差戻し",
}


def render_status_badge(value: Any) -> str:
    raw = str(value or "")
    label = STATUS_LABELS.get(raw, raw or "-")
    css_name = raw.lower().replace("_", "-") or "unknown"

    return (
        f'<span class="status-badge status-{_escape(css_name)}">'
        f'{_escape(label)}</span>'
    )


def render_ready_badge(value: bool) -> str:
    if value:
        return (
            '<span class="status-badge status-ready">'
            '公開可能</span>'
        )

    return (
        '<span class="status-badge status-not-ready">'
        '未準備</span>'
    )


AFFILIATE_BADGE_SERVICES = (
    ("amazon", "K", "Amazon", "amazon_affiliate_ready"),
    ("rakuten-kobo", "R", "楽天Kobo", "rakuten_kobo_affiliate_ready"),
    ("dmm", "D", "DMM", "dmm_affiliate_ready"),
)


def render_affiliate_readiness(row: dict[str, Any]) -> str:
    badges: list[str] = []
    status_labels: list[str] = []
    ready_count = 0

    for css_name, short_label, service_label, field_name in (
        AFFILIATE_BADGE_SERVICES
    ):
        is_ready = bool(row.get(field_name, False))
        ready_count += int(is_ready)
        state = str(
            row.get(
                field_name.replace("_ready", "_registration_state"),
                "registered" if is_ready else "unregistered",
            )
        )
        state_label = (
            "登録済み"
            if is_ready
            else "未登録（URL不正）"
            if state == "invalid"
            else "未登録"
        )
        status_labels.append(f"{service_label} {state_label}")
        badges.append(
            '<span class="affiliate-service-status">'
            '<span class="affiliate-service-badge '
            f'affiliate-service-{_escape(css_name)} '
            f'{"is-ready" if is_ready else "is-missing"}" '
            f'title="{_escape(service_label)}: {_escape(state_label)}" '
            f'aria-label="{_escape(service_label)}: {_escape(state_label)}">'
            f'{_escape(short_label)}</span>'
            f'<span>{_escape(service_label)}: {_escape(state_label)}</span>'
            '</span>'
        )

    count_label = f"{ready_count}/{len(AFFILIATE_BADGE_SERVICES)}"
    overall_label = "アフィリエイト登録状況: " + ", ".join(status_labels)
    return (
        '<span class="affiliate-readiness" '
        f'title="{_escape(overall_label)}" '
        f'aria-label="{_escape(overall_label)}; {count_label}">'
        f'{"".join(badges)}'
        f'<span class="affiliate-ready-count" aria-hidden="true">'
        f'{_escape(count_label)}</span></span>'
    )


BULK_CAPABILITY_LABELS = {
    "READY_TO_REGISTER": "可",
    "NEEDS_INPUT": "確認必要",
    "ALREADY_REGISTERED": "登録済み",
    "INVALID": "不可",
    "READY": "可",
    "NOT_APPROVED": "未承認",
    "ALREADY_CREATED": "作成済み",
    "MISSING_REQUIRED_DATA": "情報不足",
    "INVALID_STATE": "不可",
    "NOT_DRAFT": "下書きなし",
    "MISSING_POST_ID": "投稿IDなし",
}


def render_bulk_capabilities(row: dict[str, Any]) -> str:
    capabilities = (
        ("登録", row.get("affiliate_registration_capability")),
        ("下書き", row.get("wordpress_draft_capability")),
        ("予約", row.get("wordpress_schedule_capability")),
    )
    return '<span class="bulk-capabilities">' + "".join(
        '<span>'
        f'{_escape(label)}: '
        f'{_escape(BULK_CAPABILITY_LABELS.get(str(value), "不可"))}'
        '</span>'
        for label, value in capabilities
    ) + "</span>"


def render_bulk_selection_checkbox(row: dict[str, Any]) -> str:
    item_id = str(row.get("id") or "").strip()
    disabled_reason = ""
    if not item_id:
        disabled_reason = "作品IDがないため選択できません"
    elif bool(row.get("is_excluded", False)):
        disabled_reason = "除外済みのため選択できません"
    disabled = "disabled" if disabled_reason else ""
    title = disabled_reason or "一括処理対象に選択"
    return (
        '<input type="checkbox" '
        'name="selected_ebook_item_ids" '
        'class="bulk-operation-item-checkbox" '
        f'value="{_escape(item_id)}" {disabled} '
        f'title="{_escape(title)}" aria-label="{_escape(title)}">'
    )



WORKFLOW_ACTIONS = {
    "NEW": ("REVIEW", "レビュー開始"),
    "SCHEDULED": ("PUBLISHED", "公開済"),
}

WORKFLOW_NOTICES = {
    "success": (
        "success",
        "状態を更新し、変更履歴を保存しました。",
    ),
    "invalid_token": (
        "error",
        "確認トークンが一致しないため更新を拒否しました。",
    ),
    "invalid_target": (
        "error",
        "GUIから許可されていない状態です。",
    ),
    "item_not_found": (
        "error",
        "対象データが見つかりません。",
    ),
    "invalid_transition": (
        "error",
        "現在の状態からその状態へは変更できません。",
    ),
    "invalid_request": (
        "error",
        "更新リクエストが不正です。",
    ),
    "internal_error": (
        "error",
        "状態更新中にエラーが発生しました。",
    ),
    "REVIEW_READY_REQUIRES_APPROVAL": (
        "error",
        "REVIEW_READY_REQUIRES_APPROVAL: 承認申請と明示承認が必要です。",
    ),
}

REVIEW_READY_NOTICES = {
    "request_created": (
        "success",
        "承認申請を作成しました。人間による判断を待っています。",
    ),
    "request_reissued": (
      "success",
      "承認申請を再発行しました。新しい申請で判断できます。",
    ),
    "approved": (
        "success",
        "承認しました。WorkflowをREADYへ更新しました。",
    ),
    "rejected": (
        "error",
        "否認しました。WorkflowはREVIEWのままです。",
    ),
    "invalid_token": (
        "error",
        "確認トークンが一致しないため操作を拒否しました。",
    ),
    "approval_token_unavailable": (
        "error",
        "承認tokenを復元できません。管理確認が必要です。",
    ),
    "duplicate_pending": (
        "error",
        "有効な承認待ち申請がすでに存在します。",
    ),
    "excluded_item": (
        "error",
        "除外済み項目は承認申請・承認できません。",
    ),
    "expired": (
        "error",
        "承認申請の期限が切れています。",
    ),
    "request_expired": (
        "error",
        "承認申請の期限が切れています。",
    ),
    "request_item_mismatch": (
        "error",
        "承認申請と対象作品が一致しません。",
    ),
    "request_not_found": (
        "error",
        "承認申請が見つかりません。",
    ),
    "invalid_approval_type": (
        "error",
        "承認申請の種別が不正です。",
    ),
    "already_decided": (
        "error",
        "この承認申請はすでに判断済みです。",
    ),
    "reissue_not_allowed": (
      "error",
      "現在の承認申請は有効なため再発行できません。",
    ),
    "invalid_decision": (
        "error",
        "承認判断が不正です。",
    ),
    "invalid_note": (
        "error",
        "承認コメントが長すぎます。",
    ),
    "item_not_found": (
        "error",
        "対象データが見つかりません。",
    ),
    "invalid_current_status": (
        "error",
        "現在のWorkflow状態では承認申請できません。",
    ),
    "invalid_review_status": (
        "error",
        "現在のReview状態では承認申請できません。",
    ),
    "approval_state_mismatch": (
        "error",
        "承認状態が整合しません。管理確認が必要です。",
    ),
    "stale_state": (
        "error",
        "申請後に状態が変化したため承認を拒否しました。",
    ),
    "transition_failed": (
        "error",
        "正式な状態遷移に失敗しました。",
    ),
    "invalid_request": (
        "error",
        "承認リクエストが不正です。",
    ),
    "internal_error": (
        "error",
        "承認処理中にエラーが発生しました。",
    ),
}

AMAZON_OFFER_NOTICES = {
    "success": (
        "success",
        "Amazonアフィリエイトリンクを保存しました。",
    ),
    "invalid_token": (
        "error",
        "確認トークンが一致しないため保存を拒否しました。",
    ),
    "invalid_input": (
        "error",
        "ASINまたはトラッキングIDの形式が不正です。",
    ),
    "tracking_id_not_configured": (
        "error",
        "AmazonトラッキングIDが未設定です。アフィリエイト設定から登録してください。",
    ),
    "unchanged": (
        "success",
        "Amazonリンクは保存済みの内容と同じため変更しませんでした。",
    ),
    "item_not_found": (
        "error",
        "対象の電子書籍データが見つかりません。",
    ),
    "invalid_request": (
        "error",
        "Amazonリンク登録リクエストが不正です。",
    ),
    "internal_error": (
        "error",
        "Amazonリンクの保存中にエラーが発生しました。",
    ),
}

CATALOG_EDIT_NOTICES = {
    "success": ("success", "基本情報を保存しました。"),
    "series_rule_skipped": (
        "success",
        "基本情報を保存しました。作者または出版社が不足しているため、同シリーズルールは保存されませんでした。",
    ),
    "unchanged": ("success", "基本情報に変更はありませんでした。"),
    "item_not_found": ("error", "対象データが見つかりません。"),
    "invalid_input": ("error", "基本情報の入力内容が不正です。"),
    "internal_error": ("error", "基本情報の保存中にエラーが発生しました。"),
}

MANUAL_STORE_OFFER_NOTICES = {
  "MANUAL_STORE_OFFER_CREATED": (
    "success",
    "楽天Koboリンクを登録しました。",
  ),
  "STORE_OFFER_ALREADY_EXISTS": (
    "error",
    "楽天Koboリンクは登録済みです。既存編集を使用してください。",
  ),
  "INVALID_CSRF": ("error", "CSRF検証に失敗しました。"),
  "CONFIRMATION_REQUIRED": ("error", "URLの人間確認が必要です。"),
  "INVALID_INPUT": ("error", "ストアリンクの入力内容が不正です。"),
  "INTERNAL_ERROR": ("error", "ストアリンクの登録に失敗しました。"),
}

METADATA_AUTOFILL_NOTICES = {
    "applied": ("success", "書誌情報の安全な補完を確定しました。"),
    "partially_applied": (
        "success",
        "補完可能な書誌情報だけを確定しました。未解決項目は人間確認が必要です。",
    ),
    "unchanged": ("success", "補完対象の書誌情報はありませんでした。"),
    "item_not_found": ("error", "対象データが見つかりません。"),
    "preview_changed": (
        "error",
        "プレビュー後にデータが変わったため補完を中止しました。再度プレビューしてください。",
    ),
    "invalid_input": ("error", "書誌情報の補完リクエストが不正です。"),
    "evidence_error": (
        "error",
        "DB更新後の証跡保存に失敗しました。管理確認が必要です。",
    ),
    "internal_error": ("error", "書誌情報の補完中にエラーが発生しました。"),
}

DMM_OFFER_NOTICES = {
    "success": ("success", "DMMリンクを保存し、レビュー状態を安全側へ戻しました。"),
    "unchanged": ("success", "DMMリンクは保存済みの内容と同じため変更しませんでした。"),
    "item_not_found": ("error", "対象データが見つかりません。"),
    "not_configured": ("error", "DMM IDまたはURLテンプレートが未設定です。"),
    "invalid_input": ("error", "DMMリンクの入力内容が不正です。"),
    "invalid_token": ("error", "確認トークンが一致しないため保存を拒否しました。"),
    "internal_error": ("error", "DMMリンクの保存中にエラーが発生しました。"),
}

AFFILIATE_SETTING_NOTICES = {
    "success": ("success", "アフィリエイト設定を保存しました。"),
    "deleted": ("success", "指定した設定を明示的に削除しました。"),
    "invalid_input": ("error", "設定値の形式が不正です。"),
    "invalid_token": ("error", "確認トークンが一致しないため保存を拒否しました。"),
    "internal_error": ("error", "設定の保存中にエラーが発生しました。"),
}


WORDPRESS_DRAFT_NOTICES = {
  "DRAFT_CREATED": ("success", "WordPress下書きを作成しました。"),
  "DRAFT_CREATED_IMAGE_REVIEW_REQUIRED": (
    "error",
    "WordPress下書きは作成しましたが、書影確認が必要です。",
  ),
  "WORDPRESS_DRAFT_CREATED_DB_RECONCILIATION_REQUIRED": (
    "error",
    "WordPress下書きは作成済みの可能性があります。管理確認が必要です。",
  ),
}

WORDPRESS_SCHEDULE_NOTICES = {
  "scheduled": ("success", "WordPressカテゴリーと予約投稿を設定しました。"),
  "rescheduled": ("success", "WordPressカテゴリーと予約日時を変更しました。"),
  "category_updated": ("success", "WordPress投稿カテゴリーを更新しました。"),
  "cancelled": ("success", "WordPress予約を解除し、下書きへ戻しました。"),
  "invalid_token": ("error", "確認トークンが一致しないため操作を拒否しました。"),
  "invalid_request": ("error", "予約投稿リクエストが不正です。"),
  "invalid_publish_at": ("error", "公開予約日時の形式が不正です。"),
  "publish_at_too_soon": ("error", "公開予約日時は現在から60秒より後を指定してください。"),
  "not_approved": ("error", "承認済みの記事だけ予約できます。"),
  "invalid_state": ("error", "現在の状態では予約操作できません。"),
  "post_item_mismatch": ("error", "記事とWordPress投稿IDが一致しません。"),
  "remote_state_mismatch": ("error", "WordPress上の投稿状態が一致しません。"),
  "response_mismatch": ("error", "WordPressの応答を確認できなかったため成功扱いしませんでした。"),
  "invalid_category": ("error", "投稿カテゴリーの指定が不正です。"),
  "category_not_found": ("error", "指定カテゴリーはWordPressに存在しません。"),
  "category_not_allowed": ("error", "指定カテゴリーはGUIから選択できません。"),
  "category_update_failed": ("error", "WordPress投稿カテゴリーの更新に失敗しました。"),
  "execution_claim_exists": ("error", "予約処理はすでに実行中です。"),
  "draft_execution_in_progress": ("error", "WordPress下書き処理中のため予約できません。"),
  "schedule_failed": ("error", "WordPress予約処理に失敗しました。"),
  "internal_error": ("error", "WordPress予約処理中にエラーが発生しました。"),
}


def render_workflow_action_form(
    row: dict[str, Any],
    query_string: str = "",
    pending_approval: dict[str, Any] | None = None,
) -> str:
    item_id = str(row.get("id") or "")
    current_status = str(
        row.get("workflow_status") or ""
    ).upper()
    review_status = str(
        row.get("review_status") or ""
    ).upper()
    is_excluded = bool(row.get("is_excluded"))

    if not item_id:
        return (
            '<span class="workflow-action-unavailable">'
            'IDなし</span>'
        )

    if is_excluded:
        return (
            '<span class="workflow-action-unavailable">'
            '除外済み：操作不可</span>'
        )

    clean_query = str(query_string or "").lstrip("?")
    return_to = "/database-search"

    if clean_query:
        return_to = f"{return_to}?{clean_query}"

    token = get_workflow_action_token()

    if current_status == "REVIEW":
        if review_status in {"IN_REVIEW", "REJECTED"} and not pending_approval:
            return f"""
<form
  method="post"
  action="/database-review-ready-request"
  class="workflow-action-form"
  onsubmit="return confirm('REVIEW から READY への承認申請を作成します。よろしいですか？');"
>
  <input type="hidden" name="csrf_token" value="{_escape(token)}">
  <input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">
  <input type="hidden" name="return_to" value="{_escape(return_to)}">
  <button type="submit" class="workflow-action-button">承認申請</button>
</form>
""".strip()

        if review_status == "IN_REVIEW" and pending_approval:
            request_id = str(pending_approval.get("id") or "")
            approval_type = str(
                pending_approval.get("approval_type") or ""
            )
            expires_at = str(
                pending_approval.get("expires_at") or ""
            )
            token_available = bool(
              pending_approval.get("token_available")
            )
            is_expired = bool(pending_approval.get("is_expired"))

            if not request_id or approval_type != "REVIEW_READY":
                return (
                    '<span class="workflow-action-unavailable">'
                    '状態不整合：管理確認が必要</span>'
                )

            request_short = request_id[:8]

            if is_expired or not token_available:
                reason = (
                    "期限切れ"
                    if is_expired
                    else "承認tokenを復元できません"
                )
                return f"""
<div class="review-ready-approval">
  <div class="workflow-action-pending">承認待ち（{_escape(reason)}）</div>
  <div class="workflow-action-detail">request={_escape(request_short)}…</div>
  <div class="workflow-action-detail">expires={_escape(expires_at)}</div>
  <form
    method="post"
    action="/database-review-ready-reissue"
    class="workflow-action-form"
    onsubmit="return confirm('現在の承認申請を終了し、新しい承認申請を発行します。よろしいですか？');"
  >
    <input type="hidden" name="csrf_token" value="{_escape(token)}">
    <input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">
    <input type="hidden" name="approval_request_id" value="{_escape(request_id)}">
    <input type="hidden" name="return_to" value="{_escape(return_to)}">
    <button type="submit" class="workflow-action-button">承認申請を再発行</button>
  </form>
</div>
""".strip()

            return f"""
<div class="review-ready-approval">
  <div class="workflow-action-pending">承認待ち</div>
  <div class="workflow-action-detail">request={_escape(request_short)}…</div>
  <div class="workflow-action-detail">type={_escape(approval_type)}</div>
  <div class="workflow-action-detail">expires={_escape(expires_at)}</div>
  <form
    method="post"
    action="/database-review-ready-decision"
    class="workflow-action-form"
    onsubmit="return confirm('この作品を承認し、REVIEW から READY へ進めます。よろしいですか？');"
  >
    <input type="hidden" name="csrf_token" value="{_escape(token)}">
    <input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">
    <input type="hidden" name="approval_request_id" value="{_escape(request_id)}">
    <input type="hidden" name="decision" value="APPROVE">
    <input type="hidden" name="return_to" value="{_escape(return_to)}">
    <input type="text" name="note" maxlength="1000" placeholder="コメント（任意）">
    <button type="submit" class="workflow-action-button">承認</button>
  </form>
  <form
    method="post"
    action="/database-review-ready-decision"
    class="workflow-action-form"
    onsubmit="return confirm('この承認申請を否認します。よろしいですか？');"
  >
    <input type="hidden" name="csrf_token" value="{_escape(token)}">
    <input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">
    <input type="hidden" name="approval_request_id" value="{_escape(request_id)}">
    <input type="hidden" name="decision" value="REJECT">
    <input type="hidden" name="return_to" value="{_escape(return_to)}">
    <input type="text" name="note" maxlength="1000" placeholder="コメント（任意）">
    <button type="submit" class="workflow-action-button is-reject">否認</button>
  </form>
</div>
""".strip()

        return (
            '<span class="workflow-action-unavailable">'
            '状態不整合：管理確認が必要</span>'
        )

    if current_status == "READY":
        if review_status == "APPROVED":
            return (
                '<span class="workflow-action-done">'
                '準備完了 / 承認済み</span>'
            )

        return (
            '<span class="workflow-action-unavailable">'
            '状態不整合：管理確認が必要</span>'
        )

    action = WORKFLOW_ACTIONS.get(current_status)

    if action is None:
        if current_status == "PUBLISHED":
            return (
                '<span class="workflow-action-done">'
                '完了</span>'
            )

        return (
            '<span class="workflow-action-unavailable">'
            '操作なし</span>'
        )

    new_status, button_label = action

    confirm_message = (
        f"{current_status} から {new_status} "
        "へ状態を変更します。よろしいですか？"
    )

    return f"""
<form
  method="post"
  action="/database-workflow"
  class="workflow-action-form"
  onsubmit="return confirm('{_escape(confirm_message)}');"
>
  <input
    type="hidden"
    name="csrf_token"
    value="{_escape(token)}"
  >
  <input
    type="hidden"
    name="item_id"
    value="{_escape(item_id)}"
  >
  <input
    type="hidden"
    name="new_status"
    value="{_escape(new_status)}"
  >
  <input
    type="hidden"
    name="return_to"
    value="{_escape(return_to)}"
  >
  <button
    type="submit"
    class="workflow-action-button"
  >{_escape(button_label)}</button>
</form>
""".strip()


def render_workflow_notice(
    params: dict[str, list[str]],
) -> str:
    code = _first(params, "workflow_update")
    notice = WORKFLOW_NOTICES.get(code)

    if notice is None:
        return ""

    css_name, message = notice

    return (
        f'<div class="workflow-notice '
        f'workflow-notice-{_escape(css_name)}">'
        f'{_escape(message)}</div>'
    )


def render_review_ready_notice(
    params: dict[str, list[str]],
) -> str:
    code = _first(params, "review_ready_result")
    notice = REVIEW_READY_NOTICES.get(code)

    if notice is None:
        return ""

    css_name, message = notice

    return (
        f'<div class="workflow-notice '
        f'workflow-notice-{_escape(css_name)}">'
        f'{_escape(message)}</div>'
    )


def render_amazon_offer_notice(
    params: dict[str, list[str]],
) -> str:
    code = _first(params, "amazon_offer_result")
    notice = AMAZON_OFFER_NOTICES.get(code)

    if notice is None:
        return ""

    css_name, message = notice
    asin = _first(params, "amazon_offer_asin")

    detail_html = ""
    if code == "success" and asin:
        detail_html = (
            '<div class="workflow-notice-detail">'
            f'ASIN={_escape(asin)}'
            '</div>'
        )

    return (
        f'<div class="workflow-notice '
        f'workflow-notice-{_escape(css_name)}">'
        f'{_escape(message)}'
        f'{detail_html}'
        '</div>'
    )


def render_named_notice(
    params: dict[str, list[str]],
    parameter: str,
    notices: dict[str, tuple[str, str]],
) -> str:
    notice = notices.get(_first(params, parameter))
    if notice is None:
        return ""
    css_name, message = notice
    return (
        f'<div class="workflow-notice workflow-notice-{_escape(css_name)}">'
        f'{_escape(message)}</div>'
    )


def render_wordpress_draft_notice(
    params: dict[str, list[str]],
) -> str:
    code = _first(params, "wordpress_draft_result")
    notice = WORDPRESS_DRAFT_NOTICES.get(code)

    if notice is None:
        return ""

    css_name, message = notice
    post_id = _first(params, "wordpress_post_id")
    image_status = _first(params, "image_status")
    featured_media_set = _first(params, "featured_media_set")
    image_error_summary = _first(params, "image_error_summary")
    price_status = _first(params, "price_status")
    missing_price_stores = _first(params, "missing_price_stores")
    price_review_reasons = _first(params, "price_review_reasons")
    detail_parts = []

    if post_id:
        detail_parts.append(f"post_id={post_id}")
    if image_status:
        detail_parts.append(f"image_status={image_status}")
    if featured_media_set:
      detail_parts.append(
        f"featured_media_set={featured_media_set}"
      )
    if image_error_summary:
        detail_parts.append(f"image_error={image_error_summary}")
    if price_status:
        detail_parts.append(f"price_status={price_status}")
    if missing_price_stores:
        detail_parts.append(
            f"missing_price_stores={missing_price_stores}"
        )
    if price_review_reasons:
        detail_parts.append(
            f"price_review_reasons={price_review_reasons}"
        )

    detail_html = ""
    if detail_parts:
        detail_html = (
            '<div class="workflow-notice-detail">'
            f'{_escape(" / ".join(detail_parts))}'
            '</div>'
        )

    return (
        f'<div class="workflow-notice '
        f'workflow-notice-{_escape(css_name)}">'
        f'{_escape(message)}'
        f'{detail_html}'
        '</div>'
    )


def render_wordpress_draft_action_form(
    row: dict[str, Any],
    query_string: str = "",
    approved_request: dict[str, Any] | None = None,
    execution_state: dict[str, Any] | None = None,
) -> str:
    item_id = str(row.get("id") or "")
    title = str(row.get("title") or "").strip()
    volume_label = str(row.get("volume_label") or "").strip()
    workflow_status = str(
        row.get("workflow_status") or ""
    ).upper()
    review_status = str(
        row.get("review_status") or ""
    ).upper()
    wordpress_status = str(
        row.get("wordpress_status") or ""
    ).upper()
    wordpress_post_id = str(
        row.get("wordpress_post_id") or ""
    ).strip()
    publish_ready = bool(row.get("publish_ready"))
    is_excluded = bool(row.get("is_excluded"))

    if not item_id:
      return (
        '<button type="button" disabled '
        'class="workflow-action-button is-disabled">IDなし</button>'
      )

    execution_status = str(
      (execution_state or {}).get("status") or ""
    )
    evidence_post_id = str(
      (execution_state or {}).get("wordpress_post_id") or ""
    ).strip()

    if wordpress_status == "DRAFT" and wordpress_post_id:
      return (
        '<span class="workflow-action-done">'
        '下書き作成済み'
        f' / post_id={_escape(wordpress_post_id)}</span>'
      )

    if bool((execution_state or {}).get("loader_error")):
      return (
        '<span class="workflow-action-unavailable">'
        '下書き実行状態を確認できません：管理確認が必要</span>'
      )

    if execution_status in {"CLAIMED", "EXTERNAL_CALL_STARTED"}:
      return (
        '<span class="workflow-action-pending">'
        '下書き作成処理中</span>'
      )

    if execution_status in {
      "WORDPRESS_DRAFT_CREATED_DB_RECONCILIATION_REQUIRED",
      "WORDPRESS_DRAFT_POST_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED",
    }:
      post_detail = (
        f' / post_id={_escape(evidence_post_id)}'
        if evidence_post_id
        else ""
      )
      return (
        '<span class="workflow-action-unavailable">'
        'WordPress下書きは作成済みの可能性があります'
        f'{post_detail}</span>'
      )

    if wordpress_post_id or wordpress_status in {
      "DRAFT",
      "SCHEDULED",
      "PUBLISHED",
    }:
      return (
        '<span class="workflow-action-unavailable">'
        'WordPress状態不整合：管理確認が必要</span>'
      )

    if (
      execution_status
      and execution_status != "WORDPRESS_DRAFT_CREATED"
    ) or is_excluded:
      return (
        '<span class="workflow-action-unavailable">'
        '状態不整合：管理確認が必要</span>'
      )

    approval_is_eligible = bool(
      approved_request
      and approved_request.get("ebook_item_id") == item_id
      and approved_request.get("approval_type") == "REVIEW_READY"
      and approved_request.get("status") == "APPROVED"
      and approved_request.get("decided_at") is not None
      and approved_request.get("expected_current_status") == "REVIEW"
      and approved_request.get("requested_status") == "READY"
    )

    if (
      workflow_status != "READY"
      or review_status != "APPROVED"
      or publish_ready
      or wordpress_status not in {"", "NOT_CREATED"}
      or not approval_is_eligible
    ):
      return (
        '<button type="button" disabled '
        'class="workflow-action-button is-disabled" '
        'title="WorkflowをREADY、ReviewをAPPROVEDにすると実行できます">'
        'WordPress下書き作成（承認後）</button>'
      )

    missing_metadata = [
      field_name
      for field_name in ("author_name", "publisher_name")
      if not str(row.get(field_name) or "").strip()
    ]
    if missing_metadata:
      return (
        '<span class="workflow-action-unavailable">'
        'METADATA_REVIEW_REQUIRED: missing '
        f'{_escape(", ".join(missing_metadata))}</span>'
      )

    token = get_workflow_action_token()
    clean_query = str(query_string or "").lstrip("?")
    return_to = "/database-search"
    if clean_query:
      return_to = f"{return_to}?{clean_query}"

    display_title = title
    if volume_label:
      display_title = f"{display_title} {volume_label}"

    confirm_message = (
      f"{display_title}：WordPressに下書きを1件作成します。公開はしません"
    )

    return f"""
  <form
    method="post"
    action="/database-wordpress-draft"
    class="workflow-action-form"
    onsubmit="if(!confirm('{_escape(confirm_message)}')){{return false;}}var button=this.querySelector('button');if(button){{button.disabled=true;button.textContent='作成中…';}}return true;"
  >
    <input
    type="hidden"
    name="csrf_token"
    value="{_escape(token)}"
    >
    <input
    type="hidden"
    name="ebook_item_id"
    value="{_escape(item_id)}"
    >
    <input
    type="hidden"
    name="explicit_confirmation"
    value="create_wordpress_draft"
    >
    <input
    type="hidden"
    name="return_to"
    value="{_escape(return_to)}"
    >
    <button
    type="submit"
    class="workflow-action-button"
    >WordPress下書き作成</button>
  </form>
  """.strip()


def render_wordpress_schedule_action_form(
    row: dict[str, Any],
    query_string: str = "",
    execution_state: dict[str, Any] | None = None,
    schedule_state: dict[str, Any] | None = None,
    wordpress_categories: list[Any] | None = None,
    csrf_token: str | None = None,
) -> str:
    item_id = str(row.get("id") or "").strip()
    post_id = str(row.get("wordpress_post_id") or "").strip()
    review_status = str(row.get("review_status") or "").upper()
    workflow_status = str(row.get("workflow_status") or "").upper()
    wordpress_status = str(row.get("wordpress_status") or "").upper()
    execution_status = str((execution_state or {}).get("status") or "")
    schedule_execution_status = str((schedule_state or {}).get("claim_status") or "")
    if (
        not item_id
        or review_status != "APPROVED"
      or workflow_status not in {"READY", "REVIEW"}
    ):
        return ""
    categories = list(wordpress_categories or [])
    token = csrf_token or get_workflow_action_token()
    clean_query = str(query_string or "").lstrip("?")
    return_to = "/database-search"
    if clean_query:
        return_to = f"{return_to}?{clean_query}"

    missing_metadata = [
        field_name
        for field_name in ("author_name", "publisher_name")
        if not str(row.get(field_name) or "").strip()
    ]
    if not post_id or wordpress_status == "NOT_CREATED":
        missing_html = ""
        guidance = "先にWordPress下書きを作成してください"
        if missing_metadata:
            missing_html = (
                '<div class="workflow-action-unavailable">missing: '
                f'{_escape(", ".join(missing_metadata))}</div>'
            )
            guidance = "基本情報を完成後、下書きを作成してください"
        return f"""
<details class="wordpress-schedule-actions" open>
  <summary>WordPress予約・カテゴリー</summary>
  <div class="workflow-action-detail">WordPress投稿：未作成</div>
  {missing_html}
  <div class="workflow-notice workflow-notice-error">{_escape(guidance)}</div>
  <label>投稿カテゴリー:
    <select name="wordpress_category_id" disabled><option>未作成</option></select>
  </label>
  <label>公開予約日時:
    <input type="datetime-local" name="publish_at" step="60" disabled>
  </label>
  <div class="workflow-action-form">
    <button type="button" class="workflow-action-button" disabled>カテゴリーを更新</button>
    <button type="button" class="workflow-action-button" disabled>予約投稿</button>
  </div>
  <a class="workflow-action-button" href="#catalog-edit-{_escape(item_id)}">基本情報編集</a>
</details>
""".strip()

    if wordpress_status not in {"DRAFT", "SCHEDULED", "PUBLISHED"}:
        return ""
    recheck_separator = "&" if "?" in return_to else "?"
    recheck_url = (
        f"{return_to}{recheck_separator}wordpress_recheck={_escape(post_id)}"
    )

    remote_status = str((schedule_state or {}).get("remote_status") or "")
    remote_error_code = str(
        (schedule_state or {}).get("remote_error_code") or "remote_unavailable"
    )
    expected_remote_status = {
      "DRAFT": "draft",
      "SCHEDULED": "future",
      "PUBLISHED": "publish",
    }[wordpress_status]
    state_unavailable = (
        bool((execution_state or {}).get("loader_error"))
        or bool((schedule_state or {}).get("loader_error"))
        or bool((schedule_state or {}).get("remote_state_error"))
      or remote_status != expected_remote_status
        or execution_status in {"CLAIMED", "EXTERNAL_CALL_STARTED"}
        or schedule_execution_status in {"CLAIMED", "EXTERNAL_CALL_STARTED"}
    )

    if remote_status == "trash":
        state_label = "WordPress投稿はゴミ箱内です"
        warning = "ゴミ箱内の投稿は予約・カテゴリー更新を実行できません。"
        safe_code = "remote_status_trash"
    elif remote_error_code == "post_not_found":
        state_label = "WordPress投稿が見つかりません"
        warning = "ローカルのpost_idは変更していません。WordPress側を確認してください。"
        safe_code = "post_not_found"
    elif remote_error_code == "authentication_failed":
        state_label = "WordPress認証を確認してください"
        warning = "認証を確認できないため、現在は更新操作を実行できません。"
        safe_code = "authentication_failed"
    elif state_unavailable:
        state_label = "確認できません"
        warning = "WordPress投稿の状態を確認できないため、現在は予約・カテゴリー更新を実行できません。"
        safe_code = remote_error_code
    else:
        state_label = "下書き" if remote_status == "draft" else "予約済み"
        warning = ""
        safe_code = ""

    current_categories = list((schedule_state or {}).get("current_categories") or [])
    current_ids = {int(value.category_id) for value in current_categories}
    current_text = "、".join(str(value.name) for value in current_categories)

    if remote_status == "publish" and not bool(
        (schedule_state or {}).get("remote_state_error")
    ):
        remote_date = str((schedule_state or {}).get("remote_date") or "")
        published_text = remote_date[:16].replace("T", " ") if remote_date else "不明"
        return f"""
<details class="wordpress-schedule-actions" open>
  <summary>WordPress予約・カテゴリー</summary>
  <div class="workflow-action-detail">WordPress投稿: post_id={_escape(post_id)}</div>
  <div class="workflow-action-done">WordPress状態：公開済み</div>
  <div class="workflow-action-done">公開日時: {_escape(published_text)} JST</div>
  <label>投稿カテゴリー:
    <select disabled><option>{_escape(current_text or "変更不可")}</option></select>
  </label>
</details>
""".strip()

    def category_select(*, disabled: bool = False) -> str:
        options = ['<option value="">選択してください</option>']
        for category in categories:
            selected = " selected" if int(category.category_id) in current_ids else ""
            options.append(
                f'<option value="{_escape(category.category_id)}"{selected}>'
                f'{_escape(category.name)}</option>'
            )
        disabled_attribute = " disabled" if disabled else ""
        return (
            '<label>投稿カテゴリー: '
            f'<select name="wordpress_category_id" required{disabled_attribute}>'
            f'{"".join(options)}</select></label>'
        )

    if state_unavailable:
        category_disabled = not categories or state_unavailable
        category_display = (
            category_select(disabled=category_disabled)
            if categories
            else '<label>投稿カテゴリー: <select disabled><option>取得不能</option></select></label>'
        )
        return f"""
<details class="wordpress-schedule-actions" open>
  <summary>WordPress予約・カテゴリー</summary>
  <div class="workflow-action-detail">WordPress投稿: post_id={_escape(post_id)}</div>
  <div class="workflow-action-unavailable">WordPress状態: {_escape(state_label)}</div>
  {category_display}
  <label>公開予約日時:
    <input type="datetime-local" name="publish_at" step="60" disabled>
  </label>
  <div class="workflow-action-form">
    <button type="button" class="workflow-action-button" disabled>カテゴリーを更新</button>
    <button type="button" class="workflow-action-button" disabled>予約投稿</button>
  </div>
  <a class="workflow-action-button" href="{_escape(recheck_url)}">WordPress状態を再確認</a>
  <div class="workflow-notice workflow-notice-error">{_escape(warning)}</div>
  <div class="workflow-action-detail">error_code={_escape(safe_code)}</div>
</details>
""".strip()

    category_available = bool(categories)

    common = (
        f'<input type="hidden" name="csrf_token" value="{_escape(token)}">'
        f'<input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">'
        f'<input type="hidden" name="wordpress_post_id" value="{_escape(post_id)}">'
        f'<input type="hidden" name="return_to" value="{_escape(return_to)}">'
    )
    current_html = (
        f'<div class="workflow-action-done">現在のカテゴリー: {_escape(current_text)}</div>'
        if current_text
        else '<div class="workflow-action-detail">現在のカテゴリー: 未設定</div>'
    )

    category_update_form = f"""
<form method="post" action="/database-wordpress-schedule" class="workflow-action-form"
  onsubmit="if(!confirm('WordPress投稿カテゴリーを更新します。よろしいですか？')){{return false;}}this.querySelector('button').disabled=true;return true;">
  {common}
  <input type="hidden" name="operation" value="CATEGORY_UPDATE">
  {category_select(disabled=not category_available) if category_available else '<label>投稿カテゴリー: <select disabled><option>取得不能</option></select></label>'}
  <button type="submit" class="workflow-action-button"{' disabled' if not category_available else ''}>カテゴリーを更新</button>
</form>
""".strip()
    if wordpress_status == "DRAFT":
        return f"""
<details class="wordpress-schedule-actions" open>
  <summary>WordPress予約・カテゴリー</summary>
  <div class="workflow-action-detail">WordPress投稿: post_id={_escape(post_id)}</div>
  <div class="workflow-action-done">WordPress状態: 下書き</div>
  {current_html}
<form method="post" action="/database-wordpress-schedule" class="workflow-action-form"
  onsubmit="if(!confirm('カテゴリーを設定し、指定した日本時間でWordPress予約投稿を設定します。よろしいですか？')){{return false;}}this.querySelector('button').disabled=true;return true;">
  {common}
  <input type="hidden" name="operation" value="SCHEDULE">
  {category_select(disabled=not category_available) if category_available else '<label>投稿カテゴリー: <select disabled><option>取得不能</option></select></label>'}
  <label>公開予約日時:
    <input type="datetime-local" name="publish_at" step="60" required>
  </label>
  <button type="submit" class="workflow-action-button"{' disabled' if not category_available else ''}>カテゴリーを設定して予約投稿</button>
</form>
{category_update_form}
  {('<div class="workflow-notice workflow-notice-error">カテゴリー一覧を取得できないため、カテゴリー操作を停止しています。</div>' if not category_available else '')}
</details>
""".strip()

    publish_at = str((schedule_state or {}).get("publish_at_local") or "")
    if not publish_at:
        return (
            '<span class="workflow-action-unavailable">'
            '予約日時の証跡がありません：管理確認が必要</span>'
        )
    display_at = publish_at[:16].replace("T", " ")
    input_at = publish_at[:16]
    return f"""
<details class="wordpress-schedule-actions" open>
  <summary>WordPress予約・カテゴリー</summary>
  <div class="workflow-action-detail">WordPress投稿: post_id={_escape(post_id)}</div>
  <div class="workflow-action-done">WordPress状態: 予約済み</div>
  {current_html}
  <div class="workflow-action-done">予約済み: {_escape(display_at)} JST</div>
  <form method="post" action="/database-wordpress-schedule" class="workflow-action-form"
    onsubmit="if(!confirm('WordPressの予約日時を変更します。よろしいですか？')){{return false;}}this.querySelector('button').disabled=true;return true;">
    {common}
    <input type="hidden" name="operation" value="RESCHEDULE">
    {category_select(disabled=not category_available) if category_available else '<label>投稿カテゴリー: <select disabled><option>取得不能</option></select></label>'}
    <input type="datetime-local" name="publish_at" value="{_escape(input_at)}" step="60" required>
    <button type="submit" class="workflow-action-button"{' disabled' if not category_available else ''}>カテゴリーと予約日時を変更</button>
  </form>
  {category_update_form}
  <form method="post" action="/database-wordpress-schedule-cancel" class="workflow-action-form"
    onsubmit="if(!confirm('予約を解除してWordPress下書きへ戻します。よろしいですか？')){{return false;}}this.querySelector('button').disabled=true;return true;">
    {common}
    <input type="hidden" name="operation" value="CANCEL_SCHEDULE">
    <button type="submit" class="workflow-action-button is-reject">予約を解除して下書きへ戻す</button>
  </form>
  {('<div class="workflow-notice workflow-notice-error">カテゴリー一覧を取得できないため、カテゴリー操作を停止しています。</div>' if not category_available else '')}
</details>
""".strip()


def render_amazon_manual_offer_form(
    row: dict[str, Any],
    query_string: str = "",
    *,
    configured: bool = False,
    setting_source: str = "database",
) -> str:
    """Amazon手動アフィリエイトリンク登録フォームを描画する。"""

    item_id = str(row.get("id") or "").strip()
    title = str(row.get("title") or "").strip()
    volume_label = str(row.get("volume_label") or "").strip()

    if not item_id:
        return (
            '<button type="button" disabled '
            'class="workflow-action-button is-disabled">'
            'Amazon登録不可</button>'
        )

    if not configured:
        return (
            '<details class="amazon-manual-offer">'
            '<summary>Amazonリンク登録</summary>'
            '<p>トラッキングIDが未設定です。</p>'
            '<a href="/affiliate-settings">アフィリエイト設定へ</a>'
            '</details>'
        )

    clean_query = str(query_string or "").lstrip("?")
    return_to = "/database-search"

    if clean_query:
        return_to = f"{return_to}?{clean_query}"

    display_title = title
    if volume_label:
        display_title = f"{display_title} {volume_label}"

    token = get_workflow_action_token()

    confirm_message = (
        f"{display_title} にAmazonアフィリエイトリンクを保存します。"
        "ASINまたは商品URLに間違いがないことを確認しましたか？"
    )

    return f"""
<details class="amazon-manual-offer">
  <summary>Amazonリンク登録</summary>

  <form
    method="post"
    action="/database-amazon-offer"
    class="amazon-manual-offer-form"
    onsubmit="return confirm('{_escape(confirm_message)}');"
  >
    <input
      type="hidden"
      name="csrf_token"
      value="{_escape(token)}"
    >

    <input type="hidden" name="operation" value="preview">

    <input
      type="hidden"
      name="ebook_item_id"
      value="{_escape(item_id)}"
    >

    <input
      type="hidden"
      name="return_to"
      value="{_escape(return_to)}"
    >

    <label>
      ASIN または Amazon商品URL
      <input
        type="text"
        name="asin"
        maxlength="2000"
        placeholder="B0XXXXXXXX または https://www.amazon.co.jp/dp/..."
        autocomplete="off"
        required
      >
    </label>

    <div class="workflow-action-detail">
      保存済みIDを使用（優先元: {_escape(setting_source)}）
    </div>

    <button
      type="submit"
      class="workflow-action-button"
    >リンクをプレビュー</button>
  </form>
</details>
""".strip()


def render_catalog_edit_form(
    row: dict[str, Any], query_string: str = ""
) -> str:
    item_id = str(row.get("id") or "").strip()
    offer = row.get("rakuten_kobo_offer") or {}
    if not item_id:
        return '<span class="workflow-action-unavailable">基本情報編集不可（IDなし）</span>'
    if str(row.get("wordpress_status") or "NOT_CREATED").upper() not in {
        "",
        "NOT_CREATED",
    }:
        return '<span class="workflow-action-unavailable">基本情報編集不可（WordPress作成済み）</span>'
    clean_query = str(query_string or "").lstrip("?")
    return_to = "/database-search" + (f"?{clean_query}" if clean_query else "")
    price = offer.get("price_amount")
    if price is None:
        price = offer.get("price_yen")
    single_episode_checked = (
        " checked" if row.get("is_single_episode") is True else ""
    )
    split_edition_checked = (
        " checked" if row.get("is_split_edition") is True else ""
    )
    item_type = str(row.get("item_type") or "unknown")
    item_type_options = "".join(
        f'<option value="{_escape(value)}"'
        f'{" selected" if value == item_type else ""}>{_escape(label)}</option>'
        for value, label in (
            ("tankobon", "コミック単行本"),
            ("light_novel", "ライトノベル"),
            ("general_book", "一般書籍"),
            ("single_chapter", "単話"),
            ("magazine_episode", "雑誌話"),
            ("unknown", "未分類"),
        )
    )
    price_fields = ""
    if offer:
        price_fields = f"""
    <label>楽天Kobo価格 <input name="price" inputmode="decimal" value="{_escape(price)}"></label>
    <label>通貨 <input name="currency" maxlength="12" value="{_escape(offer.get('currency') or 'JPY')}" required></label>
  """
    else:
        price_fields = """
    <input type="hidden" name="price" value="">
    <input type="hidden" name="currency" value="">
  """
    return f"""
<details class="amazon-manual-offer catalog-edit-details">
  <summary>基本情報を編集</summary>
  <form method="post" action="/database-catalog-edit" class="amazon-manual-offer-form catalog-edit-form">
    <input type="hidden" name="csrf_token" value="{_escape(get_workflow_action_token())}">
    <input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">
    <input type="hidden" name="return_to" value="{_escape(return_to)}">
    <div>item_id: <code>{_escape(item_id)}</code>（変更不可）</div>
    <label>作品名 <input name="title" maxlength="500" value="{_escape(row.get('title'))}" required></label>
    <label>巻 <input name="volume_label" maxlength="100" value="{_escape(row.get('volume_label'))}"></label>
    <label>作者（|区切り） <input name="authors" maxlength="255" value="{_escape(row.get('author_name'))}"></label>
    <label>出版社 <input name="publisher" maxlength="255" value="{_escape(row.get('publisher_name'))}"></label>
    <label>レーベル <input name="imprint" maxlength="255" value="{_escape(row.get('series_name'))}"></label>
    <label>種別 <select name="item_type">{item_type_options}</select></label>
    <label>発売日 <input type="date" name="release_date" value="{_escape(row.get('release_date'))}"></label>
    {price_fields}
    <label><input type="checkbox" name="is_single_episode" value="true"{single_episode_checked}> 単話</label>
    <label><input type="checkbox" name="is_split_edition" value="true"{split_edition_checked}> 分冊版</label>
    <label><input type="checkbox" name="apply_to_future_series" value="true"> この分類を次回以降の同シリーズへ適用</label>
    <label>変更理由 <input name="reason" maxlength="500" required></label>
    <p class="catalog-edit-prefill-notice" aria-live="polite" hidden></p>
    <button type="submit" class="workflow-action-button">基本情報を保存</button>
  </form>
</details>
""".strip()


def render_manual_store_offer_form(
    row: dict[str, Any],
    query_string: str = "",
    *,
    csrf_token: str,
) -> str:
    item_id = str(row.get("id") or "").strip()
    if not item_id or row.get("rakuten_kobo_offer"):
        return ""
    wordpress_status = str(
        row.get("wordpress_status") or "NOT_CREATED"
    ).upper()
    if wordpress_status not in {"NOT_CREATED", "DRAFT"}:
        return ""
    clean_query = str(query_string or "").lstrip("?")
    return_to = "/database-search" + (f"?{clean_query}" if clean_query else "")
    return f"""
<details class="amazon-manual-offer manual-store-offer-details">
  <summary>ストアリンクを手動登録</summary>
  <form method="post" action="/database-manual-store-offer" class="amazon-manual-offer-form manual-store-offer-form">
    <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
    <input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">
    <input type="hidden" name="return_to" value="{_escape(return_to)}">
    <label>媒体
      <select name="store_name">
        <option value="rakuten_kobo" selected>楽天Kobo</option>
      </select>
    </label>
    <label>商品URL（任意）
      <input type="url" name="product_url" maxlength="2000" autocomplete="off">
    </label>
    <label>アフィリエイトURL
      <input type="url" name="affiliate_url" required maxlength="2000" autocomplete="off">
    </label>
    <label>価格（任意）
      <input name="price" inputmode="numeric">
    </label>
    <input type="hidden" name="currency" value="JPY">
    <label>在庫状態
      <select name="availability_status">
        <option value="FOUND" selected>確認済み</option>
      </select>
    </label>
    <label>確認日時（任意）
      <input type="datetime-local" name="observed_at" step="1">
    </label>
    <label><input type="checkbox" name="confirmed" value="true" required> URLを人間が確認しました</label>
    <button type="submit" class="workflow-action-button">楽天Koboリンクを登録</button>
  </form>
</details>
""".strip()


def render_supplement_cancellation_action(
    preview: Any | None,
    query_string: str = "",
    *,
    csrf_token: str,
) -> str:
    if preview is None or preview.source != "RAKUTEN_BOOKS_COMIC_CALENDAR":
        return ""
    if not preview.cancellable:
        reasons = " / ".join(preview.block_reasons)
        return (
            '<span class="workflow-action-unavailable">'
            f'補完登録取消不可: {_escape(reasons)}</span>'
        )
    if not preview.candidate_id:
        return ""
    clean_query = str(query_string or "").lstrip("?")
    return_to = "/database-search" + (f"?{clean_query}" if clean_query else "")
    return f"""
<details class="amazon-manual-offer supplement-cancellation-details">
  <summary>補完登録を取り消す</summary>
  <div class="workflow-action-detail">
    この操作は補完から作成された未処理レコードを削除し、元の補完候補を再登録可能な状態へ戻します。WordPress投稿、リンク、承認、日次まとめが存在する作品には実行できません。
  </div>
  <dl>
    <dt>ebook_item_id</dt><dd><code>{_escape(preview.ebook_item_id)}</code></dd>
    <dt>タイトル</dt><dd>{_escape(preview.title)}</dd>
    <dt>元candidate ID</dt><dd><code>{_escape(preview.candidate_id)}</code></dd>
    <dt>source</dt><dd>{_escape(preview.source)}</dd>
    <dt>現在の状態</dt><dd>{_escape(preview.current_state)}</dd>
    <dt>取消後の状態</dt><dd>{_escape(preview.resulting_state)}</dd>
  </dl>
  <form method="post" action="/database-supplement-cancel" class="amazon-manual-offer-form">
    <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
    <input type="hidden" name="ebook_item_id" value="{_escape(preview.ebook_item_id)}">
    <input type="hidden" name="candidate_id" value="{_escape(preview.candidate_id)}">
    <input type="hidden" name="return_to" value="{_escape(return_to)}">
    <label>タイトルを確認
      <input name="expected_title" required maxlength="500" autocomplete="off">
    </label>
    <label><input type="checkbox" name="confirmed" value="true" required> この補完登録を取り消します</label>
    <button type="submit" class="workflow-action-button">補完登録を取り消す</button>
  </form>
</details>
""".strip()


def render_metadata_autofill_form(
    row: dict[str, Any], query_string: str = ""
) -> str:
    item_id = str(row.get("id") or "").strip()
    if not item_id:
        return '<span class="workflow-action-unavailable">書誌情報補完不可</span>'
    if not row.get("rakuten_kobo_offer"):
      return '<span class="workflow-action-unavailable">楽天Kobo自動補完不可（楽天Kobo行なし）</span>'
    return f"""
<div class="metadata-autofill" data-ebook-item-id="{_escape(item_id)}">
  <button
    type="button"
    class="workflow-action-button metadata-autofill-button"
    data-csrf-token="{_escape(get_workflow_action_token())}"
  >基本情報更新</button>
  <section class="metadata-autofill-panel" aria-live="polite" hidden></section>
</div>
""".strip()


def render_metadata_autofill_preview_page(
    preview: Any,
    *,
    csrf_token: str,
    return_to: str,
) -> str:
    labels = {
        "volume_label": "巻数",
        "author_name": "作者",
        "publisher_name": "出版社",
    }
    rows = ""
    for result in preview.field_results:
        before = result.before or "空欄"
        candidate = result.candidate or "候補なし"
        conflict = (
            " / ".join(result.conflict_values)
            if result.conflict_values
            else ""
        )
        reason = result.reason or "-"
        if conflict:
            reason = f"{reason}: {conflict}"
        source_types = " / ".join(result.source_types)
        rows += f"""
        <tr>
          <th>{_escape(labels.get(result.field_name, result.field_name))}</th>
          <td>{_escape(before)} → {_escape(candidate)}</td>
          <td>{_escape(source_types or result.source_type or "-")}</td>
          <td>{_escape(result.confidence or "-")}</td>
          <td>{_escape(result.status)}</td>
          <td>{_escape(reason)}</td>
        </tr>
        """
    apply_form = ""
    if preview.apply_possible:
        apply_form = f"""
        <form method="post" action="/database-metadata-autofill">
          <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
          <input type="hidden" name="ebook_item_id" value="{_escape(preview.ebook_item_id)}">
          <input type="hidden" name="return_to" value="{_escape(return_to)}">
          <input type="hidden" name="operation" value="apply">
          <input type="hidden" name="preview_fingerprint" value="{_escape(preview.fingerprint)}">
          <label><input type="checkbox" name="confirmed" value="true" required> 内容を確認しました</label>
          <button type="submit">補完を確定</button>
        </form>
        """
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>書誌情報自動補完プレビュー</title></head>
<body>
  <h1>書誌情報自動補完プレビュー</h1>
  <p>状態: <strong>{_escape(preview.metadata_status)}</strong></p>
  <p>この画面の表示だけではDBを更新しません。</p>
  <table border="1">
    <thead><tr><th>項目</th><th>変更</th><th>情報源</th><th>確度</th><th>項目状態</th><th>理由</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  {apply_form}
  <p><a href="{_escape(return_to)}">キャンセル</a></p>
</body></html>"""


def render_dmm_manual_offer_form(
    row: dict[str, Any],
    query_string: str = "",
    *,
    generation_available: bool = False,
) -> str:
    item_id = str(row.get("id") or "").strip()
    if not item_id:
        return '<span class="workflow-action-unavailable">DMM登録不可</span>'
    clean_query = str(query_string or "").lstrip("?")
    return_to = "/database-search" + (f"?{clean_query}" if clean_query else "")
    setting_help = "" if generation_available else (
        '<p>有効なDMM掲載先別プロファイルを設定してください。'
        '<a href="/affiliate-settings">DMM設定へ</a></p>'
    )
    return f"""
<details class="amazon-manual-offer">
  <summary>DMMリンク登録</summary>
  <form method="post" action="/database-dmm-offer" class="amazon-manual-offer-form">
    <input type="hidden" name="csrf_token" value="{_escape(get_workflow_action_token())}">
    <input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">
    <input type="hidden" name="return_to" value="{_escape(return_to)}">
    <input type="hidden" name="operation" value="preview">
    <div>item_id: <code>{_escape(item_id)}</code>（変更不可）</div>
    <label>URLまたはDMMアフィリエイトHTML
      <textarea name="dmm_input" maxlength="12000" rows="6" required
        placeholder='https://book.dmm.com/product/.../.../ または &lt;a href="https://al.dmm.com/...?lurl=..."&gt;商品名&lt;/a&gt;'></textarea>
    </label>
    <label>DMM価格（任意） <input name="price" inputmode="decimal"></label>
    <label>通貨 <input name="currency" maxlength="12" value="JPY"></label>
    {setting_help}
    <button type="submit" class="workflow-action-button">解析して確認</button>
  </form>
</details>
""".strip()



def _first(params: dict[str, list[str]], name: str) -> str:
    values = params.get(name) or []
    return values[0].strip() if values else ""


def _parse_bool(value: str) -> bool:
    return str(value or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _parse_page(value: str) -> int:
    try:
        page = int(str(value or "").strip())
    except ValueError:
        return 1
    return page if page > 0 else 1


def parse_database_search_query(
    raw_query: str,
) -> DatabaseSearchPageState:
    params = parse_qs(raw_query, keep_blank_values=True)

    tokyo_today = datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    missing_affiliate = _parse_bool(_first(params, "missing_affiliate"))
    affiliate_status = _first(params, "affiliate_status")
    if affiliate_status not in {
      "all",
      "all_unregistered",
      "partially_registered",
      "all_registered",
    }:
      affiliate_status = "all"
    if missing_affiliate and "affiliate_status" not in params:
      affiliate_status = "all_unregistered"

    def store_affiliate_status(name: str) -> str:
      value = _first(params, name)
      return value if value in {"all", "registered", "unregistered"} else "all"

    return DatabaseSearchPageState(
        keyword=_first(params, "keyword"),
        release_date_from=_first(params, "release_date_from"),
        release_date_to=_first(params, "release_date_to"),
        item_type=_first(params, "item_type"),
        store_name=_first(params, "store_name"),
        workflow_status=_first(params, "workflow_status"),
        review_status=_first(params, "review_status"),
        wordpress_status=_first(params, "wordpress_status"),
        include_excluded=_parse_bool(
            _first(params, "include_excluded")
        ),
        excluded_only=_parse_bool(
            _first(params, "excluded_only")
        ),
        missing_price=_parse_bool(
            _first(params, "missing_price")
        ),
        missing_affiliate=missing_affiliate,
        affiliate_status=affiliate_status,
        amazon_affiliate_status=store_affiliate_status(
          "amazon_affiliate_status"
        ),
        rakuten_kobo_affiliate_status=store_affiliate_status(
          "rakuten_kobo_affiliate_status"
        ),
        dmm_affiliate_status=store_affiliate_status(
          "dmm_affiliate_status"
        ),
        summary_date=_first(params, "summary_date") or tokyo_today,
        page=_parse_page(_first(params, "page")),
    )


def load_daily_summary_snapshot(summary_date_text: str) -> Any:
    from app.services.daily_summary_query_service import DailySummaryQueryService

    summary_date = date.fromisoformat(summary_date_text)
    with ReadOnlySessionLocal() as session:
        return DailySummaryQueryService(session).build_snapshot(summary_date)


def load_dashboard_summary() -> dict[str, Any]:
    with ReadOnlySessionLocal() as session:
        return EbookDashboardService(session).build_summary()


def load_affiliate_setting_views() -> dict[str, Any]:
    from app.db.access_guard import is_test_environment
    from app.services.affiliate_account_settings_service import (
        AffiliateAccountSettingsService,
    )

    if is_test_environment():
        environment_values = {
            "amazon": os.getenv("AMAZON_TRACKING_ID", "").strip(),
            "dmm": os.getenv("DMM_AFFILIATE_ID", "").strip(),
        }
        return {
            service_name: AffiliateSettingDisplay(
                service_name=service_name,
                masked_affiliate_id=(
                    _mask_affiliate_id(value)
                ),
                configured=bool(value),
                enabled=bool(value),
                updated_at="",
                source=(
                    f"environment:{'AMAZON_TRACKING_ID' if service_name == 'amazon' else 'DMM_AFFILIATE_ID'}"
                    if value
                    else "database"
                ),
                url_template_configured=(
                    service_name == "dmm"
                    and bool(os.getenv("DMM_AFFILIATE_URL_TEMPLATE", "").strip())
                ),
            )
            for service_name, value in environment_values.items()
        }

    with ReadOnlySessionLocal() as session:
        return {
            setting.service_name: setting
            for setting in AffiliateAccountSettingsService(session).list_settings()
        }


def load_dmm_destination_profile_views(
) -> dict[str, DmmDestinationProfileDisplay]:
    from app.db.access_guard import is_test_environment
    from app.db.repositories.affiliate_destination_profile_repository import (
        AffiliateDestinationProfileRepository,
    )

    definitions = {
        "blog_main": ("wordpress", "メインブログ"),
        "x_main": ("x", "公式X"),
    }
    if is_test_environment():
        return {
            key: DmmDestinationProfileDisplay(
                provider="dmm",
                destination_type=destination_type,
                destination_key=key,
                display_name=display_name,
                masked_affiliate_id="未登録",
                configured=False,
                active=False,
                channel="toolbar",
                channel_id="text",
            )
            for key, (destination_type, display_name) in definitions.items()
        }
    with ReadOnlySessionLocal() as session:
        profiles = {
            profile.destination_key: profile
            for profile in AffiliateDestinationProfileRepository(
                session
            ).list_for_provider(provider="dmm")
        }
    views: dict[str, DmmDestinationProfileDisplay] = {}
    for key, (destination_type, display_name) in definitions.items():
        profile = profiles.get(key)
        views[key] = DmmDestinationProfileDisplay(
            provider="dmm",
            destination_type=(
                profile.destination_type if profile else destination_type
            ),
            destination_key=key,
            display_name=profile.display_name if profile else display_name,
            masked_affiliate_id=_mask_affiliate_id(
                profile.affiliate_id if profile else None
            ),
            configured=profile is not None,
            active=bool(profile and profile.is_active),
            channel=(profile.channel or "toolbar") if profile else "toolbar",
            channel_id=(
                profile.channel_id or "text"
            ) if profile else "text",
        )
    return views


def search_database_rows(
    state: DatabaseSearchPageState,
) -> list[dict[str, Any]]:
  query = database_query_from_state(state)
  with ReadOnlySessionLocal() as session: return EbookDatabaseViewModel(session).search(query)


def count_database_rows(state: DatabaseSearchPageState) -> int:
  query = database_query_from_state(state)
  with ReadOnlySessionLocal() as session: return EbookDatabaseViewModel(session).count(query)


def database_query_from_state(
    state: DatabaseSearchPageState,
) -> EbookDatabaseQuery:
    return EbookDatabaseQuery(
        keyword=state.keyword,
        release_date_from=state.release_date_from,
        release_date_to=state.release_date_to,
        item_type=state.item_type,
        store_name=state.store_name,
        workflow_status=state.workflow_status,
        review_status=state.review_status,
        wordpress_status=state.wordpress_status,
        include_excluded=state.include_excluded,
        excluded_only=state.excluded_only,
        missing_price=state.missing_price,
        missing_affiliate=state.missing_affiliate,
        affiliate_status=state.affiliate_status,
        amazon_affiliate_status=state.amazon_affiliate_status,
        rakuten_kobo_affiliate_status=state.rakuten_kobo_affiliate_status,
        dmm_affiliate_status=state.dmm_affiliate_status,
        limit=DATABASE_SEARCH_PER_PAGE,
        offset=(state.page - 1) * DATABASE_SEARCH_PER_PAGE,
    )


def database_search_page_url(raw_query: str, page: int) -> str:
    raw_pairs = parse_qsl(
        str(raw_query or ""), keep_blank_values=True
    )
    has_affiliate_status = any(
        name == "affiliate_status" for name, _value in raw_pairs
    )
    legacy_missing_affiliate = any(
        name == "missing_affiliate" and _parse_bool(value)
        for name, value in raw_pairs
    )
    query_pairs = [
        (name, value)
        for name, value in raw_pairs
        if name in DATABASE_SEARCH_FILTER_PARAMETERS
        and name != "missing_affiliate"
    ]
    if legacy_missing_affiliate and not has_affiliate_status:
        query_pairs.append(("affiliate_status", "all_unregistered"))
    query_pairs.append(("page", str(page)))
    return f"/database-search?{urlencode(query_pairs)}"


def daily_summary_return_url(
    raw_query: str, summary_date: str
) -> str:
    query = parse_qs(str(raw_query or ""), keep_blank_values=True)
    query["summary_date"] = [summary_date]
    return f"/database-search?{urlencode(query, doseq=True)}"


def load_pending_review_ready_approvals(
    ebook_item_ids: list[str],
) -> dict[str, dict[str, Any]]:
    normalized_ids = [
        str(item_id).strip()
        for item_id in ebook_item_ids
        if str(item_id).strip()
    ]

    if not normalized_ids:
        return {}

    with ReadOnlySessionLocal() as session:
        statement = (
            select(WorkflowApprovalRequest)
            .where(
                WorkflowApprovalRequest.ebook_item_id.in_(
                    normalized_ids
                ),
                WorkflowApprovalRequest.approval_type
                == "REVIEW_READY",
                WorkflowApprovalRequest.status == "PENDING",
            )
            .order_by(
                WorkflowApprovalRequest.requested_at.desc(),
                WorkflowApprovalRequest.id.desc(),
            )
        )
        approvals: dict[str, dict[str, Any]] = {}

        for request in session.scalars(statement):
            approvals.setdefault(
                request.ebook_item_id,
                {
                    "id": request.id,
                    "approval_type": request.approval_type,
                    "status": request.status,
                    "expires_at": request.expires_at,
                },
            )

        return approvals


def load_approved_review_ready_approvals(
    ebook_item_ids: list[str],
) -> dict[str, dict[str, Any]]:
    normalized_ids = [
        str(item_id).strip()
        for item_id in ebook_item_ids
        if str(item_id).strip()
    ]
    if not normalized_ids:
        return {}

    with ReadOnlySessionLocal() as session:
        statement = (
            select(WorkflowApprovalRequest)
            .where(
                WorkflowApprovalRequest.ebook_item_id.in_(
                    normalized_ids
                ),
                WorkflowApprovalRequest.approval_type
                == "REVIEW_READY",
                WorkflowApprovalRequest.status == "APPROVED",
                WorkflowApprovalRequest.decided_at.is_not(None),
                WorkflowApprovalRequest.expected_current_status
                == "REVIEW",
                WorkflowApprovalRequest.requested_status == "READY",
            )
            .order_by(
                WorkflowApprovalRequest.decided_at.desc(),
                WorkflowApprovalRequest.requested_at.desc(),
                WorkflowApprovalRequest.id.desc(),
            )
        )
        approvals: dict[str, dict[str, Any]] = {}
        for request in session.scalars(statement):
            approvals.setdefault(
                request.ebook_item_id,
                {
                    "id": request.id,
                    "ebook_item_id": request.ebook_item_id,
                    "approval_type": request.approval_type,
                    "status": request.status,
                    "decided_at": request.decided_at,
                    "expected_current_status": (
                        request.expected_current_status
                    ),
                    "requested_status": request.requested_status,
                },
            )
        return approvals


def load_wordpress_draft_execution_states(
    ebook_item_ids: list[str],
) -> dict[str, dict[str, Any]]:
    from app.services.wordpress_draft_execution_service import (
        default_wordpress_draft_execution_store,
    )

    store = default_wordpress_draft_execution_store()
    states: dict[str, dict[str, Any]] = {}
    for raw_item_id in ebook_item_ids:
        item_id = str(raw_item_id or "").strip()
        if not item_id:
            continue
        try:
          state = store.read_for_item(item_id)
        except Exception:
          states[item_id] = {"loader_error": True}
          continue
        if state is not None:
            states[item_id] = state
    return states


def load_wordpress_schedule_states(
    ebook_item_ids: list[str],
) -> dict[str, dict[str, Any]]:
    from app.services.wordpress_post_schedule_service import (
        default_wordpress_post_schedule_execution_store,
    )

    store = default_wordpress_post_schedule_execution_store()
    states: dict[str, dict[str, Any]] = {}
    for raw_item_id in ebook_item_ids:
        item_id = str(raw_item_id or "").strip()
        if not item_id:
            continue
        try:
          state = store.read_latest_success(item_id)
          claim = store.read_claim(item_id)
        except Exception:
          states[item_id] = {
            "loader_error": True,
            "claim_status": "UNKNOWN",
          }
          continue
        if state is not None or claim is not None:
          states[item_id] = {
            **(state or {}),
            "claim_status": str((claim or {}).get("status") or ""),
          }
    return states


def load_supplement_cancellation_previews(
    ebook_item_ids: list[str],
) -> dict[str, Any]:
    from pathlib import Path

    from app.services.supplement_import_cancellation_service import (
        SupplementImportCancellationService,
    )

    previews: dict[str, Any] = {}
    if not ebook_item_ids:
        return previews
    with ReadOnlySessionLocal() as session:
        service = SupplementImportCancellationService(
            session,
            repository_root=Path(__file__).resolve().parents[2],
        )
        for ebook_item_id in ebook_item_ids:
            previews[ebook_item_id] = service.preview_cancel(ebook_item_id)
    return previews


def load_wordpress_category_context(
    rows: list[dict[str, Any]],
) -> WordPressCategoryPageContext:
    from app.integrations.wordpress_rest_client import WordPressRestClient
    from app.services.wordpress_post_schedule_service import (
        DEFAULT_WORDPRESS_CATEGORY_ALLOWLIST,
      WordPressPostScheduleService,
      default_wordpress_post_schedule_execution_store,
    )
    from app.db.session import SessionLocal

    base_url = os.environ.get("WORDPRESS_BASE_URL") or os.environ.get("WP_BASE_URL") or ""
    username = os.environ.get("WORDPRESS_USERNAME") or os.environ.get("WP_USERNAME") or ""
    password = (
        os.environ.get("WORDPRESS_APPLICATION_PASSWORD")
        or os.environ.get("WP_APPLICATION_PASSWORD")
        or os.environ.get("WP_APP_PASSWORD")
        or ""
    )
    eligible_rows = [
        row
        for row in rows
        if (
            str(row.get("id") or "").strip()
            and str(row.get("wordpress_post_id") or "").strip().isdigit()
            and str(row.get("review_status") or "").upper() == "APPROVED"
            and str(row.get("wordpress_status") or "").upper() in {"DRAFT", "SCHEDULED", "PUBLISHED"}
        )
    ]
    if not str(base_url).strip().startswith("https://"):
        return WordPressCategoryPageContext(
            categories=[],
            item_states={
                str(row["id"]): {
                    "remote_state_error": True,
                    "remote_error_code": "configuration_error",
                }
                for row in eligible_rows
            },
            error="WordPressカテゴリー設定を読み込めませんでした。",
        )
    try:
        client = WordPressRestClient(
            base_url=base_url,
            username=username,
            application_password=password,
        )
    except Exception:
        return WordPressCategoryPageContext(
            categories=[],
            item_states={
                str(row["id"]): {
                    "remote_state_error": True,
                    "remote_error_code": "configuration_error",
                }
                for row in eligible_rows
            },
            error="WordPress接続設定を読み込めませんでした。",
        )
    category_error = ""
    try:
        all_categories = client.list_categories(per_page=100)
    except Exception:
        all_categories = []
        category_error = "WordPressカテゴリー一覧を取得できませんでした。"
    category_by_id = {category.category_id: category for category in all_categories}
    allowed = [
        category
        for category in all_categories
        if category.slug in DEFAULT_WORDPRESS_CATEGORY_ALLOWLIST
    ]
    item_states: dict[str, dict[str, Any]] = {}
    for row in eligible_rows:
        item_id = str(row.get("id") or "").strip()
        post_id = str(row.get("wordpress_post_id") or "").strip()
        try:
          remote = client.get_post_state(post_id=int(post_id))
          synced_local_status = str(row.get("wordpress_status") or "").upper()
          if remote.status == "publish" and synced_local_status in {"DRAFT", "SCHEDULED"}:
            with SessionLocal() as session:
              sync_result = WordPressPostScheduleService(
                session,
                wordpress_client=client,
                execution_store=default_wordpress_post_schedule_execution_store(),
              ).sync_remote_status(
                ebook_item_id=item_id,
                wordpress_post_id=int(post_id),
              )
            synced_local_status = sync_result.new_local_status
        except Exception as exc:
            item_states[item_id] = {
                "remote_state_error": True,
                "remote_error_code": str(
                    getattr(exc, "code", "remote_unavailable")
                ),
                "remote_http_status": getattr(exc, "http_status", None),
            }
            continue
        item_states[item_id] = {
          "remote_status": remote.status,
          "remote_date": getattr(remote, "date", None),
          "remote_date_gmt": getattr(remote, "date_gmt", None),
            "current_categories": [
                category_by_id[category_id]
            for category_id in remote.categories
                if category_id in category_by_id
            ],
          "remote_category_ids": list(remote.categories),
          "synced_local_status": synced_local_status,
        }
    return WordPressCategoryPageContext(
        categories=allowed,
        item_states=item_states,
        error=category_error,
    )


def build_database_search_page_context(
    raw_query: str,
  review_ready_token_ids: set[str] | None = None,
  *,
  csrf_token: str | None = None,
) -> DatabaseSearchPageContext:
    from urllib.parse import parse_qs as _workflow_parse_qs

    params = _workflow_parse_qs(
    str(raw_query or ""),
        keep_blank_values=True,
    )
    state = parse_database_search_query(raw_query)
    rows: list[dict[str, Any]] = []
    total_count = 0
    total_pages = 1
    current_page = 1
    error = ""
    dashboard = load_dashboard_summary()
    cards = dashboard["cards"]
    dates = dashboard["dates"]
    database_info = dashboard["database"]
    setting_views = load_affiliate_setting_views()
    amazon_setting = setting_views["amazon"]
    dmm_destination_profiles = load_dmm_destination_profile_views()

    try:
        total_count = count_database_rows(state)
        total_pages = max(
            1,
            (total_count + DATABASE_SEARCH_PER_PAGE - 1)
            // DATABASE_SEARCH_PER_PAGE,
        )
        current_page = min(state.page, total_pages)
        state = replace(state, page=current_page)
        rows = search_database_rows(state)
    except ValueError as exc:
        error = str(exc)

    if total_count:
        display_start = (
            (current_page - 1) * DATABASE_SEARCH_PER_PAGE + 1
        )
        display_end = min(
            current_page * DATABASE_SEARCH_PER_PAGE,
            total_count,
        )
    else:
        display_start = 0
        display_end = 0

    page_controls = []
    for page_number in range(1, total_pages + 1):
        if page_number == current_page:
            page_controls.append(
                f'<strong aria-current="page">{_escape(page_number)}</strong>'
            )
        else:
            page_controls.append(
                f'<a class="workflow-action-button" href="'
                f'{_escape(database_search_page_url(raw_query, page_number))}'
                f'">{_escape(page_number)}</a>'
            )
    numeric_page_controls = " ".join(page_controls)
    item_ids = [str(row.get("id") or "") for row in rows]
    pending_approvals = load_pending_review_ready_approvals(item_ids)
    token_ids = review_ready_token_ids or set()
    now = datetime.now(timezone.utc)
    for approval in pending_approvals.values():
      expires_at = approval.get("expires_at")
      if isinstance(expires_at, datetime):
        if expires_at.tzinfo is None:
          expires_at = expires_at.replace(tzinfo=timezone.utc)
        approval["is_expired"] = expires_at <= now
      else:
        approval["is_expired"] = True
      approval["token_available"] = approval.get("id") in token_ids
    approved_approvals = load_approved_review_ready_approvals(item_ids)
    try:
      wordpress_execution_states = load_wordpress_draft_execution_states(item_ids)
    except Exception:
      wordpress_execution_states = {
        item_id: {"loader_error": True} for item_id in item_ids
      }
    try:
      wordpress_schedule_states = load_wordpress_schedule_states(item_ids)
    except Exception:
      wordpress_schedule_states = {
        item_id: {"loader_error": True, "claim_status": "UNKNOWN"}
        for item_id in item_ids
      }
    try:
      supplement_cancellation_previews = (
        load_supplement_cancellation_previews(item_ids)
      )
    except Exception:
      supplement_cancellation_previews = {}
      LOGGER.exception("Supplement cancellation previews could not be loaded")
    try:
      category_context = load_wordpress_category_context(rows)
    except Exception:
      category_context = WordPressCategoryPageContext(
        categories=[],
        item_states={},
        error="WordPressカテゴリー一覧を取得できませんでした。",
      )
    for item_id, item_state in category_context.item_states.items():
      wordpress_schedule_states.setdefault(item_id, {}).update(item_state)

    notices = {
      "workflow": render_workflow_notice(params),
      "review_ready": render_review_ready_notice(params),
      "amazon_offer": render_amazon_offer_notice(params),
      "catalog_edit": render_named_notice(
        params, "catalog_edit_result", CATALOG_EDIT_NOTICES
      ),
      "manual_store_offer": render_named_notice(
        params,
        "manual_store_offer_result",
        MANUAL_STORE_OFFER_NOTICES,
      ),
      "supplement_cancel": render_named_notice(
        params,
        "supplement_cancel_result",
        {
          "SUPPLEMENT_REGISTRATION_CANCELLED": (
            "success",
            "補完登録を取り消しました。元の候補を編集して再登録できます。",
          ),
          "CANCEL_INVALID_CSRF": ("error", "CSRF検証に失敗しました。"),
          "CANCEL_INVALID_INPUT": ("error", "取消確認の入力が不正です。"),
          "CANCEL_INTERNAL_ERROR": ("error", "補完登録の取消に失敗しました。"),
        },
      ),
      "metadata_autofill": render_named_notice(
        params, "metadata_autofill_result", METADATA_AUTOFILL_NOTICES
      ),
      "dmm_offer": render_named_notice(
        params, "dmm_offer_result", DMM_OFFER_NOTICES
      ),
      "wordpress_draft": render_wordpress_draft_notice(params),
      "wordpress_schedule": render_named_notice(
        params,
        "wordpress_schedule_result",
        WORDPRESS_SCHEDULE_NOTICES,
      ),
      "daily_summary": render_named_notice(
        params,
        "daily_summary_result",
        {
          "selection_saved": ("success", "日次まとめの掲載選択を保存しました。"),
          "auto_selected": ("success", "自動選択候補を反映しました。"),
          "all_excluded": ("success", "対象日の選択をすべて人間除外にしました。"),
          "reset_to_auto": ("success", "人間選択を解除して自動選択へ戻しました。"),
          "preview_ready": ("success", "日次まとめの生成前プレビューを更新しました。"),
          "dry_run_ready": ("success", "日次まとめ下書き生成のdry-runが完了しました。"),
          "invalid_token": ("error", "CSRF検証に失敗しました。"),
          "invalid_request": ("error", "日次まとめ操作の入力が不正です。"),
          "generation_blocked": ("error", "状態不整合があるため日次まとめ生成を停止しました。"),
          "internal_error": ("error", "日次まとめ処理中にエラーが発生しました。"),
        },
      ),
    }
    daily_summary_error_code = ""
    try:
      daily_summary_snapshot = load_daily_summary_snapshot(state.summary_date)
      daily_summary_selections = {
        item.ebook_item_id: item.inclusion_state
        for item in daily_summary_snapshot.items
        if item.inclusion_state
      }
    except ValueError:
      daily_summary_snapshot = None
      daily_summary_selections = {}
      daily_summary_error_code = "DAILY_SUMMARY_INVALID_DATE"
      LOGGER.exception(
        "Daily summary context load failed",
        extra={"summary_date": state.summary_date},
      )
    except OperationalError as exc:
      daily_summary_snapshot = None
      daily_summary_selections = {}
      message = str(exc).casefold()
      daily_summary_error_code = (
        "DAILY_SUMMARY_TABLE_MISSING"
        if "no such table" in message or "undefined table" in message
        else "DAILY_SUMMARY_QUERY_FAILED"
      )
      LOGGER.exception(
        "Daily summary context load failed",
        extra={"summary_date": state.summary_date},
      )
    except Exception:
      daily_summary_snapshot = None
      daily_summary_selections = {}
      daily_summary_error_code = "DAILY_SUMMARY_CONTEXT_FAILED"
      LOGGER.exception(
        "Daily summary context load failed",
        extra={"summary_date": state.summary_date},
      )
    return DatabaseSearchPageContext(
      raw_query=str(raw_query or ""),
      params=params,
      state=state,
      rows=rows,
      total_count=total_count,
      total_pages=total_pages,
      current_page=current_page,
      display_start=display_start,
      display_end=display_end,
      numeric_page_controls=numeric_page_controls,
      error=error,
      dashboard=dashboard,
      setting_views=setting_views,
      dmm_destination_profiles=dmm_destination_profiles,
      pending_approvals=pending_approvals,
      approved_approvals=approved_approvals,
      wordpress_execution_states=wordpress_execution_states,
      wordpress_schedule_states=wordpress_schedule_states,
      supplement_cancellation_previews=supplement_cancellation_previews,
      wordpress_categories=category_context.categories,
      wordpress_context_error=category_context.error,
      csrf_token=csrf_token or get_workflow_action_token(),
      notices=notices,
      daily_summary_snapshot=daily_summary_snapshot,
      daily_summary_selections=daily_summary_selections,
      daily_summary_error_code=daily_summary_error_code,
    )


def render_database_search_page(
    raw_query: str,
    review_ready_token_ids: set[str] | None = None,
    *,
    csrf_token: str | None = None,
  daily_summary_preview: Any | None = None,
) -> str:
    context = build_database_search_page_context(
      raw_query,
      review_ready_token_ids,
      csrf_token=csrf_token,
    )
    params = context.params
    state = context.state
    rows = context.rows
    total_count = context.total_count
    total_pages = context.total_pages
    current_page = context.current_page
    display_start = context.display_start
    display_end = context.display_end
    numeric_page_controls = context.numeric_page_controls
    error = context.error
    dashboard = context.dashboard
    cards = dashboard["cards"]
    dates = dashboard["dates"]
    database_info = dashboard["database"]
    amazon_setting = context.setting_views["amazon"]
    dmm_destination_profiles = context.dmm_destination_profiles
    pending_approvals = context.pending_approvals
    approved_approvals = context.approved_approvals
    wordpress_execution_states = context.wordpress_execution_states
    wordpress_schedule_states = context.wordpress_schedule_states
    wordpress_categories = context.wordpress_categories
    workflow_notice = context.notices["workflow"]
    review_ready_notice = context.notices["review_ready"]
    amazon_offer_notice = context.notices["amazon_offer"]
    catalog_edit_notice = context.notices["catalog_edit"]
    manual_store_offer_notice = context.notices["manual_store_offer"]
    supplement_cancel_notice = context.notices["supplement_cancel"]
    metadata_autofill_notice = context.notices["metadata_autofill"]
    dmm_offer_notice = context.notices["dmm_offer"]
    wordpress_draft_notice = context.notices["wordpress_draft"]
    wordpress_schedule_notice = context.notices["wordpress_schedule"]
    daily_summary_notice = context.notices["daily_summary"]
    daily_snapshot = context.daily_summary_snapshot
    daily_selections = context.daily_summary_selections
    daily_summary_error_code = context.daily_summary_error_code
    daily_return_to = daily_summary_return_url(
      raw_query, state.summary_date
    )
    wordpress_context_notice = (
      '<div class="workflow-notice workflow-notice-error">'
      f'{_escape(context.wordpress_context_error)}</div>'
      if context.wordpress_context_error
      else ""
    )

    row_html = ""

    for row in rows:
        excluded_text = "除外" if row["is_excluded"] else ""
        item_id = str(row.get("id") or "")
        selection_state = daily_selections.get(item_id)
        summary_checked = (
            "checked"
            if selection_state in {"AUTO_INCLUDED", "HUMAN_INCLUDED"}
            else ""
        )
        selection_labels = {
            "AUTO_INCLUDED": "自動選択",
            "HUMAN_INCLUDED": "人間が掲載",
            "HUMAN_EXCLUDED": "人間が除外",
        }
        if str(row.get("release_date") or "") == state.summary_date:
            summary_control = f"""
              <form method="post" action="/database-daily-summary-selection">
                <input type="hidden" name="csrf_token" value="{_escape(context.csrf_token)}">
                <input type="hidden" name="ebook_item_id" value="{_escape(item_id)}">
                <input type="hidden" name="summary_date" value="{_escape(state.summary_date)}">
                <input type="hidden" name="return_to" value="{_escape(daily_return_to)}">
                <input type="hidden" name="included" value="false">
                <label><input type="checkbox" name="included" value="true" {summary_checked} onchange="this.form.submit()">日次まとめに掲載</label>
                <small>まとめ状態: {_escape(selection_labels.get(selection_state, '対象外'))}</small>
              </form>
            """
        else:
            summary_control = '<span class="workflow-action-unavailable">対象日外</span>'

        row_html += f"""
        <tr>
          <td>{render_bulk_selection_checkbox(row)}</td>
          <td>{_escape(row["release_date"])}</td>
          <td>{_escape(row["title"])}</td>
          <td>{_escape(row["volume_label"])}</td>
          <td>{_escape(row["author_name"])}</td>
          <td>{_escape(row["publisher_name"])}</td>
          <td>{_escape(row["item_type"])}</td>
          <td>{_escape(row["store_names"])}</td>
          <td>{_escape(row["prices"])}</td>
          <td>{render_affiliate_readiness(row)}</td>
          <td>{render_status_badge(row["workflow_status"])}</td>
          <td>{render_status_badge(row["wordpress_status"])}</td>
          <td>{render_status_badge(row["x_status"])}</td>
          <td>{render_status_badge(row["review_status"])}</td>
          <td>{render_status_badge(row["affiliate_status"])}</td>
          <td>{render_status_badge(row["image_status"])}</td>
          <td>{render_ready_badge(row["publish_ready"])}</td>
          <td>{render_bulk_capabilities(row)}</td>
          <td>{summary_control}</td>
          <td>
            {render_workflow_action_form(
                row,
                raw_query,
                pending_approvals.get(str(row.get("id") or "")),
            )}
            <div style="margin-top:0.4rem;">
              {render_wordpress_draft_action_form(
                  row,
                  raw_query,
                  approved_approvals.get(str(row.get("id") or "")),
                  wordpress_execution_states.get(
                      str(row.get("id") or "")
                  ),
              )}
            </div>
            <div style="margin-top:0.4rem;">
              {render_wordpress_schedule_action_form(
                  row,
                  raw_query,
                  wordpress_execution_states.get(str(row.get("id") or "")),
                  wordpress_schedule_states.get(str(row.get("id") or "")),
                    wordpress_categories,
                    context.csrf_token,
              )}
            </div>
            <div style="margin-top:0.4rem;">
              {render_metadata_autofill_form(row, raw_query)}
            </div>
            <div id="catalog-edit-{_escape(row.get('id') or '')}" style="margin-top:0.4rem;">
              {render_catalog_edit_form(row, raw_query)}
            </div>
            <div style="margin-top:0.4rem;">
              {render_manual_store_offer_form(
                  row,
                  raw_query,
                  csrf_token=context.csrf_token,
              )}
            </div>
            <div style="margin-top:0.4rem;">
              {render_supplement_cancellation_action(
                  context.supplement_cancellation_previews.get(item_id),
                  raw_query,
                  csrf_token=context.csrf_token,
              )}
            </div>
            <div style="margin-top:0.4rem;">
              {render_amazon_manual_offer_form(
                  row,
                  raw_query,
                  configured=amazon_setting.configured and amazon_setting.enabled,
                  setting_source=amazon_setting.source,
              )}
            </div>
            <div style="margin-top:0.4rem;">
              {render_dmm_manual_offer_form(
                  row,
                  raw_query,
                  generation_available=(
                      any(
                          profile.configured and profile.active
                          for profile in dmm_destination_profiles.values()
                      )
                  ),
              )}
            </div>
          </td>
          <td>{_escape(excluded_text)}</td>
        </tr>
        """

    if not row_html:
        row_html = """
        <tr>
          <td colspan="21">該当するデータはありません。</td>
        </tr>
        """

    error_html = (
        f"<p class='error'>{_escape(error)}</p>"
        if error
        else ""
    )

    missing_price_checked = (
        "checked" if state.missing_price else ""
    )
    excluded_only_checked = (
        "checked" if state.excluded_only else ""
    )

    item_type_options = [
        ("", "すべて"),
        ("normal", "通常版"),
        ("single_episode", "単話"),
        ("split_edition", "分冊版"),
        ("single_or_split", "単話または分冊版"),
        ("unclassified", "未分類"),
    ]

    item_type_html = "".join(
        (
            f'<option value="{_escape(value)}" '
            f'{"selected" if state.item_type == value else ""}>'
            f'{_escape(label)}</option>'
        )
        for value, label in item_type_options
    )

    store_options = [
        ("", "すべて"),
        ("amazon", "Amazon"),
        ("rakuten_kobo", "楽天Kobo"),
        ("dmm", "DMM"),
        ("new_release_catalog", "新刊カタログ"),
    ]

    store_html = "".join(
        (
            f'<option value="{_escape(value)}" '
            f'{"selected" if state.store_name == value else ""}>'
            f'{_escape(label)}</option>'
        )
        for value, label in store_options
    )

    def filter_options(
        options: list[tuple[str, str]], selected_value: str
    ) -> str:
        return "".join(
            f'<option value="{_escape(value)}" '
            f'{"selected" if selected_value == value else ""}>'
            f'{_escape(label)}</option>'
            for value, label in options
        )

    affiliate_status_html = filter_options(
        [
            ("all", "すべて"),
            ("all_unregistered", "全媒体未登録"),
            ("partially_registered", "一部登録済み"),
            ("all_registered", "全媒体登録済み"),
        ],
        state.affiliate_status,
    )
    store_affiliate_options = [
        ("all", "すべて"),
        ("registered", "登録済み"),
        ("unregistered", "未登録"),
    ]
    amazon_affiliate_status_html = filter_options(
        store_affiliate_options, state.amazon_affiliate_status
    )
    rakuten_kobo_affiliate_status_html = filter_options(
        store_affiliate_options, state.rakuten_kobo_affiliate_status
    )
    dmm_affiliate_status_html = filter_options(
        store_affiliate_options, state.dmm_affiliate_status
    )

    if daily_snapshot is None:
      if daily_summary_error_code == "DAILY_SUMMARY_TABLE_MISSING":
        daily_summary_message = (
          "日次まとめ情報を読み込めませんでした。"
          "migration適用状態を確認してください。"
        )
      else:
        daily_summary_message = (
          "日次まとめ情報の読み込みに失敗しました。"
          f"error_code={daily_summary_error_code or 'DAILY_SUMMARY_CONTEXT_FAILED'}"
        )
      daily_summary_html = (
        f'<p class="error">{_escape(daily_summary_message)}</p>'
      )
    else:
      daily_summary_html = f"""
      <div class="summary-grid">
        <div class="summary-card"><span>対象件数</span><strong>{daily_snapshot.target_count}件</strong></div>
        <div class="summary-card"><span>掲載選択</span><strong>{daily_snapshot.selected_count}件</strong></div>
        <div class="summary-card"><span>公開済み</span><strong>{daily_snapshot.published_count}件</strong></div>
        <div class="summary-card"><span>3ストア完備</span><strong>{daily_snapshot.three_store_complete_count}件</strong></div>
        <div class="summary-card warning"><span>リンク不足</span><strong>{daily_snapshot.link_missing_count}件</strong></div>
        <div class="summary-card warning"><span>未公開</span><strong>{daily_snapshot.unpublished_count}件</strong></div>
        <div class="summary-card warning"><span>状態不整合</span><strong>{daily_snapshot.inconsistent_count}件</strong></div>
      </div>
      """
    return_to = daily_return_to
    bulk_forms = "".join(
      f"""<form method="post" action="/database-daily-summary-action" style="display:inline-block;margin:0.5rem 0.3rem 0 0;">
        <input type="hidden" name="csrf_token" value="{_escape(context.csrf_token)}">
        <input type="hidden" name="summary_date" value="{_escape(state.summary_date)}">
        <input type="hidden" name="return_to" value="{_escape(return_to)}">
        <input type="hidden" name="operation" value="{operation}">
        <button type="submit" class="workflow-action-button" {disabled}>{label}</button>
      </form>"""
      for operation, label, disabled in (
        ("auto_select", "対象を自動選択", ""),
        ("exclude_all", "選択をすべて解除", ""),
        ("reset_auto", "自動選択へ戻す", ""),
        ("preview", "プレビュー更新", ""),
        (
          "generate_dry_run",
          "日次まとめ下書きを生成（dry-run）",
          "" if daily_summary_preview and daily_summary_preview.generation_allowed else "disabled",
        )
      )
    )
    preview_html = ""
    if daily_summary_preview is not None:
      warning_html = "".join(
        f"<li>{_escape(warning)}</li>"
        for warning in daily_summary_preview.warnings
      )
      item_html = "".join(
        f"<li>{_escape(item.title)} / WP:{_escape(item.remote_status or item.wordpress_status)} / "
        f"3ストア:{'完備' if item.three_store_complete else '不足'}</li>"
        for item in daily_summary_preview.items
      )
      preview_html = f"""
        <h3>生成前プレビュー</h3>
        <p>対象日: {_escape(daily_summary_preview.summary_date)}</p>
        <p>選択作品数: {len(daily_summary_preview.items)}件</p>
        <p>タイトル: {_escape(daily_summary_preview.title)}</p>
        <p>slug: {_escape(daily_summary_preview.slug)}</p>
        <p>予定操作: {'既存下書き更新' if daily_summary_preview.action == 'update' else '新規下書き作成'}</p>
        <ul>{item_html}</ul><ul>{warning_html}</ul>
        <details><summary>生成予定HTML</summary><pre style="white-space:pre-wrap;">{_escape(daily_summary_preview.html)}</pre></details>
      """

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>電子書籍DB検索</title>
  <style>
    body {{
      font-family: sans-serif;
      margin: 1.2rem;
      background: #f7f7f7;
      color: #222;
    }}
    nav {{
      display: flex;
      gap: 0.8rem;
      margin-bottom: 1rem;
    }}
    nav a {{
      display: inline-block;
      padding: 0.55rem 0.9rem;
      border: 1px solid #bbb;
      border-radius: 6px;
      background: #fff;
      text-decoration: none;
      color: #222;
    }}
    .card {{
      background: #fff;
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 1rem;
      margin-bottom: 1rem;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 0.8rem;
    }}
    .summary-card {{
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
      padding: 1rem;
      border: 1px solid #d8dee9;
      border-radius: 8px;
      text-decoration: none;
      color: #222;
      background: #fff;
    }}
    .summary-card strong {{
      font-size: 1.55rem;
    }}
    .summary-card.release {{
      background: #f1f8f4;
      border-color: #b8dfc3;
    }}
    .summary-card.warning {{
      background: #fff5f2;
      border-color: #f0bbb0;
    }}
    .summary-card.muted {{
      background: #f4f5f7;
    }}
    .filters {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 0.8rem;
      align-items: end;
    }}
    label {{
      display: block;
      font-weight: 600;
    }}
    input, select {{
      box-sizing: border-box;
      width: 100%;
      margin-top: 0.25rem;
      padding: 0.5rem;
    }}
    button {{
      padding: 0.6rem 1rem;
    }}
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 0.55rem;
      text-align: left;
      white-space: nowrap;
    }}
    th {{
      background: #eee;
    }}
    .status-badge {{
      display: inline-block;
      min-width: 4.5rem;
      padding: 0.25rem 0.45rem;
      border: 1px solid #d0d5dd;
      border-radius: 999px;
      background: #f4f5f7;
      text-align: center;
      font-size: 0.78rem;
      font-weight: 700;
    }}
    .affiliate-readiness {{
      display: inline-flex;
      align-items: center;
      gap: 0.2rem;
      white-space: nowrap;
    }}
    .affiliate-service-badge {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-sizing: border-box;
      width: 1.45rem;
      height: 1.45rem;
      border: 1px solid transparent;
      border-radius: 0.3rem;
      font-size: 0.75rem;
      font-weight: 800;
      line-height: 1;
    }}
    .affiliate-service-amazon.is-ready {{
      border-color: #d97706;
      background: #f59e0b;
      color: #1f2937;
    }}
    .affiliate-service-rakuten-kobo.is-ready {{
      border-color: #991b1b;
      background: #bf0000;
      color: #fff;
    }}
    .affiliate-service-dmm.is-ready {{
      border-color: #075985;
      background: #0369a1;
      color: #fff;
    }}
    .affiliate-service-badge.is-missing {{
      border-color: #cbd5e1;
      background: #e5e7eb;
      color: #6b7280;
    }}
    .affiliate-ready-count {{
      margin-left: 0.15rem;
      color: #344054;
      font-size: 0.78rem;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }}
    .bulk-selection-panel {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.65rem 1rem;
      padding: 0.75rem;
      margin: 0.75rem 0;
      border: 1px solid #b8c2cc;
      background: #f7f9fb;
    }}
    .bulk-selection-panel h3 {{
      margin: 0;
      font-size: 1rem;
    }}
    .bulk-selection-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }}
    .bulk-selection-message {{
      flex-basis: 100%;
      min-height: 1.25rem;
      margin: 0;
      color: #8a3b00;
      font-weight: 700;
    }}
    .bulk-selection-result {{
      flex-basis: 100%;
      margin: 0;
      padding-left: 1.25rem;
    }}
    .bulk-capabilities {{
      display: grid;
      gap: 0.15rem;
      min-width: 7rem;
      font-size: 0.78rem;
      white-space: nowrap;
    }}
    .status-new,
    .status-not-created,
    .status-not-reviewed,
    .status-unchecked {{
      background: #f2f4f7;
      border-color: #d0d5dd;
    }}
    .status-review,
    .status-in-review {{
      background: #fff7e6;
      border-color: #f1c875;
    }}
    .status-ready,
    .status-approved,
    .status-published,
    .status-posted {{
      background: #edf8f0;
      border-color: #9fd5ad;
    }}
    .status-scheduled,
    .status-draft {{
      background: #eef4ff;
      border-color: #9ebcf3;
    }}
    .status-hold,
    .status-missing,
    .status-not-ready {{
      background: #fff4e5;
      border-color: #efc27b;
    }}
    .status-error,
    .status-rejected {{
      background: #fff0f0;
      border-color: #e4a1a1;
    }}
    .amazon-manual-offer {{
      min-width: 13rem;
      border: 1px solid #d8dee8;
      border-radius: 0.45rem;
      background: #fafbfc;
      padding: 0.35rem 0.5rem;
    }}

    .amazon-manual-offer summary {{
      cursor: pointer;
      font-weight: 700;
      color: #8a4b00;
    }}

    .amazon-manual-offer-form {{
      display: grid;
      gap: 0.45rem;
      margin-top: 0.55rem;
    }}

    .amazon-manual-offer-form label {{
      display: grid;
      gap: 0.2rem;
      font-size: 0.82rem;
      font-weight: 700;
    }}

    .amazon-manual-offer-form input,
    .amazon-manual-offer-form textarea {{
      width: 100%;
      box-sizing: border-box;
      padding: 0.45rem;
      border: 1px solid #aeb7c2;
      border-radius: 0.35rem;
      background: #ffffff;
    }}


    .workflow-action-form {{
      margin: 0;
      min-width: 7rem;
    }}
    .workflow-action-button {{
      border: 1px solid #8aa4d6;
      border-radius: 0.45rem;
      background: #eef4ff;
      padding: 0.4rem 0.6rem;
      cursor: pointer;
      font-size: 0.78rem;
      font-weight: 700;
      white-space: nowrap;
    }}
    .workflow-action-button:hover {{
      background: #dfeaff;
    }}
    .workflow-action-done {{
      color: #26743a;
      font-weight: 700;
    }}
    .workflow-action-unavailable {{
      color: #667085;
      font-size: 0.78rem;
    }}
    .metadata-autofill-panel {{
      min-width: 30rem;
      margin-top: 0.5rem;
      padding: 0.75rem;
      border: 1px solid #aeb7c2;
      border-radius: 0.45rem;
      background: #fff;
      white-space: normal;
    }}
    .metadata-autofill-panel h3 {{
      margin: 0 0 0.6rem;
      font-size: 1rem;
    }}
    .metadata-field {{
      margin: 0.45rem 0;
      padding: 0.55rem;
      border-left: 0.35rem solid #98a2b3;
      background: #f2f4f7;
    }}
    .metadata-field p {{
      margin: 0.2rem 0;
    }}
    .metadata-state-green {{ border-color: #398a50; background: #edf8f0; }}
    .metadata-state-yellow {{ border-color: #c48a13; background: #fff7e6; }}
    .metadata-state-orange {{ border-color: #d66b18; background: #fff4e5; }}
    .metadata-state-red {{ border-color: #c83b3b; background: #fff0f0; }}
    .metadata-state-gray {{ border-color: #98a2b3; background: #f2f4f7; }}
    .metadata-autofill-actions {{
      display: flex;
      gap: 0.5rem;
      margin-top: 0.7rem;
    }}
    .metadata-autofill-error {{
      color: #9f1c1c;
      font-weight: 700;
    }}
    .workflow-notice {{
      margin: 0 0 1rem;
      padding: 0.75rem 1rem;
      border: 1px solid;
      border-radius: 0.5rem;
      font-weight: 700;
    }}
    .workflow-notice-success {{
      border-color: #9fd5ad;
      background: #edf8f0;
      color: #206b35;
    }}
    .workflow-notice-error {{
      border-color: #e4a1a1;
      background: #fff0f0;
      color: #9f1c1c;
    }}
    .error {{
      color: #b00020;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <nav>
    <a href="/">CSV取込・事前検証</a>
    <a href="/database-search">SQLite検索</a>
    <a href="/supplement-import">不足作品補完</a>
    <a href="/affiliate-settings">アフィリエイト設定</a>
  </nav>

  <h1>電子書籍データベース検索</h1>
      {workflow_notice}
      {review_ready_notice}
      {wordpress_draft_notice}
      {wordpress_schedule_notice}
      {wordpress_context_notice}
      {daily_summary_notice}

      {amazon_offer_notice}
      {catalog_edit_notice}
      {manual_store_offer_notice}
      {supplement_cancel_notice}
      {metadata_autofill_notice}
      {dmm_offer_notice}
  {error_html}

  <section class="card">
    <h2>{_escape(state.summary_date)} 日次まとめ</h2>
    <form method="get" action="/database-search">
      <label>対象日<input type="date" name="summary_date" value="{_escape(state.summary_date)}"></label>
      <button type="submit">対象日を表示</button>
    </form>
    {daily_summary_html}
    {bulk_forms}
    {preview_html}
  </section>

  <section class="card">
    <h2>運用サマリー</h2>

    <div class="summary-grid">
      <a class="summary-card release" href="/database-search?release_date_from={_escape(dates['today'])}&release_date_to={_escape(dates['today'])}">
        <span>今日発売</span>
        <strong>{_escape(cards["today_release"])}件</strong>
      </a>

      <a class="summary-card release" href="/database-search?release_date_from={_escape(dates['tomorrow'])}&release_date_to={_escape(dates['tomorrow'])}">
        <span>明日発売</span>
        <strong>{_escape(cards["tomorrow_release"])}件</strong>
      </a>

      <a class="summary-card release" href="/database-search?release_date_from={_escape(dates['today'])}&release_date_to={_escape(dates['week_end'])}">
        <span>今週発売</span>
        <strong>{_escape(cards["this_week_release"])}件</strong>
      </a>

      <a class="summary-card release" href="/database-search?release_date_from={_escape(dates['month_start'])}&release_date_to={_escape(dates['month_end'])}">
        <span>今月発売</span>
        <strong>{_escape(cards["this_month_release"])}件</strong>
      </a>

      <a class="summary-card warning" href="/database-search?missing_price=true">
        <span>価格未取得</span>
        <strong>{_escape(cards["missing_price"])}件</strong>
      </a>

      <a class="summary-card warning" href="/database-search?affiliate_status=all_unregistered">
        <span>アフィリエイト未設定</span>
        <strong>{_escape(cards["missing_affiliate"])}件</strong>
      </a>

      <a class="summary-card muted" href="/database-search?excluded_only=true">
        <span>除外済み</span>
        <strong>{_escape(cards["excluded"])}件</strong>
      </a>
    </div>
  </section>

  <section class="card">
    <form method="get" action="/database-search">
      <input type="hidden" name="summary_date" value="{_escape(state.summary_date)}">
      <div class="filters">
        <label>
          検索文字
          <input
            type="text"
            name="keyword"
            value="{_escape(state.keyword)}"
          />
        </label>

        <label>
          発売日 From
          <input
            type="date"
            name="release_date_from"
            value="{_escape(state.release_date_from)}"
          />
        </label>

        <label>
          発売日 To
          <input
            type="date"
            name="release_date_to"
            value="{_escape(state.release_date_to)}"
          />
        </label>

        <label>
          作品種別
          <select name="item_type">
            {item_type_html}
          </select>
        </label>

        <label>
          ストア
          <select name="store_name">
            {store_html}
          </select>
        </label>

        <label>
          <input
            type="checkbox"
            name="missing_price"
            value="true"
            {missing_price_checked}
          />
          価格未取得だけ表示
        </label>

        <label>
          アフィリエイト登録状態
          <select name="affiliate_status">
            {affiliate_status_html}
          </select>
        </label>

        <label>
          Amazon
          <select name="amazon_affiliate_status">
            {amazon_affiliate_status_html}
          </select>
        </label>

        <label>
          楽天Kobo
          <select name="rakuten_kobo_affiliate_status">
            {rakuten_kobo_affiliate_status_html}
          </select>
        </label>

        <label>
          DMM
          <select name="dmm_affiliate_status">
            {dmm_affiliate_status_html}
          </select>
        </label>

        <label>
          <input
            type="checkbox"
            name="excluded_only"
            value="true"
            {excluded_only_checked}
          />
          除外済みだけ表示
        </label>

        <div>
          <button type="submit">検索</button>
          <a href="/database-search">条件を解除</a>
        </div>
      </div>
    </form>
  </section>

  <section class="card">
    <p>検索結果: 全{_escape(total_count)}件</p>
    <p>表示中: {_escape(display_start)}〜{_escape(display_end)}件</p>
    <p class="pagination">{numeric_page_controls}</p>

    <div
      id="database-bulk-selection"
      data-endpoint="/api/database-bulk-selection/validate"
      data-csrf-token="{_escape(context.csrf_token)}"
      data-max-count="5"
    >
      <div class="bulk-selection-panel">
        <h3>一括処理対象</h3>
        <strong>選択件数: <span data-bulk-selection-count>0 / 5件</span></strong>
        <span>最大5件</span>
        <span>選択は現在のページ内だけ有効です</span>
        <div class="bulk-selection-actions">
          <button type="button" data-bulk-select-visible>表示中を選択</button>
          <button type="button" data-bulk-clear-selection>選択解除</button>
          <button type="button" data-bulk-validate-selection>選択内容を確認</button>
          <button type="button" data-bulk-affiliate-prepare disabled>アフィリエイト一括登録</button>
          <button type="button" data-bulk-wordpress-draft-prepare disabled>WordPress下書き一括作成</button>
        </div>
        <p class="bulk-selection-message" data-bulk-selection-message role="status" aria-live="polite"></p>
        <ul class="bulk-selection-result" data-bulk-selection-result aria-live="polite"></ul>
      </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>選択</th>
            <th>発売日</th>
            <th>タイトル</th>
            <th>巻</th>
            <th>作者</th>
            <th>出版社</th>
            <th>種別</th>
            <th>ストア</th>
            <th>価格</th>
            <th>アフィリエイト登録</th>
            <th>Workflow</th>
            <th>WordPress</th>
            <th>X</th>
            <th>Review</th>
            <th>Affiliate</th>
            <th>Image</th>
            <th>Publish Ready</th>
            <th>一括処理可否</th>
            <th>日次まとめ</th>
            <th>操作</th>
            <th>除外</th>
          </tr>
        </thead>
        <tbody>
          {row_html}
        </tbody>
      </table>
    </div>
    </div>
  </section>

  <section class="card">
    <h2>データベース情報</h2>
    <p>
      総アイテム数: {_escape(database_info["total_items"])}件 /
      ストア数: {_escape(database_info["store_count"])}件 /
      最終更新: {_escape(database_info["latest_import_at"] or "-")}
    </p>
  </section>
  <script src="/assets/ebook-metadata-autofill.js" defer></script>
  <script src="/assets/ebook-bulk-selection.js" defer></script>
</body>
</html>
"""


def render_bulk_affiliate_page(
    *,
    selection_token: str,
    csrf_token: str,
    items: list[Any],
    return_to: str,
) -> str:
    from app.services.ebook_bulk_affiliate_registration_service import (
        SUPPORTED_STORES,
        offer_state_hash,
    )

    store_labels = {
        "amazon": ("Amazon", "ASIN"),
        "rakuten_kobo": ("楽天Kobo", "item_code / product_id"),
        "dmm": ("DMMブックス", "content_id"),
    }
    item_sections: list[str] = []
    for item in items:
        store_sections: list[str] = []
        for store_name in SUPPORTED_STORES:
            offers = [
                offer for offer in item.offers
                if offer.store_name == store_name
            ]
            offer = offers[0] if len(offers) == 1 else None
            label, identifier_label = store_labels[store_name]
            prefix = f"offer__{item.id}__{store_name}__"
            state = (
                "競合（複数登録）" if len(offers) > 1 else
                "登録済み" if offer and offer.affiliate_url else
                "未登録"
            )
            store_sections.append(f"""
              <fieldset class="bulk-affiliate-store">
                <legend>{_escape(label)} <small>{_escape(state)}</small></legend>
                <input type="hidden" name="{_escape(prefix)}expected_hash" value="{_escape(offer_state_hash(offers))}">
                <label>{_escape(identifier_label)}
                  <input name="{_escape(prefix)}store_item_id" maxlength="255" value="{_escape(offer.store_item_id if offer else '')}">
                </label>
                <label>product_url
                  <input type="url" name="{_escape(prefix)}product_url" maxlength="2048" value="{_escape(offer.product_url if offer else '')}">
                </label>
                <label>affiliate_url
                  <input type="url" name="{_escape(prefix)}affiliate_url" maxlength="2048" value="{_escape(offer.affiliate_url if offer else '')}">
                </label>
                <label>価格（円）
                  <input inputmode="numeric" name="{_escape(prefix)}price" value="{_escape(offer.price_yen if offer and offer.price_yen is not None else '')}">
                </label>
                <label>image_url（確認のみ・StoreOfferには保存しません）
                  <input type="url" name="{_escape(prefix)}image_url" maxlength="2048" value="">
                </label>
                <label><input type="checkbox" name="{_escape(prefix)}overwrite" value="true"> 既存登録情報を更新する</label>
              </fieldset>
            """)
        item_sections.append(f"""
          <section class="bulk-affiliate-item">
            <h2>{_escape(item.title)} {_escape(item.volume_label or '')}</h2>
            <p>作品ID: {_escape(item.id)}</p>
            <div class="bulk-affiliate-stores">{''.join(store_sections)}</div>
          </section>
        """)
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>アフィリエイト一括登録確認</title>
  <style>
    body {{ font-family: sans-serif; margin: 1.2rem; color:#222; background:#f7f7f7; }}
    .bulk-affiliate-item {{ background:#fff; border:1px solid #ccc; padding:1rem; margin:1rem 0; }}
    .bulk-affiliate-stores {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:0.8rem; }}
    .bulk-affiliate-store {{ min-width:0; }}
    label {{ display:block; margin:0.5rem 0; }}
    input[type=url], input[type=text], input[inputmode=numeric], input:not([type]) {{ box-sizing:border-box; width:100%; }}
    .error {{ color:#b00020; }}
    .success {{ color:#176b35; }}
  </style>
</head>
<body>
  <nav><a href="{_escape(return_to)}">検索一覧へ戻る</a></nav>
  <h1>アフィリエイト一括登録確認</h1>
  <p>対象作品: {_escape(len(items))}件 / dry-run後に本登録できます。</p>
  <form id="bulk-affiliate-form" method="post" action="/database-bulk-affiliate/apply"
        data-dry-run-endpoint="/api/database-bulk-affiliate/dry-run">
    <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
    <input type="hidden" name="selection_token" value="{_escape(selection_token)}">
    <input type="hidden" name="dry_run_input_hash" value="">
    {''.join(item_sections)}
    <section>
      <button type="button" data-bulk-affiliate-dry-run>dry-run</button>
      <label><input type="checkbox" name="operation_confirmation" value="true" data-bulk-affiliate-confirmation disabled> 内容を確認して本登録する</label>
      <button type="submit" data-bulk-affiliate-apply disabled>本登録</button>
      <p data-bulk-affiliate-message role="status" aria-live="polite"></p>
      <div data-bulk-affiliate-result></div>
    </section>
  </form>
  <script src="/assets/ebook-bulk-affiliate.js" defer></script>
</body>
</html>"""


def render_bulk_affiliate_result_page(
    *, result: dict[str, Any], return_to: str
) -> str:
    items = "".join(
        "<li>" + _escape(item.get("title", "")) + " "
        + _escape(item.get("volume_label", "")) + ": "
        + ", ".join(
            f"{_escape(store)}={_escape(details.get('operation', 'NONE'))}"
            for store, details in item.get("stores", {}).items()
        ) + "</li>"
        for item in result.get("items", [])
    )
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>アフィリエイト一括登録完了</title></head><body>
<h1>アフィリエイト一括登録完了</h1>
<p>対象作品: {_escape(result.get('selected_count', 0))}件 / 新規登録: {_escape(result.get('create_count', 0))}媒体 / 更新: {_escape(result.get('update_count', 0))}媒体 / 変更なし: {_escape(result.get('unchanged_count', 0))}媒体 / 失敗: 0件</p>
<ul>{items}</ul><a href="{_escape(return_to)}">検索一覧へ戻る</a>
</body></html>"""


def render_bulk_wordpress_draft_page(
  *,
  selection_token: str,
  csrf_token: str,
  items: list[Any],
  return_to: str,
  apply_limit: int,
) -> str:
  item_rows = "".join(
    "<li>" + _escape(item.title) + " "
    + _escape(item.volume_label or "") + "</li>"
    for item in items
  )
  return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WordPress下書き一括作成確認</title>
<style>
body {{ font-family:sans-serif; margin:1.2rem; color:#222; background:#f7f7f7; }}
.summary {{ background:#fff; border:1px solid #ccc; padding:1rem; margin:1rem 0; }}
table {{ width:100%; border-collapse:collapse; background:#fff; }}
th,td {{ border:1px solid #ccc; padding:.5rem; text-align:left; vertical-align:top; }}
.error {{ color:#b00020; }} .success {{ color:#176b35; }}
</style></head><body>
<nav><a href="{_escape(return_to)}">検索一覧へ戻る</a></nav>
<h1>WordPress下書き一括作成確認</h1>
<section class="summary">
<p>選択件数: {_escape(len(items))}件</p>
<p>現在の本番作成上限: <strong>{_escape(apply_limit)}件</strong></p>
<p>WordPressへ送信するstatusはdraftに固定されます。</p>
<ol>{item_rows}</ol>
</section>
<form id="bulk-wordpress-draft-form" method="post"
 action="/database-bulk-wordpress-draft/apply"
 data-dry-run-endpoint="/api/database-bulk-wordpress-draft/dry-run">
<input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
<input type="hidden" name="selection_token" value="{_escape(selection_token)}">
<input type="hidden" name="dry_run_input_hash" value="">
<input type="hidden" name="dry_run_content_hashes" value="">
<button type="button" data-bulk-wordpress-draft-dry-run>dry-run</button>
<label><input type="checkbox" name="human_confirmation" value="true"
 data-bulk-wordpress-draft-confirmation disabled>
選択した作品をWordPressの下書きとして作成します</label>
<button type="submit" data-bulk-wordpress-draft-apply disabled>下書きを作成</button>
<p data-bulk-wordpress-draft-message role="status" aria-live="polite"></p>
<div data-bulk-wordpress-draft-result></div>
</form>
<script src="/assets/ebook-bulk-wordpress-draft.js" defer></script>
</body></html>"""


def render_bulk_wordpress_draft_result_page(
  *, result: dict[str, Any], return_to: str
) -> str:
  rows = "".join(
    "<tr><td>" + _escape(item.get("title", "")) + "</td><td>"
    + _escape(item.get("volume_label", "")) + "</td><td>"
    + _escape(item.get("wordpress_post_id") or "-") + "</td><td>"
    + _escape(item.get("remote_status") or "-") + "</td><td>"
    + _escape(item.get("local_status") or "-") + "</td><td>"
    + _escape(item.get("result_code") or "-") + "</td><td>"
    + ("要" if item.get("management_review_required") else "不要")
    + "</td></tr>"
    for item in result.get("items", [])
  )
  return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WordPress下書き一括作成結果</title></head><body>
<h1>WordPress下書き一括作成結果</h1>
<p>選択: {_escape(result.get('selected_count', 0))}件 / 作成: {_escape(result.get('created_count', 0))}件 / 同期成功: {_escape(result.get('synced_count', 0))}件 / 失敗: {_escape(result.get('failed_count', 0))}件 / 未実行: {_escape(result.get('not_executed_count', 0))}件</p>
<table><thead><tr><th>作品名</th><th>巻数</th><th>post_id</th><th>remote</th><th>local</th><th>結果</th><th>管理確認</th></tr></thead><tbody>{rows}</tbody></table>
<p><a href="{_escape(return_to)}">検索一覧へ戻る</a></p>
</body></html>"""


def render_affiliate_settings_page(raw_query: str = "") -> str:
    params = parse_qs(raw_query, keep_blank_values=True)
    notice = render_named_notice(
        params,
        "affiliate_settings_result",
        AFFILIATE_SETTING_NOTICES,
    )
    settings = load_affiliate_setting_views()
    dmm_profiles = load_dmm_destination_profile_views()
    token = get_workflow_action_token()

    def setting_form(service_name: str, label: str, template: bool = False) -> str:
        setting = settings[service_name]
        template_html = (
            """
            <label>DMMアフィリエイトURLテンプレート（任意）
              <input name="url_template" maxlength="2000" placeholder="https://...{affiliate_id}...{product_url}...">
            </label>
            """
            if template
            else ""
        )
        return f"""
        <section class="card">
          <h2>{_escape(label)}</h2>
          <p>現在値: <code>{_escape(setting.masked_affiliate_id)}</code></p>
          <p>優先元: <strong>{_escape(setting.source)}</strong> / 有効: {_escape(setting.enabled)}</p>
          <form method="post" action="/affiliate-settings" class="settings-form">
            <input type="hidden" name="csrf_token" value="{_escape(token)}">
            <input type="hidden" name="service_name" value="{_escape(service_name)}">
            <input type="hidden" name="operation" value="save">
            <label>{_escape(label)} ID（空欄は既存値を維持）
              <input name="affiliate_id" maxlength="255" autocomplete="off">
            </label>
            {template_html}
            <label><input type="checkbox" name="enabled" value="true" {'checked' if setting.enabled else ''}> 有効</label>
            <button type="submit">保存</button>
          </form>
          <form method="post" action="/affiliate-settings" onsubmit="return confirm('この設定値を明示的に削除しますか？');">
            <input type="hidden" name="csrf_token" value="{_escape(token)}">
            <input type="hidden" name="service_name" value="{_escape(service_name)}">
            <input type="hidden" name="operation" value="delete">
            <button type="submit">明示的に削除</button>
          </form>
        </section>
        """

    def destination_form(destination_key: str) -> str:
        profile = dmm_profiles[destination_key]
        return f"""
        <section class="card">
          <h3>{_escape(profile.display_name)}</h3>
          <p>用途: <code>{_escape(profile.destination_type)}</code> /
             destination_key: <code>{_escape(profile.destination_key)}</code></p>
          <p>現在値: <code>{_escape(profile.masked_affiliate_id)}</code> /
             有効: {_escape(profile.active)}</p>
          <form method="post" action="/affiliate-settings" class="settings-form">
            <input type="hidden" name="csrf_token" value="{_escape(token)}">
            <input type="hidden" name="operation" value="save_destination_profile">
            <input type="hidden" name="provider" value="dmm">
            <input type="hidden" name="destination_key" value="{_escape(profile.destination_key)}">
            <input type="hidden" name="destination_type" value="{_escape(profile.destination_type)}">
            <label>affiliate ID（空欄は既存値を維持）
              <input name="affiliate_id" maxlength="255" autocomplete="off">
            </label>
            <label>channel
              <input name="channel" maxlength="64" value="{_escape(profile.channel)}">
            </label>
            <label>channel_id
              <input name="channel_id" maxlength="64" value="{_escape(profile.channel_id)}">
            </label>
            <label><input type="checkbox" name="is_active" value="true" {'checked' if profile.active or not profile.configured else ''}> 有効</label>
            <button type="submit">掲載先設定を保存</button>
          </form>
        </section>
        """

    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>アフィリエイト設定</title>
<style>
body{{font-family:sans-serif;margin:1.2rem;background:#f7f7f7;color:#222}}nav{{display:flex;gap:.8rem;margin-bottom:1rem}}nav a{{padding:.55rem .9rem;border:1px solid #bbb;border-radius:6px;background:#fff;color:#222;text-decoration:none}}.card{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:1rem;margin-bottom:1rem}}label{{display:block;margin:.7rem 0}}input[type=text],input:not([type]){{width:min(100%,48rem);padding:.45rem}}button{{padding:.45rem .8rem;margin:.25rem 0}}.workflow-notice{{padding:.75rem 1rem;border-radius:.5rem;margin-bottom:1rem}}.workflow-notice-success{{background:#edf8f0;color:#206b35}}.workflow-notice-error{{background:#fff0f0;color:#9f1c1c}}
</style></head><body>
<nav><a href="/">CSV取込・事前検証</a><a href="/database-search">SQLite検索</a><a href="/supplement-import">不足作品補完</a><a href="/affiliate-settings">アフィリエイト設定</a></nav>
<h1>アフィリエイト設定</h1>
<p>Amazonは環境変数がDB保存値より優先されます。Access Key / Secret Keyは保存しません。</p>
{notice}
{setting_form('amazon', 'Amazonトラッキング')}
<section class="card">
  <h2>DMM掲載先別設定</h2>
  <p>ブログ用とX用は独立しています。未設定の掲載先を別IDで代替しません。</p>
</section>
{destination_form('blog_main')}
{destination_form('x_main')}
</body></html>"""


def render_supplement_import_page(
    raw_query: str = "",
    *,
    csrf_token: str,
    import_run: Any | None = None,
    candidates: tuple[Any, ...] = (),
) -> str:
    params = parse_qs(raw_query, keep_blank_values=True)
    target_date = (params.get("target_date") or [""])[0]
    result_code = (params.get("supplement_result") or [""])[0]
    notices = {
        "parsed": "解析結果を保存しました。DB作品は更新していません。",
        "parse_reused": "同一入力の解析結果を再表示しました。",
        "candidate_updated": "候補の編集内容を保存し、重複判定を更新しました。",
        "selection_updated": "候補の選択状態を保存しました。",
        "imported": "選択した新規候補を補完登録しました。",
        "already_imported": "同じ登録操作は完了済みです。重複登録していません。",
        "SUPPLEMENT_REGISTRATION_CANCELLED": "補完登録を取り消しました。元の候補を編集して再登録できます。",
        "manual_review": "手動候補は重複の可能性があるため登録せず表示しました。",
        "empty_text": "貼り付け内容が空です。",
        "invalid_date": "対象発売日が未指定または不正です。",
        "no_items": "解析できる作品が0件です。",
        "title_missing": "タイトルは必須です。",
        "exact_duplicate": "EXACT_DUPLICATEの候補は登録できません。",
        "possible_duplicate": "POSSIBLE_DUPLICATEは確認が必要なため登録しません。",
        "no_selection": "登録する候補を選択してください。",
        "db_error": "DB登録に失敗しました。変更はすべて取り消しました。",
        "csrf_error": "CSRF検証に失敗しました。",
    }
    notice = notices.get(result_code, "")
    notice_class = (
        "notice success"
        if result_code in {
            "parsed",
            "parse_reused",
            "candidate_updated",
            "selection_updated",
            "imported",
            "already_imported",
        }
        else "notice error"
    )
    notice_html = (
        f'<p class="{notice_class}">{_escape(notice)}</p>' if notice else ""
    )

    candidate_rows: list[str] = []
    for candidate in candidates:
        selectable = (
            candidate.match_status == "NEW_CANDIDATE"
            and candidate.import_status != "IMPORTED"
        )
        checked = "checked" if candidate.selected else ""
        disabled = "" if selectable else "disabled"
        warnings = ", ".join(
          str(value)
          for value in json.loads(candidate.parser_warnings or "[]")
        )
        candidate_rows.append(
            f"""
            <article class="candidate" id="candidate-{_escape(candidate.id)}">
              <div class="candidate-summary">
                <form method="post" action="/supplement-candidate-selection">
                  <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
                  <input type="hidden" name="candidate_id" value="{_escape(candidate.id)}">
                  <input type="hidden" name="import_run_id" value="{_escape(candidate.import_run_id)}">
                  <input type="hidden" name="target_date" value="{_escape(target_date)}">
                  <label><input type="checkbox" name="selected" value="true" {checked} {disabled} onchange="this.form.submit()"> 選択</label>
                </form>
                <h3>{_escape(candidate.title)}</h3>
                <dl>
                  <dt>巻数</dt><dd>{_escape(candidate.volume_label or '-')}</dd>
                  <dt>発売日</dt><dd>{_escape(candidate.release_date)}</dd>
                  <dt>出版社</dt><dd>{_escape(candidate.publisher_name or '-')}</dd>
                  <dt>著者</dt><dd>{_escape(candidate.author_name or '-')}</dd>
                  <dt>レーベル／シリーズ</dt><dd>{_escape(candidate.imprint_name or '-')}</dd>
                  <dt>解析信頼度</dt><dd>{_escape(candidate.parser_confidence)}</dd>
                  <dt>DB照合</dt><dd><strong>{_escape(candidate.match_status)}</strong></dd>
                  <dt>警告</dt><dd>{_escape(warnings or '-')}</dd>
                </dl>
              </div>
              <details>
                <summary>編集</summary>
                <form method="post" action="/supplement-candidate-edit" class="edit-grid">
                  <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
                  <input type="hidden" name="candidate_id" value="{_escape(candidate.id)}">
                  <input type="hidden" name="import_run_id" value="{_escape(candidate.import_run_id)}">
                  <input type="hidden" name="target_date" value="{_escape(target_date)}">
                  <label>タイトル<input name="title" required maxlength="500" value="{_escape(candidate.title)}"></label>
                  <label>巻数<input name="volume_label" maxlength="100" value="{_escape(candidate.volume_label)}"></label>
                  <label>発売日<input type="date" name="release_date" required value="{_escape(candidate.release_date)}"></label>
                  <label>出版社<input name="publisher_name" maxlength="255" value="{_escape(candidate.publisher_name)}"></label>
                  <label>著者<input name="author_name" maxlength="255" value="{_escape(candidate.author_name)}"></label>
                  <label>レーベル<input name="imprint_name" maxlength="255" value="{_escape(candidate.imprint_name)}"></label>
                  <button type="submit">編集内容を保存</button>
                </form>
              </details>
            </article>
            """
        )

    results_html = "<p>解析候補はありません。</p>"
    import_form = ""
    if import_run is not None:
        results_html = "".join(candidate_rows) or "<p>解析候補は0件です。</p>"
        import_form = f"""
        <form method="post" action="/supplement-import-selected">
          <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
          <input type="hidden" name="import_run_id" value="{_escape(import_run.id)}">
          <input type="hidden" name="target_date" value="{_escape(target_date)}">
          <button type="submit">選択作品を補完登録</button>
        </form>
        """

    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>不足作品補完</title>
<style>
body{{font-family:sans-serif;margin:1.2rem;background:#f7f7f7;color:#222}}nav{{display:flex;gap:.8rem;flex-wrap:wrap;margin-bottom:1rem}}nav a{{padding:.55rem .9rem;border:1px solid #bbb;border-radius:6px;background:#fff;color:#222;text-decoration:none}}.card,.candidate{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:1rem;margin-bottom:1rem}}label{{display:block;margin:.65rem 0}}input,textarea{{box-sizing:border-box;width:min(100%,48rem);padding:.5rem}}input[type=checkbox]{{width:auto}}textarea{{min-height:16rem;font-family:monospace}}button{{padding:.55rem .9rem}}.actions{{display:flex;gap:.6rem;align-items:center}}.notice{{padding:.75rem 1rem;border-radius:6px;font-weight:700}}.success{{background:#edf8f0;color:#206b35}}.error{{background:#fff0f0;color:#9f1c1c}}dl{{display:grid;grid-template-columns:max-content 1fr;gap:.3rem .8rem}}dt{{font-weight:700}}dd{{margin:0}}.edit-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.5rem 1rem}}.edit-grid button{{align-self:end}}h1,h2,h3{{letter-spacing:0}}
</style></head><body>
<nav><a href="/">CSV取込・事前検証</a><a href="/database-search">SQLite検索</a><a href="/supplement-import">不足作品補完</a><a href="/affiliate-settings">アフィリエイト設定</a></nav>
<h1>不足作品補完</h1>
{notice_html}
<section class="card">
  <h2>楽天ブックス コミック新刊カレンダー</h2>
  <p><a href="https://books.rakuten.co.jp/event/book/comic/calendar/" target="_blank" rel="noopener noreferrer">情報源を新しいタブで開く</a></p>
  <form method="post" action="/supplement-parse">
    <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
    <label>対象発売日<input type="date" name="target_date" required value="{_escape(target_date)}"></label>
    <label>一覧テキスト<textarea name="raw_text" required></textarea></label>
    <div class="actions"><button type="submit">解析して差分候補を表示</button><a href="/supplement-import">入力をクリア</a></div>
  </form>
</section>
<section class="card"><h2>解析結果一覧</h2>{results_html}{import_form}</section>
<section class="card">
  <h2>1件手動追加</h2>
  <form method="post" action="/supplement-manual-add" class="edit-grid">
    <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
    <label>タイトル<input name="title" required maxlength="500"></label>
    <label>巻数<input name="volume_label" maxlength="100"></label>
    <label>発売日<input type="date" name="release_date" required value="{_escape(target_date)}"></label>
    <label>出版社<input name="publisher_name" maxlength="255"></label>
    <label>著者<input name="author_name" maxlength="255"></label>
    <label>レーベル<input name="imprint_name" maxlength="255"></label>
    <label>情報源URL<input type="url" name="source_url" readonly value="https://books.rakuten.co.jp/event/book/comic/calendar/"></label>
    <button type="submit">1件手動追加</button>
  </form>
</section>
</body></html>"""
