#!/usr/bin/env python3

from __future__ import annotations

import base64
import copy
import hashlib
import html
import json
import os
import pwd
import re
import socket
import ssl
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_draft_creation_final_"
    "one_shot_execution_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_final_execute_approval.json"
)

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
PAYLOAD = ROOT / (
    "exchange/payloads/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload.json"
)
SECRET_LINK = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
)

M11_FIX2_REVIEW = ROOT / (
    "exchange/reviews/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_payload_human_review.json"
)
M11_FIX2_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m11_fix2_result.json"
)
M12_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_authorization.json"
)
M12_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m12_result.json"
)
M13_PRE_WRITER_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_writer_result.json"
)
M13_PRE_NETWORK_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_"
    "m13_pre_network_result.json"
)
CRED1_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m6_cred1_result.json"
)

WRITER_CREDENTIAL = Path(
    "/etc/ai-media-os/credential.env"
)

CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_consumption.json"
)
SECRET_RESPONSE = ROOT / (
    "exchange/wordpress/new_release/fresh/"
    "new-release-comic-20260703-001."
    "wordpress_draft_creation_response.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m13_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m13_"
    "wordpress_draft_creation_report.md"
)

EXPECTED_ARTICLE_SHA = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
EXPECTED_PAYLOAD_SHA = (
    "30a70be4110e863a85e2896f69f5b3e5"
    "1d814a6fd82d5489f899d8a244166d8f"
)
EXPECTED_PAYLOAD_DIGEST = (
    "2ab27b59305dbae98f997ca3a4604002"
    "98152f173ef605b534df922c187411c6"
)
EXPECTED_M11_FIX2_REVIEW_DIGEST = (
    "52136cc8b50e8a7279e13ea4cb224033"
    "eca9790f354c7bcb18b0f6d694d71c25"
)
EXPECTED_M11_FIX2_RESULT_DIGEST = (
    "dc08a7212e812e366b05952c8e8eceba"
    "85f8f8421e2f9fcc65a54ddaa82ea404"
)
EXPECTED_M12_AUTH_SHA = (
    "7c9662a7a13502e165862e4524278992"
    "28794bce6904a0215c45a5b54ba1142b"
)
EXPECTED_M12_AUTH_DIGEST = (
    "d3ede61a71d75cbbc00a594f0a8d319a"
    "ed0e598bd9c061609a52bed7e96d07c3"
)
EXPECTED_M12_RESULT_DIGEST = (
    "51b0602ae6daf31f583693f6052bec44"
    "cc45ead92da4296075c6fc6f5cad6fc4"
)
EXPECTED_M13_PRE_WRITER_DIGEST = (
    "aee2c18d623fc54142312b8c06ee18a6"
    "553f251dcc5023db5b1ca82b4566ea69"
)
EXPECTED_M13_PRE_NETWORK_DIGEST = (
    "00e55b372e2345c597e6de3b9f161364"
    "0e6c852b22f19c6f75886e82925ec5d9"
)
EXPECTED_SECRET_LINK_FILE_SHA = (
    "c5a70d9804a4e2dfd91049ee20bdda53"
    "79abf3e1fe3c25b0fb8cbd5fa587faa0"
)
EXPECTED_SECRET_LINK_DIGEST = (
    "4807e0a6d8a8416a936bafa978ba4f90"
    "d43ae7d304322bbd6a6ababcb2cd2db6"
)
EXPECTED_CRED1_DIGEST = (
    "7a173b74bef53781a3b2fe2e2cc2d3f3"
    "63a096b937508c241d454311d072ec7e"
)
EXPECTED_TITLE = (
    "ダークギャザリング 第20巻｜配信開始"
)
EXPECTED_PRODUCT_URL = (
    "https://book.dmm.com/product/"
    "861056/b950yshes32617/"
)

CRED1_CONTEXT = (
    b"LS-NEW-BATCH-4G-2E-RECOVERY-M6-CRED1"
    b"\x00DMM_AFFILIATE_ID\x00"
)

MAX_RESPONSE_BYTES = 16 * 1024 * 1024

REQUIRED_CREDENTIAL_KEYS = (
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
)


class ValidationError(RuntimeError):
    pass


class PostExecutionUncertain(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValidationError(code)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.exists() and path.is_file(),
        f"REQUIRED_JSON_MISSING:{path.name}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValidationError(
            f"JSON_PARSE_FAILED:{path.name}"
        ) from None

    require(
        isinstance(value, dict),
        f"JSON_ROOT_NOT_OBJECT:{path.name}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    field: str,
    expected: str,
) -> None:
    comparable = copy.deepcopy(value)
    stored = comparable.pop(field, None)

    require(
        isinstance(stored, str),
        f"DIGEST_FIELD_MISSING:{field}",
    )
    require(
        digest(comparable) == stored,
        f"DIGEST_INTERNAL_MISMATCH:{field}",
    )
    require(
        stored == expected,
        f"DIGEST_EXPECTED_MISMATCH:{field}",
    )


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
    mode: int = 0o600,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                value,
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        directory_fd = os.open(
            path.parent,
            os.O_RDONLY,
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def atomic_write_text(
    path: Path,
    value: str,
    mode: int = 0o600,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())

        directory_fd = os.open(
            path.parent,
            os.O_RDONLY,
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def normalize_env_value(
    raw_value: str,
) -> str:
    value = raw_value.strip()

    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]

    return value


def read_writer_credentials(
    path: Path,
) -> tuple[dict[str, str], os.stat_result]:
    require(
        path.exists(),
        "WRITER_CREDENTIAL_MISSING",
    )

    before = path.lstat()

    require(
        not stat.S_ISLNK(before.st_mode),
        "WRITER_CREDENTIAL_SYMLINK_REJECTED",
    )
    require(
        stat.S_ISREG(before.st_mode),
        "WRITER_CREDENTIAL_NOT_REGULAR_FILE",
    )
    require(
        stat.S_IMODE(before.st_mode) == 0o600,
        "WRITER_CREDENTIAL_MODE_NOT_0600",
    )
    require(
        before.st_uid == os.geteuid(),
        "WRITER_CREDENTIAL_OWNER_UID_MISMATCH",
    )
    require(
        pwd.getpwuid(before.st_uid).pw_name
        == "deploy",
        "WRITER_CREDENTIAL_OWNER_NOT_DEPLOY",
    )

    values: dict[str, list[str]] = {
        key: []
        for key in REQUIRED_CREDENTIAL_KEYS
    }

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for raw_line in handle:
                require(
                    "\x00" not in raw_line,
                    "WRITER_CREDENTIAL_CONTAINS_NUL",
                )

                line = raw_line.strip()

                if not line or line.startswith("#"):
                    continue

                if line.startswith("export "):
                    line = line[7:].lstrip()

                key, separator, raw_value = (
                    line.partition("=")
                )
                key = key.strip()

                if (
                    separator == "="
                    and key in values
                ):
                    values[key].append(
                        normalize_env_value(
                            raw_value
                        )
                    )

    except UnicodeDecodeError:
        raise ValidationError(
            "WRITER_CREDENTIAL_ENCODING_INVALID"
        ) from None

    for key in REQUIRED_CREDENTIAL_KEYS:
        require(
            len(values[key]) == 1,
            "REQUIRED_WRITER_KEY_COUNT_MISMATCH",
        )
        require(
            values[key][0] != "",
            "REQUIRED_WRITER_VALUE_EMPTY",
        )

    return {
        key: values[key][0]
        for key in REQUIRED_CREDENTIAL_KEYS
    }, before


def read_dmm_identifier(
    path: Path,
) -> str:
    values: list[str] = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for raw_line in handle:
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("export "):
                line = line[7:].lstrip()

            key, separator, raw_value = (
                line.partition("=")
            )

            if (
                separator == "="
                and key.strip()
                == "DMM_AFFILIATE_ID"
            ):
                values.append(
                    normalize_env_value(
                        raw_value
                    )
                )

    require(
        len(values) == 1,
        "DMM_IDENTIFIER_KEY_COUNT_MUST_BE_ONE",
    )

    identifier = values[0]

    require(
        re.fullmatch(
            r"[A-Za-z0-9]+-[0-9]{3}",
            identifier,
        ) is not None,
        "DMM_IDENTIFIER_FORMAT_INVALID",
    )

    return identifier


def same_metadata(
    before: os.stat_result,
    after: os.stat_result,
) -> bool:
    return (
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_gid,
        before.st_size,
        before.st_mtime_ns,
    ) == (
        after.st_ino,
        after.st_mode,
        after.st_uid,
        after.st_gid,
        after.st_size,
        after.st_mtime_ns,
    )


def validate_base_url(
    base_url: str,
) -> str:
    parsed = urllib.parse.urlsplit(
        base_url
    )

    require(
        parsed.scheme.casefold() == "https",
        "WORDPRESS_BASE_URL_SCHEME_INVALID",
    )
    require(
        parsed.hostname == "hoshido.jp",
        "WORDPRESS_BASE_URL_HOST_INVALID",
    )
    require(
        parsed.port is None,
        "WORDPRESS_BASE_URL_EXPLICIT_PORT_REJECTED",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "WORDPRESS_BASE_URL_USERINFO_REJECTED",
    )
    require(
        parsed.path in {"", "/"},
        "WORDPRESS_BASE_URL_PATH_REJECTED",
    )
    require(
        parsed.query == "",
        "WORDPRESS_BASE_URL_QUERY_REJECTED",
    )
    require(
        parsed.fragment == "",
        "WORDPRESS_BASE_URL_FRAGMENT_REJECTED",
    )

    return "https://hoshido.jp"


def validate_request_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)

    require(
        parsed.scheme == "https",
        "REQUEST_URL_SCHEME_INVALID",
    )
    require(
        parsed.hostname == "hoshido.jp",
        "REQUEST_URL_HOST_INVALID",
    )
    require(
        parsed.port is None,
        "REQUEST_URL_EXPLICIT_PORT_REJECTED",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "REQUEST_URL_USERINFO_REJECTED",
    )
    require(
        parsed.fragment == "",
        "REQUEST_URL_FRAGMENT_REJECTED",
    )
    require(
        parsed.path.startswith(
            "/wp-json/wp/v2/"
        ),
        "REQUEST_URL_PATH_OUTSIDE_ALLOWED_SCOPE",
    )


