from __future__ import annotations

import os
from collections.abc import Mapping
from urllib.parse import urlencode

from app.integrations.rakuten_kobo_api_client import (
    RakutenKoboApiError,
    RakutenKoboRequestConfiguration,
)


OFFICIAL_ENDPOINT = (
    "https://openapi.rakuten.co.jp/services/api/Kobo/EbookSearch/20170426"
)
OFFICIAL_ELEMENTS = (
    "title",
    "author",
    "publisherName",
    "itemNumber",
    "salesDate",
    "itemPrice",
    "itemUrl",
    "affiliateUrl",
    "smallImageUrl",
    "mediumImageUrl",
    "largeImageUrl",
    "koboGenreId",
    "salesType",
)


def load_repository_live_configuration(
    *,
    title: str | None = None,
    item_number: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> RakutenKoboRequestConfiguration | None:
    values = os.environ if environment is None else environment
    application_id = _environment_value(
        values, "RAKUTEN_KOBO_APPLICATION_ID"
    )
    access_key = _environment_value(values, "RAKUTEN_KOBO_ACCESS_KEY")
    affiliate_id = _environment_value(
        values, "RAKUTEN_KOBO_AFFILIATE_ID"
    )
    if application_id is None or access_key is None:
        return None
    return build_live_request_configuration(
        application_id=application_id,
        access_key=access_key,
        affiliate_id=affiliate_id,
        title=title,
        item_number=item_number,
    )


def build_live_request_configuration(
    *,
    application_id: str,
    access_key: str,
    affiliate_id: str | None = None,
    title: str | None = None,
    item_number: str | None = None,
) -> RakutenKoboRequestConfiguration:
    normalized_application_id = _required_value(application_id)
    normalized_access_key = _required_value(access_key)
    normalized_affiliate_id = _optional_value(affiliate_id)
    normalized_title = _optional_value(title)
    normalized_item_number = _optional_value(item_number)
    if normalized_title is None and normalized_item_number is None:
        raise RakutenKoboApiError("SEARCH_SELECTOR_REQUIRED")

    query: list[tuple[str, str | int]] = [
        ("applicationId", normalized_application_id),
        ("format", "json"),
        ("formatVersion", 1),
        ("language", "JA"),
        ("hits", 1),
        ("page", 1),
        ("elements", ",".join(OFFICIAL_ELEMENTS)),
    ]
    if normalized_affiliate_id is not None:
        query.append(("affiliateId", normalized_affiliate_id))
    if normalized_title is not None:
        query.append(("title", normalized_title))
    if normalized_item_number is not None:
        query.append(("itemNumber", normalized_item_number))

    return RakutenKoboRequestConfiguration(
        endpoint_url=f"{OFFICIAL_ENDPOINT}?{urlencode(query)}",
        headers={"accessKey": normalized_access_key},
    )


def _environment_value(
    environment: Mapping[str, str], name: str
) -> str | None:
    value = environment.get(name)
    return _optional_value(value)


def _required_value(value: str) -> str:
    normalized = _optional_value(value)
    if normalized is None:
        raise RakutenKoboApiError("REQUIRED_CONFIGURATION_MISSING")
    return normalized


def _optional_value(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RakutenKoboApiError("INVALID_CONFIGURATION_VALUE")
    if "\r" in value or "\n" in value:
        raise RakutenKoboApiError("INVALID_CONFIGURATION_VALUE")
    normalized = value.strip()
    return normalized or None