#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import os
import re
import ssl
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "one_shot_recheck_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "recheck_execute_request.example.json"
)
RECHECK_RESULT_PATH = (
    ROOT
    / "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_result.json"
)
CONSUMPTION_PATH = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_consumption.json"
)
PACKAGE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "recheck_result_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m2_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_m2_"
    "dmm_latest_alias_recheck_report.md"
)


class ValidationError(RuntimeError):
    pass


class RedirectPolicyError(RuntimeError):
    pass


class ResponseLimitError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise ValidationError(message)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def digest(value: Any) -> str:
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


def write_exclusive_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
    )

    fd = os.open(
        path,
        flags,
        0o600,
    )

    try:
        with os.fdopen(
            fd,
            "wb",
            closefd=True,
        ) as handle:
            handle.write(
                json_bytes(value)
            )
            handle.flush()
            os.fsync(
                handle.fileno()
            )
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise

    directory_fd = os.open(
        path.parent,
        os.O_RDONLY,
    )

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


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
    field: str,
    expected: str,
    label: str,
) -> str:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
        f"{label} digest invalid",
    )
    require(
        stored == expected,
        f"{label} digest mismatch",
    )

    return stored


def normalize_text(value: str) -> str:
    return " ".join(
        unicodedata.normalize(
            "NFKC",
            value,
        ).split()
    )


def extract_expected_volume_from_title_candidates(
    candidates: list[str],
    *,
    expected_work_title: str,
    expected_volume_number: int,
) -> tuple[str | None, str | None]:
    normalized_work_title = normalize_text(
        expected_work_title
    )
    escaped_number = re.escape(
        str(expected_volume_number)
    )

    prefix = r"^[\s:：\-–—|｜/]*"
    terminator = (
        r"(?=$|[\s(（\[【\-–—|｜:：/])"
    )

    patterns = [
        re.compile(
            prefix
            + rf"第\s*{escaped_number}\s*巻"
            + terminator
        ),
        re.compile(
            prefix
            + rf"{escaped_number}\s*巻"
            + terminator
        ),
        re.compile(
            prefix
            + rf"{escaped_number}"
            + terminator
        ),
    ]

    for candidate in candidates:
        normalized_candidate = normalize_text(
            candidate
        )

        work_index = normalized_candidate.find(
            normalized_work_title
        )

        if work_index < 0:
            continue

        suffix = normalized_candidate[
            work_index + len(normalized_work_title):
        ]

        for pattern in patterns:
            if pattern.search(suffix):
                return (
                    f"第{expected_volume_number}巻",
                    (
                        "TITLE_OR_STRUCTURED_DATA_"
                        "WORK_BOUND_VOLUME"
                    ),
                )

    return None, None


def validate_https_book_dmm_url(
    value: str,
    *,
    allow_latest: bool,
) -> str:
    parsed = urllib.parse.urlparse(
        value
    )

    if parsed.scheme != "https":
        raise RedirectPolicyError(
            "URL_SCHEME_NOT_ALLOWED"
        )

    if parsed.hostname != "book.dmm.com":
        raise RedirectPolicyError(
            "URL_HOST_NOT_ALLOWED"
        )

    if parsed.username or parsed.password:
        raise RedirectPolicyError(
            "URL_USERINFO_NOT_ALLOWED"
        )

    normalized = urllib.parse.urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            "",
        )
    )

    if (
        not allow_latest
        and normalized
        == (
            "https://book.dmm.com/"
            "product/861056/latest/"
        )
    ):
        raise RedirectPolicyError(
            "LATEST_ALIAS_NOT_CANONICAL"
        )

    return normalized


class StrictRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    def __init__(
        self,
        *,
        maximum_redirect_count: int,
        request_headers: dict[str, str],
    ) -> None:
        super().__init__()
        self.maximum_redirect_count = (
            maximum_redirect_count
        )
        self.request_headers = dict(
            request_headers
        )
        self.redirect_chain: list[
            dict[str, Any]
        ] = []

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request:
        if len(
            self.redirect_chain
        ) >= self.maximum_redirect_count:
            raise RedirectPolicyError(
                "MAXIMUM_REDIRECT_COUNT_EXCEEDED"
            )

        resolved = urllib.parse.urljoin(
            req.full_url,
            newurl,
        )

        normalized = (
            validate_https_book_dmm_url(
                resolved,
                allow_latest=True,
            )
        )

        self.redirect_chain.append(
            {
                "status": code,
                "from_url": req.full_url,
                "to_url": normalized,
            }
        )

        return urllib.request.Request(
            normalized,
            headers=self.request_headers,
            method="GET",
        )


class MinimalPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.title_parts: list[str] = []
        self.meta: dict[str, list[str]] = {}
        self.canonical_urls: list[str] = []
        self.text_parts: list[str] = []
        self.json_ld_parts: list[str] = []
        self.in_title = False
        self.in_json_ld = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        values = {
            key.lower(): value or ""
            for key, value in attrs
        }

        if tag.lower() == "title":
            self.in_title = True

        if tag.lower() == "meta":
            name = (
                values.get("property")
                or values.get("name")
                or ""
            ).lower()
            content = values.get(
                "content",
                "",
            )

            if name and content:
                self.meta.setdefault(
                    name,
                    [],
                ).append(content)

        if tag.lower() == "link":
            rel_tokens = {
                token.lower()
                for token in values.get(
                    "rel",
                    "",
                ).split()
            }

            href = values.get(
                "href",
                "",
            )

            if "canonical" in rel_tokens and href:
                self.canonical_urls.append(
                    href
                )

        if tag.lower() == "script":
            script_type = values.get(
                "type",
                "",
            ).lower()

            self.in_json_ld = (
                script_type
                == "application/ld+json"
            )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if tag.lower() == "title":
            self.in_title = False

        if tag.lower() == "script":
            self.in_json_ld = False

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self.in_json_ld:
            self.json_ld_parts.append(
                data
            )
            return

        compact = normalize_text(data)

        if not compact:
            return

        if self.in_title:
            self.title_parts.append(
                compact
            )

        if sum(
            len(part)
            for part in self.text_parts
        ) < 2000000:
            self.text_parts.append(
                compact
            )


def collect_json_ld_values(
    value: Any,
    *,
    names: list[str],
) -> list[str]:
    results: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            if key in names:
                if isinstance(child, str):
                    results.append(child)
                elif isinstance(child, dict):
                    name = child.get("name")

                    if isinstance(name, str):
                        results.append(name)
                elif isinstance(child, list):
                    for item in child:
                        if isinstance(item, str):
                            results.append(item)
                        elif isinstance(item, dict):
                            name = item.get("name")

                            if isinstance(name, str):
                                results.append(name)

            results.extend(
                collect_json_ld_values(
                    child,
                    names=names,
                )
            )

    elif isinstance(value, list):
        for child in value:
            results.extend(
                collect_json_ld_values(
                    child,
                    names=names,
                )
            )

    return results


def parse_json_ld(
    parser: MinimalPageParser,
) -> list[Any]:
    values: list[Any] = []

    for part in parser.json_ld_parts:
        stripped = part.strip()

        if not stripped:
            continue

        try:
            values.append(
                json.loads(stripped)
            )
        except json.JSONDecodeError:
            continue

    return values


def first_matching_candidate(
    candidates: list[str],
    expected: str,
) -> tuple[
    str | None,
    str | None,
]:
    expected_normalized = normalize_text(
        expected
    )

    for candidate in candidates:
        normalized = normalize_text(
            candidate
        )

        if (
            expected_normalized
            in normalized
        ):
            return normalized, "METADATA_OR_STRUCTURED_DATA"

    return None, None


def read_limited_body(
    response: Any,
    maximum_bytes: int,
) -> tuple[
    bytes,
    str,
    int,
]:
    hasher = hashlib.sha256()
    buffer = bytearray()
    total = 0

    while True:
        chunk = response.read(
            65536
        )

        if not chunk:
            break

        total += len(chunk)

        if total > maximum_bytes:
            raise ResponseLimitError(
                "MAXIMUM_RAW_RESPONSE_BYTES_EXCEEDED"
            )

        hasher.update(chunk)
        buffer.extend(chunk)

    return (
        bytes(buffer),
        hasher.hexdigest(),
        total,
    )


def decode_response_body(
    raw_body: bytes,
    content_encoding: str,
) -> bytes:
    encoding = content_encoding.strip().lower()

    if encoding in {
        "",
        "identity",
    }:
        return raw_body

    if encoding == "gzip":
        return gzip.decompress(
            raw_body
        )

    if encoding == "deflate":
        try:
            return zlib.decompress(
                raw_body
            )
        except zlib.error:
            return zlib.decompress(
                raw_body,
                -zlib.MAX_WBITS,
            )

    raise ValidationError(
        "UNSUPPORTED_CONTENT_ENCODING"
    )


def select_canonical_url(
    *,
    target_url: str,
    final_url: str,
    parser: MinimalPageParser,
    json_ld_values: list[Any],
) -> tuple[
    str | None,
    str | None,
]:
    candidates: list[
        tuple[str, str]
    ] = []

    if final_url != target_url:
        candidates.append(
            (
                final_url,
                "FINAL_REDIRECT_URL",
            )
        )

    for url in parser.canonical_urls:
        candidates.append(
            (
                url,
                "HTML_CANONICAL_LINK",
            )
        )

    for url in parser.meta.get(
        "og:url",
        [],
    ):
        candidates.append(
            (
                url,
                "OPEN_GRAPH_URL",
            )
        )

    for structured in json_ld_values:
        for url in collect_json_ld_values(
            structured,
            names=[
                "url",
                "@id",
            ],
        ):
            candidates.append(
                (
                    url,
                    "JSON_LD_URL",
                )
            )

    for candidate, source in candidates:
        try:
            absolute = urllib.parse.urljoin(
                final_url,
                candidate,
            )
            normalized = (
                validate_https_book_dmm_url(
                    absolute,
                    allow_latest=False,
                )
            )
        except RedirectPolicyError:
            continue

        return normalized, source

    return None, None


