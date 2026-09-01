from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from app.services.store_url_policy import StoreUrlPolicyError, normalize_store_url


class DmmSearchDiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class DmmSearchCandidate:
    product_url: str
    product_title: str
    score: float


class _DmmProductLinkParser(
    HTMLParser
):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )
        self._current_href: str | None = None
        self._current_parts: list[str] = []
        self.results: list[
            tuple[str, str]
        ] = []

    def handle_starttag(
        self,
        tag: str,
        attrs,
    ) -> None:
        attributes = dict(attrs)

        if tag == "a":
            href = str(
                attributes.get("href")
                or ""
            )

            if "/product/" in href:
                self._current_href = href
                self._current_parts = []

        elif (
            tag == "img"
            and self._current_href
        ):
            alt = str(
                attributes.get("alt")
                or ""
            ).strip()

            if alt:
                self._current_parts.append(
                    alt
                )

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._current_href:
            value = str(data or "").strip()

            if value:
                self._current_parts.append(
                    value
                )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag == "a"
            and self._current_href
        ):
            title = " ".join(
                self._current_parts
            ).strip()

            self.results.append(
                (
                    self._current_href,
                    title,
                )
            )

            self._current_href = None
            self._current_parts = []


def _normalize(
    value: str,
) -> str:
    return re.sub(
        r"[\W_]+",
        "",
        str(value or ""),
        flags=re.UNICODE,
    ).casefold()


def _compact_normalized(value: str) -> str:
    """Normalize DMM link text and collapse an exact duplicated title."""
    normalized = _normalize(value)
    midpoint = len(normalized) // 2
    if (
        normalized
        and len(normalized) % 2 == 0
        and normalized[:midpoint] == normalized[midpoint:]
    ):
        return normalized[:midpoint]
    return normalized


def _extract_volume_side(value: str | None) -> str | None:
    match = re.search(r"[（(]\s*([上下])\s*[）)]", str(value or ""))
    if match:
        return {"上": "upper", "下": "lower"}[match.group(1)]
    return None


def _extract_volume_number(
    item_title: str,
    volume_label: str | None,
) -> int | None:
    values = [
        str(volume_label or ""),
        str(item_title or ""),
    ]

    patterns = (
        r"第\s*(\d+)\s*巻",
        r"(\d+)\s*巻",
        r"[（(]\s*(\d+)\s*[）)]\s*$",
    )

    for value in values:
        for pattern in patterns:
            match = re.search(
                pattern,
                value,
            )

            if match:
                return int(match.group(1))

    return None


def _candidate_mentions_volume(
    product_title: str,
    volume_number: int | None,
    volume_side: str | None = None,
) -> bool:
    if volume_number is not None:
        escaped = re.escape(str(volume_number))
        patterns = (
            rf"第\s*{escaped}\s*巻",
            rf"(?<!\d){escaped}\s*巻",
            rf"[（(]\s*{escaped}\s*[）)]",
        )
        if any(re.search(pattern, product_title) for pattern in patterns):
            return True
    expected_side = {"upper": "上", "lower": "下"}.get(volume_side or "")
    return bool(
        expected_side
        and re.search(rf"[（(]\s*{expected_side}\s*[）)]", product_title)
    )



def _product_identity_from_url(
    product_url: str,
) -> tuple[str, str] | None:
    parsed = urlsplit(product_url)

    if parsed.hostname != "book.dmm.com":
        return None

    match = re.fullmatch(
        r"/product/([^/]+)/([^/]+)/?",
        parsed.path,
    )

    if not match:
        return None

    product_group_id = match.group(1).strip()
    content_id = match.group(2).strip()

    if (
        not product_group_id
        or not content_id
        or content_id == "latest"
    ):
        return None

    return (
        product_group_id,
        content_id,
    )


