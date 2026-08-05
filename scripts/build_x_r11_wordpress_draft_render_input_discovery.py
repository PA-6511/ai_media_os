from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-DRAFT-RENDER-INPUT-DISCOVERY"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_DESIGN_DIGEST = (
    "62f72e88d48e4b9b09ee19bbf6298b39"
    "38ef83595b6951dba40f905e201caf90"
)

EXPECTED_INPUT_DIGEST = (
    "f08301106c3475168d31f53c13ffa3e8"
    "83e0bdb7889de06196e9a21b48256337"
)

EXPECTED_IDENTITY_DIGEST = (
    "9ca9f6c09301a2631db9872e9f89484a"
    "026d01e021b0632160e009d03c632aeb"
)

EXPECTED_CONTRACT_ID = (
    "X_R11_LOCAL_WORDPRESS_DRAFT_TEMPLATE_V1"
)

EXPECTED_PRODUCT_URL = (
    "https://books.rakuten.co.jp/rk/"
    "6ffa7a8daf403477a5936eb1279e0478/"
)

EXPECTED_TITLE = "のあ先輩はともだち。"
EXPECTED_VOLUME_LABEL = "第11巻"
EXPECTED_VOLUME_NUMBER = "11"
EXPECTED_AUTHOR = "あきやまえんま"

EXPECTED_PRODUCT_NUMBER = "4972000159536"

EXPECTED_KOBO_ID = (
    "6ffa7a8daf403477a5936eb1279e0478"
)

ALLOWED_IMAGE_HOSTS = {
    "tshop.r10s.jp",
    "shop.r10s.jp",
    "thumbnail.image.rakuten.co.jp",
    "books.rakuten.co.jp",
}

BAD_IMAGE_PATH_TOKENS = (
    "logo",
    "icon",
    "banner",
    "sprite",
    "header",
    "footer",
    "rating",
    "rank",
    "point",
    "campaign",
    "appstore",
    "googleplay",
)

MIN_IMAGE_WIDTH = 240
MIN_IMAGE_HEIGHT = 300
MAX_IMAGE_BYTES = 3_000_000
MAX_PAGE_BYTES = 6_000_000

# Bound remote cover-image discovery.
IMAGE_FETCH_TIMEOUT_SECONDS = 8
MAX_IMAGE_FETCH_ATTEMPTS = 4
class RenderInputDiscoveryError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RenderInputDiscoveryError(
            message
        )


def normalize_text(
    value: str,
) -> str:
    value = unicodedata.normalize(
        "NFKC",
        value,
    ).casefold()

    return re.sub(
        r"[\s\u3000]+",
        "",
        value,
    )


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise RenderInputDiscoveryError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def verify_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    expected_digest: str,
    label: str,
) -> None:
    recorded = value.get(
        digest_field
    )

    require(
        recorded == expected_digest,
        f"{label} digest mismatch",
    )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == expected_digest,
        f"{label} digest verification failed",
    )


class ProductPageParser(
    HTMLParser
):
    def __init__(self) -> None:
        super().__init__(
            convert_charrefs=True
        )

        self.image_candidates: list[
            dict[str, Any]
        ] = []

        self.json_ld_blocks: list[str] = []

        self._inside_json_ld = False
        self._json_ld_buffer: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[str, str | None]
        ],
    ) -> None:
        attributes = {
            key.casefold(): (
                value or ""
            )
            for key, value in attrs
        }

        lowered_tag = tag.casefold()

        if lowered_tag == "meta":
            property_name = (
                attributes.get("property")
                or attributes.get("name")
                or ""
            ).casefold()

            content = attributes.get(
                "content",
                "",
            ).strip()

            if (
                property_name
                in {
                    "og:image",
                    "og:image:url",
                    "twitter:image",
                    "twitter:image:src",
                }
                and content
            ):
                self.image_candidates.append(
                    {
                        "url": content,
                        "alt": "",
                        "source": (
                            "meta:"
                            + property_name
                        ),
                    }
                )

        if lowered_tag == "img":
            alt = attributes.get(
                "alt",
                "",
            ).strip()

            for field in (
                "src",
                "data-src",
                "data-original",
                "data-lazy-src",
            ):
                candidate_url = (
                    attributes.get(
                        field,
                        "",
                    ).strip()
                )

                if candidate_url:
                    self.image_candidates.append(
                        {
                            "url": candidate_url,
                            "alt": alt,
                            "source": (
                                "img:" + field
                            ),
                        }
                    )

            srcset = attributes.get(
                "srcset",
                "",
            ).strip()

            if srcset:
                for entry in srcset.split(","):
                    candidate_url = (
                        entry.strip().split()[0]
                    )

                    if candidate_url:
                        self.image_candidates.append(
                            {
                                "url": (
                                    candidate_url
                                ),
                                "alt": alt,
                                "source": (
                                    "img:srcset"
                                ),
                            }
                        )

        if lowered_tag == "script":
            script_type = (
                attributes.get(
                    "type",
                    "",
                ).casefold()
            )

            if (
                script_type
                == "application/ld+json"
            ):
                self._inside_json_ld = True
                self._json_ld_buffer = []

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._inside_json_ld:
            self._json_ld_buffer.append(
                data
            )

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        if (
            tag.casefold() == "script"
            and self._inside_json_ld
        ):
            self.json_ld_blocks.append(
                "".join(
                    self._json_ld_buffer
                )
            )

            self._inside_json_ld = False
            self._json_ld_buffer = []


