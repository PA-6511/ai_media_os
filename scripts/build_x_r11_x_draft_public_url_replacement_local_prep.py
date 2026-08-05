from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
    "X-DRAFT-PUBLIC-URL-REPLACEMENT-LOCAL-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_SOURCE_X_DRAFT_PACK_DIGEST = (
    "869143e190d896c80df3c0ec21df51e2"
    "9ba9528c4b3dbdb9f8b456119b5b76f7"
)

EXPECTED_WORDING_GATE_DIGEST = (
    "b52ca408c72095ea3b958bf28c044804"
    "c1f554ceda5f7b8fa7084539eda6ea8c"
)

EXPECTED_PUBLICATION_VERIFICATION_DIGEST = (
    "16e863ba32985294189c2f63314ddf6a"
    "ed7cf9a3ab3ed594568da35d9dba552c"
)

EXPECTED_SOURCE_DRAFT_ID = (
    "xr11-x-draft-local-"
    "7b571ccea2b70141224efa17"
)

EXPECTED_SOURCE_TEXT_SHA = (
    "7b571ccea2b70141224efa17cbd3fbff"
    "89383ca5ad5460e7edd110d8af49b6da"
)

EXPECTED_REPLACED_TEXT_SHA = (
    "4842647be85ea1d60aab47fd159b85ee"
    "ef23c9632809a617fc2f49c21586e7af"
)

EXPECTED_REPLACED_DRAFT_ID = (
    "xr11-x-draft-public-url-"
    "4842647be85ea1d60aab47fd"
)

EXPECTED_PUBLIC_URL = (
    "https://hoshido.jp/2026/07/18/"
    "noa-senpai-wa-tomodachi-11-6ffa7a8d/"
)

PUBLIC_URL_PLACEHOLDER = (
    "{{WORDPRESS_PUBLIC_URL}}"
)

EXPECTED_LITERAL_CHARACTER_COUNT = 160
EXPECTED_TCO_CHARACTER_COUNT = 117
TCO_URL_CHARACTER_COUNT = 23

EXPECTED_SOURCE_TEXT = (
    "【新刊】\n"
    "『のあ先輩はともだち。』"
    "第11巻が7月17日に配信開始📚\n"
    "\n"
    "著者：あきやまえんま\n"
    "出版社：集英社\n"
    "\n"
    "楽天Koboの配信情報・価格はこちら\n"
    "{{WORDPRESS_PUBLIC_URL}}\n"
    "\n"
    "#のあ先輩はともだち "
    "#コミック新刊"
)

