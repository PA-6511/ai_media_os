from __future__ import annotations

import hashlib
import json
import re
import socket
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping, Protocol
from urllib.parse import parse_qsl, urlsplit

import requests


DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class RakutenKoboFailureDetails:
    """Allowlisted diagnostics that never contain request or header values."""

    response_status: int | None = None
    response_content_type: str | None = None
    response_content_length_present: bool = False
    response_content_length: int | None = None
    provider_error_code: str | None = None
    provider_error_message: str | None = None
    failure_category: str = "OTHER"
    retryable: bool = False
    request_host: str | None = None
    request_path: str | None = None
    request_query_key_names: tuple[str, ...] = ()
    request_header_names: tuple[str, ...] = ()
    response_body_sha256: str | None = None
    response_body_byte_count: int | None = None


class RakutenKoboApiError(RuntimeError):
    """A response or transport failure safe to expose without request secrets."""

    def __init__(
        self,
        code: str,
        *,
        status_code: int | None = None,
        cause: BaseException | None = None,
        failure_details: RakutenKoboFailureDetails | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.cause_type = type(cause).__name__ if cause is not None else None
        self.failure_details = failure_details

    @property
    def safe_summary(self) -> str:
        parts = [self.code]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.cause_type is not None:
            parts.append(f"cause={self.cause_type}")
        return ";".join(parts)


@dataclass(frozen=True)
class RakutenKoboRequestConfiguration:
    """Opaque request material supplied by a separately reviewed config adapter.

    This module intentionally does not invent an endpoint, authentication scheme,
    header name, or query parameter.  Secrets may be carried in ``headers`` but
    are never included in results or exception text.
    """

    endpoint_url: str = field(repr=False)
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        parsed = urlsplit(self.endpoint_url)
        if parsed.scheme.lower() != "https":
            raise RakutenKoboApiError("HTTPS_REQUIRED")
        if not parsed.hostname or parsed.username or parsed.password:
            raise RakutenKoboApiError("INVALID_ENDPOINT")
        if parsed.fragment:
            raise RakutenKoboApiError("ENDPOINT_FRAGMENT_FORBIDDEN")
        normalized_headers: dict[str, str] = {}
        for name, value in self.headers.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise RakutenKoboApiError("INVALID_HEADER_CONFIGURATION")
            if not name.strip() or "\n" in name or "\r" in name:
                raise RakutenKoboApiError("INVALID_HEADER_CONFIGURATION")
            if "\n" in value or "\r" in value:
                raise RakutenKoboApiError("INVALID_HEADER_CONFIGURATION")
            normalized_headers[name] = value
        object.__setattr__(self, "headers", MappingProxyType(normalized_headers))

    @property
    def endpoint_host(self) -> str:
        return str(urlsplit(self.endpoint_url).hostname or "").lower()


@dataclass(frozen=True)
class TransportResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


class GetOnlyTransport(Protocol):
    def get(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
        maximum_bytes: int,
    ) -> TransportResponse: ...


class RequestsGetTransport:
    """The only concrete live transport.  It exposes no non-GET operation."""

    def get(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
        maximum_bytes: int,
    ) -> TransportResponse:
        session = requests.Session()
        try:
            with session.get(
                url,
                headers=dict(headers),
                timeout=timeout_seconds,
                allow_redirects=False,
                stream=True,
            ) as response:
                declared_length = response.headers.get("Content-Length")
                if declared_length:
                    try:
                        if int(declared_length) > maximum_bytes:
                            raise RakutenKoboApiError("RESPONSE_SIZE_LIMIT_EXCEEDED")
                    except ValueError as exc:
                        raise RakutenKoboApiError(
                            "INVALID_CONTENT_LENGTH", cause=exc
                        ) from exc
                chunks: list[bytes] = []
                received = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > maximum_bytes:
                        raise RakutenKoboApiError("RESPONSE_SIZE_LIMIT_EXCEEDED")
                    chunks.append(bytes(chunk))
                return TransportResponse(
                    status_code=int(response.status_code),
                    headers={str(k): str(v) for k, v in response.headers.items()},
                    body=b"".join(chunks),
                )
        except RakutenKoboApiError:
            raise
        except requests.RequestException as exc:
            raise RakutenKoboApiError(
                "GET_TRANSPORT_FAILED",
                cause=exc,
                failure_details=RakutenKoboFailureDetails(
                    failure_category=_transport_failure_category(exc),
                    retryable=True,
                ),
            ) from None
        finally:
            session.close()


@dataclass(frozen=True)
class FetchedRakutenKoboResponse:
    endpoint_host: str
    status_code: int
    content_type: str
    body: bytes


class RakutenKoboApiClient:
    def __init__(
        self,
        transport: GetOnlyTransport,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        maximum_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if maximum_response_bytes <= 0:
            raise ValueError("maximum_response_bytes must be positive")
        self._transport = transport
        self.timeout_seconds = float(timeout_seconds)
        self.maximum_response_bytes = int(maximum_response_bytes)

    def fetch(
        self, configuration: RakutenKoboRequestConfiguration
    ) -> FetchedRakutenKoboResponse:
        request_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": "ai-media-os-rakuten-kobo-get-collector/1.0",
            **configuration.headers,
        }
        try:
            response = self._transport.get(
                url=configuration.endpoint_url,
                headers=request_headers,
                timeout_seconds=self.timeout_seconds,
                maximum_bytes=self.maximum_response_bytes,
            )
        except RakutenKoboApiError as exc:
            exc.failure_details = _with_request_context(
                exc.failure_details,
                configuration=configuration,
                request_headers=request_headers,
            )
            raise
        failure_details = _response_failure_details(
            response,
            configuration=configuration,
            request_headers=request_headers,
        )
        if 300 <= response.status_code < 400:
            raise RakutenKoboApiError(
                "REDIRECT_REFUSED",
                status_code=response.status_code,
                failure_details=failure_details,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise RakutenKoboApiError(
                "HTTP_STATUS_ERROR",
                status_code=response.status_code,
                failure_details=failure_details,
            )
        if len(response.body) > self.maximum_response_bytes:
            raise RakutenKoboApiError(
                "RESPONSE_SIZE_LIMIT_EXCEEDED",
                failure_details=replace(
                    failure_details,
                    failure_category="RESPONSE_SIZE_LIMIT_EXCEEDED",
                    retryable=False,
                ),
            )
        content_type = _header(response.headers, "content-type")
        media_type = content_type.split(";", 1)[0].strip().lower()
        if media_type != "application/json" and not (
            media_type.startswith("application/") and media_type.endswith("+json")
        ):
            raise RakutenKoboApiError(
                "JSON_CONTENT_TYPE_REQUIRED",
                failure_details=replace(
                    failure_details,
                    failure_category="CONTENT_TYPE_INVALID",
                    retryable=False,
                ),
            )
        return FetchedRakutenKoboResponse(
            endpoint_host=configuration.endpoint_host,
            status_code=response.status_code,
            content_type=content_type,
            body=response.body,
        )


def _header(headers: Mapping[str, str], name: str) -> str:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered:
            return str(value)
    return ""


def _response_failure_details(
    response: TransportResponse,
    *,
    configuration: RakutenKoboRequestConfiguration,
    request_headers: Mapping[str, str],
) -> RakutenKoboFailureDetails:
    content_type = _media_type(_header(response.headers, "content-type"))
    content_length_header = _header(response.headers, "content-length")
    provider_code, provider_message = _provider_error_fields(
        response.body,
        secret_values=_request_secret_values(configuration),
    )
    return _with_request_context(
        RakutenKoboFailureDetails(
            response_status=int(response.status_code),
            response_content_type=content_type,
            response_content_length_present=_has_header(
                response.headers, "content-length"
            ),
            response_content_length=_safe_content_length(content_length_header),
            provider_error_code=provider_code,
            provider_error_message=provider_message,
            failure_category=_response_failure_category(response.status_code),
            retryable=response.status_code == 429 or response.status_code >= 500,
            response_body_sha256=hashlib.sha256(response.body).hexdigest(),
            response_body_byte_count=len(response.body),
        ),
        configuration=configuration,
        request_headers=request_headers,
    )


def _with_request_context(
    details: RakutenKoboFailureDetails | None,
    *,
    configuration: RakutenKoboRequestConfiguration,
    request_headers: Mapping[str, str],
) -> RakutenKoboFailureDetails:
    current = details or RakutenKoboFailureDetails()
    parsed = urlsplit(configuration.endpoint_url)
    query_names = tuple(
        dict.fromkeys(
            name
            for name, _value in parse_qsl(parsed.query, keep_blank_values=True)
            if _safe_name(name)
        )
    )
    header_names = tuple(
        sorted(
            (
                name
                for name in request_headers
                if _safe_name(name)
                and name.lower()
                not in {
                    "authorization",
                    "cookie",
                    "proxy-authorization",
                    "set-cookie",
                }
            ),
            key=str.lower,
        )
    )
    return replace(
        current,
        request_host=str(parsed.hostname or "").lower() or None,
        request_path=_safe_path(parsed.path),
        request_query_key_names=query_names,
        request_header_names=header_names,
    )


def _request_secret_values(
    configuration: RakutenKoboRequestConfiguration,
) -> tuple[str, ...]:
    parsed = urlsplit(configuration.endpoint_url)
    query_secrets = [
        value
        for name, value in parse_qsl(parsed.query, keep_blank_values=True)
        if name in {"applicationId", "affiliateId"} and value
    ]
    header_secrets = [value for value in configuration.headers.values() if value]
    return tuple(query_secrets + header_secrets)


def _provider_error_fields(
    body: bytes, *, secret_values: tuple[str, ...]
) -> tuple[str | None, str | None]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return None, None
    candidates: list[Mapping[str, object]] = []
    if isinstance(value, dict):
        candidates.append(value)
        for key in ("error", "errors"):
            nested = value.get(key)
            if isinstance(nested, dict):
                candidates.insert(0, nested)
            elif isinstance(nested, list) and nested and isinstance(nested[0], dict):
                candidates.insert(0, nested[0])
    code: object | None = None
    message: object | None = None
    for candidate in candidates:
        code = code or _first_value(
            candidate, ("code", "errorCode", "error_code", "error")
        )
        message = message or _first_value(
            candidate,
            ("message", "errorMessage", "error_message", "error_description"),
        )
    return (
        _safe_provider_text(code, secret_values=secret_values, maximum=128),
        _safe_provider_text(message, secret_values=secret_values, maximum=512),
    )


def _first_value(
    value: Mapping[str, object], names: tuple[str, ...]
) -> object | None:
    for name in names:
        candidate = value.get(name)
        if isinstance(candidate, (str, int)) and not isinstance(candidate, bool):
            return candidate
    return None


def _safe_provider_text(
    value: object | None, *, secret_values: tuple[str, ...], maximum: int
) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())[:maximum]
    if not text:
        return None
    for secret in secret_values:
        if secret and secret in text:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"https?://\S+", "[REDACTED_URL]", text, flags=re.IGNORECASE)
    replacements = {
        r"application[_ ]id": "applicationId",
        r"affiliate[_ ]id": "affiliateId",
        r"access[_ ]key": "accessKey",
        r"authorization": "authentication",
        r"set-cookie|cookie": "[REDACTED_HEADER]",
        r"response_body": "response body",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text or None


def _safe_content_length(value: str) -> int | None:
    if not value or not value.isascii() or not value.isdecimal():
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _has_header(headers: Mapping[str, str], name: str) -> bool:
    lowered = name.lower()
    return any(key.lower() == lowered for key in headers)


def _response_failure_category(status_code: int) -> str:
    if status_code in {400, 401, 403, 404, 429}:
        return f"HTTP_{status_code}"
    if 500 <= status_code < 600:
        return "HTTP_5XX"
    if 300 <= status_code < 400:
        return "REDIRECT_REFUSED"
    return "OTHER"


def _transport_failure_category(exc: requests.RequestException) -> str:
    if isinstance(exc, requests.Timeout):
        return "TIMEOUT"
    if isinstance(exc, requests.exceptions.SSLError):
        return "TLS_FAILURE"
    if isinstance(exc, requests.ConnectionError):
        current: BaseException | None = exc
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            if isinstance(current, socket.gaierror):
                return "DNS_FAILURE"
            current = current.__cause__ or current.__context__
        return "CONNECTION_FAILURE"
    return "OTHER"


def _media_type(value: str) -> str | None:
    media_type = str(value or "").split(";", 1)[0].strip().lower()
    if not media_type or len(media_type) > 128:
        return None
    if not re.fullmatch(r"[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+", media_type):
        return None
    return media_type


def _safe_name(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9!#$%&'*+.^_`|~-]{1,128}", value))


def _safe_path(value: str) -> str | None:
    if not value.startswith("/") or len(value) > 1024:
        return None
    if any(token in value for token in ("?", "#", "://")):
        return None
    return value