def walk_json_images(
    value: Any,
) -> list[str]:
    results: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() == "image":
                if isinstance(item, str):
                    results.append(item)

                elif isinstance(item, list):
                    results.extend(
                        entry
                        for entry in item
                        if isinstance(entry, str)
                    )

                elif isinstance(item, dict):
                    for candidate_key in (
                        "url",
                        "contentUrl",
                    ):
                        candidate = item.get(
                            candidate_key
                        )

                        if isinstance(
                            candidate,
                            str,
                        ):
                            results.append(
                                candidate
                            )

            results.extend(
                walk_json_images(item)
            )

    elif isinstance(value, list):
        for item in value:
            results.extend(
                walk_json_images(item)
            )

    return results


def extract_image_candidates(
    page_html: str,
    *,
    base_url: str,
) -> list[dict[str, Any]]:
    parser = ProductPageParser()
    parser.feed(page_html)

    candidates = list(
        parser.image_candidates
    )

    for block in parser.json_ld_blocks:
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue

        for candidate_url in walk_json_images(
            value
        ):
            candidates.append(
                {
                    "url": candidate_url,
                    "alt": "",
                    "source": "json-ld:image",
                }
            )

    deduplicated: dict[
        str,
        dict[str, Any],
    ] = {}

    for candidate in candidates:
        raw_url = str(
            candidate.get(
                "url",
                "",
            )
        ).strip()

        if (
            not raw_url
            or raw_url.startswith("data:")
        ):
            continue

        absolute_url = urljoin(
            base_url,
            raw_url,
        )

        parsed = urlparse(
            absolute_url
        )

        if parsed.scheme != "https":
            continue

        existing = deduplicated.get(
            absolute_url
        )

        if existing is None:
            deduplicated[
                absolute_url
            ] = {
                "url": absolute_url,
                "alt": str(
                    candidate.get(
                        "alt",
                        "",
                    )
                ),
                "sources": [
                    str(
                        candidate.get(
                            "source",
                            "",
                        )
                    )
                ],
            }

        else:
            source = str(
                candidate.get(
                    "source",
                    "",
                )
            )

            if (
                source
                and source
                not in existing["sources"]
            ):
                existing["sources"].append(
                    source
                )

            if (
                not existing["alt"]
                and candidate.get("alt")
            ):
                existing["alt"] = str(
                    candidate["alt"]
                )

    return list(
        deduplicated.values()
    )