def _extract_detail_title(
    html: str,
) -> str:
    patterns = (
        (
            r'<meta[^>]+property=["\']og:title["\']'
            r'[^>]+content=["\']([^"\']+)'
        ),
        r"<h1[^>]*>(.*?)</h1>",
        r"<title[^>]*>(.*?)</title>",
    )

    for pattern in patterns:
        match = re.search(
            pattern,
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not match:
            continue

        value = re.sub(
            r"<[^>]+>",
            "",
            match.group(1),
        )

        value = unescape(
            value
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

        if value:
            return value

    return ""


def _extract_series_volume_candidates(
    *,
    html: str,
    product_group_id: str,
) -> tuple[DmmSearchCandidate, ...]:
    results: list[DmmSearchCandidate] = []
    seen: set[str] = set()

    # DMM currently embeds series entries in serialized page data:
    # \"contentId\":\"...\",\"title\":\"...\"
    #
    # Also accept unescaped JSON-like variants so the parser is not
    # tied to only one escaping representation.
    normalized = html

    # DMM embeds JSON-like data with escaped quotes.
    # Normalize at most two escape layers.
    escaped_quote = chr(92) + '"'
    for _ in range(2):
        if escaped_quote not in normalized:
            break
        normalized = normalized.replace(
            escaped_quote,
            '"',
        )

    pattern = re.compile(
        r'"contentId"\s*:\s*"([^"]+)"'
        r'.{0,800}?'
        r'"title"\s*:\s*"([^"]+)"',
        flags=re.DOTALL,
    )

    for match in pattern.finditer(
        normalized
    ):
        content_id = unescape(
            match.group(1)
        ).strip()

        title = unescape(
            match.group(2)
        ).strip()

        title = (
            title
            .replace(r"\/", "/")
            .replace(r"\u0026", "&")
        )

        if (
            not content_id
            or not title
            or content_id in seen
        ):
            continue

        seen.add(content_id)

        results.append(
            DmmSearchCandidate(
                product_url=(
                    "https://book.dmm.com/"
                    f"product/{product_group_id}/"
                    f"{content_id}/"
                ),
                product_title=title,
                score=0.0,
            )
        )

    return tuple(results)


def _candidate_score(
    *,
    product_title: str,
    item_title: str,
    volume_label: str | None,
) -> float:
    product = _compact_normalized(product_title)

    target_title = _normalize(
        item_title
    )

    target_with_volume = _normalize(
        f"{item_title} {volume_label or ''}"
    )

    if not product:
        return 0.0

    scores = [
        SequenceMatcher(
            None,
            product,
            target_title,
        ).ratio(),
        SequenceMatcher(
            None,
            product,
            target_with_volume,
        ).ratio(),
    ]

    if (
        target_title
        and (
            target_title in product
            or product in target_title
        )
    ):
        scores.append(0.90)

    if (
        target_with_volume
        and (
            target_with_volume in product
            or product in target_with_volume
        )
    ):
        scores.append(0.98)

    return max(scores)


class DmmSearchDiscoveryService:
    USER_AGENT = (
        "Mozilla/5.0 "
        "(compatible; AI-Media-OS/"
        "DMM-Discovery-Retry)"
    )

    @staticmethod
    def validate_search_url(
        value: str,
    ) -> str:
        url = str(value or "").strip()
        parsed = urlsplit(url)
        host = str(
            parsed.hostname or ""
        ).casefold()

        if (
            parsed.scheme != "https"
            or not (
                host == "dmm.com"
                or host.endswith(".dmm.com")
            )
        ):
            raise DmmSearchDiscoveryError(
                "invalid DMM search URL"
            )

        return url

    def _fetch_html(
        self,
        *,
        url: str,
        timeout_seconds: int,
    ) -> str:
        validated = self.validate_search_url(
            url
        )

        request = Request(
            validated,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": (
                    "text/html,"
                    "application/xhtml+xml"
                ),
            },
        )

        try:
            with urlopen(
                request,
                timeout=timeout_seconds,
            ) as response:
                status = int(
                    getattr(
                        response,
                        "status",
                        200,
                    )
                )

                if status != 200:
                    raise DmmSearchDiscoveryError(
                        "DMM HTTP "
                        f"status={status}"
                    )

                raw = response.read(
                    4 * 1024 * 1024
                )

        except Exception as exc:
            if isinstance(
                exc,
                DmmSearchDiscoveryError,
            ):
                raise

            raise DmmSearchDiscoveryError(
                f"DMM fetch failed: {exc}"
            ) from exc

        return raw.decode(
            "utf-8",
            errors="replace",
        )

    @staticmethod
    def parse_candidates(
        *,
        html: str,
        item_title: str,
        volume_label: str | None,
    ) -> tuple[DmmSearchCandidate, ...]:
        parser = _DmmProductLinkParser()
        parser.feed(html)

        target_title = _compact_normalized(
            item_title
        )

        target_with_volume = _compact_normalized(
            (
                f"{item_title} "
                f"{volume_label or ''}"
            )
        )

        candidates: list[
            DmmSearchCandidate
        ] = []

        target_volume = _extract_volume_number(
            item_title,
            volume_label,
        )
        target_volume_side = _extract_volume_side(item_title)
        has_target_volume = (
            target_volume is not None
            or target_volume_side is not None
        )

        seen: set[str] = set()

        for raw_href, raw_title in parser.results:
            joined_url = urljoin(
                "https://book.dmm.com/",
                raw_href,
            )

            try:
                product_url = normalize_store_url(
                    joined_url,
                    store_name="dmm",
                    purpose="product",
                    required=True,
                )
            except StoreUrlPolicyError:
                continue
            assert product_url is not None

            if product_url in seen:
                continue

            seen.add(product_url)

            product_title = str(
                raw_title or ""
            ).strip()

            normalized_product = _compact_normalized(product_title)

            if not normalized_product:
                continue

            scores = [
                SequenceMatcher(
                    None,
                    normalized_product,
                    target_title,
                ).ratio(),
                SequenceMatcher(
                    None,
                    normalized_product,
                    target_with_volume,
                ).ratio(),
            ]

            if (
                target_title
                and (
                    target_title
                    in normalized_product
                    or normalized_product
                    in target_title
                )
            ):
                scores.append(0.90)

            if (
                target_with_volume
                and (
                    target_with_volume
                    in normalized_product
                    or normalized_product
                    in target_with_volume
                )
            ):
                scores.append(0.98)

            score = max(scores)

            # Fail closed for numbered volumes.
            # A series-level title alone must not be
            # treated as discovery of a specific volume.
            if (
                has_target_volume
                and not _candidate_mentions_volume(
                    product_title,
                    target_volume,
                    target_volume_side,
                )
            ):
                score = min(
                    score,
                    0.61,
                )

            candidates.append(
                DmmSearchCandidate(
                    product_url=product_url,
                    product_title=product_title,
                    score=score,
                )
            )

        candidates.sort(
            key=lambda candidate: (
                candidate.score,
                candidate.product_url,
            ),
            reverse=True,
        )

        return tuple(candidates)

    def fetch_and_match(
        self,
        *,
        search_url: str,
        item_title: str,
        volume_label: str | None,
        timeout_seconds: int = 15,
    ) -> DmmSearchCandidate | None:
        url = self.validate_search_url(
            search_url
        )

        search_html = self._fetch_html(
            url=url,
            timeout_seconds=timeout_seconds,
        )

        candidates = self.parse_candidates(
            html=search_html,
            item_title=item_title,
            volume_label=volume_label,
        )

        if not candidates:
            return None

        target_volume = _extract_volume_number(
            item_title,
            volume_label,
        )
        target_volume_side = _extract_volume_side(item_title)
        has_target_volume = (
            target_volume is not None
            or target_volume_side is not None
        )

        # Stage 1:
        # Search-result title already contains the requested volume.
        for candidate in candidates:
            if candidate.score < 0.62:
                continue

            if (
                has_target_volume
                and not _candidate_mentions_volume(
                    candidate.product_title,
                    target_volume,
                    target_volume_side,
                )
            ):
                continue

            return candidate

        # No explicit volume means there is no safe series-volume
        # expansion to perform.
        if not has_target_volume:
            return None

        # Stage 2:
        # DMM search results can point to another volume while that
        # product page embeds the complete series list. Inspect only
        # the strongest two series candidates to bound network use.
        series_candidates = [
            candidate
            for candidate in candidates
            if candidate.score >= 0.55
            and _product_identity_from_url(
                candidate.product_url
            )
            is not None
        ][:2]

        for series_candidate in series_candidates:
            identity = _product_identity_from_url(
                series_candidate.product_url
            )

            if identity is None:
                continue

            product_group_id, _ = identity

            detail_html = self._fetch_html(
                url=series_candidate.product_url,
                timeout_seconds=timeout_seconds,
            )

            embedded = (
                _extract_series_volume_candidates(
                    html=detail_html,
                    product_group_id=product_group_id,
                )
            )

            ranked: list[DmmSearchCandidate] = []

            for embedded_candidate in embedded:
                if not _candidate_mentions_volume(
                    embedded_candidate.product_title,
                    target_volume,
                    target_volume_side,
                ):
                    continue

                score = _candidate_score(
                    product_title=(
                        embedded_candidate.product_title
                    ),
                    item_title=item_title,
                    volume_label=volume_label,
                )

                if score < 0.62:
                    continue

                ranked.append(
                    DmmSearchCandidate(
                        product_url=(
                            embedded_candidate.product_url
                        ),
                        product_title=(
                            embedded_candidate.product_title
                        ),
                        score=score,
                    )
                )

            ranked.sort(
                key=lambda candidate: (
                    candidate.score,
                    candidate.product_url,
                ),
                reverse=True,
            )

            for embedded_candidate in ranked[:2]:
                # Final fail-closed verification:
                # fetch the concrete content-ID URL and require its
                # actual detail title to contain the requested volume.
                exact_html = self._fetch_html(
                    url=embedded_candidate.product_url,
                    timeout_seconds=timeout_seconds,
                )

                exact_title = _extract_detail_title(
                    exact_html
                )

                if not exact_title:
                    continue

                if not _candidate_mentions_volume(
                    exact_title,
                    target_volume,
                    target_volume_side,
                ):
                    continue

                score = _candidate_score(
                    product_title=exact_title,
                    item_title=item_title,
                    volume_label=volume_label,
                )

                if score < 0.62:
                    continue

                return DmmSearchCandidate(
                    product_url=(
                        embedded_candidate.product_url
                    ),
                    product_title=exact_title,
                    score=score,
                )

        return None
