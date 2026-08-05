#!/usr/bin/env python3

from __future__ import annotations

import base64
import http.client
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)


CREDENTIAL_ENV = Path(
    "/etc/ai-media-os/credential.env"
)

EXPECTED_HOST = "hoshido.jp"
EXPECTED_POST_ID = 192
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
NETWORK_APPROVAL_ENV = (
    "M27_FIX1_SINGLE_GET_NETWORK_APPROVED"
)


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def load_env_file(
    path: Path,
) -> dict[str, str]:
    values: dict[str, str] = {}

    for raw_line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            continue

        key, raw_value = line.split(
            "=",
            1,
        )

        value = raw_value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {
                "'",
                '"',
            }
        ):
            value = value[1:-1]

        values[key.strip()] = value

    return values


def build_request_material(
    values: dict[str, str],
) -> tuple[str, str]:
    for key in [
        "WORDPRESS_BASE_URL",
        "WORDPRESS_USERNAME",
        "WORDPRESS_APP_PASSWORD",
    ]:
        if not values.get(key):
            raise RuntimeError(
                f"REQUIRED_CREDENTIAL_KEY_MISSING:{key}"
            )

    parsed = urlsplit(
        values["WORDPRESS_BASE_URL"]
    )

    if parsed.scheme != "https":
        raise RuntimeError(
            "WORDPRESS_BASE_URL_NOT_HTTPS"
        )

    if parsed.hostname != EXPECTED_HOST:
        raise RuntimeError(
            "WORDPRESS_HOST_MISMATCH"
        )

    if parsed.port not in {
        None,
        443,
    }:
        raise RuntimeError(
            "WORDPRESS_PORT_MISMATCH"
        )

    if parsed.query or parsed.fragment:
        raise RuntimeError(
            "WORDPRESS_BASE_URL_HAS_QUERY_OR_FRAGMENT"
        )

    base_path = parsed.path.rstrip("/")

    url = (
        f"https://{EXPECTED_HOST}"
        f"{base_path}/wp-json/wp/v2/posts/"
        f"{EXPECTED_POST_ID}"
        "?context=edit"
        "&_fields=id,status,title,categories,"
        "comment_status,content"
    )

    token = base64.b64encode(
        (
            values["WORDPRESS_USERNAME"]
            + ":"
            + values["WORDPRESS_APP_PASSWORD"]
        ).encode("utf-8")
    ).decode("ascii")

    return url, "Basic " + token


def urllib_single_get_transport(
    url: str,
    authorization_value: str,
    timeout_seconds: int,
) -> tuple[int, bytes]:
    request = Request(
        url,
        method="GET",
        headers={
            "Authorization": authorization_value,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": (
                "ai-media-os-m27-fix1-get-only/1.0"
            ),
            "Connection": "close",
        },
    )

    opener = build_opener(
        NoRedirectHandler()
    )

    try:
        with opener.open(
            request,
            timeout=timeout_seconds,
        ) as response:
            status = int(
                response.getcode()
            )
            body = response.read(
                MAX_RESPONSE_BYTES + 1
            )
    except HTTPError as exc:
        status = int(exc.code)
        body = exc.read(
            MAX_RESPONSE_BYTES + 1
        )

    if len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError(
            "RESPONSE_SIZE_LIMIT_EXCEEDED"
        )

    return status, body


def execute_with_transport(
    transport: Callable[
        [str, str, int],
        tuple[int, bytes],
    ],
    url: str,
    authorization_value: str,
    timeout_seconds: int = 25,
) -> dict[str, Any]:
    get_request_count = 1

    try:
        status, body = transport(
            url,
            authorization_value,
            timeout_seconds,
        )

        try:
            response_json = json.loads(
                body.decode("utf-8")
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            response_json = None

        return {
            "request_method": "GET",
            "get_request_count": (
                get_request_count
            ),
            "non_get_request_count": 0,
            "automatic_retry_count": 0,
            "redirect_followed": False,
            "http_status_code": status,
            "response_json_object": isinstance(
                response_json,
                dict,
            ),
            "network_error_type": None,
            "failure_stage": None,
            "credential_value_output": False,
            "full_url_output": False,
            "authorization_header_output": False,
            "wordpress_content_output": False
        }

    except Exception as exc:
        return {
            "request_method": "GET",
            "get_request_count": (
                get_request_count
            ),
            "non_get_request_count": 0,
            "automatic_retry_count": 0,
            "redirect_followed": False,
            "http_status_code": None,
            "response_json_object": False,
            "network_error_type": (
                type(exc).__name__
            ),
            "failure_stage": (
                "SINGLE_TRANSPORT_CALL"
            ),
            "credential_value_output": False,
            "full_url_output": False,
            "authorization_header_output": False,
            "wordpress_content_output": False
        }


def main() -> int:
    if os.environ.get(
        NETWORK_APPROVAL_ENV
    ) != "YES":
        print(
            json.dumps(
                {
                    "status": (
                        "BLOCKED_NO_EXPLICIT_SINGLE_GET_"
                        "NETWORK_APPROVAL"
                    ),
                    "get_request_count": 0,
                    "non_get_request_count": 0,
                    "automatic_retry_count": 0,
                    "wordpress_write_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_consumed": False,
                    "production_status": "NO_GO"
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    try:
        values = load_env_file(
            CREDENTIAL_ENV
        )
        url, authorization_value = (
            build_request_material(values)
        )

        result = execute_with_transport(
            urllib_single_get_transport,
            url,
            authorization_value,
        )

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": (
                        "BLOCKED_BEFORE_SINGLE_GET"
                    ),
                    "safe_error_type": (
                        type(exc).__name__
                    ),
                    "get_request_count": 0,
                    "non_get_request_count": 0,
                    "automatic_retry_count": 0,
                    "wordpress_write_performed": False,
                    "wordpress_update_performed": False,
                    "authorization_consumed": False,
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