def verify_cred1_commitment(
    identifier: str,
    cred1: dict[str, Any],
) -> None:
    commitment = cred1[
        "identifier_commitment"
    ]

    calculated = hashlib.pbkdf2_hmac(
        "sha256",
        identifier.encode("utf-8"),
        (
            CRED1_CONTEXT
            + bytes.fromhex(
                commitment["salt_hex"]
            )
        ),
        commitment["iterations"],
    ).hex()

    require(
        calculated
        == commitment["commitment_hex"],
        "CRED1_COMMITMENT_MISMATCH",
    )


class DmmAnchorInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self.current: (
            dict[str, Any] | None
        ) = None
        self.matches: list[
            dict[str, Any]
        ] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        if tag.casefold() != "a":
            return

        attr_map = {
            name.casefold(): (
                "" if value is None else value
            )
            for name, value in attrs
        }

        classes = set(
            attr_map.get(
                "class",
                "",
            ).split()
        )

        if "ls-store-dmm" not in classes:
            return

        self.current = {
            "classes": classes,
            "href": html.unescape(
                attr_map.get("href", "")
            ),
            "target": attr_map.get(
                "target"
            ),
            "rel": set(
                attr_map.get(
                    "rel",
                    "",
                ).split()
            ),
            "aria_disabled": (
                "aria-disabled" in attr_map
            ),
            "text_parts": [],
        }

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self.current is not None:
            self.current[
                "text_parts"
            ].append(data)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag.casefold() != "a"
            or self.current is None
        ):
            return

        current = self.current
        self.current = None

        self.matches.append(
            {
                "classes": (
                    current["classes"]
                ),
                "href": current["href"],
                "target": (
                    current["target"]
                ),
                "rel": current["rel"],
                "aria_disabled": (
                    current[
                        "aria_disabled"
                    ]
                ),
                "text": re.sub(
                    r"\s+",
                    " ",
                    "".join(
                        current[
                            "text_parts"
                        ]
                    ),
                ).strip(),
            }
        )


def validate_dmm_url(
    final_url: str,
    identifier: str,
) -> None:
    parsed = urllib.parse.urlsplit(
        final_url
    )

    require(
        parsed.scheme == "https",
        "DMM_URL_SCHEME_INVALID",
    )
    require(
        parsed.hostname == "al.dmm.com",
        "DMM_URL_HOST_INVALID",
    )
    require(
        parsed.port is None,
        "DMM_URL_PORT_REJECTED",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        "DMM_URL_USERINFO_REJECTED",
    )
    require(
        parsed.fragment == "",
        "DMM_URL_FRAGMENT_REJECTED",
    )

    require(
        urllib.parse.parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
        == [
            (
                "lurl",
                EXPECTED_PRODUCT_URL,
            ),
            (
                "af_id",
                identifier,
            ),
            (
                "ch",
                "link_tool",
            ),
            (
                "ch_id",
                "link",
            ),
        ],
        "DMM_URL_QUERY_BINDING_MISMATCH",
    )


class NoRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        raise ValidationError(
            "REDIRECT_BLOCKED"
        )


