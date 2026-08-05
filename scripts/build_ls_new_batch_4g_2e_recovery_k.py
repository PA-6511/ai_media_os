#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_article_"
    "one_shot_offline_generation_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "one_shot_offline_generation_execute_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
CONSUMPTION_PATH = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_consumption.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_article_"
    "one_shot_offline_generation_result_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_k_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_k_"
    "one_shot_offline_generation_report.md"
)


class ValidationError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def json_bytes(
    value: dict[str, Any],
) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.exists(),
        f"required file missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON: {path}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_bytes(
        json_bytes(value)
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def write_text(
    path: Path,
    value: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    temporary.write_text(
        value,
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def stage_bytes(
    path: Path,
    value: bytes,
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        path.name
        + f".tmp.{os.getpid()}"
    )

    if temporary.exists():
        temporary.unlink()

    with temporary.open("xb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())

    os.chmod(temporary, 0o600)
    return temporary


def resolve_path(value: str) -> Path:
    path = Path(value)

    return (
        path
        if path.is_absolute()
        else ROOT / path
    )


def display_path(path: Path) -> str:
    return str(
        path.resolve().relative_to(
            ROOT.resolve()
        )
    )


def verify_self_digest(
    value: dict[str, Any],
    digest_field: str,
    label: str,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        digest_field,
        None,
    )

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
        f"{label} digest invalid",
    )

    return stored


def terminal_state() -> int | None:
    output_exists = OUTPUT_PATH.exists()
    consumption_exists = CONSUMPTION_PATH.exists()

    if not output_exists and not consumption_exists:
        return None

    if output_exists and consumption_exists:
        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K"
            ),
            "status": (
                "BLOCKED_ONE_SHOT_AUTHORIZATION_"
                "ALREADY_CONSUMED"
            ),
            "content_output_exists": True,
            "consumption_evidence_exists": True,
            "authorization_reuse_allowed": False,
            "second_generation_allowed": False,
            "production_status": "NO_GO"
        }

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 3

    result = {
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-K"
        ),
        "status": (
            "FAIL_CLOSED_PARTIAL_ONE_SHOT_STATE"
        ),
        "content_output_exists": output_exists,
        "consumption_evidence_exists": (
            consumption_exists
        ),
        "automatic_repair_allowed": False,
        "authorization_reuse_allowed": False,
        "production_status": "NO_GO"
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )
    return 4


def validate_policy(
    policy: dict[str, Any],
) -> list[str]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K",
        "policy phase mismatch",
    )
    require(
        policy.get("operation_mode")
        == (
            "EXPLICITLY_APPROVED_ONE_SHOT_OFFLINE_"
            "ARTICLE_CONTENT_GENERATION"
        ),
        "operation mode mismatch",
    )

    output = policy[
        "output_contract"
    ]

    require(
        output["one_shot_creation_allowed"]
        is True,
        "one-shot creation not allowed",
    )
    require(
        output["overwrite_allowed"]
        is False,
        "output overwrite must be forbidden",
    )
    require(
        output["second_creation_allowed"]
        is False,
        "second creation must be forbidden",
    )

    consumption = policy[
        "authorization_consumption_contract"
    ]

    require(
        consumption[
            "source_authorization_modification_allowed"
        ]
        is False,
        "source authorization modification must be false",
    )
    require(
        consumption[
            "consumption_evidence_is_authoritative"
        ]
        is True,
        "consumption evidence must be authoritative",
    )
    require(
        consumption["single_use"] is True,
        "authorization must be single use",
    )
    require(
        consumption[
            "authorization_reuse_allowed"
        ]
        is False,
        "authorization reuse must be false",
    )

    navigation = policy[
        "fixed_render"
    ]["store_navigation"]

    require(
        navigation["render_mode"]
        == "RESERVED_NON_CLICKABLE_SLOTS_ONLY",
        "store render mode mismatch",
    )

    for field in [
        "anchor_element_allowed",
        "href_attribute_allowed",
        "verification_source_url_rendering_allowed",
        "final_affiliate_url_rendering_allowed",
        "dmm_url_rendering_allowed",
    ]:
        require(
            navigation[field] is False,
            f"{field} must remain false",
        )

    boundary = policy[
        "phase_boundary"
    ]

    for field in [
        "article_content_generation_allowed",
        "content_output_creation_allowed",
        "authorization_consumption_evidence_creation_allowed",
    ]:
        require(
            boundary[field] is True,
            f"{field} must be true",
        )

    for field in [
        "source_authorization_modification_allowed",
        "fresh_payload_creation_allowed",
        "payload_binding_allowed",
        "categories_field_creation_allowed",
        "production_category_id_payload_injection_allowed",
        "credential_file_read_allowed",
        "dns_resolution_allowed",
        "network_connection_allowed",
        "http_request_allowed",
        "wordpress_api_call_allowed",
        "wordpress_write_allowed",
        "wordpress_draft_creation_allowed",
        "wordpress_publish_allowed",
    ]:
        require(
            boundary[field] is False,
            f"{field} must remain false",
        )

    return [
        "policy_phase_verified",
        "operation_mode_verified",
        "one_shot_output_contract_verified",
        "output_overwrite_forbidden",
        "authorization_consumption_contract_verified",
        "source_authorization_modification_forbidden",
        "non_clickable_store_slots_verified",
        "store_url_rendering_blocked",
        "payload_and_wordpress_boundary_closed",
    ]