def score_candidate(
    candidate: dict[str, Any],
    *,
    expected_title: str,
    expected_volume_number: str,
) -> dict[str, Any]:
    result = dict(candidate)

    candidate_url = str(
        candidate["url"]
    )

    parsed = urlparse(
        candidate_url
    )

    host = (
        parsed.hostname or ""
    ).casefold()

    path = parsed.path.casefold()

    normalized_alt = normalize_text(
        str(
            candidate.get(
                "alt",
                "",
            )
        )
    )

    normalized_title = normalize_text(
        expected_title
    )

    title_match = (
        normalized_title
        in normalized_alt
    )

    volume_match = (
        expected_volume_number
        in normalized_alt
    )

    official_image_host = (
        host in ALLOWED_IMAGE_HOSTS
    )

    product_cabinet_path = (
        "rakutenkobo-ebooks/cabinet/"
        in path
    )

    bad_path_token_found = any(
        token in path
        for token in BAD_IMAGE_PATH_TOKENS
    )

    score = 0

    if official_image_host:
        score += 100

    if product_cabinet_path:
        score += 250

    if title_match:
        score += 300

    if volume_match:
        score += 100

    if title_match and volume_match:
        score += 200

    if path.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )
    ):
        score += 20

    for source in candidate.get(
        "sources",
        [],
    ):
        if source.startswith(
            "meta:og:image"
        ):
            score += 80

        if source == "json-ld:image":
            score += 60

    if bad_path_token_found:
        score -= 600

    result.update(
        {
            "hostname": host,
            "title_match": title_match,
            "volume_match": volume_match,
            "official_image_host": (
                official_image_host
            ),
            "product_cabinet_path": (
                product_cabinet_path
            ),
            "bad_path_token_found": (
                bad_path_token_found
            ),
            "strong_identity_signal": (
                title_match
                and volume_match
            ),
            "candidate_score": score,
        }
    )

    return result


def select_image_fetch_candidates(
    scored_candidates: list[
        dict[str, Any]
    ],
) -> list[dict[str, Any]]:
    eligible = [
        candidate
        for candidate in scored_candidates
        if (
            candidate.get(
                "official_image_host"
            )
            is True
            and candidate.get(
                "bad_path_token_found"
            )
            is False
            and int(
                candidate.get(
                    "candidate_score",
                    0,
                )
            )
            >= 100
        )
    ]

    eligible.sort(
        key=lambda candidate: (
            not bool(
                candidate.get(
                    "strong_identity_signal"
                )
            ),
            -int(
                candidate.get(
                    "candidate_score",
                    0,
                )
            ),
            str(
                candidate.get(
                    "url",
                    "",
                )
            ),
        )
    )

    return eligible[
        :MAX_IMAGE_FETCH_ATTEMPTS
    ]


def parse_jpeg_dimensions(
    data: bytes,
) -> tuple[int, int] | None:
    if not data.startswith(
        b"\xff\xd8"
    ):
        return None

    index = 2

    start_of_frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }

    while index + 8 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue

        while (
            index < len(data)
            and data[index] == 0xFF
        ):
            index += 1

        if index >= len(data):
            break

        marker = data[index]
        index += 1

        if marker in {
            0xD8,
            0xD9,
        }:
            continue

        if marker == 0xDA:
            break

        if index + 2 > len(data):
            break

        segment_length = int.from_bytes(
            data[index:index + 2],
            "big",
        )

        if (
            segment_length < 2
            or index
            + segment_length
            > len(data)
        ):
            break

        if (
            marker
            in start_of_frame_markers
            and segment_length >= 7
        ):
            height = int.from_bytes(
                data[
                    index + 3:
                    index + 5
                ],
                "big",
            )

            width = int.from_bytes(
                data[
                    index + 5:
                    index + 7
                ],
                "big",
            )

            return width, height

        index += segment_length

    return None


def inspect_image_bytes(
    data: bytes,
    *,
    content_type: str,
) -> dict[str, Any]:
    lowered_content_type = (
        content_type
        .split(";", 1)[0]
        .strip()
        .casefold()
    )

    if data.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):
        require(
            len(data) >= 24,
            "PNG image header is incomplete",
        )

        width = int.from_bytes(
            data[16:20],
            "big",
        )

        height = int.from_bytes(
            data[20:24],
            "big",
        )

        image_format = "png"

    elif data.startswith(
        b"\xff\xd8"
    ):
        dimensions = parse_jpeg_dimensions(
            data
        )

        require(
            dimensions is not None,
            (
                "JPEG dimensions "
                "could not be parsed"
            ),
        )

        width, height = dimensions
        image_format = "jpeg"

    else:
        raise RenderInputDiscoveryError(
            (
                "unsupported image format; "
                f"content_type={lowered_content_type!r}"
            )
        )

    return {
        "format": image_format,
        "content_type": (
            lowered_content_type
        ),
        "byte_size": len(data),
        "width": width,
        "height": height,
        "sha256": sha256_bytes(data),
    }


