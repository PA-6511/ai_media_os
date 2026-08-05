from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import atomic_write_json
from scripts.build_x_r9_preflight_approval_pack import canonical_digest


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-DRAFT-CREATION-ONE-SHOT"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_FINAL_GATE_DIGEST = (
    "f348d6f37980fdd5ccd5e9c9f5bc84c3"
    "7afc80509b369cd293fb5614f7edfd86"
)

EXPECTED_APPROVAL_CERTIFICATE_DIGEST = (
    "794843a83eb52837ea01181754f3f3f66"
    "89f1eb4c8ca6225adc85884203962fa"
)

EXPECTED_CREATION_REQUEST_ID = (
    "xr11-wp-draft-create-"
    "baf4e4451e14b3b4b3984bd2"
)

EXPECTED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "DRAFT_CREATION_ONLY"
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
HTTP_TIMEOUT_SECONDS = 20

POST_STATUSES = (
    "publish",
    "future",
    "draft",
    "pending",
    "private",
)


class DraftCreationError(RuntimeError):
    pass


class WordPressHTTPError(DraftCreationError):
    def __init__(
        self,
        *,
        method: str,
        url: str,
        status_code: int,
        response_body: str,
    ) -> None:
        self.method = method
        self.url = url
        self.status_code = status_code
        self.response_body = response_body

        super().__init__(
            f"WordPress HTTP {status_code} "
            f"during {method} {url}: "
            f"{response_body[:500]}"
        )


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise DraftCreationError(message)


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise DraftCreationError(
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
    expected_digest: str | None,
    label: str,
) -> str:
    recorded = value.get(digest_field)

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
        f"{label} canonical digest verification failed",
    )

    return recorded


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
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise DraftCreationError(
            f"one-shot artifact already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def parse_env_file(
    path: Path,
) -> dict[str, str]:
    path = path.resolve()

    require(
        path.is_file(),
        f"credential env file is missing: {path}",
    )

    mode = stat.S_IMODE(
        path.stat().st_mode
    )

    require(
        mode == 0o600,
        (
            "credential env mode must equal "
            f"0600; actual={oct(mode)}"
        ),
    )

    require(
        path.stat().st_uid == os.geteuid(),
        (
            "credential env owner must equal "
            "the executing user"
        ),
    )

    result: dict[str, str] = {}

    for line_number, raw_line in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        require(
            "=" in line,
            (
                "credential env line has no '=': "
                f"line={line_number}"
            ),
        )

        key, raw_value = line.split(
            "=",
            1,
        )

        key = key.strip()
        value = raw_value.strip()

        require(
            re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*",
                key,
            )
            is not None,
            (
                "credential env key is invalid: "
                f"line={line_number}"
            ),
        )

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        result[key] = value

    return result


def first_env(
    values: dict[str, str],
    names: tuple[str, ...],
    label: str,
) -> str:
    matches = [
        values[name].strip()
        for name in names
        if values.get(name, "").strip()
    ]

    unique = list(
        dict.fromkeys(matches)
    )

    require(
        len(unique) == 1,
        (
            f"{label} must resolve to exactly "
            f"one value; found={len(unique)}"
        ),
    )

    return unique[0]


def build_rest_base(
    values: dict[str, str],
) -> str:
    direct_names = (
        "WORDPRESS_REST_BASE_URL",
        "WP_REST_BASE_URL",
    )

    direct_values = [
        values[name].strip()
        for name in direct_names
        if values.get(name, "").strip()
    ]

    if direct_values:
        require(
            len(set(direct_values)) == 1,
            "multiple REST base URLs conflict",
        )
        base = direct_values[0].rstrip("/")
    else:
        base = first_env(
            values,
            (
                "WORDPRESS_BASE_URL",
                "WP_BASE_URL",
                "WORDPRESS_SITE_URL",
                "WP_SITE_URL",
                "WORDPRESS_URL",
                "WP_URL",
            ),
            "WordPress site URL",
        ).rstrip("/")

    parsed = urllib.parse.urlparse(base)

    require(
        parsed.scheme == "https",
        "WordPress URL must use HTTPS",
    )

    require(
        bool(parsed.hostname),
        "WordPress URL hostname is missing",
    )

    if base.endswith("/wp-json/wp/v2"):
        return base

    if base.endswith("/wp-json"):
        return base + "/wp/v2"

    return base + "/wp-json/wp/v2"


def build_authorization_header(
    username: str,
    application_password: str,
) -> str:
    token = base64.b64encode(
        (
            username
            + ":"
            + application_password
        ).encode("utf-8")
    ).decode("ascii")

    return "Basic " + token