def extract_identity(
    *,
    decoded_body: bytes,
    charset: str,
    target_url: str,
    final_url: str,
) -> dict[str, Any]:
    text = decoded_body.decode(
        charset,
        errors="replace",
    )

    parser = MinimalPageParser()
    parser.feed(text)

    json_ld_values = parse_json_ld(
        parser
    )

    body_text = normalize_text(
        " ".join(
            parser.text_parts
        )
    )

    title_candidates: list[str] = []

    title_candidates.extend(
        parser.title_parts
    )

    for key in [
        "og:title",
        "twitter:title",
    ]:
        title_candidates.extend(
            parser.meta.get(
                key,
                [],
            )
        )

    author_candidates: list[str] = []
    author_candidates.extend(
        parser.meta.get(
            "author",
            [],
        )
    )

    publisher_candidates: list[str] = []

    for structured in json_ld_values:
        title_candidates.extend(
            collect_json_ld_values(
                structured,
                names=[
                    "name",
                    "headline",
                ],
            )
        )
        author_candidates.extend(
            collect_json_ld_values(
                structured,
                names=[
                    "author",
                    "creator",
                ],
            )
        )
        publisher_candidates.extend(
            collect_json_ld_values(
                structured,
                names=[
                    "publisher",
                    "brand",
                ],
            )
        )

    work_value, work_source = (
        first_matching_candidate(
            title_candidates,
            "ダークギャザリング",
        )
    )

    if (
        work_value is None
        and "ダークギャザリング"
        in body_text
    ):
        work_value = "ダークギャザリング"
        work_source = (
            "BODY_TEXT_EXACT_SUBSTRING"
        )

    (
        volume_value,
        volume_source,
    ) = extract_expected_volume_from_title_candidates(
        title_candidates,
        expected_work_title="ダークギャザリング",
        expected_volume_number=20,
    )

    author_value, author_source = (
        first_matching_candidate(
            author_candidates,
            "近藤憲一",
        )
    )

    if (
        author_value is None
        and "近藤憲一" in body_text
    ):
        author_value = "近藤憲一"
        author_source = (
            "BODY_TEXT_EXACT_SUBSTRING"
        )

    publisher_value, publisher_source = (
        first_matching_candidate(
            publisher_candidates,
            "集英社",
        )
    )

    if (
        publisher_value is None
        and "集英社" in body_text
    ):
        publisher_value = "集英社"
        publisher_source = (
            "BODY_TEXT_EXACT_SUBSTRING"
        )

    canonical_url, canonical_source = (
        select_canonical_url(
            target_url=target_url,
            final_url=final_url,
            parser=parser,
            json_ld_values=json_ld_values,
        )
    )

    parsed_target = urllib.parse.urlparse(
        target_url
    )

    target_series_match = (
        parsed_target.path
        == "/product/861056/latest/"
    )

    matches = {
        "work_title_match": (
            work_value is not None
            and "ダークギャザリング"
            in normalize_text(work_value)
        ),
        "volume_match": (
            volume_value == "第20巻"
        ),
        "author_match": (
            author_value is not None
            and "近藤憲一"
            in normalize_text(author_value)
        ),
        "publisher_match": (
            publisher_value is not None
            and "集英社"
            in normalize_text(
                publisher_value
            )
        ),
        "series_identity_match": (
            target_series_match
        ),
        "canonical_product_url_resolved": (
            canonical_url is not None
        ),
    }

    all_required_match = all(
        matches.values()
    )

    return {
        "page_title_candidates": [
            normalize_text(value)
            for value in title_candidates[:10]
        ],
        "extracted_work_title": (
            work_value
        ),
        "work_title_source": (
            work_source
        ),
        "extracted_volume": (
            volume_value
        ),
        "volume_source": (
            volume_source
        ),
        "extracted_author": (
            author_value
        ),
        "author_source": (
            author_source
        ),
        "extracted_publisher": (
            publisher_value
        ),
        "publisher_source": (
            publisher_source
        ),
        "extracted_series_id": (
            "861056"
            if target_series_match
            else None
        ),
        "series_id_source": (
            "EXACT_TARGET_URL_PATH"
            if target_series_match
            else None
        ),
        "canonical_product_url": (
            canonical_url
        ),
        "canonical_product_url_source": (
            canonical_source
        ),
        "identity_matches": matches,
        "all_required_identity_fields_match": (
            all_required_match
        ),
    }


