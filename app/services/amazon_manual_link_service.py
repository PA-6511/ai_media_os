from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
TRACKING_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9._]+(?:-[A-Za-z0-9._]+)*-[0-9]{2}$"
)


@dataclass(frozen=True)
class AmazonManualLink:
    asin: str
    product_url: str
    affiliate_url: str


class AmazonManualLinkError(ValueError):
    """Amazon暫定リンク生成時の入力エラー。"""


class AmazonManualLinkService:
    """ASINからAmazon商品URLとアフィリエイトURLを生成する最小Service。"""

    AMAZON_HOST = "www.amazon.co.jp"

    def generate(
        self,
        *,
        asin: str,
        tracking_id: str,
    ) -> AmazonManualLink:
        normalized_asin, supplied_url = self._normalize_asin_or_url(asin)
        normalized_tracking_id = self._normalize_tracking_id(tracking_id)

        product_url = supplied_url or f"https://{self.AMAZON_HOST}/dp/{normalized_asin}"

        affiliate_base_url = (
            product_url
            if supplied_url is not None
            else f"{product_url}/ref=nosim"
        )
        parsed = urlsplit(affiliate_base_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["tag"] = normalized_tracking_id
        affiliate_url = urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), "")
        )

        return AmazonManualLink(
            asin=normalized_asin,
            product_url=product_url,
            affiliate_url=affiliate_url,
        )

    def _normalize_asin_or_url(self, asin: str) -> tuple[str, str | None]:
        raw = asin.strip()
        supplied_url: str | None = None
        normalized = raw.upper()

        if raw.startswith("https://"):
            parsed = urlsplit(raw)
            if parsed.hostname not in {
                "amazon.co.jp",
                "www.amazon.co.jp",
            }:
                raise AmazonManualLinkError(
                    "Amazon product URL must use amazon.co.jp."
                )
            match = re.search(
                r"/(?:dp|gp/product)/([A-Za-z0-9]{10})(?:[/?]|$)",
                parsed.path + ("?" if parsed.query else ""),
            )
            if not match:
                raise AmazonManualLinkError(
                    "Amazon product URL does not contain an ASIN."
                )
            normalized = match.group(1).upper()
            supplied_url = urlunsplit(
                ("https", parsed.netloc, parsed.path, parsed.query, "")
            )

        if not normalized:
            raise AmazonManualLinkError("ASIN is required.")

        if not ASIN_PATTERN.fullmatch(normalized):
            raise AmazonManualLinkError(
                "ASIN must be exactly 10 alphanumeric characters."
            )

        return normalized, supplied_url

    def _normalize_tracking_id(self, tracking_id: str) -> str:
        normalized = tracking_id.strip()

        if not normalized:
            raise AmazonManualLinkError("Tracking ID is required.")

        if not TRACKING_ID_PATTERN.fullmatch(normalized):
            raise AmazonManualLinkError(
                "Tracking ID contains unsupported characters."
            )

        return normalized
