import json
from types import SimpleNamespace

from app.services.verified_cover_lookup import (
    verified_kobo_item,
)


DB_ID = "2000021568661"

PRODUCT_URL = (
    "https://books.rakuten.co.jp/"
    "rk/94afc762ec763b03b50b4f9ce968dd3e/"
)

API_ID = "6671315341810"


class FakeClient:
    def __init__(self):
        self.calls = 0

    def fetch(self, _configuration):
        self.calls += 1

        if self.calls == 1:
            payload = {
                "Items": [],
            }

        else:
            payload = {
                "Items": [
                    {
                        "Item": {
                            "title": "other",
                            "itemNumber":
                                "9999999999999",
                            "itemUrl":
                                "https://books.rakuten.co.jp/"
                                "rk/not-this-product/",
                            "largeImageUrl":
                                "https://thumbnail.image."
                                "rakuten.co.jp/test/other.jpg",
                            "affiliateUrl":
                                "https://hb.afl.rakuten.co.jp/test",
                        }
                    },
                    {
                        "Item": {
                            "title": "target",
                            "itemNumber":
                                API_ID,
                            "itemUrl":
                                PRODUCT_URL,
                            "largeImageUrl":
                                "https://thumbnail.image."
                                "rakuten.co.jp/test/target.jpg",
                            "affiliateUrl":
                                "https://hb.afl.rakuten.co.jp/test",
                        }
                    },
                ],
            }

        return SimpleNamespace(
            body=json.dumps(
                payload
            ).encode("utf-8")
        )


def test_zero_exact_id_falls_back_to_exact_product_url():
    calls = []

    def loader(**kwargs):
        calls.append(kwargs)
        return object()

    result = verified_kobo_item(
        SimpleNamespace(
            title=(
                "アプレト〜無双の勇者×"
                "はじまりのゆうしゃ〜【合冊版】"
            ),
        ),
        SimpleNamespace(
            store_item_id=DB_ID,
            product_url=PRODUCT_URL,
        ),
        api_client=FakeClient(),
        configuration_loader=loader,
    )

    assert result["itemNumber"] == API_ID
    assert result["itemUrl"] == PRODUCT_URL

    assert calls == [
        {
            "title": None,
            "item_number": DB_ID,
        },
        {
            "title": (
                "アプレト〜無双の勇者×"
                "はじまりのゆうしゃ〜【合冊版】"
            ),
            "item_number": None,
            "hits": 30,
        },
    ]