def terminal_state() -> int | None:
    result_exists = (
        RECHECK_RESULT_PATH.exists()
    )
    consumption_exists = (
        CONSUMPTION_PATH.exists()
    )

    if (
        not result_exists
        and not consumption_exists
    ):
        return None

    if (
        result_exists
        and consumption_exists
    ):
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M2"
                    ),
                    "status": (
                        "BLOCKED_DMM_RECHECK_"
                        "AUTHORIZATION_ALREADY_CONSUMED"
                    ),
                    "recheck_result_exists": True,
                    "consumption_evidence_exists": True,
                    "authorization_reuse_allowed": False,
                    "automatic_retry_allowed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 3

    print(
        json.dumps(
            {
                "phase_id": (
                    "LS-NEW-BATCH-4G-2E-"
                    "RECOVERY-M2"
                ),
                "status": (
                    "FAIL_CLOSED_PARTIAL_DMM_"
                    "RECHECK_TERMINAL_STATE"
                ),
                "recheck_result_exists": (
                    result_exists
                ),
                "consumption_evidence_exists": (
                    consumption_exists
                ),
                "automatic_repair_allowed": False,
                "authorization_reuse_allowed": False,
                "production_status": "NO_GO"
            },
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )
    return 4


def validate_preflight(
    policy: dict[str, Any],
    request: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Path],
]:
    require(
        policy.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M2",
        "policy phase mismatch",
    )

    require(
        request.get("phase_id")
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M2",
        "request phase mismatch",
    )

    require(
        request.get("target_url")
        == policy[
            "target_contract"
        ]["url"],
        "target URL mismatch",
    )

    require(
        request.get("method") == "GET",
        "method must be GET",
    )

    for field in [
        "one_shot_network_get_requested",
        "authorization_consumption_requested",
        "consumption_evidence_creation_requested",
        "recheck_result_creation_requested",
    ]:
        require(
            request.get(field) is True,
            f"{field} must be true",
        )

    for field in [
        "automatic_retry_requested",
        "authentication_requested",
        "cookie_send_requested",
        "cookie_persistence_requested",
        "login_requested",
        "credential_file_read_requested",
        "request_body_requested",
        "write_operation_requested",
        "full_response_body_persistence_requested",
        "final_affiliate_link_generation_requested",
        "article_modification_requested",
        "article_url_injection_requested",
        "fresh_payload_creation_requested",
        "payload_binding_requested",
        "production_category_id_payload_injection_requested",
        "wordpress_access_requested",
        "wordpress_write_requested",
        "wordpress_publish_requested",
    ]:
        require(
            request.get(field) is False,
            f"{field} must remain false",
        )

    bindings = request[
        "source_bindings"
    ]

    path_specs = {
        "m1_result": (
            "m1_result_path",
            "m1_result_file_sha256",
            None,
            None,
        ),
        "authorization": (
            "authorization_path",
            "authorization_file_sha256",
            "authorization_digest_sha256",
            "authorization_artifact_digest_sha256",
        ),
        "plan": (
            "store_link_finalization_plan_path",
            "store_link_finalization_plan_file_sha256",
            "store_link_finalization_plan_digest_sha256",
            "store_link_finalization_plan_artifact_digest_sha256",
        ),
        "article": (
            "generated_article_path",
            "generated_article_file_sha256",
            "article_content_digest_sha256",
            "generated_article_artifact_digest_sha256",
        ),
        "review": (
            "content_human_review_path",
            "content_human_review_file_sha256",
            "human_review_digest_sha256",
            "content_human_review_artifact_digest_sha256",
        ),
    }

    values: dict[
        str,
        dict[str, Any]
    ] = {}
    paths: dict[
        str,
        Path
    ] = {}

    for label, (
        path_field,
        file_hash_field,
        artifact_digest_field,
        artifact_digest_reference,
    ) in path_specs.items():
        path = resolve_path(
            bindings[path_field]
        )

        require(
            file_sha256(path)
            == bindings[file_hash_field],
            f"{label} file hash mismatch",
        )

        value = load_json(path)

        if artifact_digest_field:
            verify_self_digest(
                value,
                artifact_digest_field,
                bindings[
                    artifact_digest_reference
                ],
                label,
            )

        paths[label] = path
        values[label] = value

    m1_result = values[
        "m1_result"
    ]
    authorization = values[
        "authorization"
    ]

    require(
        m1_result.get("status")
        == (
            "PASS_DMM_LATEST_ALIAS_ONE_SHOT_"
            "READ_ONLY_RECHECK_AUTHORIZATION_"
            "FIXED_NO_NETWORK"
        ),
        "M1 status mismatch",
    )

    require(
        m1_result.get(
            "ready_for_dmm_recheck_execute_now_confirmation"
        )
        is True,
        "M1 not ready for execute confirmation",
    )

    require(
        authorization.get(
            "authorization_consumed"
        )
        is False,
        "authorization already consumed",
    )
    require(
        authorization.get(
            "authorization_reuse_allowed"
        )
        is False,
        "authorization reuse contract mismatch",
    )
    require(
        authorization[
            "target_request"
        ]["method"]
        == "GET",
        "authorization method mismatch",
    )
    require(
        authorization[
            "target_request"
        ]["url"]
        == request["target_url"],
        "authorization target mismatch",
    )

    approval = load_json(
        resolve_path(
            request[
                "execute_now_approval_path"
            ]
        )
    )

    comparable = copy.deepcopy(
        approval
    )
    stored = comparable.pop(
        "approval_evidence_digest_sha256",
        None,
    )

    require(
        isinstance(stored, str)
        and digest(comparable) == stored,
        "execute approval digest invalid",
    )
    require(
        digest(approval)
        == request[
            "execute_now_approval_file_digest_sha256"
        ],
        "execute approval file digest mismatch",
    )
    require(
        approval.get("approval_label")
        == (
            "FRESH_DMM_LATEST_ALIAS_"
            "RECHECK_EXECUTE_NOW_APPROVED"
        ),
        "execute approval label mismatch",
    )
    require(
        approval.get(
            "human_explicit_approval"
        )
        is True,
        "explicit human approval missing",
    )

    return authorization, approval, paths


