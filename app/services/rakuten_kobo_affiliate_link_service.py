from __future__ import annotations

# KOBO_AFFILIATE_AUTO_GENERATE_V2_2

from dataclasses import dataclass
import re
from urllib.parse import urlencode, urlsplit

from app.services.store_url_policy import (
    StoreUrlPolicyError,
    normalize_store_url,
)


class RakutenKoboAffiliateLinkError(
    ValueError
):
    pass


@dataclass(frozen=True)
class RakutenKoboAffiliateLink:
    product_url: str
    affiliate_url: str


class RakutenKoboAffiliateLinkService:
    """
    Build the documented Rakuten affiliate link locally.

    No network request is performed.

    Manual input can still bypass this generator by supplying
    an affiliate URL directly to the caller.
    """

    _AFFILIATE_ID_PATTERN = re.compile(
        r"^[A-Za-z0-9._-]{3,255}$"
    )

    def generate(
        self,
        *,
        product_url: str,
        affiliate_id: str,
    ) -> RakutenKoboAffiliateLink:
        try:
            normalized_product = (
                normalize_store_url(
                    product_url,
                    store_name="rakuten_kobo",
                    purpose="product",
                    required=True,
                )
            )
        except StoreUrlPolicyError as exc:
            raise RakutenKoboAffiliateLinkError(
                str(exc)
            ) from exc

        assert normalized_product is not None

        normalized_id = str(
            affiliate_id or ""
        ).strip()

        if not normalized_id:
            raise RakutenKoboAffiliateLinkError(
                "RAKUTEN_AFFILIATE_ID_REQUIRED"
            )

        if not self._AFFILIATE_ID_PATTERN.fullmatch(
            normalized_id
        ):
            raise RakutenKoboAffiliateLinkError(
                "RAKUTEN_AFFILIATE_ID_INVALID"
            )

        query = urlencode(
            {
                "pc": normalized_product,
                "m": normalized_product,
            }
        )

        generated = (
            "https://hb.afl.rakuten.co.jp/"
            f"hgc/{normalized_id}/?"
            f"{query}"
        )

        try:
            normalized_affiliate = (
                normalize_store_url(
                    generated,
                    store_name="rakuten_kobo",
                    purpose="affiliate",
                    required=True,
                )
            )
        except StoreUrlPolicyError as exc:
            raise RakutenKoboAffiliateLinkError(
                str(exc)
            ) from exc

        assert normalized_affiliate is not None

        parsed = urlsplit(
            normalized_affiliate
        )

        if (
            parsed.hostname
            != "hb.afl.rakuten.co.jp"
            or not parsed.path.startswith(
                "/hgc/"
            )
        ):
            raise RakutenKoboAffiliateLinkError(
                "RAKUTEN_AFFILIATE_URL_INVALID"
            )

        return RakutenKoboAffiliateLink(
            product_url=normalized_product,
            affiliate_url=normalized_affiliate,
        )
