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
from urllib.parse import urlparse


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
    "X-DRAFT-LOCAL-GENERATION"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_VERIFICATION_DIGEST = (
    "3271baa516a5d5de36a087195430aade3"
    "788a364aa543670c2044d33f7699514"
)

EXPECTED_FINAL_GATE_DIGEST = (
    "f348d6f37980fdd5ccd5e9c9f5bc84c3"
    "7afc80509b369cd293fb5614f7edfd86"
)

EXPECTED_POST_ID = 195

EXPECTED_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

EXPECTED_CURRENT_PRODUCT_HASH = (
    "bce9f1878b0032dc4745ecf22fd179a6"
)

BLOCKED_OLD_PRODUCT_HASH = (
    "f402536ea6473a172c957407fae06192"
)

PUBLIC_URL_PLACEHOLDER = (
    "{{WORDPRESS_PUBLIC_URL}}"
)

ALLOWED_AFFILIATE_HOSTS = {
    "hb.afl.rakuten.co.jp",
    "a.r10.to",
}

X_MAX_CHARACTER_COUNT = 280
X_TCO_ESTIMATED_URL_LENGTH = 23


class XDraftGenerationError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XDraftGenerationError(
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
        raise XDraftGenerationError(
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


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def verify_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    expected_digest: str,
    label: str,
) -> None:
    recorded = value.get(
        digest_field
    )

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
        == expected_digest,
        (
            f"{label} canonical digest "
            "verification failed"
        ),
    )


def atomic_write_text(
    path: Path,
    value: str,
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        path.name + ".tmp"
    )

    temporary.write_text(
        value,
        encoding="utf-8",
    )

    temporary.replace(path)


def extract_affiliate_url(
    rendered_html: str,
) -> str:
    href_values = re.findall(
        r'''href=["']([^"']+)["']''',
        rendered_html,
        flags=re.IGNORECASE,
    )

    candidates: list[str] = []

    for raw_value in href_values:
        value = html.unescape(
            raw_value.strip()
        )

        parsed = urlparse(value)

        hostname = (
            parsed.hostname or ""
        ).casefold()

        if (
            parsed.scheme == "https"
            and hostname
            in ALLOWED_AFFILIATE_HOSTS
        ):
            candidates.append(value)

    unique = list(
        dict.fromkeys(candidates)
    )

    require(
        len(unique) == 1,
        (
            "exactly one permitted affiliate "
            f"URL is required; found={len(unique)}"
        ),
    )

    affiliate_url = unique[0]

    require(
        EXPECTED_CURRENT_PRODUCT_HASH
        in affiliate_url,
        (
            "current affiliate product "
            "hash is missing"
        ),
    )

    require(
        BLOCKED_OLD_PRODUCT_HASH
        not in affiliate_url,
        (
            "superseded affiliate product "
            "hash was found"
        ),
    )

    return affiliate_url


def build_x_draft_text() -> str:
    return (
        "【新刊】\n"
        "『のあ先輩はともだち。』"
        "第11巻が7月17日に配信開始📚\n"
        "\n"
        "著者：あきやまえんま\n"
        "出版社：集英社\n"
        "\n"
        "楽天Koboの配信情報・価格はこちら\n"
        f"{PUBLIC_URL_PLACEHOLDER}\n"
        "\n"
        "#のあ先輩はともだち "
        "#コミック新刊"
    )


def estimated_x_character_count(
    draft_text: str,
) -> int:
    require(
        draft_text.count(
            PUBLIC_URL_PLACEHOLDER
        )
        == 1,
        (
            "X draft must contain exactly "
            "one public URL placeholder"
        ),
    )

    without_placeholder = (
        draft_text.replace(
            PUBLIC_URL_PLACEHOLDER,
            "",
            1,
        )
    )

    return (
        len(without_placeholder)
        + X_TCO_ESTIMATED_URL_LENGTH
    )