def request_json(
    *,
    method: str,
    url: str,
    authorization: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    data: bytes | None = None

    headers = {
        "Accept": "application/json",
        "Authorization": authorization,
        "User-Agent": (
            "ai-media-os-x-r11-one-shot/1.0"
        ),
    }

    if payload is not None:
        data = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        headers["Content-Type"] = (
            "application/json; charset=utf-8"
        )

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            body = response.read().decode(
                "utf-8"
            )

    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
        except Exception:
            body = "<unreadable response body>"

        raise WordPressHTTPError(
            method=method,
            url=url,
            status_code=exc.code,
            response_body=body,
        ) from exc

    except urllib.error.URLError as exc:
        raise DraftCreationError(
            f"WordPress connection failed: {exc}"
        ) from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise DraftCreationError(
            (
                "WordPress returned invalid JSON: "
                f"{body[:500]}"
            )
        ) from exc


def collection_url(
    rest_base: str,
    resource: str,
    parameters: dict[str, Any],
) -> str:
    return (
        rest_base.rstrip("/")
        + "/"
        + resource.lstrip("/")
        + "?"
        + urllib.parse.urlencode(
            parameters,
            doseq=True,
        )
    )


def extract_title(
    post: dict[str, Any],
) -> str:
    title = post.get("title")

    if isinstance(title, str):
        return title.strip()

    if isinstance(title, dict):
        for key in ("raw", "rendered"):
            value = title.get(key)

            if isinstance(value, str):
                cleaned = re.sub(
                    r"<[^>]+>",
                    "",
                    html.unescape(value),
                ).strip()

                if cleaned:
                    return cleaned

    return ""


def find_duplicate_posts(
    *,
    rest_base: str,
    authorization: str,
) -> dict[str, Any]:
    common = {
        "context": "edit",
        "per_page": 100,
        "status[]": list(POST_STATUSES),
        "_fields": "id,slug,status,title",
    }

    slug_url = collection_url(
        rest_base,
        "posts",
        {
            **common,
            "slug": EXPECTED_SLUG,
        },
    )

    slug_result = request_json(
        method="GET",
        url=slug_url,
        authorization=authorization,
    )

    require(
        isinstance(slug_result, list),
        "slug duplicate response must be a list",
    )

    slug_matches = [
        post
        for post in slug_result
        if (
            isinstance(post, dict)
            and post.get("slug")
            == EXPECTED_SLUG
        )
    ]

    title_url = collection_url(
        rest_base,
        "posts",
        {
            **common,
            "search": EXPECTED_TITLE,
        },
    )

    title_result = request_json(
        method="GET",
        url=title_url,
        authorization=authorization,
    )

    require(
        isinstance(title_result, list),
        "title duplicate response must be a list",
    )

    title_matches = [
        post
        for post in title_result
        if (
            isinstance(post, dict)
            and extract_title(post)
            == EXPECTED_TITLE
        )
    ]

    matched_ids = sorted(
        {
            int(post["id"])
            for post in (
                slug_matches
                + title_matches
            )
            if isinstance(
                post.get("id"),
                int,
            )
        }
    )

    return {
        "slug_query_count": len(
            slug_result
        ),
        "title_query_count": len(
            title_result
        ),
        "exact_slug_match_count": len(
            slug_matches
        ),
        "exact_title_match_count": len(
            title_matches
        ),
        "matched_post_ids": matched_ids,
        "duplicate_found": bool(
            slug_matches or title_matches
        ),
    }


def validate_category(
    *,
    rest_base: str,
    authorization: str,
) -> dict[str, Any]:
    url = (
        rest_base.rstrip("/")
        + "/categories/"
        + str(EXPECTED_CATEGORY_ID)
        + "?context=edit"
        + "&_fields=id,name,slug"
    )

    category = request_json(
        method="GET",
        url=url,
        authorization=authorization,
    )

    require(
        isinstance(category, dict),
        "category response must be an object",
    )

    require(
        category.get("id")
        == EXPECTED_CATEGORY_ID,
        "category ID mismatch",
    )

    require(
        category.get("slug")
        == "comic-new-release",
        "category slug mismatch",
    )

    require(
        category.get("name")
        == "コミック新刊",
        "category name mismatch",
    )

    return {
        "id": category["id"],
        "name": category["name"],
        "slug": category["slug"],
    }


def validate_created_post(
    post: dict[str, Any],
    *,
    expected_content: str,
) -> dict[str, Any]:
    require(
        isinstance(post.get("id"), int)
        and post["id"] > 0,
        "created post ID is invalid",
    )

    require(
        post.get("status") == "draft",
        "created post status must equal draft",
    )

    require(
        post.get("slug") == EXPECTED_SLUG,
        "created post slug mismatch",
    )

    categories = post.get("categories")

    require(
        isinstance(categories, list)
        and categories
        == [EXPECTED_CATEGORY_ID],
        "created post categories mismatch",
    )

    require(
        extract_title(post)
        == EXPECTED_TITLE,
        "created post title mismatch",
    )

    content = post.get("content")

    if isinstance(content, dict):
        raw_content = content.get(
            "raw"
        )
    else:
        raw_content = content

    require(
        raw_content == expected_content,
        "created post content mismatch",
    )

    return {
        "post_id": post["id"],
        "title": EXPECTED_TITLE,
        "slug": post["slug"],
        "status": post["status"],
        "categories": categories,
        "link": post.get("link"),
    }


def run_one_shot(
    *,
    production_database_path: Path,
    final_gate_pack_path: Path,
    approval_certificate_path: Path,
    issuance_lock_path: Path,
    credential_env_path: Path,
    execution_claim_path: Path,
    consumption_lock_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    state = {
        "duplicate_preflight_completed": False,
        "execution_claim_created": False,
        "wordpress_post_attempted": False,
        "wordpress_post_created": False,
    }

    try:
        require(
            sha256_file(
                production_database_path
            )
            == EXPECTED_DATABASE_SHA,
            "production database changed",
        )

        require(
            not execution_claim_path.exists(),
            "execution claim already exists",
        )

        require(
            not consumption_lock_path.exists(),
            "creation approval was already consumed",
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
            label="Final Gate",
        )

        require(
            final_gate.get(
                "creation_request_id"
            )
            == EXPECTED_CREATION_REQUEST_ID,
            "creation request ID mismatch",
        )

        require(
            final_gate.get(
                "next_approval_label"
            )
            == EXPECTED_APPROVAL_LABEL,
            "Final Gate approval label mismatch",
        )

        approval = load_json(
            approval_certificate_path
        )

        verify_digest(
            approval,
            digest_field=(
                "wordpress_draft_creation_"
                "approval_certificate_digest_sha256"
            ),
            expected_digest=(
                EXPECTED_APPROVAL_CERTIFICATE_DIGEST
            ),
            label="creation approval certificate",
        )

        require(
            approval.get("status")
            == (
                "WORDPRESS_DRAFT_CREATION_"
                "APPROVAL_ISSUED_NOT_CONSUMED"
            ),
            "creation approval status mismatch",
        )

        require(
            approval.get("approval_label")
            == EXPECTED_APPROVAL_LABEL,
            "creation approval label mismatch",
        )

        require(
            approval.get(
                "creation_request_id"
            )
            == EXPECTED_CREATION_REQUEST_ID,
            "approval creation request ID mismatch",
        )

        require(
            approval.get(
                "runner_execution_allowed"
            )
            is True,
            "runner execution is not allowed",
        )

        require(
            approval.get(
                "approval_consumed"
            )
            is False,
            "approval is already consumed",
        )

        require(
            approval.get(
                "draft_creation_executed"
            )
            is False,
            "draft creation was already executed",
        )

        issuance_lock = load_json(
            issuance_lock_path
        )

        require(
            issuance_lock.get(
                "approval_certificate_digest_sha256"
            )
            == EXPECTED_APPROVAL_CERTIFICATE_DIGEST,
            "issuance lock certificate mismatch",
        )

        require(
            issuance_lock.get(
                "approval_consumed"
            )
            is False,
            "issuance lock says approval is consumed",
        )

        payload_preview_path = Path(
            final_gate[
                "payload_preview_path"
            ]
        ).resolve()

        payload_preview = load_json(
            payload_preview_path
        )

        payload_digest = verify_digest(
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
            label="payload preview",
        )

        request_payload = payload_preview.get(
            "wordpress_request"
        )

        require(
            isinstance(request_payload, dict),
            "WordPress request payload is missing",
        )

        require(
            request_payload.get("title")
            == EXPECTED_TITLE,
            "payload title mismatch",
        )

        require(
            request_payload.get("slug")
            == EXPECTED_SLUG,
            "payload slug mismatch",
        )

        require(
            request_payload.get("status")
            == "draft",
            "payload status must equal draft",
        )

        require(
            request_payload.get("categories")
            == [EXPECTED_CATEGORY_ID],
            "payload category mismatch",
        )

        content = request_payload.get(
            "content"
        )

        require(
            isinstance(content, str)
            and content,
            "payload content is missing",
        )

        require(
            sha256_file(
                Path(
                    final_gate[
                        "rendered_html_path"
                    ]
                )
            )
            == final_gate[
                "rendered_html_sha256"
            ],
            "rendered HTML changed after Final Gate",
        )

        env_values = parse_env_file(
            credential_env_path
        )

        rest_base = build_rest_base(
            env_values
        )

        username = first_env(
            env_values,
            (
                "WORDPRESS_USERNAME",
                "WP_USERNAME",
                "WORDPRESS_USER",
                "WP_USER",
            ),
            "WordPress username",
        )

        application_password = first_env(
            env_values,
            (
                "WORDPRESS_APPLICATION_PASSWORD",
                "WP_APPLICATION_PASSWORD",
                "WORDPRESS_APP_PASSWORD",
                "WP_APP_PASSWORD",
            ),
            "WordPress application password",
        )

        authorization = (
            build_authorization_header(
                username,
                application_password,
            )
        )

        duplicate_check = (
            find_duplicate_posts(
                rest_base=rest_base,
                authorization=authorization,
            )
        )

        state[
            "duplicate_preflight_completed"
        ] = True

        require(
            duplicate_check[
                "duplicate_found"
            ]
            is False,
            (
                "duplicate WordPress post found: "
                f"{duplicate_check}"
            ),
        )

        category = validate_category(
            rest_base=rest_base,
            authorization=authorization,
        )

        claimed_at = datetime.now(
            timezone.utc
        ).isoformat()

        claim_payload = {
            "lock_type": (
                "X_R11_WORDPRESS_DRAFT_"
                "CREATION_EXECUTION_CLAIM"
            ),
            "created_at": claimed_at,
            "creation_request_id": (
                EXPECTED_CREATION_REQUEST_ID
            ),
            "approval_certificate_digest_sha256": (
                EXPECTED_APPROVAL_CERTIFICATE_DIGEST
            ),
            "payload_preview_digest_sha256": (
                payload_digest
            ),
            "duplicate_preflight": (
                duplicate_check
            ),
            "category_preflight": category,
            "maximum_post_create_count": 1,
            "execution_claimed": True,
            "reexecution_allowed": False,
        }

        atomic_create_json(
            execution_claim_path,
            claim_payload,
        )

        state[
            "execution_claim_created"
        ] = True

        posts_url = (
            rest_base.rstrip("/")
            + "/posts"
        )

        state[
            "wordpress_post_attempted"
        ] = True

        created = request_json(
            method="POST",
            url=posts_url,
            authorization=authorization,
            payload=request_payload,
        )

        require(
            isinstance(created, dict),
            "WordPress POST response is invalid",
        )

        created_post_id = created.get("id")

        require(
            isinstance(created_post_id, int)
            and created_post_id > 0,
            "WordPress POST returned no post ID",
        )

        verify_url = (
            rest_base.rstrip("/")
            + "/posts/"
            + str(created_post_id)
            + "?context=edit"
            + "&_fields=id,title,slug,status,"
            + "categories,content,link"
        )

        verified = request_json(
            method="GET",
            url=verify_url,
            authorization=authorization,
        )

        require(
            isinstance(verified, dict),
            "post-verification response is invalid",
        )

        post_result = validate_created_post(
            verified,
            expected_content=content,
        )

        state[
            "wordpress_post_created"
        ] = True

        consumed_at = datetime.now(
            timezone.utc
        ).isoformat()

        consumption_payload = {
            "lock_type": (
                "X_R11_WORDPRESS_DRAFT_"
                "CREATION_APPROVAL_CONSUMPTION"
            ),
            "created_at": consumed_at,
            "creation_request_id": (
                EXPECTED_CREATION_REQUEST_ID
            ),
            "approval_certificate_path": str(
                approval_certificate_path.resolve()
            ),
            "approval_certificate_digest_sha256": (
                EXPECTED_APPROVAL_CERTIFICATE_DIGEST
            ),
            "execution_claim_path": str(
                execution_claim_path.resolve()
            ),
            "wordpress_post_id": (
                post_result["post_id"]
            ),
            "wordpress_post_status": "draft",
            "approval_consumed": True,
            "reexecution_allowed": False,
        }

        atomic_create_json(
            consumption_lock_path,
            consumption_payload,
        )

        receipt_payload = {
            "phase": PHASE,
            "status": (
                "PASS_WORDPRESS_DRAFT_CREATED_"
                "ONE_SHOT"
            ),
            "executed_at": consumed_at,
            "creation_request_id": (
                EXPECTED_CREATION_REQUEST_ID
            ),
            "source_final_gate_digest_sha256": (
                EXPECTED_FINAL_GATE_DIGEST
            ),
            "approval_certificate_digest_sha256": (
                EXPECTED_APPROVAL_CERTIFICATE_DIGEST
            ),
            "payload_preview_digest_sha256": (
                payload_digest
            ),
            "duplicate_preflight": (
                duplicate_check
            ),
            "category_preflight": category,
            "wordpress_post": post_result,
            "approval_consumed": True,
            "runner_execution_allowed": False,
            "reexecution_allowed": False,
            "maximum_create_count": 1,
            "actual_create_count": 1,
            "draft_creation_executed": True,
            "wordpress_api_call": True,
            "wordpress_write": True,
            "wordpress_post_creation": True,
            "wordpress_post_status": "draft",
            "publication_allowed": False,
            "wordpress_media_upload_required_before_publish": (
                True
            ),
            "database_write": False,
            "workflow_write": False,
            "x_api_call": False,
            "x_post": False,
            "production_status": "NO_GO",
            "safety_state": (
                "ONE_WORDPRESS_DRAFT_CREATED_"
                "REEXECUTION_BLOCKED"
            ),
            "authorized_next_phase": (
                "X-R11-PRODUCTION-CANDIDATE-1-"
                "WORDPRESS-DRAFT-POST-CREATION-"
                "VERIFICATION"
            ),
        }

        receipt = {
            **receipt_payload,
            "wordpress_draft_creation_"
            "one_shot_receipt_digest_sha256": (
                canonical_digest(
                    receipt_payload
                )
            ),
        }

        atomic_write_json(
            receipt_path,
            receipt,
        )

        return receipt

    except Exception as exc:
        failure_payload = {
            "phase": PHASE,
            "status": (
                "FAIL_WORDPRESS_DRAFT_CREATION_"
                "ONE_SHOT"
            ),
            "failed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "error": str(exc),
            **state,
            "approval_consumed": False,
            "automatic_reexecution_allowed": False,
            "manual_verification_required": bool(
                state[
                    "execution_claim_created"
                ]
            ),
            "wordpress_api_call": bool(
                state[
                    "wordpress_post_attempted"
                ]
            ),
            "wordpress_write_possible": bool(
                state[
                    "wordpress_post_attempted"
                ]
            ),
            "database_write": False,
            "workflow_write": False,
            "x_api_call": False,
            "x_post": False,
            "production_status": "NO_GO",
        }

        failure = {
            **failure_payload,
            "wordpress_draft_creation_"
            "failure_receipt_digest_sha256": (
                canonical_digest(
                    failure_payload
                )
            ),
        }

        atomic_write_json(
            receipt_path,
            failure,
        )

        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--final-gate-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--approval-certificate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--issuance-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--credential-env",
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
        "--receipt",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_one_shot(
            production_database_path=(
                args.production_db.resolve()
            ),
            final_gate_pack_path=(
                args.final_gate_pack.resolve()
            ),
            approval_certificate_path=(
                args.approval_certificate.resolve()
            ),
            issuance_lock_path=(
                args.issuance_lock.resolve()
            ),
            credential_env_path=(
                args.credential_env.resolve()
            ),
            execution_claim_path=(
                args.execution_claim.resolve()
            ),
            consumption_lock_path=(
                args.consumption_lock.resolve()
            ),
            receipt_path=(
                args.receipt.resolve()
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_DRAFT_"
                        "CREATION_ONE_SHOT"
                    ),
                    "error": str(exc),
                    "automatic_reexecution_allowed": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    post = result["wordpress_post"]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "creation_request_id": (
                    result["creation_request_id"]
                ),
                "wordpress_post_id": (
                    post["post_id"]
                ),
                "wordpress_post_title": (
                    post["title"]
                ),
                "wordpress_post_slug": (
                    post["slug"]
                ),
                "wordpress_post_status": (
                    post["status"]
                ),
                "wordpress_category_ids": (
                    post["categories"]
                ),
                "wordpress_post_link": (
                    post["link"]
                ),
                "actual_create_count": 1,
                "approval_consumed": True,
                "reexecution_allowed": False,
                "wordpress_api_call": True,
                "wordpress_write": True,
                "publication_allowed": False,
                "production_status": "NO_GO",
                "receipt_path": str(
                    args.receipt.resolve()
                ),
                "receipt_digest_sha256": (
                    result[
                        "wordpress_draft_creation_"
                        "one_shot_receipt_digest_sha256"
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
