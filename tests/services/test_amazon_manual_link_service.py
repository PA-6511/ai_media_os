from __future__ import annotations

import pytest

from app.services.amazon_manual_link_service import (
    AmazonManualLinkError,
    AmazonManualLinkService,
)


def test_generate_amazon_manual_link() -> None:
    service = AmazonManualLinkService()

    result = service.generate(
        asin="b0abcdefgh",
        tracking_id="example-22",
    )

    assert result.asin == "B0ABCDEFGH"
    assert (
        result.product_url
        == "https://www.amazon.co.jp/dp/B0ABCDEFGH"
    )
    assert (
        result.affiliate_url
        == "https://www.amazon.co.jp/dp/"
        "B0ABCDEFGH/ref=nosim?tag=example-22"
    )


@pytest.mark.parametrize(
    "asin",
    [
        "",
        "B0ABC",
        "B0ABCDEFGHI",
        "B0ABC!EFGH",
        "Ｂ０ＡＢＣＤＥＦＧＨ",
    ],
)
def test_reject_invalid_asin(asin: str) -> None:
    service = AmazonManualLinkService()

    with pytest.raises(AmazonManualLinkError):
        service.generate(
            asin=asin,
            tracking_id="example-22",
        )


@pytest.mark.parametrize(
    "tracking_id",
    [
        "",
        "example",
        "example22",
        "example-2",
        "example-222",
        "example 22",
    ],
)
def test_reject_invalid_tracking_id(tracking_id: str) -> None:
    service = AmazonManualLinkService()

    with pytest.raises(AmazonManualLinkError):
        service.generate(
            asin="B0ABCDEFGH",
            tracking_id=tracking_id,
        )
