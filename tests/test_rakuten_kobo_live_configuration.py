from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from app.integrations.rakuten_kobo_api_client import RakutenKoboApiError
from app.integrations.rakuten_kobo_live_configuration import (
    OFFICIAL_ELEMENTS,
    OFFICIAL_ENDPOINT,
    build_live_request_configuration,
    load_repository_live_configuration,
)


ACCESS_KEY = "secret-access-key"


@pytest.mark.parametrize(
    "environment",
    [
        {"RAKUTEN_KOBO_ACCESS_KEY": ACCESS_KEY},
        {"RAKUTEN_KOBO_APPLICATION_ID": "application-id"},
        {
            "RAKUTEN_KOBO_APPLICATION_ID": "   ",
            "RAKUTEN_KOBO_ACCESS_KEY": ACCESS_KEY,
        },
    ],
)
def test_missing_required_environment_is_not_configured(environment) -> None:
    assert load_repository_live_configuration(
        title="作品", environment=environment
    ) is None


def test_official_configuration_uses_query_and_secret_header() -> None:
    configuration = build_live_request_configuration(
        application_id=" application-id ",
        access_key=f" {ACCESS_KEY} ",
        title=" SAKAMOTO DAYS 28 ",
        item_number=" item-28 ",
    )
    parsed = urlsplit(configuration.endpoint_url)
    query = parse_qs(parsed.query)

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == OFFICIAL_ENDPOINT
    assert parsed.scheme == "https"
    assert parsed.hostname == "openapi.rakuten.co.jp"
    assert parsed.path == "/services/api/Kobo/EbookSearch/20170426"
    assert "app.rakuten.co.jp" not in configuration.endpoint_url
    assert query == {
        "applicationId": ["application-id"],
        "format": ["json"],
        "formatVersion": ["1"],
        "language": ["JA"],
        "hits": ["1"],
        "page": ["1"],
        "elements": [",".join(OFFICIAL_ELEMENTS)],
        "title": ["SAKAMOTO DAYS 28"],
        "itemNumber": ["item-28"],
    }
    assert configuration.headers == {"accessKey": ACCESS_KEY}
    assert ACCESS_KEY not in configuration.endpoint_url
    assert "%E4%BD%9C%E5%93%81" in build_live_request_configuration(
        application_id="application-id",
        access_key=ACCESS_KEY,
        title="作品",
    ).endpoint_url


def test_optional_affiliate_id_is_omitted_or_added() -> None:
    without = build_live_request_configuration(
        application_id="application-id",
        access_key=ACCESS_KEY,
        title="作品",
    )
    with_affiliate = build_live_request_configuration(
        application_id="application-id",
        access_key=ACCESS_KEY,
        affiliate_id="affiliate-id",
        item_number="item-1",
    )
    assert "affiliateId" not in parse_qs(urlsplit(without.endpoint_url).query)
    assert parse_qs(urlsplit(with_affiliate.endpoint_url).query)["affiliateId"] == [
        "affiliate-id"
    ]


def test_selector_is_required_before_request_configuration() -> None:
    with pytest.raises(RakutenKoboApiError) as exc:
        build_live_request_configuration(
            application_id="application-id",
            access_key=ACCESS_KEY,
        )
    assert exc.value.code == "SEARCH_SELECTOR_REQUIRED"


@pytest.mark.parametrize("value", ["bad\nvalue", "bad\rvalue"])
def test_newlines_are_rejected_without_secret_disclosure(value: str) -> None:
    with pytest.raises(RakutenKoboApiError) as exc:
        build_live_request_configuration(
            application_id="application-id",
            access_key=value,
            title="作品",
        )
    assert value not in str(exc.value)
    assert value not in exc.value.safe_summary


def test_configuration_repr_hides_endpoint_and_access_key() -> None:
    configuration = build_live_request_configuration(
        application_id="application-id",
        access_key=ACCESS_KEY,
        affiliate_id="affiliate-id",
        title="作品",
    )
    rendered = repr(configuration)
    assert ACCESS_KEY not in rendered
    assert "application-id" not in rendered
    assert "affiliate-id" not in rendered
    assert configuration.endpoint_host == "openapi.rakuten.co.jp"