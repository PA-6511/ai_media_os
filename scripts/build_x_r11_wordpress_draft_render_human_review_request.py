from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-DRAFT-RENDER-HUMAN-REVIEW"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_DRY_RUN_DIGEST = (
    "f17a372e636541d21b4d0b522cdd49863"
    "054e3f6c43442363521b4f7ce8f52db"
)

EXPECTED_RENDERED_HTML_SHA = (
    "ae18a9116741fea0ea51bc105ed89a6c5"
    "14bf512bc02d1d0c69f6998695aef5b"
)

EXPECTED_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

EXPECTED_CATEGORY_ID = 43

EXPECTED_CURRENT_PRODUCT_HASH = (
    "bce9f1878b0032dc4745ecf22fd179a6"
)

BLOCKED_OLD_PRODUCT_HASH = (
    "f402536ea6473a172c957407fae06192"
)

EXPECTED_COVER_SHA = (
    "fcd5ed6e8a2136f45a380e055d3a34e7"
    "fe1e0d90cfaed9c8bcc8839c95a890c7"
)

APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "DRAFT_FINAL_GATE_ONLY"
)

REJECTION_LABEL = (
    "REJECTED_FOR_X_R11_WORDPRESS_"
    "DRAFT_FINAL_GATE"
)


class HumanReviewRequestError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise HumanReviewRequestError(
            message
        )


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
        raise HumanReviewRequestError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


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


def verify_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    expected_digest: str | None = None,
    label: str,
) -> str:
    recorded = value.get(
        digest_field
    )

    require(
        isinstance(recorded, str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            recorded,
        )
        is not None,
        f"{label} digest is invalid",
    )

    if expected_digest is not None:
        require(
            recorded == expected_digest,
            f"{label} digest mismatch",
        )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == recorded,
        f"{label} digest verification failed",
    )

    return recorded