class WordPressOneShotClient:
    def __init__(
        self,
        origin: str,
        authorization_header: str,
    ) -> None:
        self.origin = origin
        self.authorization_header = (
            authorization_header
        )
        self.get_count = 0
        self.post_count = 0

        context = ssl.create_default_context()

        self.opener = (
            urllib.request.build_opener(
                urllib.request.ProxyHandler(
                    {}
                ),
                NoRedirectHandler(),
                urllib.request.HTTPSHandler(
                    context=context
                ),
            )
        )

    def duplicate_get(
        self,
        title: str,
    ) -> tuple[
        Any,
        dict[str, str],
        int,
    ]:
        require(
            self.get_count == 0,
            "DUPLICATE_GET_ALREADY_USED",
        )
        require(
            self.post_count == 0,
            "POST_ALREADY_STARTED",
        )

        query = urllib.parse.urlencode(
            {
                "context": "edit",
                "status": "draft",
                "search": title,
                "per_page": 100,
                "page": 1,
                "_fields": (
                    "id,title,content,"
                    "status,categories"
                ),
            },
            encoding="utf-8",
        )

        url = (
            self.origin
            + "/wp-json/wp/v2/posts?"
            + query
        )

        validate_request_url(url)

        request = urllib.request.Request(
            url=url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": (
                    self.authorization_header
                ),
                "User-Agent": (
                    "ai-media-os-m13/1.0"
                ),
                "Cache-Control": "no-store",
            },
        )

        self.get_count += 1

        try:
            with self.opener.open(
                request,
                timeout=20,
            ) as response:
                status_code = int(
                    response.getcode()
                )

                require(
                    status_code == 200,
                    (
                        "DUPLICATE_GET_"
                        f"HTTP_STATUS_{status_code}"
                    ),
                )
                require(
                    response.geturl() == url,
                    "DUPLICATE_GET_FINAL_URL_CHANGED",
                )

                body = response.read(
                    MAX_RESPONSE_BYTES + 1
                )

                require(
                    len(body)
                    <= MAX_RESPONSE_BYTES,
                    "DUPLICATE_GET_RESPONSE_TOO_LARGE",
                )

                try:
                    parsed_body = json.loads(
                        body.decode("utf-8")
                    )
                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                ):
                    raise ValidationError(
                        "DUPLICATE_GET_JSON_PARSE_FAILED"
                    ) from None

                headers = {
                    "x-wp-total": (
                        response.headers.get(
                            "X-WP-Total",
                            "",
                        )
                    ),
                    "x-wp-totalpages": (
                        response.headers.get(
                            "X-WP-TotalPages",
                            "",
                        )
                    ),
                }

                return (
                    parsed_body,
                    headers,
                    status_code,
                )

        except ValidationError:
            raise
        except urllib.error.HTTPError as exc:
            code = int(exc.code)

            try:
                exc.close()
            except Exception:
                pass

            if 300 <= code < 400:
                raise ValidationError(
                    "REDIRECT_BLOCKED"
                ) from None

            raise ValidationError(
                (
                    "DUPLICATE_GET_"
                    f"HTTP_STATUS_{code}"
                )
            ) from None

        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            ssl.SSLError,
        ):
            raise ValidationError(
                "DUPLICATE_GET_NETWORK_FAILED"
            ) from None

    def create_post(
        self,
        body: bytes,
    ) -> tuple[
        int,
        str,
        str,
        bytes,
    ]:
        require(
            self.get_count == 1,
            "DUPLICATE_GET_COUNT_NOT_ONE",
        )
        require(
            self.post_count == 0,
            "CREATE_POST_ALREADY_USED",
        )

        url = (
            self.origin
            + "/wp-json/wp/v2/posts"
        )

        validate_request_url(url)

        request = urllib.request.Request(
            url=url,
            method="POST",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": (
                    "application/json; "
                    "charset=utf-8"
                ),
                "Authorization": (
                    self.authorization_header
                ),
                "User-Agent": (
                    "ai-media-os-m13/1.0"
                ),
                "Cache-Control": "no-store",
            },
        )

        self.post_count += 1

        try:
            with self.opener.open(
                request,
                timeout=30,
            ) as response:
                status_code = int(
                    response.getcode()
                )
                final_url = response.geturl()
                content_type = (
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                )

                require(
                    final_url == url,
                    "CREATE_POST_FINAL_URL_CHANGED",
                )

                raw_body = response.read(
                    MAX_RESPONSE_BYTES + 1
                )

                if (
                    len(raw_body)
                    > MAX_RESPONSE_BYTES
                ):
                    raise PostExecutionUncertain(
                        "CREATE_POST_RESPONSE_TOO_LARGE"
                    )

                return (
                    status_code,
                    final_url,
                    content_type,
                    raw_body,
                )

        except ValidationError:
            raise
        except urllib.error.HTTPError as exc:
            code = int(exc.code)
            final_url = exc.geturl()
            content_type = (
                exc.headers.get(
                    "Content-Type",
                    "",
                )
                if exc.headers is not None
                else ""
            )

            try:
                raw_body = exc.read(
                    MAX_RESPONSE_BYTES + 1
                )
            except Exception:
                raw_body = b""

            try:
                exc.close()
            except Exception:
                pass

            if (
                len(raw_body)
                > MAX_RESPONSE_BYTES
            ):
                raw_body = raw_body[
                    :MAX_RESPONSE_BYTES
                ]

            return (
                code,
                final_url,
                content_type,
                raw_body,
            )

        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            ssl.SSLError,
        ):
            raise PostExecutionUncertain(
                "CREATE_POST_NETWORK_RESULT_UNKNOWN"
            ) from None


def write_secret_response(
    *,
    attempt_id: str,
    response_received: bool,
    http_status: int | None,
    final_url_verified: bool,
    content_type: str | None,
    raw_body: bytes | None,
    parsed_json: Any | None,
    error_code: str | None,
) -> None:
    require(
        not SECRET_RESPONSE.exists(),
        "SECRET_RESPONSE_ALREADY_EXISTS",
    )

    artifact_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M13"
        ),
        "document_role": (
            "SECRET_WORDPRESS_DRAFT_"
            "CREATION_RESPONSE"
        ),
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "execution_attempt_id": attempt_id,
        "response_received": response_received,
        "http_status": http_status,
        "final_response_url_verified": (
            final_url_verified
        ),
        "content_type": content_type,
        "body_json": parsed_json,
        "body_base64": (
            base64.b64encode(
                raw_body
            ).decode("ascii")
            if (
                raw_body is not None
                and parsed_json is None
            )
            else None
        ),
        "error_code": error_code,
        "contains_potential_affiliate_content": (
            raw_body is not None
        ),
        "mode_required": "0600",
        "created_at_utc": now()
    }

    artifact = copy.deepcopy(
        artifact_without_digest
    )
    artifact[
        "secret_response_digest_sha256"
    ] = digest(artifact_without_digest)

    atomic_write_json(
        SECRET_RESPONSE,
        artifact,
        0o600,
    )