def build_recheck_result(
    *,
    attempt_id: str,
    target_url: str,
    redirect_chain: list[
        dict[str, Any]
    ],
    final_status: int | None,
    final_url: str | None,
    response_headers: dict[str, str],
    response_body_sha256: str | None,
    response_body_bytes: int,
    response_body_sha256_complete: bool,
    extraction: dict[str, Any],
    failure_reason_codes: list[str],
    network_error_type: str | None,
    network_error_message: str | None,
    consumption_digest: str,
) -> dict[str, Any]:
    accepted_status = (
        final_status == 200
    )

    identity_match = bool(
        extraction.get(
            "all_required_identity_fields_match",
            False,
        )
    )

    successful_match = (
        accepted_status
        and response_body_sha256_complete
        and identity_match
        and not failure_reason_codes
    )

    decision = (
        "DMM_IDENTITY_MATCHED_CANONICAL_PRODUCT_"
        "RESOLVED_READY_FOR_FINAL_LINK_GENERATION_GATE"
        if successful_match
        else
        "DMM_RECHECK_FAILED_CLOSED_SLOT_UNAVAILABLE_"
        "RETURN_TO_HUMAN_REVIEW"
    )

    without_digest = {
        "schema_version": "1.0.0",
        "document_role": (
            "DMM_LATEST_ALIAS_ONE_SHOT_"
            "READ_ONLY_RECHECK_RESULT"
        ),
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M2"
        ),
        "attempt_id": attempt_id,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "dmm_series_id": "861056",
        "request": {
            "method": "GET",
            "target_url": target_url,
            "request_body_used": False,
            "authentication_used": False,
            "login_used": False,
            "cookie_sent": False,
            "cookie_persisted": False,
            "credential_file_read": False,
            "automatic_retry_performed": False,
        },
        "network": {
            "network_attempt_performed": True,
            "http_request_attempted": True,
            "http_response_received": (
                final_status is not None
            ),
            "redirect_chain": redirect_chain,
            "redirect_count": len(
                redirect_chain
            ),
            "http_statuses": (
                [
                    entry["status"]
                    for entry
                    in redirect_chain
                ]
                + (
                    [final_status]
                    if final_status
                    is not None
                    else []
                )
            ),
            "final_http_status": (
                final_status
            ),
            "final_url": final_url,
            "response_headers_allowlisted": (
                response_headers
            ),
            "response_body_sha256": (
                response_body_sha256
            ),
            "response_body_bytes": (
                response_body_bytes
            ),
            "response_body_sha256_complete": (
                response_body_sha256_complete
            ),
            "full_response_body_persisted": False,
            "network_error_type": (
                network_error_type
            ),
            "network_error_message": (
                network_error_message
            ),
        },
        "extracted_identity": extraction,
        "verification": {
            "accepted_http_status": (
                accepted_status
            ),
            "all_required_identity_fields_match": (
                identity_match
            ),
            "canonical_product_url_resolved": (
                bool(
                    extraction.get(
                        "canonical_product_url"
                    )
                )
            ),
            "successful_match": (
                successful_match
            ),
            "failure_reason_codes": (
                failure_reason_codes
            ),
        },
        "decision": decision,
        "dmm_slot_available": (
            successful_match
        ),
        "dmm_slot_must_be_hidden": (
            not successful_match
        ),
        "human_review_required": (
            not successful_match
        ),
        "automatic_fallback_url_used": False,
        "dummy_url_used": False,
        "authorization_consumed": True,
        "authorization_reuse_allowed": False,
        "consumption_evidence_path": (
            display_path(
                CONSUMPTION_PATH
            )
        ),
        "consumption_evidence_digest_sha256": (
            consumption_digest
        ),
        "final_affiliate_link_generated": False,
        "article_modified": False,
        "article_url_injection_performed": False,
        "fresh_payload_created": False,
        "production_category_id_payload_injected": False,
        "wordpress_access_performed": False,
        "wordpress_write_performed": False,
        "wordpress_published": False,
        "production_status": "NO_GO",
        "completed_at_utc": utc_now(),
    }

    result = copy.deepcopy(
        without_digest
    )
    result[
        "dmm_recheck_result_digest_sha256"
    ] = digest(without_digest)

    return result


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
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M2"
                    ),
                    "status": (
                        "BLOCKED_EXPLICIT_EXECUTE_"
                        "FLAG_REQUIRED"
                    ),
                    "authorization_consumed": False,
                    "network_attempt_performed": False,
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

        (
            authorization,
            approval,
            source_paths,
        ) = validate_preflight(
            policy,
            request,
        )

        source_hashes_before = {
            label: file_sha256(path)
            for label, path
            in source_paths.items()
        }

        attempt_id = str(
            uuid.uuid4()
        )
        attempt_started_at = utc_now()

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "document_role": (
                "DMM_LATEST_ALIAS_RECHECK_"
                "AUTHORIZATION_CONSUMPTION_EVIDENCE"
            ),
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M2"
            ),
            "attempt_id": attempt_id,
            "authorization_id": (
                authorization[
                    "authorization_id"
                ]
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "authorized_operation": (
                authorization[
                    "authorized_operation"
                ]
            ),
            "authorization_consumed": True,
            "consumption_is_authoritative": True,
            "consumed_at_network_attempt_start_utc": (
                attempt_started_at
            ),
            "single_use": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "retry_after_success_allowed": False,
            "retry_after_http_failure_allowed": False,
            "retry_after_communication_failure_allowed": False,
            "retry_after_identity_mismatch_allowed": False,
            "source_authorization_path": (
                request["source_bindings"][
                    "authorization_path"
                ]
            ),
            "source_authorization_file_sha256": (
                request["source_bindings"][
                    "authorization_file_sha256"
                ]
            ),
            "source_authorization_digest_sha256": (
                request["source_bindings"][
                    "authorization_artifact_digest_sha256"
                ]
            ),
            "source_authorization_modified": False,
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
            "request_method": "GET",
            "target_url": (
                request["target_url"]
            ),
            "network_attempt_state": (
                "CONSUMED_IMMEDIATELY_BEFORE_"
                "NETWORK_ATTEMPT"
            ),
            "recheck_result_path": (
                display_path(
                    RECHECK_RESULT_PATH
                )
            ),
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "fresh_payload_created": False,
            "wordpress_access_performed": False,
            "production_status": "NO_GO"
        }

        consumption = copy.deepcopy(
            consumption_without_digest
        )
        consumption[
            "consumption_evidence_digest_sha256"
        ] = digest(
            consumption_without_digest
        )

        write_exclusive_json(
            CONSUMPTION_PATH,
            consumption,
        )

        consumption_digest = consumption[
            "consumption_evidence_digest_sha256"
        ]

        target_url = request[
            "target_url"
        ]
        target_contract = policy[
            "target_contract"
        ]
        request_headers = policy[
            "allowed_explicit_request_headers"
        ]

        redirect_handler = (
            StrictRedirectHandler(
                maximum_redirect_count=(
                    target_contract[
                        "maximum_redirect_count"
                    ]
                ),
                request_headers=(
                    request_headers
                ),
            )
        )

        ssl_context = (
            ssl.create_default_context()
        )

        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler(
                {}
            ),
            redirect_handler,
            urllib.request.HTTPSHandler(
                context=ssl_context
            ),
        )

        request_object = urllib.request.Request(
            target_url,
            headers=request_headers,
            method="GET",
        )

        final_status: int | None = None
        final_url: str | None = None
        allowlisted_headers: dict[
            str,
            str
        ] = {}
        response_body_sha256: str | None = None
        response_body_bytes = 0
        response_hash_complete = False
        extraction: dict[str, Any] = {
            "extracted_work_title": None,
            "extracted_volume": None,
            "extracted_author": None,
            "extracted_publisher": None,
            "extracted_series_id": None,
            "canonical_product_url": None,
            "identity_matches": {
                "work_title_match": False,
                "volume_match": False,
                "author_match": False,
                "publisher_match": False,
                "series_identity_match": False,
                "canonical_product_url_resolved": False
            },
            "all_required_identity_fields_match": False
        }
        failure_codes: list[str] = []
        network_error_type: str | None = None
        network_error_message: str | None = None

        try:
            response: Any

            try:
                response = opener.open(
                    request_object,
                    timeout=target_contract[
                        "request_timeout_seconds"
                    ],
                )
            except urllib.error.HTTPError as exc:
                response = exc

            final_status = int(
                response.getcode()
            )
            final_url = (
                validate_https_book_dmm_url(
                    response.geturl(),
                    allow_latest=True,
                )
            )

            allowed_header_names = {
                "content-type",
                "content-encoding",
                "location",
                "last-modified",
                "etag",
            }

            for key, value in response.headers.items():
                normalized_key = key.lower()

                if (
                    normalized_key
                    in allowed_header_names
                ):
                    allowlisted_headers[
                        normalized_key
                    ] = value

            (
                raw_body,
                response_body_sha256,
                response_body_bytes,
            ) = read_limited_body(
                response,
                target_contract[
                    "maximum_raw_response_bytes"
                ],
            )

            response_hash_complete = True

            content_encoding = (
                response.headers.get(
                    "Content-Encoding",
                    "",
                )
            )

            decoded_body = (
                decode_response_body(
                    raw_body,
                    content_encoding,
                )
            )

            content_type = (
                response.headers.get(
                    "Content-Type",
                    ""
                )
            )

            charset = "utf-8"

            match = re.search(
                r"charset\s*=\s*[\"']?"
                r"([A-Za-z0-9._-]+)",
                content_type,
                flags=re.IGNORECASE,
            )

            if match:
                charset = match.group(1)

            if final_status != 200:
                failure_codes.append(
                    "UNEXPECTED_FINAL_HTTP_STATUS"
                )

            extraction = extract_identity(
                decoded_body=decoded_body,
                charset=charset,
                target_url=target_url,
                final_url=final_url,
            )

            identity_matches = extraction[
                "identity_matches"
            ]

            if not identity_matches[
                "work_title_match"
            ]:
                failure_codes.append(
                    "WORK_TITLE_MISMATCH"
                )

            if not identity_matches[
                "volume_match"
            ]:
                failure_codes.append(
                    "VOLUME_MISMATCH"
                )

            if not identity_matches[
                "author_match"
            ]:
                failure_codes.append(
                    "AUTHOR_MISMATCH"
                )

            if not identity_matches[
                "publisher_match"
            ]:
                failure_codes.append(
                    "PUBLISHER_MISMATCH"
                )

            if not identity_matches[
                "series_identity_match"
            ]:
                failure_codes.append(
                    "SERIES_IDENTITY_MISMATCH"
                )

            if not identity_matches[
                "canonical_product_url_resolved"
            ]:
                failure_codes.append(
                    "CANONICAL_PRODUCT_UNRESOLVED"
                )

        except RedirectPolicyError as exc:
            failure_codes.append(
                "REDIRECT_POLICY_VIOLATION"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )

        except ResponseLimitError as exc:
            failure_codes.append(
                "RESPONSE_BODY_TOO_LARGE"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )

        except (
            urllib.error.URLError,
            TimeoutError,
            ssl.SSLError,
            OSError,
        ) as exc:
            failure_codes.append(
                "COMMUNICATION_FAILURE"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )[:500]

        except ValidationError as exc:
            failure_codes.append(
                str(exc)
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )[:500]

        except Exception as exc:
            failure_codes.append(
                "UNEXPECTED_RECHECK_EXCEPTION"
            )
            network_error_type = type(
                exc
            ).__name__
            network_error_message = str(
                exc
            )[:500]

        failure_codes = list(
            dict.fromkeys(
                failure_codes
            )
        )

        recheck_result = (
            build_recheck_result(
                attempt_id=attempt_id,
                target_url=target_url,
                redirect_chain=(
                    redirect_handler.redirect_chain
                ),
                final_status=final_status,
                final_url=final_url,
                response_headers=(
                    allowlisted_headers
                ),
                response_body_sha256=(
                    response_body_sha256
                ),
                response_body_bytes=(
                    response_body_bytes
                ),
                response_body_sha256_complete=(
                    response_hash_complete
                ),
                extraction=extraction,
                failure_reason_codes=(
                    failure_codes
                ),
                network_error_type=(
                    network_error_type
                ),
                network_error_message=(
                    network_error_message
                ),
                consumption_digest=(
                    consumption_digest
                ),
            )
        )

        write_exclusive_json(
            RECHECK_RESULT_PATH,
            recheck_result,
        )

        for label, path in source_paths.items():
            require(
                file_sha256(path)
                == source_hashes_before[
                    label
                ],
                f"source artifact modified: {label}",
            )

        success = recheck_result[
            "verification"
        ]["successful_match"]

        package_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M2"
            ),
            "policy_id": policy[
                "policy_id"
            ],
            "attempt_id": attempt_id,
            "authorization_consumption_path": (
                display_path(
                    CONSUMPTION_PATH
                )
            ),
            "authorization_consumption_file_sha256": (
                file_sha256(
                    CONSUMPTION_PATH
                )
            ),
            "authorization_consumption_digest_sha256": (
                consumption_digest
            ),
            "recheck_result_path": (
                display_path(
                    RECHECK_RESULT_PATH
                )
            ),
            "recheck_result_file_sha256": (
                file_sha256(
                    RECHECK_RESULT_PATH
                )
            ),
            "recheck_result_digest_sha256": (
                recheck_result[
                    "dmm_recheck_result_digest_sha256"
                ]
            ),
            "successful_match": success,
            "dmm_slot_available": (
                recheck_result[
                    "dmm_slot_available"
                ]
            ),
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "network_attempt_performed": True,
            "final_affiliate_link_generated": False,
            "article_modified": False,
            "fresh_payload_created": False,
            "wordpress_access_performed": False,
        }

        package = copy.deepcopy(
            package_without_digest
        )
        package[
            "dmm_recheck_package_digest_sha256"
        ] = digest(
            package_without_digest
        )

        result = {
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-RECOVERY-M2"
            ),
            "status": (
                "PASS_DMM_LATEST_ALIAS_ONE_SHOT_"
                "RECHECK_EXECUTED_AUTH_CONSUMED_"
                "NO_LINK_GENERATION"
            ),
            "decision": (
                recheck_result[
                    "decision"
                ]
            ),
            "approval_label": (
                "FRESH_DMM_LATEST_ALIAS_"
                "RECHECK_EXECUTE_NOW_APPROVED"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "attempt_id": attempt_id,
            "target_url": target_url,
            "method": "GET",
            "authorization_consumption_path": (
                package[
                    "authorization_consumption_path"
                ]
            ),
            "authorization_consumption_digest_sha256": (
                consumption_digest
            ),
            "recheck_result_path": (
                package[
                    "recheck_result_path"
                ]
            ),
            "recheck_result_digest_sha256": (
                package[
                    "recheck_result_digest_sha256"
                ]
            ),
            "dmm_recheck_package_digest_sha256": (
                package[
                    "dmm_recheck_package_digest_sha256"
                ]
            ),
            "authorization_consumed": True,
            "consumption_evidence_created": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "network_attempt_performed": True,
            "http_request_attempted": True,
            "http_response_received": (
                recheck_result[
                    "network"
                ]["http_response_received"]
            ),
            "redirect_count": (
                recheck_result[
                    "network"
                ]["redirect_count"]
            ),
            "final_http_status": (
                recheck_result[
                    "network"
                ]["final_http_status"]
            ),
            "final_url": (
                recheck_result[
                    "network"
                ]["final_url"]
            ),
            "response_body_sha256": (
                recheck_result[
                    "network"
                ]["response_body_sha256"]
            ),
            "full_response_body_persisted": False,
            "all_required_identity_fields_match": (
                recheck_result[
                    "verification"
                ][
                    "all_required_identity_fields_match"
                ]
            ),
            "canonical_product_url": (
                recheck_result[
                    "extracted_identity"
                ][
                    "canonical_product_url"
                ]
            ),
            "successful_match": success,
            "failure_reason_codes": (
                recheck_result[
                    "verification"
                ]["failure_reason_codes"]
            ),
            "dmm_slot_available": (
                recheck_result[
                    "dmm_slot_available"
                ]
            ),
            "dmm_slot_must_be_hidden": (
                recheck_result[
                    "dmm_slot_must_be_hidden"
                ]
            ),
            "human_review_required": (
                recheck_result[
                    "human_review_required"
                ]
            ),
            "automatic_fallback_url_used": False,
            "final_affiliate_link_generated": False,
            "final_affiliate_link_validated": False,
            "article_modified": False,
            "article_url_injection_performed": False,
            "source_artifacts_modified": False,
            "fresh_payload_created": False,
            "payload_binding_complete": False,
            "production_category_id_payload_injected": False,
            "wordpress_access_performed": False,
            "wordpress_write_performed": False,
            "wordpress_draft_created": False,
            "wordpress_published": False,
            "execution_allowed": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DMM_RECHECK_MATCHED_AWAITING_"
                "FINAL_LINK_GENERATION_GATE"
                if success
                else
                "DMM_RECHECK_FAILED_CLOSED_"
                "AWAITING_HUMAN_REVIEW"
            ),
            "ready_for_final_affiliate_link_generation_gate": (
                success
            ),
            "ready_for_dmm_failure_human_review": (
                not success
            ),
            "ready_for_article_url_injection": False,
            "ready_for_fresh_payload_generation": False,
            "ready_for_wordpress_draft": False,
            "ready_for_execution": False
        }

        write_json(
            PACKAGE_PATH,
            package,
        )
        write_json(
            RESULT_PATH,
            result,
        )

        report = f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M2

