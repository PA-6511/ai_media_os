"""Fail-closed affiliate-link contract for XNR WordPress publication.

Pure validation only:
- no DB
- no network
- no WordPress
- no runtime writes

The safe-published source is authoritative for which store links
must appear in the generated WordPress HTML.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Mapping
from urllib.parse import urlparse


STORE_KEYS = (
    "kindle",
    "rakuten",
    "dmm",
)

STORE_CLASSES = {
    "kindle": "ai-nr-roundup__btn--kindle",
    "rakuten": "ai-nr-roundup__btn--rakuten",
    "dmm": "ai-nr-roundup__btn--dmm",
}


class XnrRoundupPublicationContractError(
    ValueError
):
    def __init__(
        self,
        code: str,
        *,
        detail: str = "",
    ) -> None:
        self.code = code
        self.detail = detail
        super().__init__(
            code
            if not detail
            else f"{code}: {detail}"
        )


@dataclass(frozen=True)
class XnrRoundupPublicationContractResult:
    target_date: str
    item_count: int
    expected_by_store: Mapping[str, int]
    rendered_by_store: Mapping[str, int]

    @property
    def expected_total(self) -> int:
        return sum(
            self.expected_by_store.values()
        )

    @property
    def rendered_total(self) -> int:
        return sum(
            self.rendered_by_store.values()
        )


def _https_url(
    value: Any,
) -> str:
    url = str(
        value or ""
    ).strip()

    parsed = urlparse(
        url
    )

    if (
        parsed.scheme != "https"
        or not parsed.netloc
    ):
        return ""

    return url


class _AffiliateAnchorParser(
    HTMLParser
):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.urls: dict[
            str,
            list[str],
        ] = {
            key: []
            for key in STORE_KEYS
        }

        self.invalid: list[
            tuple[str, str]
        ] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        if tag.lower() != "a":
            return

        values = {
            str(key).lower(): (
                ""
                if value is None
                else str(value)
            )
            for key, value in attrs
        }

        classes = set(
            values.get(
                "class",
                "",
            ).split()
        )

        matched = [
            key
            for key, css_class
            in STORE_CLASSES.items()
            if css_class in classes
        ]

        if not matched:
            return

        if len(matched) != 1:
            self.invalid.append(
                (
                    "AMBIGUOUS_STORE_CLASS",
                    values.get(
                        "class",
                        "",
                    ),
                )
            )
            return

        store_key = matched[0]

        href = _https_url(
            values.get(
                "href",
                "",
            )
        )

        if not href:
            self.invalid.append(
                (
                    store_key,
                    values.get(
                        "href",
                        "",
                    ),
                )
            )
            return

        self.urls[
            store_key
        ].append(
            href
        )


def validate_xnr_roundup_publication_contract(
    *,
    source_payload: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> XnrRoundupPublicationContractResult:
    """Require exact safe-published affiliate URLs in generated WP HTML."""

    target_date = str(
        plan.get(
            "target_date"
        )
        or ""
    ).strip()

    if not target_date:
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_TARGET_DATE_MISSING"
        )

    releases = source_payload.get(
        "new_releases"
    )

    if not isinstance(
        releases,
        list,
    ):
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_SOURCE_MALFORMED",
            detail=(
                "new_releases must be a list"
            ),
        )

    items = [
        item
        for item in releases
        if (
            isinstance(
                item,
                Mapping,
            )
            and str(
                item.get(
                    "release_date"
                )
                or ""
            ).strip()
            == target_date
        )
    ]

    if not items:
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_NO_TARGET_ITEMS"
        )

    try:
        wordpress_item_count = int(
            plan.get(
                "wordpress_item_count"
            )
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_ITEM_COUNT_INVALID"
        ) from exc

    if (
        wordpress_item_count
        != len(items)
    ):
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_ITEM_COUNT_MISMATCH",
            detail=(
                f"source={len(items)} "
                f"plan={wordpress_item_count}"
            ),
        )

    expected: dict[
        str,
        list[str],
    ] = {
        key: []
        for key in STORE_KEYS
    }

    for item in items:
        item_id = str(
            item.get(
                "item_id"
            )
            or "UNKNOWN"
        )

        stores = item.get(
            "stores"
        )

        if not isinstance(
            stores,
            Mapping,
        ):
            raise XnrRoundupPublicationContractError(
                "XNR_PUBLICATION_STORES_MALFORMED",
                detail=item_id,
            )

        item_expected = 0

        for store_key in STORE_KEYS:
            store = stores.get(
                store_key
            )

            if not isinstance(
                store,
                Mapping,
            ):
                continue

            status = str(
                store.get(
                    "status"
                )
                or ""
            ).strip().upper()

            if status != "FOUND":
                continue

            url = _https_url(
                store.get(
                    "url"
                )
            )

            if not url:
                raise XnrRoundupPublicationContractError(
                    "XNR_PUBLICATION_FOUND_STORE_URL_INVALID",
                    detail=(
                        f"item={item_id} "
                        f"store={store_key}"
                    ),
                )

            expected[
                store_key
            ].append(
                url
            )

            item_expected += 1

        if item_expected == 0:
            raise XnrRoundupPublicationContractError(
                "XNR_PUBLICATION_ITEM_WITHOUT_AFFILIATE_LINK",
                detail=item_id,
            )

    expected_total = sum(
        len(urls)
        for urls in expected.values()
    )

    if expected_total == 0:
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_NO_AFFILIATE_LINKS_EXPECTED"
        )

    wordpress_html = str(
        plan.get(
            "wordpress_html"
        )
        or ""
    )

    if not wordpress_html:
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_HTML_MISSING"
        )

    parser = _AffiliateAnchorParser()

    try:
        parser.feed(
            wordpress_html
        )
        parser.close()
    except Exception as exc:
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_HTML_PARSE_FAILED"
        ) from exc

    if parser.invalid:
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_AFFILIATE_ANCHOR_INVALID",
            detail=repr(
                parser.invalid[:3]
            ),
        )

    expected_counts = {
        key: len(
            expected[key]
        )
        for key in STORE_KEYS
    }

    rendered_counts = {
        key: len(
            parser.urls[key]
        )
        for key in STORE_KEYS
    }

    for store_key in STORE_KEYS:
        expected_counter = Counter(
            expected[
                store_key
            ]
        )

        rendered_counter = Counter(
            parser.urls[
                store_key
            ]
        )

        if (
            expected_counter
            != rendered_counter
        ):
            raise XnrRoundupPublicationContractError(
                "XNR_PUBLICATION_AFFILIATE_LINK_MISMATCH",
                detail=(
                    f"store={store_key} "
                    f"expected={sum(expected_counter.values())} "
                    f"rendered={sum(rendered_counter.values())}"
                ),
            )

    if (
        sum(
            rendered_counts.values()
        )
        != expected_total
    ):
        raise XnrRoundupPublicationContractError(
            "XNR_PUBLICATION_AFFILIATE_TOTAL_MISMATCH",
            detail=(
                f"expected={expected_total} "
                f"rendered={sum(rendered_counts.values())}"
            ),
        )

    return (
        XnrRoundupPublicationContractResult(
            target_date=target_date,
            item_count=len(items),
            expected_by_store=expected_counts,
            rendered_by_store=rendered_counts,
        )
    )