def validate_image_metadata(
    metadata: dict[str, Any],
) -> None:
    width = int(
        metadata["width"]
    )

    height = int(
        metadata["height"]
    )

    require(
        width >= MIN_IMAGE_WIDTH,
        (
            "cover image width is too small: "
            f"{width}"
        ),
    )

    require(
        height >= MIN_IMAGE_HEIGHT,
        (
            "cover image height is too small: "
            f"{height}"
        ),
    )

    require(
        height > width,
        (
            "cover image must use "
            "portrait orientation"
        ),
    )

    aspect_ratio = (
        width / height
    )

    require(
        0.5 <= aspect_ratio <= 0.95,
        (
            "cover image aspect ratio "
            f"is invalid: {aspect_ratio}"
        ),
    )


def fetch_page(
    url: str,
) -> tuple[str, str, int]:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "Chrome/126 Safari/537.36"
            ),
            "Accept": (
                "text/html,"
                "application/xhtml+xml"
            ),
            "Accept-Language": (
                "ja,en-US;q=0.7,en;q=0.5"
            ),
        },
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=30,
        ) as response:
            data = response.read(
                MAX_PAGE_BYTES + 1
            )

            require(
                len(data) <= MAX_PAGE_BYTES,
                "product page is too large",
            )

            charset = (
                response.headers
                .get_content_charset()
                or "utf-8"
            )

            try:
                page_html = data.decode(
                    charset,
                    errors="strict",
                )
            except (
                LookupError,
                UnicodeDecodeError,
            ):
                page_html = data.decode(
                    "utf-8",
                    errors="replace",
                )

            return (
                page_html,
                str(response.geturl()),
                int(response.status),
            )

    except HTTPError as exc:
        raise RenderInputDiscoveryError(
            (
                "product-page GET failed: "
                f"HTTP {exc.code}"
            )
        ) from exc

    except URLError as exc:
        raise RenderInputDiscoveryError(
            (
                "product-page GET failed: "
                f"{exc.reason}"
            )
        ) from exc


def fetch_image(
    url: str,
) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "Chrome/126 Safari/537.36"
            ),
            "Accept": (
                "image/avif,image/webp,"
                "image/png,image/jpeg,"
                "image/*;q=0.8"
            ),
            "Referer": EXPECTED_PRODUCT_URL,
        },
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=IMAGE_FETCH_TIMEOUT_SECONDS,
        ) as response:
            data = response.read(
                MAX_IMAGE_BYTES + 1
            )

            require(
                len(data)
                <= MAX_IMAGE_BYTES,
                "cover image is too large",
            )

            metadata = inspect_image_bytes(
                data,
                content_type=(
                    response.headers.get(
                        "Content-Type",
                        "",
                    )
                ),
            )

            final_url = str(
                response.geturl()
            )

            final_host = (
                urlparse(
                    final_url
                ).hostname
                or ""
            ).casefold()

            require(
                final_host
                in ALLOWED_IMAGE_HOSTS,
                (
                    "cover image redirected "
                    "to a disallowed host: "
                    f"{final_host}"
                ),
            )

            validate_image_metadata(
                metadata
            )

            return {
                "requested_url": url,
                "final_url": final_url,
                "final_hostname": final_host,
                "http_status": int(
                    response.status
                ),
                **metadata,
            }

    except HTTPError as exc:
        raise RenderInputDiscoveryError(
            (
                "cover-image GET failed: "
                f"HTTP {exc.code}"
            )
        ) from exc

    except URLError as exc:
        raise RenderInputDiscoveryError(
            (
                "cover-image GET failed: "
                f"{exc.reason}"
            )
        ) from exc