def validate_request_and_sources(
    request: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    list[str],
]:
    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K",
        "request phase mismatch",
    )
    require(
        request.get("operation_mode")
        == policy["operation_mode"],
        "request operation mode mismatch",
    )

    for field in [
        "one_shot_article_generation_requested",
        "content_output_creation_requested",
        "authorization_consumption_requested",
        "independent_consumption_evidence_creation_requested",
        "fixed_disclosure_requested",
        "current_cover_requested",
        "information_card_requested",
        "non_clickable_store_slots_only_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "source_authorization_modification_requested",
        "verification_source_url_output_requested",
        "final_affiliate_url_output_requested",
        "dmm_url_output_requested",
        "synopsis_generation_requested",
        "story_detail_generation_requested",
        "discount_generation_requested",
        "point_return_generation_requested",
        "campaign_generation_requested",
        "inventory_generation_requested",
        "fresh_payload_creation_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
        "credential_file_read_requested",
        "network_connection_requested",
        "http_request_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "wordpress_draft_creation_requested",
        "wordpress_publish_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    bindings = request[
        "source_bindings"
    ]

    preflight_result_path = resolve_path(
        bindings[
            "preflight_result_path"
        ]
    )
    preflight_plan_path = resolve_path(
        bindings[
            "preflight_plan_path"
        ]
    )
    authorization_path = resolve_path(
        bindings[
            "authorization_path"
        ]
    )

    preflight_result = load_json(
        preflight_result_path
    )
    preflight_plan = load_json(
        preflight_plan_path
    )
    authorization = load_json(
        authorization_path
    )

    require(
        file_sha256(preflight_result_path)
        == bindings[
            "preflight_result_file_sha256"
        ],
        "preflight result file changed",
    )
    require(
        file_sha256(preflight_plan_path)
        == bindings[
            "preflight_plan_file_sha256"
        ],
        "preflight plan file changed",
    )
    require(
        file_sha256(authorization_path)
        == bindings[
            "authorization_file_sha256"
        ],
        "authorization file changed",
    )

    plan_digest = verify_self_digest(
        preflight_plan,
        "preflight_plan_digest_sha256",
        "preflight plan",
    )
    authorization_digest = verify_self_digest(
        authorization,
        "authorization_digest_sha256",
        "authorization",
    )

    require(
        plan_digest
        == bindings[
            "preflight_plan_artifact_digest_sha256"
        ],
        "preflight plan digest reference mismatch",
    )
    require(
        authorization_digest
        == bindings[
            "authorization_artifact_digest_sha256"
        ],
        "authorization digest reference mismatch",
    )

    require(
        preflight_result.get("status")
        == (
            "PASS_FRESH_ARTICLE_ONE_SHOT_OFFLINE_"
            "GENERATION_PREFLIGHT_NO_CONTENT_"
            "NO_AUTH_CONSUMPTION_NO_NETWORK"
        ),
        "preflight status mismatch",
    )
    require(
        preflight_result.get(
            "ready_for_recovery_k_execute_now_confirmation"
        )
        is True,
        "preflight not ready for execute confirmation",
    )
    require(
        preflight_plan.get("preflight_id")
        == (
            "DARK_GATHERING_VOLUME_20_"
            "OFFLINE_GENERATION_PREFLIGHT_V1"
        ),
        "preflight ID mismatch",
    )
    require(
        preflight_plan[
            "template"
        ]["template_artifact_resolved"]
        is True,
        "template artifact unresolved",
    )
    require(
        authorization.get("authorization_id")
        == (
            "DARK_GATHERING_VOLUME_20_"
            "OFFLINE_CONTENT_GENERATION_AUTHORIZATION_V1"
        ),
        "authorization ID mismatch",
    )
    require(
        authorization.get("single_use")
        is True,
        "authorization not single use",
    )
    require(
        authorization.get("authorization_consumed")
        is False,
        "source authorization already consumed",
    )
    require(
        authorization.get("authorized_next_phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-K",
        "authorization phase mismatch",
    )

    approval_path = resolve_path(
        request[
            "execute_now_approval_path"
        ]
    )
    approval = load_json(
        approval_path
    )
    approval_digest = verify_self_digest(
        approval,
        "approval_evidence_digest_sha256",
        "execute approval",
    )

    require(
        digest(approval)
        == request[
            "execute_now_approval_digest_sha256"
        ],
        "execute approval file digest mismatch",
    )
    require(
        approval.get("approval_label")
        == (
            "FRESH_ARTICLE_ONE_SHOT_OFFLINE_"
            "GENERATION_EXECUTE_NOW_APPROVED"
        ),
        "execute approval label mismatch",
    )
    require(
        approval.get("human_explicit_approval")
        is True,
        "explicit human approval missing",
    )
    require(
        approval[
            "approved_execution_scope"
        ]["source_authorization_modification"]
        is False,
        "approval unexpectedly permits authorization modification",
    )
    require(
        isinstance(approval_digest, str),
        "execute approval digest missing",
    )

    render = preflight_plan[
        "planned_render"
    ]

    require(
        render["component_order"]
        == [
            "advertising_disclosure",
            "cover_and_information_card",
            "store_navigation_slots",
        ],
        "component order mismatch",
    )
    require(
        render[
            "advertising_disclosure"
        ]["exact_text"]
        == (
            "【PR】本記事にはアフィリエイト広告を含みます。"
            "価格・配信状況は各ストアで確認してください。"
        ),
        "disclosure mismatch",
    )
    require(
        render[
            "store_navigation"
        ]["render_mode"]
        == "RESERVED_NON_CLICKABLE_SLOTS_ONLY",
        "store navigation mode mismatch",
    )
    require(
        render[
            "store_navigation"
        ]["store_urls_included"]
        is False,
        "store URLs unexpectedly included",
    )
    require(
        render[
            "store_navigation"
        ]["final_affiliate_urls_included"]
        is False,
        "final affiliate URLs unexpectedly included",
    )

    return (
        preflight_plan,
        authorization,
        approval,
        [
            "request_identity_verified",
            "execute_scope_verified",
            "preflight_result_file_verified",
            "preflight_plan_file_verified",
            "preflight_plan_digest_verified",
            "authorization_file_verified",
            "authorization_digest_verified",
            "authorization_single_use_verified",
            "authorization_unconsumed_before_execution",
            "execute_now_human_approval_verified",
            "fixed_render_verified",
            "store_urls_excluded",
            "dmm_url_excluded",
            "payload_not_requested",
            "network_not_requested",
            "wordpress_not_requested",
        ],
    )


def render_html(
    plan: dict[str, Any],
) -> str:
    render = plan[
        "planned_render"
    ]
    disclosure = render[
        "advertising_disclosure"
    ]
    cover = render["cover"]
    card = render[
        "information_card"
    ]
    navigation = render[
        "store_navigation"
    ]

    card_lines = []

    for field in card[
        "ordered_fields"
    ]:
        card_lines.append(
            "        <li>"
            f"<strong>{html.escape(field['label'])}：</strong>"
            f"{html.escape(field['value'])}"
            "</li>"
        )

    slot_lines = []

    for slot in navigation[
        "slots"
    ]:
        classes = " ".join(
            slot["reserved_css_classes"]
        )

        slot_lines.append(
            "    <span "
            f'class="{html.escape(classes, quote=True)}" '
            'aria-disabled="true">'
            f"{html.escape(slot['display_text'])}"
            "</span>"
        )

    article_html = "\n".join(
        [
            (
                '<div class="ebook-new-release-article" '
                'data-template-id="POST185_STANDARD_TEMPLATE_V1">'
            ),
            (
                '  <p class="ebook-pr-disclosure">'
                f"{html.escape(disclosure['exact_text'])}"
                "</p>"
            ),
            '  <div class="ebook-release-layout">',
            '    <figure class="ls-book-cover">',
            (
                "      <img "
                f'src="{html.escape(cover["image_url"], quote=True)}" '
                f'alt="{html.escape(cover["alt_text"], quote=True)}" '
                'loading="lazy">'
            ),
            "    </figure>",
            '    <div class="ls-store-card">',
            "      <ul>",
            *card_lines,
            "      </ul>",
            "    </div>",
            "  </div>",
            (
                '  <div class="ls-store-buttons" '
                'aria-label="電子書籍ストア">'
            ),
            *slot_lines,
            "  </div>",
            "</div>",
            "",
        ]
    )

    return article_html


def validate_generated_html(
    article_html: str,
    plan: dict[str, Any],
) -> None:
    disclosure = plan[
        "planned_render"
    ]["advertising_disclosure"][
        "exact_text"
    ]

    require(
        article_html.startswith(
            (
                '<div class="ebook-new-release-article" '
                'data-template-id="POST185_STANDARD_TEMPLATE_V1">\n'
                '  <p class="ebook-pr-disclosure">'
            )
        ),
        "article root or disclosure position invalid",
    )
    require(
        disclosure in article_html,
        "fixed disclosure missing",
    )
    require(
        article_html.count("<img ") == 1,
        "cover image count mismatch",
    )
    require(
        article_html.count("<span ") == 3,
        "store slot count mismatch",
    )
    require(
        "<a " not in article_html.lower(),
        "anchor element unexpectedly rendered",
    )
    require(
        "href=" not in article_html.lower(),
        "href unexpectedly rendered",
    )

    for forbidden_url in [
        "https://www.amazon.co.jp/dp/",
        "https://books.rakuten.co.jp/rk/",
        "https://book.dmm.com/",
        "https://al.dmm.com/",
        "https://hb.afl.rakuten.co.jp/",
    ]:
        require(
            forbidden_url not in article_html,
            (
                "forbidden store URL rendered: "
                + forbidden_url
            ),
        )

    for required_text in [
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
        "Amazonで確認（リンク準備中）",
        "楽天Koboで確認（リンク準備中）",
        "DMMブックスで確認（再確認待ち）",
    ]:
        require(
            required_text in article_html,
            f"required text missing: {required_text}",
        )

    for forbidden_text in [
        "月曜日のたわわ",
        "比村奇石",
        "税込792円",
        "B0H6DQLPPB",
        "4071859",
        "あらすじ",
        "ポイント還元",
        "割引",
        "在庫",
        "キャンペーン",
    ]:
        require(
            forbidden_text not in article_html,
            (
                "forbidden content rendered: "
                + forbidden_text
            ),
        )


def main() -> int:
    terminal = terminal_state()

    if terminal is not None:
        return terminal

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
    )
    args = parser.parse_args()

    if not args.execute:
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-RECOVERY-K"
                    ),
                    "status": (
                        "BLOCKED_EXPLICIT_EXECUTE_FLAG_REQUIRED"
                    ),
                    "content_output_created": False,
                    "authorization_consumed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    try:
        policy = load_json(
            POLICY_PATH
        )
        request = load_json(
            REQUEST_PATH
        )

        policy_checks = validate_policy(
            policy
        )

        (
            preflight_plan,
            authorization,
            approval,
            source_checks,
        ) = validate_request_and_sources(
            request,
            policy,
        )

        authorization_path = resolve_path(
            request["source_bindings"][
                "authorization_path"
            ]
        )
        authorization_hash_before = file_sha256(
            authorization_path
        )

        require(
            not OUTPUT_PATH.exists(),
            "content output already exists",
        )
        require(
            not CONSUMPTION_PATH.exists(),
            "consumption evidence already exists",
        )

        article_html = render_html(
            preflight_plan
        )
        validate_generated_html(
            article_html,
            preflight_plan,
        )

        article_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "OFFLINE_FRESH_NEW_RELEASE_"
                "ARTICLE_CONTENT_DRAFT"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "template_contract_id": (
                "POST185_STANDARD_TEMPLATE_V1_FIXED"
            ),
            "template_id": (
                "POST185_STANDARD_TEMPLATE_V1"
            ),
            "output_language": "ja-JP",
            "wordpress_status": "draft",
            "description_mode": "minimal",
            "post_excerpt": (
                "『ダークギャザリング 第20巻』の"
                "発売日・価格・配信ストア情報です。"
            ),
            "content_html": article_html,
            "content_html_sha256": hashlib.sha256(
                article_html.encode("utf-8")
            ).hexdigest(),
            "rendered_components": [
                "advertising_disclosure",
                "cover_and_information_card",
                "store_navigation_slots"
            ],
            "rendered_metadata": {
                "work_title": "ダークギャザリング",
                "volume_label": "第20巻",
                "price_text": "616円（税込）",
                "author_name": "近藤憲一",
                "publisher_name": "集英社",
                "release_date": "2026-07-03",
                "cover_source": "rakuten_kobo",
                "cover_image_url": (
                    preflight_plan[
                        "planned_render"
                    ]["cover"]["image_url"]
                ),
                "amazon_asin": "B0H3N7QK5K",
                "rakuten_kobo_product_number": (
                    "4972000159519"
                ),
                "dmm_series_id": "861056"
            },
            "store_navigation": {
                "render_mode": (
                    "RESERVED_NON_CLICKABLE_SLOTS_ONLY"
                ),
                "store_order": [
                    "amazon",
                    "rakuten_kobo",
                    "dmm_books"
                ],
                "anchor_elements_included": False,
                "href_attributes_included": False,
                "verification_source_urls_included": False,
                "final_affiliate_urls_included": False,
                "dmm_url_included": False,
                "dmm_latest_alias_recheck_completed": False
            },
            "content_limits": {
                "synopsis_included": False,
                "story_detail_included": False,
                "discount_claims_included": False,
                "point_return_claims_included": False,
                "campaign_claims_included": False,
                "inventory_claims_included": False,
                "legacy_post185_product_data_included": False,
                "legacy_post185_urls_included": False
            },
            "source_lineage": {
                "preflight_plan_path": (
                    request[
                        "source_bindings"
                    ]["preflight_plan_path"]
                ),
                "preflight_plan_digest_sha256": (
                    request[
                        "source_bindings"
                    ][
                        "preflight_plan_artifact_digest_sha256"
                    ]
                ),
                "authorization_path": (
                    request[
                        "source_bindings"
                    ]["authorization_path"]
                ),
                "authorization_digest_sha256": (
                    request[
                        "source_bindings"
                    ][
                        "authorization_artifact_digest_sha256"
                    ]
                ),
                "execute_now_approval_path": (
                    request[
                        "execute_now_approval_path"
                    ]
                ),
                "execute_now_approval_digest_sha256": (
                    approval[
                        "approval_evidence_digest_sha256"
                    ]
                )
            },
            "categories_field_present": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "article_content_generated": True,
            "human_review_complete": False,
            "production_status": "NO_GO",
            "safety_state": (
                "OFFLINE_ARTICLE_CONTENT_GENERATED_"
                "AWAITING_HUMAN_REVIEW"
            )
        }

        article = copy.deepcopy(
            article_without_digest
        )
        article[
            "article_content_digest_sha256"
        ] = digest(article_without_digest)

        article_bytes = json_bytes(
            article
        )
        article_file_hash = bytes_sha256(
            article_bytes
        )

        consumed_at = datetime.now(
            timezone.utc
        ).isoformat()

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "ONE_SHOT_OFFLINE_CONTENT_GENERATION_"
                "AUTHORIZATION_CONSUMPTION_EVIDENCE"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K"
            ),
            "authorization_id": (
                authorization[
                    "authorization_id"
                ]
            ),
            "authorized_operation": (
                authorization[
                    "authorized_operation"
                ]
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorization_consumed": True,
            "consumption_is_authoritative": True,
            "consumed_at_utc": consumed_at,
            "single_use": True,
            "authorization_reuse_allowed": False,
            "second_generation_allowed": False,
            "source_authorization_modified": False,
            "source_authorization_path": (
                request[
                    "source_bindings"
                ]["authorization_path"]
            ),
            "source_authorization_file_sha256": (
                request[
                    "source_bindings"
                ]["authorization_file_sha256"]
            ),
            "source_authorization_digest_sha256": (
                request[
                    "source_bindings"
                ][
                    "authorization_artifact_digest_sha256"
                ]
            ),
            "preflight_plan_path": (
                request[
                    "source_bindings"
                ]["preflight_plan_path"]
            ),
            "preflight_plan_digest_sha256": (
                request[
                    "source_bindings"
                ][
                    "preflight_plan_artifact_digest_sha256"
                ]
            ),
            "execute_now_approval_path": (
                request[
                    "execute_now_approval_path"
                ]
            ),
            "execute_now_approval_digest_sha256": (
                approval[
                    "approval_evidence_digest_sha256"
                ]
            ),
            "generated_content_path": (
                display_path(OUTPUT_PATH)
            ),
            "generated_content_file_sha256": (
                article_file_hash
            ),
            "generated_content_artifact_digest_sha256": (
                article[
                    "article_content_digest_sha256"
                ]
            ),
            "article_content_generated": True,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_published": False,
            "production_status": "NO_GO",
            "safety_state": (
                "AUTHORIZATION_CONSUMED_"
                "OFFLINE_CONTENT_AWAITING_HUMAN_REVIEW"
            )
        }

        consumption = copy.deepcopy(
            consumption_without_digest
        )
        consumption[
            "consumption_evidence_digest_sha256"
        ] = digest(
            consumption_without_digest
        )

        consumption_bytes = json_bytes(
            consumption
        )

        output_temporary = stage_bytes(
            OUTPUT_PATH,
            article_bytes,
        )
        consumption_temporary = stage_bytes(
            CONSUMPTION_PATH,
            consumption_bytes,
        )

        try:
            output_temporary.replace(
                OUTPUT_PATH
            )
            consumption_temporary.replace(
                CONSUMPTION_PATH
            )
        except Exception:
            if output_temporary.exists():
                output_temporary.unlink()

            if consumption_temporary.exists():
                consumption_temporary.unlink()

            raise

        require(
            file_sha256(OUTPUT_PATH)
            == article_file_hash,
            "generated article file hash mismatch",
        )
        require(
            file_sha256(authorization_path)
            == authorization_hash_before,
            "source authorization modified during execution",
        )

        stored_article = load_json(
            OUTPUT_PATH
        )
        stored_consumption = load_json(
            CONSUMPTION_PATH
        )

        verify_self_digest(
            stored_article,
            "article_content_digest_sha256",
            "stored article",
        )
        verify_self_digest(
            stored_consumption,
            "consumption_evidence_digest_sha256",
            "stored consumption evidence",
        )

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "content_output_path": (
                display_path(OUTPUT_PATH)
            ),
            "content_output_file_sha256": (
                file_sha256(OUTPUT_PATH)
            ),
            "article_content_digest_sha256": (
                article[
                    "article_content_digest_sha256"
                ]
            ),
            "consumption_evidence_path": (
                display_path(CONSUMPTION_PATH)
            ),
            "consumption_evidence_file_sha256": (
                file_sha256(CONSUMPTION_PATH)
            ),
            "consumption_evidence_digest_sha256": (
                consumption[
                    "consumption_evidence_digest_sha256"
                ]
            ),
            "authorization_consumed": True,
            "source_authorization_modified": False,
            "article_content_generated": True,
            "fresh_payload_created": False,
            "category_id_injected": False,
            "network_access_performed": False,
            "wordpress_access_performed": False,
            "verified_checks": (
                policy_checks
                + source_checks
            ),
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "one_shot_generation_package_digest_sha256"
        ] = digest(
            package_without_digest
        )

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K"
            ),
            "status": (
                "PASS_FRESH_ARTICLE_CONTENT_GENERATED_"
                "OFFLINE_ONE_SHOT_AUTHORIZATION_CONSUMED_"
                "NO_PAYLOAD_NO_NETWORK"
            ),
            "decision": (
                "DARK_GATHERING_VOLUME_20_OFFLINE_CONTENT_"
                "GENERATED_AWAITING_HUMAN_REVIEW"
            ),
            "approval_label": (
                "FRESH_ARTICLE_ONE_SHOT_OFFLINE_"
                "GENERATION_EXECUTE_NOW_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "work_title": "ダークギャザリング",
            "volume_label": "第20巻",
            "article_title": (
                "ダークギャザリング 第20巻｜配信開始"
            ),
            "content_output_path": (
                package[
                    "content_output_path"
                ]
            ),
            "content_output_file_sha256": (
                package[
                    "content_output_file_sha256"
                ]
            ),
            "article_content_digest_sha256": (
                package[
                    "article_content_digest_sha256"
                ]
            ),
            "consumption_evidence_path": (
                package[
                    "consumption_evidence_path"
                ]
            ),
            "consumption_evidence_digest_sha256": (
                package[
                    "consumption_evidence_digest_sha256"
                ]
            ),
            "one_shot_generation_package_digest_sha256": (
                package[
                    "one_shot_generation_package_digest_sha256"
                ]
            ),
            "article_content_generated": True,
            "content_output_exists": True,
            "authorization_consumed": True,
            "consumption_evidence_created": True,
            "consumption_evidence_is_authoritative": True,
            "source_authorization_modified": False,
            "authorization_reuse_allowed": False,
            "second_generation_allowed": False,
            "fixed_disclosure_rendered": True,
            "current_cover_rendered": True,
            "information_card_rendered": True,
            "store_navigation_slots_rendered": True,
            "store_anchor_elements_included": False,
            "store_href_attributes_included": False,
            "store_urls_included": False,
            "final_affiliate_urls_included": False,
            "dmm_url_included": False,
            "dmm_latest_alias_recheck_completed": False,
            "synopsis_included": False,
            "story_detail_included": False,
            "discount_claims_included": False,
            "point_return_claims_included": False,
            "campaign_claims_included": False,
            "inventory_claims_included": False,
            "legacy_post185_product_data_included": False,
            "legacy_post185_urls_included": False,
            "categories_field_present": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "credential_file_read": False,
            "network_connection_performed": False,
            "http_request_performed": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "OFFLINE_ARTICLE_CONTENT_GENERATED_"
                "AUTHORIZATION_CONSUMED_AWAITING_HUMAN_REVIEW"
            ),
            "ready_for_ls_new_batch_4g_2e_recovery_l": True,
            "ready_for_article_content_human_review": True,
            "ready_for_fresh_payload_generation": False,
            "ready_for_payload_injection": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False,
            "verified_checks": (
                package["verified_checks"]
                + [
                    "article_content_digest_verified",
                    "consumption_evidence_digest_verified",
                    "fixed_disclosure_rendered",
                    "current_cover_rendered",
                    "information_card_rendered",
                    "non_clickable_store_slots_rendered",
                    "store_urls_excluded",
                    "dmm_url_excluded",
                    "unsupported_content_excluded",
                    "legacy_product_data_excluded",
                    "source_authorization_preserved",
                    "authorization_consumed_by_evidence",
                    "authorization_reuse_blocked",
                    "payload_not_created",
                    "category_id_not_injected",
                    "network_unaccessed",
                    "wordpress_unaccessed",
                    "production_gate_closed",
                ]
            ),
        }

        write_json(
            PACKAGE_PATH,
            package,
        )
        write_json(
            RESULT_PATH,
            result,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-K One-Shot Offline Generation

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Work: `{result["work_title"]}`
- Volume: `{result["volume_label"]}`

## Generated Artifact

- Content path: `{result["content_output_path"]}`
- Article digest: `{result["article_content_digest_sha256"]}`
- Article content generated: `true`

## Authorization Consumption

- Authorization consumed: `true`
- Independent evidence created: `true`
- Source authorization modified: `false`
- Authorization reuse allowed: `false`
- Second generation allowed: `false`

## Content Boundary

- Fixed disclosure rendered: `true`
- Current cover rendered: `true`
- Information card rendered: `true`
- Non-clickable store slots rendered: `true`
- Store URLs included: `false`
- Final affiliate URLs included: `false`
- DMM URL included: `false`
- Synopsis included: `false`
- Discount claims included: `false`
- Point-return claims included: `false`

## Production Boundary

- Payload created: `false`
- Category ID injected: `false`
- Network accessed: `false`
- WordPress written: `false`
- Published: `false`
- Production status: `NO_GO`
"""

        write_text(
            REPORT_PATH,
            report,
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    except ValidationError as exc:
        failure = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-K"
            ),
            "status": "FAIL_VALIDATION",
            "error": str(exc),
            "article_content_generated": False,
            "authorization_consumed": False,
            "fresh_payload_created": False,
            "production_category_id_payload_injected": False,
            "network_connection_performed": False,
            "wordpress_write_performed": False,
            "production_status": "NO_GO"
        }

        print(
            json.dumps(
                failure,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