def build_human_review_request(
    *,
    production_database_path: Path,
    dry_run_pack_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    dry_run_pack_path = (
        dry_run_pack_path.resolve()
    )

    output_path = output_path.resolve()

    require(
        production_database_path.is_file(),
        "production database is missing",
    )

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    dry_run = load_json(
        dry_run_pack_path
    )

    verify_digest(
        dry_run,
        digest_field=(
            "wordpress_draft_render_dry_run_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_DRY_RUN_DIGEST
        ),
        label="render dry-run pack",
    )

    require(
        dry_run.get("status")
        == (
            "PASS_WORDPRESS_DRAFT_"
            "RENDER_DRY_RUN"
        ),
        "render dry run did not pass",
    )

    require(
        dry_run.get("render_state")
        == (
            "LOCAL_RENDER_COMPLETE_"
            "HUMAN_REVIEW_REQUIRED"
        ),
        "render state mismatch",
    )

    require(
        dry_run.get(
            "render_dry_run_completed"
        )
        is True,
        "render dry run is incomplete",
    )

    require(
        dry_run.get(
            "human_review_completed"
        )
        is False,
        (
            "human review is already "
            "recorded as completed"
        ),
    )

    require(
        dry_run.get(
            "draft_creation_allowed"
        )
        is False,
        (
            "draft creation must remain "
            "blocked"
        ),
    )

    require(
        dry_run.get(
            "wordpress_api_call"
        )
        is False,
        "WordPress API was unexpectedly called",
    )

    require(
        dry_run.get(
            "wordpress_write"
        )
        is False,
        "WordPress write was unexpectedly made",
    )

    post_preview = dry_run.get(
        "post_preview"
    )

    require(
        isinstance(post_preview, dict),
        "post preview is missing",
    )

    require(
        post_preview.get("title")
        == EXPECTED_TITLE,
        "post title mismatch",
    )

    require(
        post_preview.get("slug")
        == EXPECTED_SLUG,
        "post slug mismatch",
    )

    require(
        post_preview.get("status")
        == "draft",
        "post status must be draft",
    )

    require(
        post_preview.get("category_ids")
        == [EXPECTED_CATEGORY_ID],
        "post category mismatch",
    )

    require(
        post_preview.get(
            "maximum_post_create_count"
        )
        == 1,
        "maximum post count must be one",
    )

    rendered_html_path = Path(
        dry_run["rendered_html_path"]
    ).resolve()

    payload_preview_path = Path(
        dry_run["payload_preview_path"]
    ).resolve()

    require(
        rendered_html_path.is_file(),
        "rendered HTML is missing",
    )

    require(
        payload_preview_path.is_file(),
        "payload preview is missing",
    )

    rendered_html_sha = sha256_file(
        rendered_html_path
    )

    require(
        rendered_html_sha
        == EXPECTED_RENDERED_HTML_SHA,
        "rendered HTML SHA mismatch",
    )

    require(
        dry_run.get(
            "rendered_html_sha256"
        )
        == EXPECTED_RENDERED_HTML_SHA,
        (
            "rendered HTML SHA evidence "
            "mismatch"
        ),
    )

    rendered_html = (
        rendered_html_path.read_text(
            encoding="utf-8"
        )
    )

    payload_preview = load_json(
        payload_preview_path
    )

    payload_digest = verify_digest(
        payload_preview,
        digest_field=(
            "wordpress_draft_payload_"
            "preview_digest_sha256"
        ),
        label="payload preview",
    )

    require(
        payload_digest
        == dry_run.get(
            "payload_preview_digest_sha256"
        ),
        "payload preview digest mismatch",
    )

    require(
        payload_preview.get(
            "preview_only"
        )
        is True,
        "payload must remain preview-only",
    )

    require(
        payload_preview.get(
            "execution_allowed"
        )
        is False,
        "payload execution must be blocked",
    )

    require(
        payload_preview.get(
            "wordpress_api_method"
        )
        == "NOT_CALLED",
        "WordPress API method mismatch",
    )

    request = payload_preview.get(
        "wordpress_request"
    )

    require(
        isinstance(request, dict),
        "WordPress request preview is missing",
    )

    require(
        request.get("title")
        == EXPECTED_TITLE,
        "request title mismatch",
    )

    require(
        request.get("slug")
        == EXPECTED_SLUG,
        "request slug mismatch",
    )

    require(
        request.get("status")
        == "draft",
        "request status must be draft",
    )

    require(
        request.get("categories")
        == [EXPECTED_CATEGORY_ID],
        "request categories mismatch",
    )

    require(
        request.get("content")
        == rendered_html,
        (
            "payload content differs from "
            "rendered HTML"
        ),
    )

    machine_checks = {
        "post_title_verified": (
            request.get("title")
            == EXPECTED_TITLE
        ),
        "article_heading_verified": (
            "のあ先輩はともだち。 第11巻"
            in rendered_html
        ),
        "pr_disclosure_verified": (
            "※本記事にはアフィリエイトリンクが含まれます。"
            in rendered_html
        ),
        "book_title_verified": (
            "のあ先輩はともだち。"
            in rendered_html
        ),
        "volume_verified": (
            "第11巻"
            in rendered_html
        ),
        "author_verified": (
            "あきやまえんま"
            in rendered_html
        ),
        "publisher_verified": (
            "集英社"
            in rendered_html
        ),
        "release_date_verified": (
            "2026年7月17日"
            in rendered_html
        ),
        "current_affiliate_hash_verified": (
            EXPECTED_CURRENT_PRODUCT_HASH
            in rendered_html
        ),
        "old_affiliate_hash_absent": (
            BLOCKED_OLD_PRODUCT_HASH
            not in rendered_html
        ),
        "sponsored_rel_verified": (
            'rel="sponsored nofollow '
            'noopener noreferrer"'
            in rendered_html
        ),
        "target_blank_verified": (
            'target="_blank"'
            in rendered_html
        ),
        "cover_alt_verified": (
            'alt="のあ先輩はともだち。 '
            '第11巻 書影"'
            in rendered_html
        ),
        "single_rakuten_button_verified": (
            rendered_html.count(
                "store-button-rakuten-kobo"
            )
            == 1
        ),
        "forbidden_script_absent": (
            re.search(
                r"<\s*script\b",
                rendered_html,
                flags=re.IGNORECASE,
            )
            is None
        ),
        "unresolved_placeholder_absent": (
            re.search(
                r"\{\{[^{}]+\}\}",
                rendered_html,
            )
            is None
        ),
    }

    failed_machine_checks = [
        name
        for name, passed
        in machine_checks.items()
        if not passed
    ]

    require(
        not failed_machine_checks,
        (
            "machine review checks failed: "
            + ", ".join(
                failed_machine_checks
            )
        ),
    )

    cover_policy = dry_run.get(
        "cover_image_policy"
    )

    require(
        isinstance(cover_policy, dict),
        "cover image policy is missing",
    )

    require(
        cover_policy.get(
            "source_image_hotlink_approved"
        )
        is False,
        "remote image hotlink is not blocked",
    )

    require(
        cover_policy.get(
            "publication_with_remote_image_allowed"
        )
        is False,
        "remote image publication is not blocked",
    )

    require(
        cover_policy.get(
            "wordpress_media_upload_required_before_publish"
        )
        is True,
        (
            "WordPress media upload "
            "requirement is missing"
        ),
    )

    review_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_DRAFT_RENDER_"
            "HUMAN_REVIEW_REQUEST_READY"
        ),
        "human_review_state": (
            "AWAITING_EXPLICIT_HUMAN_DECISION"
        ),
        "prepared_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_dry_run_pack_path": str(
            dry_run_pack_path
        ),
        "source_dry_run_digest_sha256": (
            EXPECTED_DRY_RUN_DIGEST
        ),
        "rendered_html_path": str(
            rendered_html_path
        ),
        "rendered_html_sha256": (
            rendered_html_sha
        ),
        "payload_preview_path": str(
            payload_preview_path
        ),
        "payload_preview_digest_sha256": (
            payload_digest
        ),
        "production_database_path": str(
            production_database_path
        ),
        "required_production_database_sha256": (
            EXPECTED_DATABASE_SHA
        ),
        "review_target": {
            "title": EXPECTED_TITLE,
            "slug": EXPECTED_SLUG,
            "status": "draft",
            "category_ids": [
                EXPECTED_CATEGORY_ID
            ],
            "category_name": (
                "コミック新刊"
            ),
            "maximum_post_create_count": 1,
            "rendered_html_character_count": (
                len(rendered_html)
            ),
            "rendered_html_byte_size": (
                len(
                    rendered_html.encode(
                        "utf-8"
                    )
                )
            ),
        },
        "machine_precheck": {
            "passed": True,
            "checks": machine_checks,
            "cover_image_sha256": (
                EXPECTED_COVER_SHA
            ),
        },
        "human_review_checklist": [
            {
                "check_id": "TITLE_AND_VOLUME",
                "description": (
                    "作品名と巻数が正しい"
                ),
                "human_decision": "PENDING"
            },
            {
                "check_id": "AUTHOR_AND_PUBLISHER",
                "description": (
                    "著者と出版社が正しい"
                ),
                "human_decision": "PENDING"
            },
            {
                "check_id": "RELEASE_DATE",
                "description": (
                    "配信日が正しい"
                ),
                "human_decision": "PENDING"
            },
            {
                "check_id": "PR_DISCLOSURE",
                "description": (
                    "アフィリエイト表記が明確"
                ),
                "human_decision": "PENDING"
            },
            {
                "check_id": "COVER_IMAGE",
                "description": (
                    "書影が対象商品第11巻と一致"
                ),
                "human_decision": "PENDING"
            },
            {
                "check_id": "RAKUTEN_LINK",
                "description": (
                    "楽天リンクが対象商品と一致"
                ),
                "human_decision": "PENDING"
            },
            {
                "check_id": "LAYOUT_AND_COPY",
                "description": (
                    "記事構成と表示文言に問題がない"
                ),
                "human_decision": "PENDING"
            },
            {
                "check_id": "REMOTE_IMAGE_RESTRICTION",
                "description": (
                    "公開前のWordPressメディア登録が必要"
                ),
                "human_decision": "PENDING"
            }
        ],
        "approval_label_if_approved": (
            APPROVAL_LABEL
        ),
        "rejection_label_if_rejected": (
            REJECTION_LABEL
        ),
        "human_decision": "PENDING",
        "human_review_completed": False,
        "approval_issued": False,
        "approval_consumed": False,
        "final_gate_allowed": False,
        "draft_creation_allowed": False,
        "publication_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "wordpress_media_write": False,
        "wordpress_post_creation": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "HUMAN_REVIEW_PENDING_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
    }

    review = {
        **review_payload,
        "wordpress_draft_render_human_"
        "review_request_digest_sha256": (
            canonical_digest(
                review_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        review,
    )

    return review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--dry-run-pack",
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
        result = build_human_review_request(
            production_database_path=(
                args.production_db
            ),
            dry_run_pack_path=(
                args.dry_run_pack
            ),
            output_path=args.output,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_DRAFT_"
                        "RENDER_HUMAN_REVIEW_REQUEST"
                    ),
                    "error": str(exc),
                    "human_review_completed": False,
                    "approval_issued": False,
                    "draft_creation_allowed": False,
                    "wordpress_api_call": False,
                    "wordpress_write": False,
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
                "human_review_state": (
                    result[
                        "human_review_state"
                    ]
                ),
                "machine_precheck_passed": True,
                "review_target": (
                    result["review_target"]
                ),
                "human_check_count": len(
                    result[
                        "human_review_checklist"
                    ]
                ),
                "human_decision": "PENDING",
                "approval_issued": False,
                "draft_creation_allowed": False,
                "wordpress_api_call": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "approval_label_if_approved": (
                    APPROVAL_LABEL
                ),
                "review_pack_path": str(
                    args.output.resolve()
                ),
                "review_digest_sha256": (
                    result[
                        "wordpress_draft_render_"
                        "human_review_request_"
                        "digest_sha256"
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
