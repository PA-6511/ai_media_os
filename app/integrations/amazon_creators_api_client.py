from __future__ import annotations

"""Small, secret-safe client for Amazon Creators API (Credential Version 3.3)."""

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

import requests


TOKEN_ENDPOINT_JP = "https://api.amazon.co.jp/auth/o2/token"
API_BASE_URL = "https://creatorsapi.amazon/catalog/v1"
MARKETPLACE_JP = "www.amazon.co.jp"
TOKEN_SCOPE = "creatorsapi::default"
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class AmazonCreatorsApiError(RuntimeError):
    """Deliberately contains no credential, bearer token, request body or URL."""

    def __init__(self, code: str, *, status_code: int | None = None, retryable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable

    @property
    def safe_summary(self) -> str:
        parts = [self.code]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        return ";".join(parts)


@dataclass(frozen=True)
class AmazonCreatorsCredentials:
    credential_id: str
    credential_secret: str
    partner_tag: str
    credential_version: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "AmazonCreatorsCredentials":
        values = os.environ if environment is None else environment
        credential_id = str(values.get("AMAZON_CREATORS_CREDENTIAL_ID") or "").strip()
        credential_secret = str(values.get("AMAZON_CREATORS_CREDENTIAL_SECRET") or "").strip()
        partner_tag = str(values.get("AMAZON_PARTNER_TAG") or "").strip()
        version = str(values.get("AMAZON_CREATORS_CREDENTIAL_VERSION") or "").strip()
        if not credential_id or not credential_secret or not partner_tag or not version:
            raise AmazonCreatorsApiError("CREATORS_CREDENTIALS_NOT_CONFIGURED")
        if version != "3.3":
            raise AmazonCreatorsApiError("CREATORS_CREDENTIAL_VERSION_UNSUPPORTED")
        return cls(credential_id, credential_secret, partner_tag, version)


@dataclass(frozen=True)
class AmazonCreatorsItem:
    asin: str
    title: str | None
    detail_page_url: str | None
    cover_url: str | None
    authors: tuple[str, ...]
    publisher: str | None
    isbn_values: tuple[str, ...]
    is_kindle: bool
    raw: Mapping[str, Any]


class AmazonCreatorsApiClient:
    """OAuth-caching Creators API client with bounded retries and safe errors."""

    def __init__(
        self,
        credentials: AmazonCreatorsCredentials,
        *,
        session: requests.Session | None = None,
        timeout_seconds: float = 20.0,
        max_attempts: int = 3,
        minimum_request_interval_seconds: float = 0.0,
        now: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if timeout_seconds <= 0 or max_attempts < 1 or minimum_request_interval_seconds < 0:
            raise ValueError("invalid Amazon Creators API client configuration")
        self.credentials = credentials
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.minimum_request_interval_seconds = minimum_request_interval_seconds
        self._now = now
        self._sleep = sleep
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._last_request_started_at: float | None = None

    @classmethod
    def from_environment(cls, **kwargs: Any) -> "AmazonCreatorsApiClient":
        return cls(AmazonCreatorsCredentials.from_environment(), **kwargs)

    def close(self) -> None:
        self.session.close()

    def search_items(
        self,
        *,
        title: str | None = None,
        keywords: str | None = None,
        author: str | None = None,
        item_count: int = 10,
        search_index: str = "Books",
    ) -> tuple[AmazonCreatorsItem, ...]:
        if item_count < 1 or item_count > 10:
            raise ValueError("item_count must be between 1 and 10")
        payload: dict[str, Any] = {
            "marketplace": MARKETPLACE_JP,
            "partnerTag": self.credentials.partner_tag,
            "searchIndex": search_index,
            "itemCount": item_count,
            "resources": _resources(),
        }
        for key, value in (("title", title), ("keywords", keywords), ("author", author)):
            if value and value.strip():
                payload[key] = value.strip()
        if not any(key in payload for key in ("title", "keywords", "author")):
            raise ValueError("one of title, keywords, or author is required")
        return self._request_items("searchItems", payload)

    def get_items(self, asins: list[str] | tuple[str, ...]) -> tuple[AmazonCreatorsItem, ...]:
        normalized = tuple(dict.fromkeys(str(value).strip().upper() for value in asins if str(value).strip()))
        if not normalized or len(normalized) > 10:
            raise ValueError("between 1 and 10 ASINs are required")
        return self._request_items(
            "getItems",
            {
                "marketplace": MARKETPLACE_JP,
                "partnerTag": self.credentials.partner_tag,
                "itemIds": list(normalized),
                "itemIdType": "ASIN",
                "resources": _resources(),
            },
        )

    def _request_items(self, operation: str, payload: Mapping[str, Any]) -> tuple[AmazonCreatorsItem, ...]:
        response = self._post_with_retry(
            f"{API_BASE_URL}/{operation}",
            headers={
                "Authorization": f"Bearer {self._get_access_token()}",
                "Content-Type": "application/json",
                "x-marketplace": MARKETPLACE_JP,
            },
            json=dict(payload),
            error_prefix="CREATORS_API",
        )
        try:
            body = response.json()
        except ValueError as exc:
            raise AmazonCreatorsApiError("CREATORS_RESPONSE_INVALID") from exc
        if not isinstance(body, Mapping):
            raise AmazonCreatorsApiError("CREATORS_RESPONSE_INVALID")
        result = body.get("searchResult") or body.get("itemsResult") or body.get("getItemsResult") or body
        items = result.get("items") if isinstance(result, Mapping) else None
        if items is None:
            return ()
        if not isinstance(items, list):
            raise AmazonCreatorsApiError("CREATORS_RESPONSE_INVALID")
        return tuple(item for item in (_parse_item(raw) for raw in items) if item is not None)

    def _get_access_token(self) -> str:
        if self._access_token and self._now() < self._token_expires_at:
            return self._access_token
        response = self._post_with_retry(
            TOKEN_ENDPOINT_JP,
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "client_credentials",
                "client_id": self.credentials.credential_id,
                "client_secret": self.credentials.credential_secret,
                "scope": TOKEN_SCOPE,
            },
            error_prefix="CREATORS_OAUTH",
        )
        try:
            body = response.json()
            token = str(body.get("access_token") or "").strip()
            expires_in = int(body.get("expires_in") or 0)
        except (AttributeError, TypeError, ValueError) as exc:
            raise AmazonCreatorsApiError("CREATORS_OAUTH_RESPONSE_INVALID") from exc
        if not token or expires_in <= 0:
            raise AmazonCreatorsApiError("CREATORS_OAUTH_RESPONSE_INVALID")
        self._access_token = token
        self._token_expires_at = self._now() + max(1, expires_in - 60)
        return token

    def _post_with_retry(self, url: str, *, headers: Mapping[str, str], json: Mapping[str, Any], error_prefix: str) -> requests.Response:
        for attempt in range(self.max_attempts):
            try:
                self._wait_for_request_slot()
                response = self.session.post(url, headers=dict(headers), json=dict(json), timeout=self.timeout_seconds)
            except requests.RequestException as exc:
                if attempt + 1 == self.max_attempts:
                    raise AmazonCreatorsApiError(f"{error_prefix}_TRANSPORT_FAILED", retryable=True) from exc
                self._sleep(2**attempt)
                continue
            if 200 <= response.status_code < 300:
                return response
            retryable = response.status_code in RETRYABLE_STATUS_CODES
            if retryable and attempt + 1 < self.max_attempts:
                self._sleep(2**attempt)
                continue
            code = "RATE_LIMIT" if response.status_code == 429 else "HTTP_ERROR"
            raise AmazonCreatorsApiError(f"{error_prefix}_{code}", status_code=response.status_code, retryable=retryable)
        raise AssertionError("unreachable")

    def _wait_for_request_slot(self) -> None:
        if self._last_request_started_at is not None:
            wait_seconds = self.minimum_request_interval_seconds - (self._now() - self._last_request_started_at)
            if wait_seconds > 0:
                self._sleep(wait_seconds)
        self._last_request_started_at = self._now()


def _resources() -> list[str]:
    return [
        "images.primary.large",
        "images.primary.medium",
        "itemInfo.title",
        "itemInfo.byLineInfo",
        "itemInfo.productInfo",
        "itemInfo.classifications",
        "itemInfo.externalIds",
    ]


def _parse_item(raw: Any) -> AmazonCreatorsItem | None:
    if not isinstance(raw, Mapping):
        return None
    asin = str(raw.get("asin") or "").strip().upper()
    if len(asin) != 10 or not asin.isalnum():
        return None
    item_info = raw.get("itemInfo") if isinstance(raw.get("itemInfo"), Mapping) else {}
    by_line = item_info.get("byLineInfo") if isinstance(item_info.get("byLineInfo"), Mapping) else {}
    external_ids = item_info.get("externalIds") if isinstance(item_info.get("externalIds"), Mapping) else {}
    classifications = item_info.get("classifications") if isinstance(item_info.get("classifications"), Mapping) else {}
    images = raw.get("images") if isinstance(raw.get("images"), Mapping) else {}
    primary = images.get("primary") if isinstance(images.get("primary"), Mapping) else {}
    contributors = by_line.get("contributors") if isinstance(by_line.get("contributors"), list) else []
    authors = tuple(str(row.get("name")).strip() for row in contributors if isinstance(row, Mapping) and str(row.get("name") or "").strip())
    isbn_values = tuple(str(value).replace("-", "").strip() for value in external_ids.get("isbNs", {}).get("displayValues", []) if str(value).strip()) if isinstance(external_ids.get("isbNs"), Mapping) else ()
    cover_url = _first_url(primary, ("large", "medium"))
    title = _display_value(item_info.get("title"))
    publisher = _display_value(by_line.get("publisher"))
    classification_text = " ".join(
        value for value in (_display_value(entry) for entry in classifications.values()) if value
    ).lower()
    is_kindle = "kindle" in classification_text or "電子書籍" in classification_text
    return AmazonCreatorsItem(asin, title, _text(raw.get("detailPageURL")), cover_url, authors, publisher, isbn_values, is_kindle, raw)


def _first_url(primary: Mapping[str, Any], sizes: tuple[str, ...]) -> str | None:
    for size in sizes:
        value = primary.get(size)
        if isinstance(value, Mapping):
            url = _text(value.get("url"))
            if url:
                return url
    return None


def _display_value(value: Any) -> str | None:
    return _text(value.get("displayValue")) if isinstance(value, Mapping) else _text(value)


def _text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None