## Result

- Status: `{result["status"]}`
- Decision: `{result["decision"]}`
- Method: `GET`
- Target: `{result["target_url"]}`
- Authorization consumed: `true`
- Automatic retry allowed: `false`

## Network Evidence

- HTTP response received: `{str(result["http_response_received"]).lower()}`
- Redirect count: `{result["redirect_count"]}`
- Final HTTP status: `{result["final_http_status"]}`
- Final URL: `{result["final_url"]}`
- Response body SHA-256: `{result["response_body_sha256"]}`
- Full response body persisted: `false`

## Verification

- All identity fields match: `{str(result["all_required_identity_fields_match"]).lower()}`
- Canonical product URL: `{result["canonical_product_url"]}`
- Successful match: `{str(result["successful_match"]).lower()}`
- DMM slot available: `{str(result["dmm_slot_available"]).lower()}`
- Human review required: `{str(result["human_review_required"]).lower()}`
- Failure reasons: `{result["failure_reason_codes"]}`

## Boundary

- Final affiliate link generated: `false`
- Article modified: `false`
- Article URL injection: `false`
- Payload created: `false`
- WordPress accessed: `false`
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
        print(
            json.dumps(
                {
                    "phase_id": (
                        "LS-NEW-BATCH-4G-2E-"
                        "RECOVERY-M2"
                    ),
                    "status": (
                        "FAIL_PREFLIGHT_VALIDATION_"
                        "NO_NETWORK_ATTEMPT"
                    ),
                    "error": str(exc),
                    "authorization_consumed": False,
                    "network_attempt_performed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