EXPECTED_REPLACED_TEXT = (
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


class XDraftPublicUrlReplacementError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XDraftPublicUrlReplacementError(
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


def sha256_text(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


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
        raise XDraftPublicUrlReplacementError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def verify_expected_digest(
    value: dict[str, Any],
    *,
    expected_digest: str,
    label: str,
) -> str:
    matching_fields = [
        key
        for key, item in value.items()
        if (
            key.endswith(
                "digest_sha256"
            )
            and item == expected_digest
        )
    ]

    require(
        matching_fields,
        f"{label} expected digest field is missing",
    )

    for digest_field in matching_fields:
        payload = {
            key: item
            for key, item in value.items()
            if key != digest_field
        }

        if (
            canonical_digest(payload)
            == expected_digest
        ):
            return digest_field

    raise XDraftPublicUrlReplacementError(
        (
            f"{label} canonical digest "
            "verification failed"
        )
    )


def atomic_create_bytes(
    path: Path,
    value: bytes,
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
        raise XDraftPublicUrlReplacementError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(
            descriptor,
            value,
        )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_create_text(
    path: Path,
    value: str,
) -> None:
    atomic_create_bytes(
        path,
        value.encode("utf-8"),
    )


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    data = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    atomic_create_bytes(
        path,
        data,
    )


def get_nested_or_top_level(
    value: dict[str, Any],
    field: str,
) -> Any:
    nested = value.get(
        "x_draft"
    )

    if isinstance(nested, dict):
        if field in nested:
            return nested[field]

    return value.get(field)


def validate_source_x_draft_pack(
    value: dict[str, Any],
) -> None:
    verify_expected_digest(
        value,
        expected_digest=(
            EXPECTED_SOURCE_X_DRAFT_PACK_DIGEST
        ),
        label="source X draft pack",
    )

    require(
        value.get("status")
        == "PASS_X_DRAFT_LOCAL_GENERATION",
        "source X draft status mismatch",
    )

    require(
        get_nested_or_top_level(
            value,
            "draft_id",
        )
        == EXPECTED_SOURCE_DRAFT_ID,
        "source X draft ID mismatch",
    )

    recorded_sha = (
        get_nested_or_top_level(
            value,
            "text_sha256",
        )
        or value.get(
            "draft_text_sha256"
        )
    )

    require(
        recorded_sha
        == EXPECTED_SOURCE_TEXT_SHA,
        "source X draft text SHA mismatch",
    )

    source_draft = value.get(
        "x_draft"
    )

    require(
        isinstance(source_draft, dict),
        "source X draft evidence is missing",
    )

    source_text = source_draft.get(
        "text"
    )

    require(
        source_text == EXPECTED_SOURCE_TEXT,
        "source X draft fixed text mismatch",
    )

    require(
        source_text.count(
            PUBLIC_URL_PLACEHOLDER
        )
        == 1,
        (
            "source X draft must contain exactly "
            "one unresolved public URL placeholder"
        ),
    )

    require(
        EXPECTED_PUBLIC_URL
        not in source_text,
        (
            "source X draft unexpectedly already "
            "contains the published URL"
        ),
    )

    for field in (
        "x_api_call",
        "x_post",
        "normal_x_fb_write",
        "wordpress_write",
    ):
        require(
            value.get(field) is False,
            (
                "source X draft contains an "
                f"unexpected write state: {field}"
            ),
        )


def validate_wording_gate(
    value: dict[str, Any],
) -> None:
    verify_expected_digest(
        value,
        expected_digest=(
            EXPECTED_WORDING_GATE_DIGEST
        ),
        label="X wording review gate",
    )

    require(
        value.get("status")
        == (
            "PASS_X_DRAFT_WORDING_REVIEW_"
            "APPROVED_PUBLIC_URL_PENDING"
        ),
        "X wording gate status mismatch",
    )

    require(
        value.get("wording_gate_state")
        == (
            "WORDING_FIXED_AWAITING_"
            "WORDPRESS_PUBLICATION_AND_PUBLIC_URL"
        ),
        "X wording gate state mismatch",
    )

    human_review = value.get(
        "human_review"
    )

    require(
        isinstance(human_review, dict),
        "X wording human-review evidence is missing",
    )

    require(
        human_review.get("decision")
        == "APPROVED",
        "X wording was not approved",
    )

    require(
        human_review.get(
            "approval_consumed"
        )
        is True,
        "X wording approval was not consumed",
    )

    source_draft = value.get(
        "x_draft"
    )

    require(
        isinstance(source_draft, dict),
        "fixed X draft evidence is missing",
    )

    require(
        source_draft.get("draft_id")
        == EXPECTED_SOURCE_DRAFT_ID,
        "fixed X draft ID mismatch",
    )

    require(
        source_draft.get("text")
        == EXPECTED_SOURCE_TEXT,
        "fixed X draft wording mismatch",
    )

    require(
        source_draft.get("text_sha256")
        == EXPECTED_SOURCE_TEXT_SHA,
        "fixed X draft SHA mismatch",
    )

    require(
        source_draft.get("wording_fixed")
        is True,
        "X wording is not fixed",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "wording gate permits X posting",
    )


def validate_publication_verification(
    value: dict[str, Any],
) -> None:
    verify_expected_digest(
        value,
        expected_digest=(
            EXPECTED_PUBLICATION_VERIFICATION_DIGEST
        ),
        label="WordPress publication verification",
    )

    require(
        value.get("status")
        == (
            "PASS_WORDPRESS_PUBLICATION_"
            "POST_EXECUTION_VERIFICATION"
        ),
        "publication verification status mismatch",
    )

    require(
        value.get("verification_state")
        == (
            "WORDPRESS_POST_195_PUBLISH_AND_"
            "PUBLIC_URL_VERIFIED_"
            "X_URL_REPLACEMENT_READY"
        ),
        "publication verification state mismatch",
    )

    require(
        value.get("public_url_available")
        is True,
        "verified public URL is unavailable",
    )

    require(
        value.get("public_url")
        == EXPECTED_PUBLIC_URL,
        "verified public URL mismatch",
    )

    require(
        value.get(
            "x_public_url_replacement_allowed"
        )
        is True,
        "X public URL replacement is not allowed",
    )

    require(
        value.get(
            "x_final_review_allowed"
        )
        is False,
        "final X review is already allowed",
    )

    require(
        value.get(
            "x_post_execution_allowed"
        )
        is False,
        "publication verification permits X posting",
    )

    require(
        value.get("x_api_call")
        is False,
        "publication verification records an X API call",
    )

    require(
        value.get("x_post")
        is False,
        "publication verification records an X post",
    )

    post = value.get(
        "wordpress_post"
    )

    require(
        isinstance(post, dict),
        "published WordPress post evidence is missing",
    )

    require(
        post.get("post_id") == 195,
        "published WordPress post ID mismatch",
    )

    require(
        post.get("status") == "publish",
        "WordPress post is not published",
    )


def validate_source_text(
    value: str,
) -> None:
    require(
        value == EXPECTED_SOURCE_TEXT,
        "source X draft differs from fixed text",
    )

    require(
        sha256_text(value)
        == EXPECTED_SOURCE_TEXT_SHA,
        "source X draft file SHA mismatch",
    )

    require(
        value.count(
            PUBLIC_URL_PLACEHOLDER
        )
        == 1,
        (
            "source public URL placeholder "
            "count must equal one"
        ),
    )

    require(
        EXPECTED_PUBLIC_URL not in value,
        "source X draft already contains public URL",
    )


def replace_public_url(
    source_text: str,
    public_url: str = EXPECTED_PUBLIC_URL,
) -> str:
    validate_source_text(
        source_text
    )

    require(
        public_url == EXPECTED_PUBLIC_URL,
        "replacement public URL mismatch",
    )

    require(
        public_url.startswith("https://"),
        "replacement public URL must use HTTPS",
    )

    before, after = source_text.split(
        PUBLIC_URL_PLACEHOLDER,
        1,
    )

    result = (
        before
        + public_url
        + after
    )

    require(
        result == EXPECTED_REPLACED_TEXT,
        (
            "public URL replacement changed "
            "fixed wording"
        ),
    )

    require(
        sha256_text(result)
        == EXPECTED_REPLACED_TEXT_SHA,
        "replaced X draft SHA mismatch",
    )

    require(
        PUBLIC_URL_PLACEHOLDER
        not in result,
        "public URL placeholder remains",
    )

    require(
        result.count(public_url) == 1,
        "public URL count must equal one",
    )

    return result


def estimate_tco_character_count(
    value: str,
    public_url: str = EXPECTED_PUBLIC_URL,
) -> int:
    require(
        value.count(public_url) == 1,
        (
            "t.co estimate requires exactly "
            "one public URL"
        ),
    )

    return (
        len(value)
        - len(public_url)
        + TCO_URL_CHARACTER_COUNT
    )


def build_local_prep(
    *,
    production_database_path: Path,
    source_x_draft_pack_path: Path,
    source_x_draft_text_path: Path,
    wording_gate_pack_path: Path,
    publication_verification_path: Path,
    replaced_text_path: Path,
    output_path: Path,
    generation_lock_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    source_x_draft_pack_path = (
        source_x_draft_pack_path.resolve()
    )

    source_x_draft_text_path = (
        source_x_draft_text_path.resolve()
    )

    wording_gate_pack_path = (
        wording_gate_pack_path.resolve()
    )

    publication_verification_path = (
        publication_verification_path.resolve()
    )

    replaced_text_path = (
        replaced_text_path.resolve()
    )

    output_path = output_path.resolve()

    generation_lock_path = (
        generation_lock_path.resolve()
    )

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    for path, label in (
        (
            replaced_text_path,
            "replaced X draft text",
        ),
        (
            output_path,
            "replacement prep pack",
        ),
        (
            generation_lock_path,
            "replacement generation lock",
        ),
    ):
        require(
            not path.exists(),
            f"{label} already exists",
        )

    source_pack = load_json(
        source_x_draft_pack_path
    )

    validate_source_x_draft_pack(
        source_pack
    )

    wording_gate = load_json(
        wording_gate_pack_path
    )

    validate_wording_gate(
        wording_gate
    )

    publication_verification = load_json(
        publication_verification_path
    )

    validate_publication_verification(
        publication_verification
    )

    require(
        source_x_draft_text_path.is_file(),
        "source X draft text file is missing",
    )

    source_file_sha_before = sha256_file(
        source_x_draft_text_path
    )

    require(
        source_file_sha_before
        == EXPECTED_SOURCE_TEXT_SHA,
        "source X draft file SHA changed",
    )

    source_text = (
        source_x_draft_text_path.read_text(
            encoding="utf-8"
        )
    )

    replaced_text = replace_public_url(
        source_text
    )

    literal_character_count = len(
        replaced_text
    )

    require(
        literal_character_count
        == EXPECTED_LITERAL_CHARACTER_COUNT,
        "literal character count mismatch",
    )

    tco_character_count = (
        estimate_tco_character_count(
            replaced_text
        )
    )

    require(
        tco_character_count
        == EXPECTED_TCO_CHARACTER_COUNT,
        "estimated t.co character count mismatch",
    )

    atomic_create_text(
        replaced_text_path,
        replaced_text,
    )

    require(
        sha256_file(
            replaced_text_path
        )
        == EXPECTED_REPLACED_TEXT_SHA,
        "written replaced draft SHA mismatch",
    )

    require(
        sha256_file(
            source_x_draft_text_path
        )
        == source_file_sha_before,
        "source X draft was modified",
    )

    prepared_at = datetime.now(
        timezone.utc
    ).isoformat()

    prep_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_DRAFT_PUBLIC_URL_"
            "REPLACEMENT_LOCAL_PREP"
        ),
        "replacement_state": (
            "PUBLIC_URL_REPLACED_LOCAL_DRAFT_"
            "GENERATED_FINAL_HUMAN_REVIEW_REQUIRED"
        ),
        "prepared_at": prepared_at,
        "source_x_draft_pack_path": str(
            source_x_draft_pack_path
        ),
        "source_x_draft_pack_digest_sha256": (
            EXPECTED_SOURCE_X_DRAFT_PACK_DIGEST
        ),
        "source_x_draft_text_path": str(
            source_x_draft_text_path
        ),
        "source_x_draft_id": (
            EXPECTED_SOURCE_DRAFT_ID
        ),
        "source_x_draft_text_sha256": (
            EXPECTED_SOURCE_TEXT_SHA
        ),
        "source_wording_gate_pack_path": str(
            wording_gate_pack_path
        ),
        "source_wording_gate_digest_sha256": (
            EXPECTED_WORDING_GATE_DIGEST
        ),
        "source_publication_verification_path": str(
            publication_verification_path
        ),
        "source_publication_verification_digest_sha256": (
            EXPECTED_PUBLICATION_VERIFICATION_DIGEST
        ),
        "wordpress_post": {
            "post_id": 195,
            "status": "publish",
            "public_url_available": True,
            "public_url": EXPECTED_PUBLIC_URL,
            "public_http_status": 200,
        },
        "x_draft": {
            "draft_id": (
                EXPECTED_REPLACED_DRAFT_ID
            ),
            "revision": (
                "PUBLIC_URL_BOUND_V1"
            ),
            "text": replaced_text,
            "text_path": str(
                replaced_text_path
            ),
            "text_sha256": (
                EXPECTED_REPLACED_TEXT_SHA
            ),
            "literal_character_count": (
                literal_character_count
            ),
            "estimated_tco_character_count": (
                tco_character_count
            ),
            "public_url": (
                EXPECTED_PUBLIC_URL
            ),
            "public_url_count": 1,
            "public_url_placeholder_absent": True,
            "wording_outside_url_unchanged": True,
        },
        "source_x_draft_preserved": True,
        "source_x_draft_modified": False,
        "public_url_replacement_completed": True,
        "public_url_unresolved": False,
        "final_human_review_required": True,
        "final_human_review_completed": False,
        "x_final_review_allowed": False,
        "x_post_approval_issued": False,
        "x_post_execution_allowed": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PUBLIC_URL_BOUND_LOCAL_DRAFT_"
            "FINAL_REVIEW_PENDING_"
            "ALL_EXTERNAL_X_ACTIONS_BLOCKED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-DRAFT-FINAL-HUMAN-REVIEW-PREP"
        ),
    }

    prep = {
        **prep_payload,
        "x_draft_public_url_replacement_"
        "local_prep_digest_sha256": (
            canonical_digest(
                prep_payload
            )
        ),
    }

    atomic_create_json(
        output_path,
        prep,
    )

    lock_payload = {
        "lock_type": (
            "X_R11_X_DRAFT_PUBLIC_URL_"
            "REPLACEMENT_LOCAL_GENERATION"
        ),
        "created_at": prepared_at,
        "source_publication_verification_digest_sha256": (
            EXPECTED_PUBLICATION_VERIFICATION_DIGEST
        ),
        "source_x_draft_id": (
            EXPECTED_SOURCE_DRAFT_ID
        ),
        "replacement_x_draft_id": (
            EXPECTED_REPLACED_DRAFT_ID
        ),
        "replacement_text_sha256": (
            EXPECTED_REPLACED_TEXT_SHA
        ),
        "replacement_pack_path": str(
            output_path
        ),
        "replacement_pack_digest_sha256": (
            prep[
                "x_draft_public_url_replacement_"
                "local_prep_digest_sha256"
            ]
        ),
        "generation_completed": True,
        "reexecution_allowed": False,
    }

    atomic_create_json(
        generation_lock_path,
        lock_payload,
    )

    return prep


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--source-x-draft-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--source-x-draft-text",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--wording-gate-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--publication-verification",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--replaced-text",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--generation-lock",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = build_local_prep(
            production_database_path=(
                args.production_db
            ),
            source_x_draft_pack_path=(
                args.source_x_draft_pack
            ),
            source_x_draft_text_path=(
                args.source_x_draft_text
            ),
            wording_gate_pack_path=(
                args.wording_gate_pack
            ),
            publication_verification_path=(
                args.publication_verification
            ),
            replaced_text_path=(
                args.replaced_text
            ),
            output_path=args.output,
            generation_lock_path=(
                args.generation_lock
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_DRAFT_PUBLIC_URL_"
                        "REPLACEMENT_LOCAL_PREP"
                    ),
                    "error": str(exc),
                    "source_x_draft_modified": False,
                    "final_human_review_completed": False,
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

    draft = result[
        "x_draft"
    ]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "replacement_state": (
                    result["replacement_state"]
                ),
                "source_x_draft_id": (
                    result["source_x_draft_id"]
                ),
                "replacement_x_draft_id": (
                    draft["draft_id"]
                ),
                "replacement_text_sha256": (
                    draft["text_sha256"]
                ),
                "literal_character_count": (
                    draft[
                        "literal_character_count"
                    ]
                ),
                "estimated_tco_character_count": (
                    draft[
                        "estimated_tco_character_count"
                    ]
                ),
                "public_url": (
                    draft["public_url"]
                ),
                "source_x_draft_preserved": True,
                "public_url_replacement_completed": True,
                "final_human_review_required": True,
                "final_human_review_completed": False,
                "x_final_review_allowed": False,
                "x_post_approval_issued": False,
                "x_post_execution_allowed": False,
                "x_api_call": False,
                "x_post": False,
                "production_status": "NO_GO",
                "replaced_text_path": str(
                    args.replaced_text.resolve()
                ),
                "replacement_pack_path": str(
                    args.output.resolve()
                ),
                "replacement_pack_digest_sha256": (
                    result[
                        "x_draft_public_url_"
                        "replacement_local_prep_"
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