def write_result(
    *,
    status: str,
    decision: str,
    error_code: str | None,
    attempt_id: str | None,
    authorization_consumed: bool,
    consumption_digest: str | None,
    duplicate_candidate_count: int,
    duplicate_exact_match_count: int,
    duplicate_detected: bool,
    post_attempted: bool,
    response_received: bool,
    http_status: int | None,
    wordpress_post_id: int | None,
    title_match: bool,
    content_match: bool,
    category_verified: bool,
    created_count: int,
    manual_review_required: bool,
) -> dict[str, Any]:
    result_without_digest = {
        "schema_version": "1.0.0",
        "phase_id": (
            "LS-NEW-BATCH-4G-2E-RECOVERY-M13"
        ),
        "status": status,
        "decision": decision,
        "error_code": error_code,
        "content_item_id": (
            "new-release-comic-20260703-001"
        ),
        "execution_attempt_id": attempt_id,
        "payload_file_sha256": (
            EXPECTED_PAYLOAD_SHA
        ),
        "payload_digest_sha256": (
            EXPECTED_PAYLOAD_DIGEST
        ),
        "m12_authorization_file_sha256": (
            EXPECTED_M12_AUTH_SHA
        ),
        "m12_authorization_digest_sha256": (
            EXPECTED_M12_AUTH_DIGEST
        ),
        "m13_pre_network_result_digest_sha256": (
            EXPECTED_M13_PRE_NETWORK_DIGEST
        ),
        "authorization_consumed": (
            authorization_consumed
        ),
        "authorization_reuse_allowed": False,
        "automatic_retry_allowed": False,
        "automatic_reissue_allowed": False,
        "consumption_evidence_digest_sha256": (
            consumption_digest
        ),
        "duplicate_get_request_count": 1,
        "duplicate_candidate_count": (
            duplicate_candidate_count
        ),
        "duplicate_exact_match_count": (
            duplicate_exact_match_count
        ),
        "duplicate_detected": (
            duplicate_detected
        ),
        "wordpress_create_post_request_count": (
            1 if post_attempted else 0
        ),
        "wordpress_create_post_attempted": (
            post_attempted
        ),
        "wordpress_response_received": (
            response_received
        ),
        "wordpress_http_status": http_status,
        "wordpress_post_id": wordpress_post_id,
        "wordpress_post_status": (
            "draft"
            if (
                wordpress_post_id is not None
                and title_match
                and content_match
                and category_verified
            )
            else None
        ),
        "title_exact_match": title_match,
        "content_exact_match": content_match,
        "category_id_10_verified": (
            category_verified
        ),
        "created_draft_count": (
            created_count
        ),
        "request_fields_exactly_limited": True,
        "template_field_sent": False,
        "payload_modified": False,
        "article_modified": False,
        "m12_authorization_file_modified": False,
        "credential_file_modified": False,
        "credential_values_output": False,
        "username_output": False,
        "application_password_output": False,
        "authorization_header_output": False,
        "full_payload_output": False,
        "full_wordpress_response_output": False,
        "full_final_affiliate_url_output": False,
        "dmm_affiliate_identifier_output": False,
        "secret_response_artifact_path": (
            str(
                SECRET_RESPONSE.relative_to(
                    ROOT
                )
            )
            if SECRET_RESPONSE.exists()
            else None
        ),
        "secret_response_artifact_mode_0600": (
            SECRET_RESPONSE.exists()
            and stat.S_IMODE(
                SECRET_RESPONSE.stat().st_mode
            ) == 0o600
        ),
        "wordpress_write_performed": (
            post_attempted
        ),
        "wordpress_draft_created": (
            created_count == 1
        ),
        "wordpress_published": False,
        "existing_post_updated": False,
        "post_deleted": False,
        "category_created": False,
        "category_updated": False,
        "media_uploaded": False,
        "x_post_performed": False,
        "manual_wordpress_review_required": (
            manual_review_required
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "WORDPRESS_DRAFT_CREATED_AWAITING_"
            "POST_EXECUTION_EVIDENCE_REVIEW"
            if created_count == 1
            else (
                "AUTHORIZATION_CONSUMED_"
                "WORDPRESS_RESULT_REQUIRES_"
                "MANUAL_REVIEW_NO_RETRY"
                if authorization_consumed
                else (
                    "PRE_EXECUTION_BLOCKED_"
                    "M12_AUTHORIZATION_UNCONSUMED"
                )
            )
        ),
        "ready_for_post_execution_evidence_review": (
            created_count == 1
        ),
        "ready_for_wordpress_publish": False,
        "completed_at_utc": now()
    }

    result = copy.deepcopy(
        result_without_digest
    )
    result[
        "result_digest_sha256"
    ] = digest(result_without_digest)

    atomic_write_json(
        RESULT,
        result,
        0o600,
    )

    atomic_write_text(
        REPORT,
        f"""# LS-NEW-BATCH-4G-2E-RECOVERY-M13

- Status: `{status}`
- Decision: `{decision}`
- Error code: `{error_code}`
- Authorization consumed: `{str(authorization_consumed).lower()}`
- Authorization reuse allowed: `false`
- Automatic retry allowed: `false`
- Automatic reissue allowed: `false`
- Duplicate candidate count: `{duplicate_candidate_count}`
- Duplicate exact match count: `{duplicate_exact_match_count}`
- Duplicate detected: `{str(duplicate_detected).lower()}`
- WordPress create POST count: `{1 if post_attempted else 0}`
- WordPress response received: `{str(response_received).lower()}`
- HTTP status: `{http_status}`
- WordPress post ID: `{wordpress_post_id}`
- Draft status verified: `{str(created_count == 1).lower()}`
- Category ID 10 verified: `{str(category_verified).lower()}`
- Title exact match: `{str(title_match).lower()}`
- Content exact match: `{str(content_match).lower()}`
- Created draft count: `{created_count}`
- Full response output: `false`
- WordPress published: `false`
- Manual review required: `{str(manual_review_required).lower()}`
- Production status: `NO_GO`
- Ready for WordPress publish: `false`
""",
        0o600,
    )

    return result