def validate_x_draft_text(
    draft_text: str,
) -> dict[str, Any]:
    required_fragments = (
        "【新刊】",
        "のあ先輩はともだち。",
        "第11巻",
        "7月17日",
        "あきやまえんま",
        "集英社",
        "楽天Kobo",
        PUBLIC_URL_PLACEHOLDER,
        "#のあ先輩はともだち",
        "#コミック新刊",
    )

    missing = [
        fragment
        for fragment in required_fragments
        if fragment not in draft_text
    ]

    require(
        not missing,
        (
            "required X draft fragments "
            "are missing: "
            + ", ".join(missing)
        ),
    )

    require(
        EXPECTED_CURRENT_PRODUCT_HASH
        not in draft_text,
        (
            "raw affiliate URL must not be "
            "embedded in the primary X draft"
        ),
    )

    require(
        BLOCKED_OLD_PRODUCT_HASH
        not in draft_text,
        (
            "superseded affiliate product "
            "hash appears in X draft"
        ),
    )

    require(
        "https://" not in draft_text,
        (
            "public URL must remain a "
            "placeholder before publication"
        ),
    )

    estimated_count = (
        estimated_x_character_count(
            draft_text
        )
    )

    require(
        estimated_count
        <= X_MAX_CHARACTER_COUNT,
        (
            "estimated X character count "
            f"exceeds {X_MAX_CHARACTER_COUNT}: "
            f"{estimated_count}"
        ),
    )

    return {
        "required_fragments_verified": True,
        "public_url_placeholder_count": 1,
        "raw_affiliate_url_in_text": False,
        "old_affiliate_hash_absent": True,
        "literal_character_count": len(
            draft_text
        ),
        "estimated_character_count_with_tco_url": (
            estimated_count
        ),
        "maximum_character_count": (
            X_MAX_CHARACTER_COUNT
        ),
        "character_limit_passed": True,
    }