def build_render_input_discovery_pack(
    *,
    production_database_path: Path,
    design_pack_path: Path,
    input_pack_path: Path,
    identity_pack_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )
    design_pack_path = (
        design_pack_path.resolve()
    )
    input_pack_path = (
        input_pack_path.resolve()
    )
    identity_pack_path = (
        identity_pack_path.resolve()
    )
    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    design_pack = load_json(
        design_pack_path
    )

    input_pack = load_json(
        input_pack_path
    )

    identity_pack = load_json(
        identity_pack_path
    )

    verify_digest(
        design_pack,
        digest_field=(
            "local_wordpress_draft_template_"
            "contract_design_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_DESIGN_DIGEST
        ),
        label="local template design pack",
    )

    verify_digest(
        input_pack,
        digest_field=(
            "wordpress_draft_input_fixing_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_INPUT_DIGEST
        ),
        label="WordPress input pack",
    )

    verify_digest(
        identity_pack,
        digest_field=(
            "affiliate_product_identity_"
            "verification_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_IDENTITY_DIGEST
        ),
        label="affiliate identity pack",
    )

    require(
        design_pack.get("status")
        == (
            "PASS_LOCAL_WORDPRESS_DRAFT_"
            "TEMPLATE_CONTRACT_FIXED"
        ),
        "local template design did not pass",
    )

    require(
        design_pack.get(
            "unresolved_render_inputs"
        )
        == ["cover_image_url"],
        (
            "unexpected unresolved "
            "render inputs"
        ),
    )

    require(
        design_pack[
            "local_template_contract"
        ]["contract_id"]
        == EXPECTED_CONTRACT_ID,
        "local template contract mismatch",
    )

    require(
        design_pack[
            "local_template_contract"
        ]["wordpress_category_id"]
        == 43,
        "WordPress category ID mismatch",
    )

    require(
        input_pack.get("status")
        == "PASS_WORDPRESS_DRAFT_INPUTS_FIXED",
        "WordPress input fixing did not pass",
    )

    require(
        input_pack.get("title")
        == EXPECTED_TITLE,
        "input title mismatch",
    )

    require(
        input_pack.get("volume_label")
        == EXPECTED_VOLUME_LABEL,
        "input volume mismatch",
    )

    require(
        input_pack.get("author_name")
        == EXPECTED_AUTHOR,
        "input author mismatch",
    )

    require(
        input_pack.get("product_url")
        == EXPECTED_PRODUCT_URL,
        "input product URL mismatch",
    )

    require(
        identity_pack.get("status")
        == (
            "PASS_AFFILIATE_PRODUCT_"
            "IDENTITY_VERIFIED"
        ),
        (
            "affiliate identity verification "
            "did not pass"
        ),
    )

    require(
        identity_pack.get(
            "affiliate_product_identity_verified"
        )
        is True,
        "affiliate product identity is not verified",
    )

    require(
        identity_pack.get(
            "expected_product_number"
        )
        == EXPECTED_PRODUCT_NUMBER,
        "product-number evidence mismatch",
    )

    require(
        identity_pack.get(
            "expected_kobo_id"
        )
        == EXPECTED_KOBO_ID,
        "Kobo-ID evidence mismatch",
    )

    page_html, final_page_url, page_status = (
        fetch_page(
            EXPECTED_PRODUCT_URL
        )
    )

    require(
        page_status == 200,
        "product page did not return 200",
    )

    normalized_page = normalize_text(
        page_html
    )

    require(
        normalize_text(
            EXPECTED_TITLE
            + EXPECTED_VOLUME_NUMBER
        )
        in normalized_page,
        (
            "product-page title and volume "
            "could not be verified"
        ),
    )

    require(
        normalize_text(
            EXPECTED_AUTHOR
        )
        in normalized_page,
        (
            "product-page author "
            "could not be verified"
        ),
    )

    require(
        EXPECTED_PRODUCT_NUMBER
        in page_html,
        (
            "product-page product number "
            "could not be verified"
        ),
    )

    extracted_candidates = (
        extract_image_candidates(
            page_html,
            base_url=final_page_url,
        )
    )

    scored_candidates = [
        score_candidate(
            candidate,
            expected_title=EXPECTED_TITLE,
            expected_volume_number=(
                EXPECTED_VOLUME_NUMBER
            ),
        )
        for candidate
        in extracted_candidates
    ]

    scored_candidates.sort(
        key=lambda item: (
            -int(
                item["candidate_score"]
            ),
            str(item["url"]),
        )
    )

    verified_candidates: list[
        dict[str, Any]
    ] = []

    candidate_errors: list[
        dict[str, str]
    ] = []

    fetch_candidates = (
        select_image_fetch_candidates(
            scored_candidates
        )
    )

    print(
        json.dumps(
            {
                "event": "cover_image_discovery_plan",
                "eligible_candidate_count": (
                    len(fetch_candidates)
                ),
                "maximum_attempts": (
                    MAX_IMAGE_FETCH_ATTEMPTS
                ),
                "timeout_seconds_per_attempt": (
                    IMAGE_FETCH_TIMEOUT_SECONDS
                ),
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
        flush=True,
    )

    for attempt_number, candidate in enumerate(
        fetch_candidates,
        start=1,
    ):
        print(
            json.dumps(
                {
                    "event": "cover_image_candidate_fetch_start",
                    "attempt": attempt_number,
                    "maximum_attempts": (
                        MAX_IMAGE_FETCH_ATTEMPTS
                    ),
                    "timeout_seconds": (
                        IMAGE_FETCH_TIMEOUT_SECONDS
                    ),
                    "candidate_score": (
                        candidate[
                            "candidate_score"
                        ]
                    ),
                    "strong_identity_signal": (
                        candidate[
                            "strong_identity_signal"
                        ]
                    ),
                    "hostname": (
                        candidate["hostname"]
                    ),
                    "url": candidate["url"],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
            flush=True,
        )

        try:
            image_result = fetch_image(
                candidate["url"]
            )
        except Exception as exc:
            candidate_errors.append(
                {
                    "url": candidate["url"],
                    "error": str(exc),
                }
            )
            continue

        verified_candidates.append(
            {
                **candidate,
                "image_verification": (
                    image_result
                ),
            }
        )

    strong_candidates = [
        candidate
        for candidate
        in verified_candidates
        if candidate[
            "strong_identity_signal"
        ]
    ]

    require(
        strong_candidates,
        (
            "no verified cover image "
            "with title and volume identity "
            "was found"
        ),
    )

    strong_candidates.sort(
        key=lambda item: (
            -int(
                item[
                    "candidate_score"
                ]
            ),
            -int(
                item[
                    "image_verification"
                ]["width"]
                * item[
                    "image_verification"
                ]["height"]
            ),
            str(
                item[
                    "image_verification"
                ]["final_url"]
            ),
        )
    )

    selected = strong_candidates[0]

    selected_image = selected[
        "image_verification"
    ]

    cover_image_alt = (
        EXPECTED_TITLE
        + " "
        + EXPECTED_VOLUME_LABEL
        + " 書影"
    )

    discovery_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_DRAFT_RENDER_"
            "INPUT_DISCOVERY"
        ),
        "discovery_state": (
            "COVER_IMAGE_VERIFIED_"
            "RENDER_DRY_RUN_READY"
        ),
        "discovered_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_design_pack_path": str(
            design_pack_path
        ),
        "source_design_pack_digest_sha256": (
            EXPECTED_DESIGN_DIGEST
        ),
        "source_input_pack_path": str(
            input_pack_path
        ),
        "source_input_pack_digest_sha256": (
            EXPECTED_INPUT_DIGEST
        ),
        "source_identity_pack_path": str(
            identity_pack_path
        ),
        "source_identity_pack_digest_sha256": (
            EXPECTED_IDENTITY_DIGEST
        ),
        "production_database_path": str(
            production_database_path
        ),
        "required_production_database_sha256": (
            EXPECTED_DATABASE_SHA
        ),
        "product_page_verification": {
            "requested_url": (
                EXPECTED_PRODUCT_URL
            ),
            "final_url": final_page_url,
            "http_status": page_status,
            "page_sha256": (
                hashlib.sha256(
                    page_html.encode(
                        "utf-8"
                    )
                ).hexdigest()
            ),
            "title_volume_match": True,
            "author_match": True,
            "product_number_match": True,
            "product_number": (
                EXPECTED_PRODUCT_NUMBER
            ),
            "kobo_id": EXPECTED_KOBO_ID,
        },
        "cover_image": {
            "source_candidate_url": (
                selected["url"]
            ),
            "cover_image_url": (
                selected_image[
                    "final_url"
                ]
            ),
            "cover_image_alt": (
                cover_image_alt
            ),
            "hostname": (
                selected_image[
                    "final_hostname"
                ]
            ),
            "format": (
                selected_image["format"]
            ),
            "content_type": (
                selected_image[
                    "content_type"
                ]
            ),
            "byte_size": (
                selected_image[
                    "byte_size"
                ]
            ),
            "width": (
                selected_image["width"]
            ),
            "height": (
                selected_image["height"]
            ),
            "sha256": (
                selected_image["sha256"]
            ),
            "source_alt": (
                selected["alt"]
            ),
            "source_locations": (
                selected["sources"]
            ),
            "title_match": (
                selected["title_match"]
            ),
            "volume_match": (
                selected["volume_match"]
            ),
            "official_image_host": True,
            "portrait_orientation": True,
            "minimum_dimensions_verified": True,
            "cover_image_url_verified": True,
        },
        "candidate_summary": {
            "extracted_candidate_count": (
                len(
                    extracted_candidates
                )
            ),
            "verified_candidate_count": (
                len(
                    verified_candidates
                )
            ),
            "strong_candidate_count": (
                len(
                    strong_candidates
                )
            ),
            "candidate_errors": (
                candidate_errors
            ),
        },
        "image_usage_policy": {
            "render_dry_run_use_allowed": True,
            "source_image_hotlink_approved": False,
            "wordpress_media_upload_required_before_publish": (
                True
            ),
            "publication_with_remote_image_allowed": (
                False
            ),
            "image_file_downloaded_to_repository": False,
            "wordpress_media_write": False,
        },
        "remaining_render_inputs": [],
        "remaining_render_input_count": 0,
        "render_dry_run_allowed": True,
        "draft_creation_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "wordpress_media_write": False,
        "wordpress_post_creation": False,
        "normal_x_fb_write": False,
        "x_api_call": False,
        "x_post": False,
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-DRAFT-RENDER-DRY-RUN"
        ),
        "next_phase_execution_allowed": True,
        "production_status": "NO_GO",
        "safety_state": (
            "RENDER_INPUTS_VERIFIED_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
    }

    discovery = {
        **discovery_payload,
        "wordpress_draft_render_input_"
        "discovery_digest_sha256": (
            canonical_digest(
                discovery_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        discovery,
    )

    return discovery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--design-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--input-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--identity-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = (
            build_render_input_discovery_pack(
                production_database_path=(
                    args.production_db
                ),
                design_pack_path=(
                    args.design_pack
                ),
                input_pack_path=(
                    args.input_pack
                ),
                identity_pack_path=(
                    args.identity_pack
                ),
                output_path=args.output,
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_DRAFT_"
                        "RENDER_INPUT_DISCOVERY"
                    ),
                    "error": str(exc),
                    "render_dry_run_allowed": False,
                    "draft_creation_allowed": False,
                    "database_write": False,
                    "wordpress_api_call": False,
                    "wordpress_write": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    cover_image = result[
        "cover_image"
    ]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "discovery_state": (
                    result["discovery_state"]
                ),
                "product_page_title_match": True,
                "product_page_author_match": True,
                "product_number_match": True,
                "cover_image_url": (
                    cover_image[
                        "cover_image_url"
                    ]
                ),
                "cover_image_alt": (
                    cover_image[
                        "cover_image_alt"
                    ]
                ),
                "cover_image_format": (
                    cover_image["format"]
                ),
                "cover_image_width": (
                    cover_image["width"]
                ),
                "cover_image_height": (
                    cover_image["height"]
                ),
                "cover_image_sha256": (
                    cover_image["sha256"]
                ),
                "cover_image_url_verified": (
                    True
                ),
                "source_image_hotlink_approved": (
                    False
                ),
                "wordpress_media_upload_required_before_publish": (
                    True
                ),
                "remaining_render_input_count": 0,
                "render_dry_run_allowed": True,
                "draft_creation_allowed": False,
                "database_write": False,
                "wordpress_api_call": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "discovery_pack_path": str(
                    args.output.resolve()
                ),
                "discovery_digest_sha256": (
                    result[
                        "wordpress_draft_render_"
                        "input_discovery_digest_sha256"
                    ]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