def main() -> int:
    source_paths = {
        "article": ARTICLE,
        "payload": PAYLOAD,
        "secret_link": SECRET_LINK,
        "m11_fix2_review": (
            M11_FIX2_REVIEW
        ),
        "m11_fix2_result": (
            M11_FIX2_RESULT
        ),
        "m12_authorization": M12_AUTH,
        "m12_result": M12_RESULT,
        "m13_pre_writer_result": (
            M13_PRE_WRITER_RESULT
        ),
        "m13_pre_network_result": (
            M13_PRE_NETWORK_RESULT
        ),
        "cred1_result": CRED1_RESULT,
    }

    source_hashes: dict[str, str] = {}
    credentials: (
        dict[str, str] | None
    ) = None
    credential_before: (
        os.stat_result | None
    ) = None
    client: (
        WordPressOneShotClient | None
    ) = None

    duplicate_candidate_count = 0
    duplicate_exact_match_count = 0
    duplicate_detected = False
    authorization_consumed = False
    consumption_digest: str | None = None
    attempt_id: str | None = None
    post_attempted = False
    response_received = False
    http_status: int | None = None
    wordpress_post_id: int | None = None
    title_match = False
    content_match = False
    category_verified = False
    created_count = 0

    try:
        for output in [
            CONSUMPTION,
            SECRET_RESPONSE,
            RESULT,
            REPORT,
        ]:
            require(
                not output.exists(),
                f"M13_OUTPUT_ALREADY_EXISTS:{output.name}",
            )

        policy = load_json(POLICY)
        approval = load_json(APPROVAL)

        approval_copy = copy.deepcopy(
            approval
        )
        approval_digest = (
            approval_copy.pop(
                "approval_evidence_digest_sha256",
                None,
            )
        )

        require(
            isinstance(
                approval_digest,
                str,
            ),
            "APPROVAL_DIGEST_MISSING",
        )
        require(
            digest(approval_copy)
            == approval_digest,
            "APPROVAL_DIGEST_MISMATCH",
        )
        require(
            approval["approval_label"]
            == (
                "WORDPRESS_DRAFT_CREATION_FINAL_"
                "ONE_SHOT_EXECUTE_NOW_APPROVED"
            ),
            "APPROVAL_LABEL_MISMATCH",
        )
        require(
            policy["phase_id"]
            == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M13"
            ),
            "POLICY_PHASE_MISMATCH",
        )

        source_hashes = {
            name: file_sha(path)
            for name, path in (
                source_paths.items()
            )
        }

        require(
            source_hashes["article"]
            == EXPECTED_ARTICLE_SHA,
            "ARTICLE_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["payload"]
            == EXPECTED_PAYLOAD_SHA,
            "PAYLOAD_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes[
                "m12_authorization"
            ] == EXPECTED_M12_AUTH_SHA,
            "M12_AUTHORIZATION_FILE_SHA_MISMATCH",
        )
        require(
            source_hashes["secret_link"]
            == EXPECTED_SECRET_LINK_FILE_SHA,
            "SECRET_LINK_FILE_SHA_MISMATCH",
        )

        require(
            not PAYLOAD.is_symlink(),
            "PAYLOAD_SYMLINK_REJECTED",
        )
        require(
            stat.S_IMODE(
                PAYLOAD.stat().st_mode
            ) == 0o600,
            "PAYLOAD_MODE_NOT_0600",
        )
        require(
            not SECRET_LINK.is_symlink(),
            "SECRET_LINK_SYMLINK_REJECTED",
        )
        require(
            stat.S_IMODE(
                SECRET_LINK.stat().st_mode
            ) == 0o600,
            "SECRET_LINK_MODE_NOT_0600",
        )

        article = load_json(ARTICLE)
        payload = load_json(PAYLOAD)
        secret = load_json(SECRET_LINK)
        review = load_json(
            M11_FIX2_REVIEW
        )
        m11_result = load_json(
            M11_FIX2_RESULT
        )
        m12_auth = load_json(M12_AUTH)
        m12_result = load_json(
            M12_RESULT
        )
        pre_writer = load_json(
            M13_PRE_WRITER_RESULT
        )
        pre_network = load_json(
            M13_PRE_NETWORK_RESULT
        )
        cred1 = load_json(
            CRED1_RESULT
        )

        verify_digest(
            payload,
            "payload_digest_sha256",
            EXPECTED_PAYLOAD_DIGEST,
        )
        verify_digest(
            review,
            "human_review_evidence_digest_sha256",
            EXPECTED_M11_FIX2_REVIEW_DIGEST,
        )
        verify_digest(
            m11_result,
            "result_digest_sha256",
            EXPECTED_M11_FIX2_RESULT_DIGEST,
        )
        verify_digest(
            m12_auth,
            "authorization_digest_sha256",
            EXPECTED_M12_AUTH_DIGEST,
        )
        verify_digest(
            m12_result,
            "result_digest_sha256",
            EXPECTED_M12_RESULT_DIGEST,
        )
        verify_digest(
            pre_writer,
            "result_digest_sha256",
            EXPECTED_M13_PRE_WRITER_DIGEST,
        )
        verify_digest(
            pre_network,
            "result_digest_sha256",
            EXPECTED_M13_PRE_NETWORK_DIGEST,
        )
        verify_digest(
            secret,
            "secret_artifact_digest_sha256",
            EXPECTED_SECRET_LINK_DIGEST,
        )
        verify_digest(
            cred1,
            "result_digest_sha256",
            EXPECTED_CRED1_DIGEST,
        )

        require(
            pre_network["status"]
            == (
                "PASS_WORDPRESS_WRITER_"
                "AUTHENTICATED_NETWORK_PREFLIGHT_"
                "GET_ONLY_NO_DUPLICATE_"
                "NO_AUTH_CONSUMPTION"
            ),
            "M13_PRE_NETWORK_STATUS_MISMATCH",
        )
        require(
            pre_network[
                "ready_for_final_wordpress_draft_creation_execute_now_gate"
            ] is True,
            "M13_PRE_NETWORK_NOT_READY",
        )
        require(
            pre_network[
                "authenticated"
            ] is True,
            "M13_PRE_NETWORK_NOT_AUTHENTICATED",
        )
        require(
            pre_network["edit_posts"]
            is True,
            "M13_PRE_NETWORK_EDIT_POSTS_FALSE",
        )
        require(
            pre_network[
                "category_id_10_verified"
            ] is True,
            "M13_PRE_NETWORK_CATEGORY_FALSE",
        )
        require(
            pre_network[
                "duplicate_detected"
            ] is False,
            "M13_PRE_NETWORK_DUPLICATE_DETECTED",
        )

        require(
            m12_auth["authorization_id"]
            == (
                "WORDPRESS_DRAFT_CREATION_"
                "ONE_SHOT_AUTHORIZATION_V1"
            ),
            "M12_AUTHORIZATION_ID_MISMATCH",
        )
        require(
            m12_auth["single_use"]
            is True,
            "M12_AUTHORIZATION_NOT_SINGLE_USE",
        )
        require(
            m12_auth[
                "authorization_consumed"
            ] is False,
            "M12_AUTHORIZATION_ALREADY_CONSUMED",
        )
        require(
            m12_auth[
                "authorization_reuse_allowed"
            ] is False,
            "M12_AUTHORIZATION_REUSE_ALLOWED",
        )
        require(
            m12_auth[
                "automatic_retry_allowed"
            ] is False,
            "M12_AUTOMATIC_RETRY_ALLOWED",
        )
        require(
            m12_auth[
                "automatic_reissue_allowed"
            ] is False,
            "M12_AUTOMATIC_REISSUE_ALLOWED",
        )
        require(
            m12_auth[
                "wordpress_draft_contract"
            ][
                "maximum_draft_count"
            ] == 1,
            "M12_MAXIMUM_DRAFT_COUNT_MISMATCH",
        )
        require(
            m12_auth[
                "planned_execution_phase_id"
            ] == (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M13"
            ),
            "M12_PLANNED_PHASE_MISMATCH",
        )

        require(
            payload["title"]
            == EXPECTED_TITLE,
            "PAYLOAD_TITLE_MISMATCH",
        )
        require(
            payload["title"]
            == article["article_title"],
            "PAYLOAD_ARTICLE_TITLE_MISMATCH",
        )
        require(
            payload["title_source_field"]
            == "article_title",
            "PAYLOAD_TITLE_SOURCE_MISMATCH",
        )
        require(
            payload["content_html"]
            == article["content_html"],
            "PAYLOAD_CONTENT_ARTICLE_MISMATCH",
        )
        require(
            payload["post_status"]
            == "draft",
            "PAYLOAD_POST_STATUS_MISMATCH",
        )
        require(
            payload["status"] == "draft",
            "PAYLOAD_STATUS_MISMATCH",
        )
        require(
            payload["publish"]
            is False,
            "PAYLOAD_PUBLISH_TRUE",
        )
        require(
            payload["template_id"]
            == (
                "POST185_STANDARD_"
                "TEMPLATE_V1_FIXED"
            ),
            "PAYLOAD_TEMPLATE_ID_MISMATCH",
        )
        require(
            payload["category_mapping_id"]
            == (
                "COMIC_NEW_RELEASE_"
                "LATEST_VOLUME_TO_WP_CATEGORY_10"
            ),
            "PAYLOAD_CATEGORY_MAPPING_MISMATCH",
        )
        require(
            payload["category_id"] == 10,
            "PAYLOAD_CATEGORY_ID_MISMATCH",
        )
        require(
            payload["categories"] == [10],
            "PAYLOAD_CATEGORIES_MISMATCH",
        )
        require(
            payload["category_name"]
            == "最新巻",
            "PAYLOAD_CATEGORY_NAME_MISMATCH",
        )
        require(
            payload["content_item_id"]
            == (
                "new-release-comic-"
                "20260703-001"
            ),
            "PAYLOAD_CONTENT_ITEM_ID_MISMATCH",
        )

        credentials, credential_before = (
            read_writer_credentials(
                WRITER_CREDENTIAL
            )
        )

        origin = validate_base_url(
            credentials[
                "WORDPRESS_BASE_URL"
            ]
        )

        dmm_identifier = (
            read_dmm_identifier(
                WRITER_CREDENTIAL
            )
        )

        verify_cred1_commitment(
            dmm_identifier,
            cred1,
        )

        final_url = secret[
            "final_affiliate_url"
        ]

        inspector = DmmAnchorInspector()
        inspector.feed(
            payload["content_html"]
        )
        inspector.close()

        require(
            len(inspector.matches) == 1,
            "DMM_ANCHOR_COUNT_MUST_BE_ONE",
        )

        anchor = inspector.matches[0]

        require(
            anchor["classes"]
            == {
                "ls-store-btn",
                "ls-store-dmm",
            },
            "DMM_CLASS_TOKENS_MISMATCH",
        )
        require(
            anchor["text"]
            == "DMMブックスで確認",
            "DMM_TEXT_MISMATCH",
        )
        require(
            anchor["target"]
            == "_blank",
            "DMM_TARGET_MISMATCH",
        )
        require(
            anchor["rel"]
            == {
                "nofollow",
                "sponsored",
                "noopener",
            },
            "DMM_REL_TOKENS_MISMATCH",
        )
        require(
            anchor["aria_disabled"]
            is False,
            "DMM_ARIA_DISABLED_PRESENT",
        )
        require(
            "ls-store-disabled"
            not in anchor["classes"],
            "DMM_DISABLED_CLASS_PRESENT",
        )
        require(
            anchor["href"] == final_url,
            "DMM_HREF_SECRET_LINK_MISMATCH",
        )

        validate_dmm_url(
            final_url,
            dmm_identifier,
        )

        credential_pair = (
            credentials[
                "WORDPRESS_USERNAME"
            ]
            + ":"
            + credentials[
                "WORDPRESS_APP_PASSWORD"
            ]
        )

        authorization_header = (
            "Basic "
            + base64.b64encode(
                credential_pair.encode(
                    "utf-8"
                )
            ).decode("ascii")
        )

        client = WordPressOneShotClient(
            origin=origin,
            authorization_header=(
                authorization_header
            ),
        )

        (
            duplicate_data,
            duplicate_headers,
            duplicate_status,
        ) = client.duplicate_get(
            payload["title"]
        )

        require(
            duplicate_status == 200,
            "DUPLICATE_GET_STATUS_NOT_200",
        )
        require(
            isinstance(
                duplicate_data,
                list,
            ),
            "DUPLICATE_RESPONSE_NOT_ARRAY",
        )

        total_raw = duplicate_headers[
            "x-wp-total"
        ]
        total_pages_raw = (
            duplicate_headers[
                "x-wp-totalpages"
            ]
        )

        require(
            re.fullmatch(
                r"[0-9]+",
                total_raw,
            ) is not None,
            "DUPLICATE_TOTAL_HEADER_INVALID",
        )
        require(
            re.fullmatch(
                r"[0-9]+",
                total_pages_raw,
            ) is not None,
            "DUPLICATE_TOTALPAGES_HEADER_INVALID",
        )

        total = int(total_raw)
        total_pages = int(
            total_pages_raw
        )

        require(
            total_pages <= 1,
            "DUPLICATE_RESULT_SET_INCOMPLETE",
        )
        require(
            total == len(
                duplicate_data
            ),
            "DUPLICATE_TOTAL_MISMATCH",
        )

        duplicate_candidate_count = (
            len(duplicate_data)
        )

        for candidate in duplicate_data:
            require(
                isinstance(
                    candidate,
                    dict,
                ),
                "DUPLICATE_CANDIDATE_NOT_OBJECT",
            )
            require(
                candidate.get("status")
                == "draft",
                "DUPLICATE_STATUS_MISMATCH",
            )

            title_object = candidate.get(
                "title"
            )
            content_object = (
                candidate.get(
                    "content"
                )
            )

            require(
                isinstance(
                    title_object,
                    dict,
                ),
                "DUPLICATE_TITLE_OBJECT_MISSING",
            )
            require(
                isinstance(
                    content_object,
                    dict,
                ),
                "DUPLICATE_CONTENT_OBJECT_MISSING",
            )
            require(
                isinstance(
                    title_object.get(
                        "raw"
                    ),
                    str,
                ),
                "DUPLICATE_TITLE_RAW_UNAVAILABLE",
            )
            require(
                isinstance(
                    content_object.get(
                        "raw"
                    ),
                    str,
                ),
                "DUPLICATE_CONTENT_RAW_UNAVAILABLE",
            )

            if (
                title_object["raw"]
                == payload["title"]
                and content_object["raw"]
                == payload["content_html"]
            ):
                duplicate_exact_match_count += 1

        duplicate_detected = (
            duplicate_exact_match_count > 0
        )

        require(
            not duplicate_detected,
            "DUPLICATE_DRAFT_DETECTED",
        )

        for name, path in (
            source_paths.items()
        ):
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        require(
            credential_before is not None
            and same_metadata(
                credential_before,
                WRITER_CREDENTIAL.lstat(),
            ),
            "WRITER_CREDENTIAL_METADATA_CHANGED",
        )

        require(
            not CONSUMPTION.exists(),
            "M13_CONSUMPTION_ALREADY_EXISTS",
        )

        attempt_id = str(
            uuid.uuid4()
        )

        consumption_without_digest = {
            "schema_version": "1.0.0",
            "phase_id": (
                "LS-NEW-BATCH-4G-2E-"
                "RECOVERY-M13"
            ),
            "document_role": (
                "WORDPRESS_DRAFT_CREATION_"
                "AUTHORIZATION_CONSUMPTION"
            ),
            "content_item_id": (
                "new-release-comic-20260703-001"
            ),
            "execution_attempt_id": (
                attempt_id
            ),
            "source_authorization_path": str(
                M12_AUTH.relative_to(ROOT)
            ),
            "source_authorization_file_sha256": (
                EXPECTED_M12_AUTH_SHA
            ),
            "source_authorization_digest_sha256": (
                EXPECTED_M12_AUTH_DIGEST
            ),
            "payload_file_sha256": (
                EXPECTED_PAYLOAD_SHA
            ),
            "payload_digest_sha256": (
                EXPECTED_PAYLOAD_DIGEST
            ),
            "m13_pre_network_result_digest_sha256": (
                EXPECTED_M13_PRE_NETWORK_DIGEST
            ),
            "authorization_consumed": True,
            "authorization_reuse_allowed": False,
            "automatic_retry_allowed": False,
            "automatic_reissue_allowed": False,
            "maximum_draft_count": 1,
            "duplicate_check_completed": True,
            "duplicate_detected": False,
            "wordpress_create_post_not_yet_started_at_consumption": True,
            "consumed_at_utc": now(),
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

        atomic_write_json(
            CONSUMPTION,
            consumption,
            0o600,
        )

        authorization_consumed = True
        consumption_digest = consumption[
            "consumption_evidence_digest_sha256"
        ]

        request_object = {
            "title": payload["title"],
            "content": (
                payload["content_html"]
            ),
            "status": "draft",
            "categories": [10],
        }

        require(
            set(request_object.keys())
            == {
                "title",
                "content",
                "status",
                "categories",
            },
            "CREATE_REQUEST_FIELD_SET_INVALID",
        )
        require(
            "template"
            not in request_object,
            "TEMPLATE_FIELD_MUST_NOT_BE_SENT",
        )

        request_body = json.dumps(
            request_object,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        post_attempted = True

        try:
            (
                http_status,
                final_response_url,
                content_type,
                raw_response,
            ) = client.create_post(
                request_body
            )

            response_received = True

        except PostExecutionUncertain as exc:
            write_secret_response(
                attempt_id=attempt_id,
                response_received=False,
                http_status=None,
                final_url_verified=False,
                content_type=None,
                raw_body=None,
                parsed_json=None,
                error_code=str(exc),
            )

            result = write_result(
                status=(
                    "BLOCKED_WORDPRESS_DRAFT_"
                    "CREATION_RESULT_UNKNOWN_"
                    "AUTHORIZATION_CONSUMED_NO_RETRY"
                ),
                decision=(
                    "MANUAL_WORDPRESS_DRAFT_"
                    "CONFIRMATION_REQUIRED"
                ),
                error_code=str(exc),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                duplicate_candidate_count=(
                    duplicate_candidate_count
                ),
                duplicate_exact_match_count=0,
                duplicate_detected=False,
                post_attempted=True,
                response_received=False,
                http_status=None,
                wordpress_post_id=None,
                title_match=False,
                content_match=False,
                category_verified=False,
                created_count=0,
                manual_review_required=True,
            )

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2

        final_response_url_verified = (
            final_response_url
            == (
                origin
                + "/wp-json/wp/v2/posts"
            )
        )

        parsed_response: Any | None = None

        try:
            parsed_response = json.loads(
                raw_response.decode(
                    "utf-8"
                )
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            parsed_response = None

        write_secret_response(
            attempt_id=attempt_id,
            response_received=True,
            http_status=http_status,
            final_url_verified=(
                final_response_url_verified
            ),
            content_type=content_type,
            raw_body=raw_response,
            parsed_json=parsed_response,
            error_code=None,
        )

        if http_status != 201:
            result = write_result(
                status=(
                    "BLOCKED_WORDPRESS_DRAFT_"
                    "CREATION_HTTP_STATUS_"
                    "AUTHORIZATION_CONSUMED_NO_RETRY"
                ),
                decision=(
                    "NO_AUTOMATIC_RETRY_"
                    "MANUAL_REVIEW_REQUIRED"
                ),
                error_code=(
                    "WORDPRESS_CREATE_HTTP_STATUS_"
                    + str(http_status)
                ),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                duplicate_candidate_count=(
                    duplicate_candidate_count
                ),
                duplicate_exact_match_count=0,
                duplicate_detected=False,
                post_attempted=True,
                response_received=True,
                http_status=http_status,
                wordpress_post_id=None,
                title_match=False,
                content_match=False,
                category_verified=False,
                created_count=0,
                manual_review_required=True,
            )

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2

        if not final_response_url_verified:
            result = write_result(
                status=(
                    "BLOCKED_WORDPRESS_DRAFT_"
                    "CREATION_RESPONSE_URL_MISMATCH_"
                    "AUTHORIZATION_CONSUMED_NO_RETRY"
                ),
                decision=(
                    "MANUAL_WORDPRESS_REVIEW_REQUIRED"
                ),
                error_code=(
                    "CREATE_POST_FINAL_URL_CHANGED"
                ),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                duplicate_candidate_count=(
                    duplicate_candidate_count
                ),
                duplicate_exact_match_count=0,
                duplicate_detected=False,
                post_attempted=True,
                response_received=True,
                http_status=http_status,
                wordpress_post_id=None,
                title_match=False,
                content_match=False,
                category_verified=False,
                created_count=0,
                manual_review_required=True,
            )

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2

        if not isinstance(
            parsed_response,
            dict,
        ):
            result = write_result(
                status=(
                    "BLOCKED_WORDPRESS_DRAFT_"
                    "CREATION_RESPONSE_PARSE_"
                    "AUTHORIZATION_CONSUMED_NO_RETRY"
                ),
                decision=(
                    "MANUAL_WORDPRESS_REVIEW_REQUIRED"
                ),
                error_code=(
                    "WORDPRESS_CREATE_RESPONSE_"
                    "JSON_PARSE_FAILED"
                ),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                duplicate_candidate_count=(
                    duplicate_candidate_count
                ),
                duplicate_exact_match_count=0,
                duplicate_detected=False,
                post_attempted=True,
                response_received=True,
                http_status=http_status,
                wordpress_post_id=None,
                title_match=False,
                content_match=False,
                category_verified=False,
                created_count=0,
                manual_review_required=True,
            )

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2

        response_id = parsed_response.get(
            "id"
        )
        response_status = (
            parsed_response.get(
                "status"
            )
        )
        response_title = (
            parsed_response.get(
                "title"
            )
        )
        response_content = (
            parsed_response.get(
                "content"
            )
        )
        response_categories = (
            parsed_response.get(
                "categories"
            )
        )

        id_valid = (
            isinstance(response_id, int)
            and response_id > 0
        )
        status_valid = (
            response_status == "draft"
        )
        title_match = (
            isinstance(
                response_title,
                dict,
            )
            and response_title.get(
                "raw"
            ) == payload["title"]
        )
        content_match = (
            isinstance(
                response_content,
                dict,
            )
            and response_content.get(
                "raw"
            )
            == payload["content_html"]
        )
        category_verified = (
            isinstance(
                response_categories,
                list,
            )
            and response_categories == [10]
        )

        if not (
            id_valid
            and status_valid
            and title_match
            and content_match
            and category_verified
        ):
            result = write_result(
                status=(
                    "BLOCKED_WORDPRESS_DRAFT_"
                    "CREATION_RESPONSE_VALIDATION_"
                    "AUTHORIZATION_CONSUMED_NO_RETRY"
                ),
                decision=(
                    "DRAFT_MAY_EXIST_MANUAL_"
                    "WORDPRESS_REVIEW_REQUIRED"
                ),
                error_code=(
                    "WORDPRESS_CREATE_RESPONSE_"
                    "CONTRACT_MISMATCH"
                ),
                attempt_id=attempt_id,
                authorization_consumed=True,
                consumption_digest=(
                    consumption_digest
                ),
                duplicate_candidate_count=(
                    duplicate_candidate_count
                ),
                duplicate_exact_match_count=0,
                duplicate_detected=False,
                post_attempted=True,
                response_received=True,
                http_status=http_status,
                wordpress_post_id=(
                    response_id
                    if id_valid
                    else None
                ),
                title_match=title_match,
                content_match=content_match,
                category_verified=(
                    category_verified
                ),
                created_count=0,
                manual_review_required=True,
            )

            print(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 2

        wordpress_post_id = response_id
        created_count = 1

        for name, path in (
            source_paths.items()
        ):
            require(
                file_sha(path)
                == source_hashes[name],
                f"SOURCE_ARTIFACT_CHANGED:{name}",
            )

        require(
            credential_before is not None
            and same_metadata(
                credential_before,
                WRITER_CREDENTIAL.lstat(),
            ),
            "WRITER_CREDENTIAL_METADATA_CHANGED",
        )

        result = write_result(
            status=(
                "PASS_WORDPRESS_DRAFT_CREATED_"
                "ONE_SHOT_AUTHORIZATION_CONSUMED_"
                "NO_PUBLISH_NO_RETRY"
            ),
            decision=(
                "WORDPRESS_DRAFT_CREATED_"
                "READY_FOR_POST_EXECUTION_"
                "EVIDENCE_AND_HUMAN_REVIEW"
            ),
            error_code=None,
            attempt_id=attempt_id,
            authorization_consumed=True,
            consumption_digest=(
                consumption_digest
            ),
            duplicate_candidate_count=(
                duplicate_candidate_count
            ),
            duplicate_exact_match_count=0,
            duplicate_detected=False,
            post_attempted=True,
            response_received=True,
            http_status=http_status,
            wordpress_post_id=(
                wordpress_post_id
            ),
            title_match=True,
            content_match=True,
            category_verified=True,
            created_count=1,
            manual_review_required=False,
        )

        del credentials
        del credential_pair
        del authorization_header
        del dmm_identifier
        del final_url
        del raw_response
        del parsed_response
        del request_body
        del request_object

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except ValidationError as exc:
        if authorization_consumed:
            if (
                attempt_id is not None
                and not SECRET_RESPONSE.exists()
            ):
                try:
                    write_secret_response(
                        attempt_id=attempt_id,
                        response_received=(
                            response_received
                        ),
                        http_status=http_status,
                        final_url_verified=False,
                        content_type=None,
                        raw_body=None,
                        parsed_json=None,
                        error_code=str(exc),
                    )
                except Exception:
                    pass

            try:
                result = write_result(
                    status=(
                        "BLOCKED_WORDPRESS_DRAFT_"
                        "CREATION_POST_CONSUMPTION_"
                        "AUTHORIZATION_CONSUMED_NO_RETRY"
                    ),
                    decision=(
                        "MANUAL_WORDPRESS_REVIEW_REQUIRED"
                    ),
                    error_code=str(exc),
                    attempt_id=attempt_id,
                    authorization_consumed=True,
                    consumption_digest=(
                        consumption_digest
                    ),
                    duplicate_candidate_count=(
                        duplicate_candidate_count
                    ),
                    duplicate_exact_match_count=(
                        duplicate_exact_match_count
                    ),
                    duplicate_detected=(
                        duplicate_detected
                    ),
                    post_attempted=post_attempted,
                    response_received=(
                        response_received
                    ),
                    http_status=http_status,
                    wordpress_post_id=(
                        wordpress_post_id
                    ),
                    title_match=title_match,
                    content_match=content_match,
                    category_verified=(
                        category_verified
                    ),
                    created_count=(
                        created_count
                    ),
                    manual_review_required=True,
                )

                print(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    file=sys.stderr,
                )
            except Exception:
                print(
                    json.dumps(
                        {
                            "phase_id": (
                                "LS-NEW-BATCH-4G-2E-"
                                "RECOVERY-M13"
                            ),
                            "status": (
                                "AUTHORIZATION_CONSUMED_"
                                "UNRECORDED_FAILURE_"
                                "MANUAL_REVIEW_REQUIRED"
                            ),
                            "error_code": str(exc),
                            "automatic_retry_allowed": False,
                            "production_status": "NO_GO"
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    file=sys.stderr,
                )

            return 2

        duplicate_detected = (
            str(exc)
            == "DUPLICATE_DRAFT_DETECTED"
        )

        result = write_result(
            status=(
                "BLOCKED_WORDPRESS_DRAFT_"
                "CREATION_BEFORE_AUTHORIZATION_"
                "CONSUMPTION"
            ),
            decision=(
                "FAIL_CLOSED_M12_AUTHORIZATION_"
                "REMAINS_UNCONSUMED"
            ),
            error_code=str(exc),
            attempt_id=None,
            authorization_consumed=False,
            consumption_digest=None,
            duplicate_candidate_count=(
                duplicate_candidate_count
            ),
            duplicate_exact_match_count=(
                duplicate_exact_match_count
            ),
            duplicate_detected=(
                duplicate_detected
            ),
            post_attempted=False,
            response_received=False,
            http_status=None,
            wordpress_post_id=None,
            title_match=False,
            content_match=False,
            category_verified=False,
            created_count=0,
            manual_review_required=False,
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    except Exception:
        if authorization_consumed:
            error_code = (
                "UNEXPECTED_POST_CONSUMPTION_FAILURE"
            )

            if (
                attempt_id is not None
                and not SECRET_RESPONSE.exists()
            ):
                try:
                    write_secret_response(
                        attempt_id=attempt_id,
                        response_received=(
                            response_received
                        ),
                        http_status=http_status,
                        final_url_verified=False,
                        content_type=None,
                        raw_body=None,
                        parsed_json=None,
                        error_code=error_code,
                    )
                except Exception:
                    pass

            try:
                result = write_result(
                    status=(
                        "BLOCKED_WORDPRESS_DRAFT_"
                        "CREATION_UNEXPECTED_"
                        "AUTHORIZATION_CONSUMED_NO_RETRY"
                    ),
                    decision=(
                        "MANUAL_WORDPRESS_REVIEW_REQUIRED"
                    ),
                    error_code=error_code,
                    attempt_id=attempt_id,
                    authorization_consumed=True,
                    consumption_digest=(
                        consumption_digest
                    ),
                    duplicate_candidate_count=(
                        duplicate_candidate_count
                    ),
                    duplicate_exact_match_count=(
                        duplicate_exact_match_count
                    ),
                    duplicate_detected=False,
                    post_attempted=post_attempted,
                    response_received=(
                        response_received
                    ),
                    http_status=http_status,
                    wordpress_post_id=(
                        wordpress_post_id
                    ),
                    title_match=title_match,
                    content_match=content_match,
                    category_verified=(
                        category_verified
                    ),
                    created_count=(
                        created_count
                    ),
                    manual_review_required=True,
                )

                print(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    file=sys.stderr,
                )
            except Exception:
                print(
                    json.dumps(
                        {
                            "phase_id": (
                                "LS-NEW-BATCH-4G-2E-"
                                "RECOVERY-M13"
                            ),
                            "status": (
                                "AUTHORIZATION_CONSUMED_"
                                "UNEXPECTED_UNRECORDED_FAILURE"
                            ),
                            "automatic_retry_allowed": False,
                            "production_status": "NO_GO"
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    file=sys.stderr,
                )

            return 2

        result = write_result(
            status=(
                "BLOCKED_WORDPRESS_DRAFT_"
                "CREATION_UNEXPECTED_BEFORE_"
                "AUTHORIZATION_CONSUMPTION"
            ),
            decision=(
                "FAIL_CLOSED_M12_AUTHORIZATION_"
                "REMAINS_UNCONSUMED"
            ),
            error_code=(
                "UNEXPECTED_PRE_CONSUMPTION_FAILURE"
            ),
            attempt_id=None,
            authorization_consumed=False,
            consumption_digest=None,
            duplicate_candidate_count=(
                duplicate_candidate_count
            ),
            duplicate_exact_match_count=(
                duplicate_exact_match_count
            ),
            duplicate_detected=False,
            post_attempted=False,
            response_received=False,
            http_status=None,
            wordpress_post_id=None,
            title_match=False,
            content_match=False,
            category_verified=False,
            created_count=0,
            manual_review_required=False,
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