def build_local_x_draft(
    *,
    production_database_path: Path,
    verification_pack_path: Path,
    final_gate_pack_path: Path,
    draft_text_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    verification_pack_path = (
        verification_pack_path.resolve()
    )

    final_gate_pack_path = (
        final_gate_pack_path.resolve()
    )

    draft_text_path = (
        draft_text_path.resolve()
    )

    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    verification = load_json(
        verification_pack_path
    )

    verify_digest(
        verification,
        digest_field=(
            "wordpress_draft_post_creation_"
            "verification_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_VERIFICATION_DIGEST
        ),
        label="post-creation verification pack",
    )

    require(
        verification.get("status")
        == (
            "PASS_WORDPRESS_DRAFT_"
            "POST_CREATION_VERIFICATION"
        ),
        (
            "post-creation verification "
            "did not pass"
        ),
    )

    require(
        verification.get(
            "verification_state"
        )
        == (
            "WORDPRESS_DRAFT_195_VERIFIED_"
            "REEXECUTION_BLOCKED_X_DRAFT_READY"
        ),
        "post verification state mismatch",
    )

    post = verification.get(
        "wordpress_post"
    )

    require(
        isinstance(post, dict),
        "verified WordPress post is missing",
    )

    require(
        post.get("post_id")
        == EXPECTED_POST_ID,
        "verified WordPress post ID mismatch",
    )

    require(
        post.get("title")
        == EXPECTED_TITLE,
        "verified WordPress title mismatch",
    )

    require(
        post.get("slug")
        == EXPECTED_SLUG,
        "verified WordPress slug mismatch",
    )

    require(
        post.get("status")
        == "draft",
        (
            "verified WordPress post must "
            "remain draft"
        ),
    )

    require(
        post.get("categories")
        == [43],
        "verified WordPress category mismatch",
    )

    require(
        verification.get(
            "x_draft_generation_allowed"
        )
        is True,
        (
            "X draft generation is not "
            "authorized"
        ),
    )

    require(
        verification.get(
            "reexecution_allowed"
        )
        is False,
        (
            "WordPress creation reexecution "
            "must remain blocked"
        ),
    )

    require(
        verification.get(
            "wordpress_write"
        )
        is False,
        (
            "post-verification phase recorded "
            "an unexpected WordPress write"
        ),
    )

    final_gate = load_json(
        final_gate_pack_path
    )

    verify_digest(
        final_gate,
        digest_field=(
            "wordpress_draft_final_gate_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_FINAL_GATE_DIGEST
        ),
        label="Final Gate pack",
    )

    payload_preview_path = Path(
        final_gate[
            "payload_preview_path"
        ]
    ).resolve()

    payload_preview = load_json(
        payload_preview_path
    )

    verify_digest(
        payload_preview,
        digest_field=(
            "wordpress_draft_payload_"
            "preview_digest_sha256"
        ),
        expected_digest=(
            final_gate[
                "payload_preview_digest_sha256"
            ]
        ),
        label="WordPress payload preview",
    )

    request = payload_preview.get(
        "wordpress_request"
    )

    require(
        isinstance(request, dict),
        "WordPress request preview is missing",
    )

    rendered_html = request.get(
        "content"
    )

    require(
        isinstance(rendered_html, str)
        and rendered_html,
        "rendered WordPress HTML is missing",
    )

    affiliate_url = extract_affiliate_url(
        rendered_html
    )

    draft_text = build_x_draft_text()

    text_validation = (
        validate_x_draft_text(
            draft_text
        )
    )

    draft_text_sha256 = sha256_text(
        draft_text
    )

    atomic_write_text(
        draft_text_path,
        draft_text + "\n",
    )

    generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    pack_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_DRAFT_LOCAL_GENERATION"
        ),
        "x_draft_state": (
            "LOCAL_DRAFT_GENERATED_"
            "PUBLIC_URL_AND_HUMAN_REVIEW_REQUIRED"
        ),
        "generated_at": generated_at,
        "source_verification_pack_path": str(
            verification_pack_path
        ),
        "source_verification_digest_sha256": (
            EXPECTED_VERIFICATION_DIGEST
        ),
        "source_final_gate_pack_path": str(
            final_gate_pack_path
        ),
        "source_final_gate_digest_sha256": (
            EXPECTED_FINAL_GATE_DIGEST
        ),
        "wordpress_post": {
            "post_id": EXPECTED_POST_ID,
            "title": EXPECTED_TITLE,
            "slug": EXPECTED_SLUG,
            "status": "draft",
            "category_ids": [43],
            "public_url_available": False,
            "public_url_placeholder": (
                PUBLIC_URL_PLACEHOLDER
            ),
        },
        "x_draft": {
            "draft_id": (
                "xr11-x-draft-local-"
                + draft_text_sha256[:24]
            ),
            "text": draft_text,
            "text_path": str(
                draft_text_path
            ),
            "text_sha256": (
                draft_text_sha256
            ),
            "route": (
                "WORDPRESS_PUBLIC_ARTICLE"
            ),
            "language": "ja",
            "text_validation": (
                text_validation
            ),
        },
        "affiliate_evidence": {
            "store": "rakuten_kobo",
            "affiliate_url": affiliate_url,
            "affiliate_hostname": (
                urlparse(
                    affiliate_url
                ).hostname
            ),
            "current_product_hash": (
                EXPECTED_CURRENT_PRODUCT_HASH
            ),
            "old_product_hash_absent": True,
            "affiliate_url_verified": True,
            "affiliate_url_embedded_in_primary_text": (
                False
            ),
        },
        "required_before_x_review": [
            "WORDPRESS_PUBLIC_URL",
            "HUMAN_REVIEW",
        ],
        "required_before_x_post": [
            "WORDPRESS_POST_PUBLICATION",
            "PUBLIC_URL_REPLACEMENT",
            "FINAL_X_TEXT_REVIEW",
            "EXPLICIT_X_POST_APPROVAL",
        ],
        "wordpress_post_publication_allowed": (
            False
        ),
        "x_draft_generation_completed": True,
        "x_human_review_completed": False,
        "x_post_approval_issued": False,
        "x_api_call": False,
        "x_post": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "production_status": "NO_GO",
        "safety_state": (
            "LOCAL_X_DRAFT_ONLY_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-DRAFT-HUMAN-REVIEW-PREP"
        ),
    }

    pack = {
        **pack_payload,
        "x_draft_local_generation_"
        "digest_sha256": (
            canonical_digest(
                pack_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        pack,
    )

    return pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--verification-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--final-gate-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--draft-text",
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
        result = build_local_x_draft(
            production_database_path=(
                args.production_db
            ),
            verification_pack_path=(
                args.verification_pack
            ),
            final_gate_pack_path=(
                args.final_gate_pack
            ),
            draft_text_path=(
                args.draft_text
            ),
            output_path=args.output,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_DRAFT_"
                        "LOCAL_GENERATION"
                    ),
                    "error": str(exc),
                    "x_api_call": False,
                    "x_post": False,
                    "normal_x_fb_write": False,
                    "wordpress_write": False,
                    "database_write": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    x_draft = result["x_draft"]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "x_draft_state": (
                    result["x_draft_state"]
                ),
                "draft_id": (
                    x_draft["draft_id"]
                ),
                "wordpress_post_id": 195,
                "wordpress_post_status": "draft",
                "public_url_available": False,
                "public_url_placeholder": (
                    PUBLIC_URL_PLACEHOLDER
                ),
                "literal_character_count": (
                    x_draft[
                        "text_validation"
                    ][
                        "literal_character_count"
                    ]
                ),
                "estimated_character_count_with_tco_url": (
                    x_draft[
                        "text_validation"
                    ][
                        "estimated_character_count_with_tco_url"
                    ]
                ),
                "x_human_review_completed": False,
                "x_post_approval_issued": False,
                "x_api_call": False,
                "x_post": False,
                "normal_x_fb_write": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "draft_text_path": (
                    x_draft["text_path"]
                ),
                "pack_path": str(
                    args.output.resolve()
                ),
                "pack_digest_sha256": (
                    result[
                        "x_draft_local_generation_"
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
