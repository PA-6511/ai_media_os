from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile

from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from app.services.sale_store_policy import (
    sale_store_display_name,
    validate_sale_snapshot_store,
)
from app.services.sale_roundup_formatting_service import (
    format_sale_period_jst,
    group_series_items,
    price_labels,
    select_representatives,
    volume_label,
    volume_range_label,
)


SCHEMA_VERSION = (
    "sale_wordpress_sync_dry_run_v1"
)

EXPECTED_OPERATION = (
    "SALE_PUBLICATION_PROJECTION_V1"
)

WORDPRESS_META_KEY = (
    "_ai_media_os_sale_sync_key"
)

WORDPRESS_SOURCE_SHA_META_KEY = (
    "_ai_media_os_sale_projection_sha256"
)

ALLOWED_STORE = "rakuten_kobo"

ALLOWED_PRODUCT_HOST = (
    "books.rakuten.co.jp"
)

ALLOWED_AFFILIATE_HOST = (
    "hb.afl.rakuten.co.jp"
)

ALLOWED_COVER_HOST = (
    "thumbnail.image.rakuten.co.jp"
)


class SaleWordPressSyncPlanError(
    RuntimeError
):
    pass


def canonical_json_bytes(
    value: Any,
) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )


def sha256_bytes(
    value: bytes,
) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def valid_sha256(
    value: str,
) -> bool:
    return bool(
        re.fullmatch(
            r"[0-9a-f]{64}",
            value,
        )
    )


def https_host(
    value: Any,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        return ""

    text = value.strip()

    if not text:
        return ""

    try:
        parsed = urlsplit(
            text
        )
    except Exception:
        return ""

    if (
        parsed.scheme.lower()
        != "https"
    ):
        return ""

    if (
        parsed.username
        or parsed.password
        or parsed.port
    ):
        return ""

    return str(
        parsed.hostname
        or ""
    ).lower()


def slug_for_campaign(
    campaign_id: str,
) -> str:
    normalized = re.sub(
        r"[^a-z0-9-]+",
        "-",
        campaign_id.lower(),
    )

    normalized = re.sub(
        r"-+",
        "-",
        normalized,
    ).strip("-")

    if not normalized:
        normalized = hashlib.sha256(
            campaign_id.encode(
                "utf-8"
            )
        ).hexdigest()[:20]

    return (
        "ebook-sale-"
        + normalized
    )[:180]


def stable_key_for_campaign(
    campaign_id: str,
) -> str:
    return (
        "sale_campaign:"
        + campaign_id
    )


def item_block_reasons(
    item: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if (
        str(
            item.get(
                "store_name"
            )
            or ""
        )
        != ALLOWED_STORE
    ):
        reasons.append(
            "STORE_NOT_SUPPORTED"
        )

    if not str(
        item.get(
            "store_item_id"
        )
        or ""
    ).strip():
        reasons.append(
            "STORE_ITEM_ID_MISSING"
        )

    if not str(
        item.get(
            "title"
        )
        or ""
    ).strip():
        reasons.append(
            "TITLE_MISSING"
        )

    try:
        sale_price = float(
            item.get(
                "sale_price"
            )
        )
    except Exception:
        sale_price = 0.0

    if sale_price <= 0:
        reasons.append(
            "SALE_PRICE_INVALID"
        )

    product_host = https_host(
        item.get(
            "product_url"
        )
    )

    if (
        product_host
        != ALLOWED_PRODUCT_HOST
    ):
        reasons.append(
            "PRODUCT_URL_INVALID"
        )

    affiliate_host = https_host(
        item.get(
            "affiliate_url"
        )
    )

    if (
        affiliate_host
        != ALLOWED_AFFILIATE_HOST
    ):
        reasons.append(
            "AFFILIATE_URL_NOT_READY"
        )

    cover_host = https_host(
        item.get(
            "cover_image_url"
        )
    )

    if (
        cover_host
        != ALLOWED_COVER_HOST
    ):
        reasons.append(
            "COVER_IMAGE_NOT_READY"
        )

    if not str(
        item.get(
            "sale_end_at_utc"
        )
        or ""
    ).strip():
        reasons.append(
            "SALE_END_MISSING"
        )

    if not str(
        item.get(
            "source_row_sha256"
        )
        or ""
    ).strip():
        reasons.append(
            "SOURCE_SHA_MISSING"
        )

    return reasons


def ready_item_model(
    item: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ebook_item_id":
            str(
                item.get(
                    "ebook_item_id"
                )
                or ""
            ),

        "offer_id":
            str(
                item.get(
                    "offer_id"
                )
                or ""
            ),

        "store_name":
            str(
                item.get(
                    "store_name"
                )
                or ""
            ),

        "store_item_id":
            str(
                item.get(
                    "store_item_id"
                )
                or ""
            ),

        "title":
            str(
                item.get(
                    "title"
                )
                or ""
            ),

        "author_name":
            str(
                item.get(
                    "author_name"
                )
                or ""
            ),

        "publisher_name":
            str(
                item.get(
                    "publisher_name"
                )
                or ""
            ),

        "series_name":
            str(
                item.get(
                    "series_name"
                )
                or ""
            ),

        "volume_label":
            str(
                item.get(
                    "volume_label"
                )
                or ""
            ),

        "volume_number":
            item.get(
                "volume_number"
            ),

        "sale_price":
            item.get(
                "sale_price"
            ),

        "point_count": item.get("point_count"),

        "discount_percent":
            item.get(
                "discount_percent"
            ),

        "point_percent":
            item.get(
                "point_percent"
            ),

        "sale_start_at_utc":
            str(
                item.get(
                    "sale_start_at_utc"
                )
                or ""
            ),

        "sale_end_at_utc":
            str(
                item.get(
                    "sale_end_at_utc"
                )
                or ""
            ),

        "affiliate_url":
            str(
                item.get(
                    "affiliate_url"
                )
                or ""
            ),

        "cover_image_url":
            str(
                item.get(
                    "cover_image_url"
                )
                or ""
            ),

        "product_url":
            str(
                item.get(
                    "product_url"
                )
                or ""
            ),

        "affiliate_evidence":
            item.get(
                "affiliate_evidence"
            ),

        "source_row_sha256":
            str(
                item.get(
                    "source_row_sha256"
                )
                or ""
            ),

        "campaign_provenance_status":
            str(
                item.get(
                    "campaign_provenance_status"
                )
                or ""
            ),

        # Preserve evidence structurally.
        # Do not reinterpret it as a DB field.
        "normal_price_evidence_only":
            item.get(
                "normal_price_evidence_only"
            ),
    }


def render_group_html(
    *,
    snapshot: dict[str, Any],
) -> str:
    validation_snapshot = snapshot
    if snapshot.get("campaign_store") == "amazon":
        validation_snapshot = {
            **snapshot,
            "items": [
                {
                    **item,
                    "affiliate_url": (
                        item.get("affiliate_url") or item.get("product_url")
                    ),
                }
                for item in snapshot.get("items", [])
            ],
        }
    campaign_store = validate_sale_snapshot_store(validation_snapshot)
    official_start_at_utc = str(snapshot.get("starts_at") or "")
    official_end_at_utc = str(snapshot.get("ends_at") or "")
    items = snapshot["items"]
    lines: list[str] = []

    lines.append(
        '<section class="ai-media-os-sale-campaign">'
    )

    lines.append(
        "<h2>セール概要</h2>"
    )

    lines.append(
        "<style>"
        ".sale-series{margin:1.5rem 0 2rem}"
        ".sale-series-range{margin:.25rem 0 .75rem;color:#555}"
        ".sale-volume-scroll{display:flex;gap:16px;overflow-x:auto;"
        "padding:0 0 12px;scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch}"
        ".sale-volume-card{flex:0 0 auto;width:160px;scroll-snap-align:start}"
        ".sale-volume-card img{display:block;width:140px;max-width:100%;height:auto;margin:0 auto}"
        ".sale-volume-card p{margin:.3rem 0;line-height:1.4}"
        ".sale-volume-label{font-weight:700}"
        "</style>"
    )

    lines.append(
        '<p class="sale-store">販売ストア：'
        + html.escape(sale_store_display_name(campaign_store))
        + "</p>"
    )

    if (
        official_start_at_utc
        or official_end_at_utc
    ):
        lines.append(
            '<p class="sale-period">'
            + html.escape(
                format_sale_period_jst(official_start_at_utc, official_end_at_utc)
            )
            + "</p>"
        )

    for group in group_series_items(items):
        lines.append('<section class="sale-series">')
        lines.append("<h3>" + html.escape(group["title"]) + "</h3>")
        lines.append(
            '<p class="sale-series-range">'
            + html.escape(volume_range_label(group["items"]))
            + "</p>"
        )
        lines.append('<div class="sale-volume-scroll">')

        for item in group["items"]:
            title = html.escape(str(item.get("title") or ""))
            destination_url = item.get("affiliate_url") or item.get("product_url")
            affiliate_url = html.escape(str(destination_url or ""), quote=True)
            cover_image_url = html.escape(str(item.get("cover_image_url") or ""), quote=True)
            store_item_id = html.escape(str(item.get("store_item_id") or ""), quote=True)
            labels = price_labels(item)

            lines.append(
                '<article class="sale-volume-card" '
                f'data-store-item-id="{store_item_id}">'
            )
            lines.append(f'<a href="{affiliate_url}" rel="nofollow sponsored">')
            lines.append(
                f'<img src="{cover_image_url}" alt="{title}" loading="lazy">'
            )
            lines.append("</a>")
            lines.append(
                '<p class="sale-volume-label">'
                + html.escape(volume_label(item))
                + "</p>"
            )
            if labels["price"]:
                lines.append(
                    '<p class="sale-price">'
                    + html.escape(labels["price"])
                    + "</p>"
                )
            discount_parts = [
                value for value in (labels["discount"], labels["discount_amount"]) if value
            ]
            if discount_parts:
                lines.append(
                    '<p class="sale-discount">'
                    + html.escape("・".join(discount_parts))
                    + "</p>"
                )
            for key, css_class in (("points", "sale-points"),
                                   ("effective", "sale-effective-price")):
                if labels[key]:
                    lines.append(f'<p class="{css_class}">{html.escape(labels[key])}</p>')
            lines.append("</article>")

        lines.append("</div>")
        lines.append("</section>")

    lines.append(
        "</section>"
    )

    return "\n".join(
        lines
    )


def load_managed_state(
    path: Path | None,
) -> tuple[
    dict[str, Any],
    str,
]:
    if path is None:
        return (
            {
                "schema_version":
                    "sale_wordpress_managed_state_v1",
                "posts": {},
            },
            "EMPTY_INITIAL_MANAGED_NAMESPACE",
        )

    raw = path.read_bytes()

    value = json.loads(
        raw.decode(
            "utf-8"
        )
    )

    if not isinstance(
        value,
        dict,
    ):
        raise SaleWordPressSyncPlanError(
            "MANAGED_STATE_INVALID"
        )

    posts = value.get(
        "posts"
    )

    if not isinstance(
        posts,
        dict,
    ):
        raise SaleWordPressSyncPlanError(
            "MANAGED_STATE_POSTS_INVALID"
        )

    return (
        value,
        str(path),
    )


def classify_action(
    *,
    stable_key: str,
    payload_sha256: str,
    ready_count: int,
    managed_state:
        dict[str, Any],
) -> str:
    if ready_count <= 0:
        return "BLOCKED"

    posts = managed_state.get(
        "posts",
        {},
    )

    current = posts.get(
        stable_key
    )

    if not isinstance(
        current,
        dict,
    ):
        return "CREATE"

    previous_sha = str(
        current.get(
            "payload_sha256"
        )
        or ""
    )

    if (
        previous_sha
        == payload_sha256
    ):
        return "NOOP"

    return "UPDATE"


def build_plan(
    *,
    projection_path: Path,
    expected_projection_sha256:
        str,
    managed_state_path:
        Path | None = None,
) -> dict[str, Any]:
    raw = projection_path.read_bytes()

    actual_projection_sha256 = (
        sha256_bytes(
            raw
        )
    )

    if not valid_sha256(
        expected_projection_sha256
    ):
        raise SaleWordPressSyncPlanError(
            "EXPECTED_PROJECTION_SHA_INVALID"
        )

    if (
        actual_projection_sha256
        != expected_projection_sha256
    ):
        raise SaleWordPressSyncPlanError(
            "PROJECTION_SHA_MISMATCH"
        )

    projection = json.loads(
        raw.decode(
            "utf-8"
        )
    )

    if not isinstance(
        projection,
        dict,
    ):
        raise SaleWordPressSyncPlanError(
            "PROJECTION_INVALID"
        )

    if (
        projection.get(
            "operation"
        )
        != EXPECTED_OPERATION
    ):
        raise SaleWordPressSyncPlanError(
            "PROJECTION_OPERATION_INVALID"
        )

    if (
        projection.get(
            "projection_ready_for_wordpress_dry_run"
        )
        is not True
    ):
        raise SaleWordPressSyncPlanError(
            "PROJECTION_NOT_READY_FOR_WORDPRESS_DRY_RUN"
        )

    groups = projection.get(
        "campaign_groups"
    )

    if not isinstance(
        groups,
        list,
    ):
        raise SaleWordPressSyncPlanError(
            "CAMPAIGN_GROUPS_INVALID"
        )

    managed_state, managed_state_source = (
        load_managed_state(
            managed_state_path
        )
    )

    planned_groups: list[
        dict[str, Any]
    ] = []

    total_items = 0
    total_ready = 0
    total_blocked = 0

    action_counts = {
        "CREATE": 0,
        "UPDATE": 0,
        "NOOP": 0,
        "BLOCKED": 0,
    }

    for group in groups:
        if not isinstance(
            group,
            dict,
        ):
            raise SaleWordPressSyncPlanError(
                "CAMPAIGN_GROUP_INVALID"
            )

        campaign_id = str(
            group.get(
                "campaign_id"
            )
            or ""
        ).strip()

        campaign_title = str(
            group.get(
                "campaign_title"
            )
            or ""
        ).strip()

        if not campaign_id:
            raise SaleWordPressSyncPlanError(
                "CAMPAIGN_ID_MISSING"
            )

        if not campaign_title:
            raise SaleWordPressSyncPlanError(
                "CAMPAIGN_TITLE_MISSING"
            )

        source_items = group.get(
            "items"
        )

        if not isinstance(
            source_items,
            list,
        ):
            raise SaleWordPressSyncPlanError(
                "CAMPAIGN_ITEMS_INVALID"
            )

        ready_items: list[
            dict[str, Any]
        ] = []

        blocked_items: list[
            dict[str, Any]
        ] = []

        for item in source_items:
            if not isinstance(
                item,
                dict,
            ):
                raise SaleWordPressSyncPlanError(
                    "CAMPAIGN_ITEM_INVALID"
                )

            reasons = item_block_reasons(
                item
            )

            if reasons:
                blocked_items.append(
                    {
                        "store_name":
                            str(
                                item.get(
                                    "store_name"
                                )
                                or ""
                            ),

                        "store_item_id":
                            str(
                                item.get(
                                    "store_item_id"
                                )
                                or ""
                            ),

                        "ebook_item_id":
                            str(
                                item.get(
                                    "ebook_item_id"
                                )
                                or ""
                            ),

                        "title":
                            str(
                                item.get(
                                    "title"
                                )
                                or ""
                            ),

                        "reasons":
                            reasons,
                    }
                )

                continue

            ready_items.append(
                ready_item_model(
                    item
                )
            )

        ready_items.sort(
            key=lambda item: (
                str(
                    item.get(
                        "store_item_id"
                    )
                    or ""
                ),
                str(
                    item.get(
                        "ebook_item_id"
                    )
                    or ""
                ),
            )
        )

        blocked_items.sort(
            key=lambda item: (
                str(
                    item.get(
                        "store_item_id"
                    )
                    or ""
                ),
                str(
                    item.get(
                        "ebook_item_id"
                    )
                    or ""
                ),
            )
        )

        stable_key = (
            stable_key_for_campaign(
                campaign_id
            )
        )

        slug = slug_for_campaign(
            campaign_id
        )

        official_start = str(
            group.get(
                "official_start_at_utc"
            )
            or ""
        )

        official_end = str(
            group.get(
                "official_end_at_utc"
            )
            or ""
        )

        content_html = (
            render_group_html(
                snapshot={
                    "campaign_store": group.get("campaign_store"),
                    "title": campaign_title,
                    "starts_at": official_start,
                    "ends_at": official_end,
                    "items": ready_items,
                },
            )
        )

        wordpress_request = {
            "method":
                "NOT_CALLED",

            "title":
                campaign_title,

            "slug":
                slug,

            "status":
                "draft",

            "content":
                content_html,

            "meta": {
                WORDPRESS_META_KEY:
                    stable_key,

                WORDPRESS_SOURCE_SHA_META_KEY:
                    actual_projection_sha256,
            },
        }

        payload_sha256 = (
            sha256_bytes(
                canonical_json_bytes(
                    wordpress_request
                )
            )
        )

        action = classify_action(
            stable_key=stable_key,
            payload_sha256=(
                payload_sha256
            ),
            ready_count=len(
                ready_items
            ),
            managed_state=(
                managed_state
            ),
        )

        action_counts[
            action
        ] += 1

        total_items += len(
            source_items
        )

        total_ready += len(
            ready_items
        )

        total_blocked += len(
            blocked_items
        )

        planned_groups.append(
            {
                "stable_identity": {
                    "stable_key":
                        stable_key,

                    "wordpress_meta_key":
                        WORDPRESS_META_KEY,

                    "slug":
                        slug,
                },

                "campaign": {
                    "campaign_id":
                        campaign_id,

                    "campaign_title":
                        campaign_title,

                    "source_bucket":
                        str(
                            group.get(
                                "source_bucket"
                            )
                            or ""
                        ),

                    "official_start_at_utc":
                        official_start,

                    "official_end_at_utc":
                        official_end,

                    "merch_id":
                        group.get(
                            "merch_id"
                        ),

                    "sale_id":
                        group.get(
                            "sale_id"
                        ),

                    "sonar_no":
                        group.get(
                            "sonar_no"
                        ),
                },

                "source_item_count":
                    len(
                        source_items
                    ),

                "ready_item_count":
                    len(
                        ready_items
                    ),

                "blocked_item_count":
                    len(
                        blocked_items
                    ),

                "ready_items":
                    ready_items,

                "blocked_items":
                    blocked_items,

                "wordpress": {
                    "desired_action":
                        action,

                    "action_basis":
                        (
                            "INITIAL_MANAGED_NAMESPACE"
                            if managed_state_path
                            is None
                            else
                            "SUPPLIED_MANAGED_STATE"
                        ),

                    "payload_sha256":
                        payload_sha256,

                    "request_preview":
                        wordpress_request,

                    "wordpress_lookup_performed":
                        False,

                    "wordpress_write":
                        False,

                    "requires_p4_readback_before_write":
                        True,
                },
            }
        )

    planned_groups.sort(
        key=lambda group: str(
            group[
                "campaign"
            ][
                "campaign_id"
            ]
        )
    )

    standalone_sales = projection.get(
        "standalone_sales",
        [],
    )

    unresolved_items = projection.get(
        "unresolved_items",
        [],
    )

    metadata_missing = projection.get(
        "campaign_metadata_missing",
        [],
    )

    period_conflicts = projection.get(
        "campaign_period_conflicts",
        [],
    )

    if not isinstance(
        standalone_sales,
        list,
    ):
        raise SaleWordPressSyncPlanError(
            "STANDALONE_SALES_INVALID"
        )

    if not isinstance(
        unresolved_items,
        list,
    ):
        raise SaleWordPressSyncPlanError(
            "UNRESOLVED_ITEMS_INVALID"
        )

    plan: dict[str, Any] = {
        "schema_version":
            SCHEMA_VERSION,

        "operation":
            "SALE_WORDPRESS_SYNC_DRY_RUN_V1",

        "mode":
            "DRY_RUN",

        "source_projection": {
            "path":
                str(
                    projection_path
                ),

            "raw_sha256":
                actual_projection_sha256,

            "declared_projection_sha256":
                str(
                    projection.get(
                        "projection_sha256"
                    )
                    or ""
                ),

            "operation":
                str(
                    projection.get(
                        "operation"
                    )
                    or ""
                ),

            "schema_version":
                str(
                    projection.get(
                        "schema_version"
                    )
                    or ""
                ),

            "generated_at_utc":
                str(
                    projection.get(
                        "generated_at_utc"
                    )
                    or ""
                ),

            "threshold_percent":
                projection.get(
                    "threshold_percent"
                ),
        },

        "managed_state": {
            "source":
                managed_state_source,

            "wordpress_lookup_performed":
                False,

            "note":
                (
                    "P3 does not prove WordPress post absence. "
                    "P4 must read back stable identity before write."
                ),
        },

        "groups":
            planned_groups,

        "standalone_sales": {
            "source_count":
                len(
                    standalone_sales
                ),

            "status":
                (
                    "NONE"
                    if not standalone_sales
                    else
                    "DEFERRED_V1"
                ),
        },

        "summary": {
            "campaign_group_count":
                len(
                    planned_groups
                ),

            "source_item_count":
                total_items,

            "ready_item_count":
                total_ready,

            "blocked_item_count":
                total_blocked,

            "create_count":
                action_counts[
                    "CREATE"
                ],

            "update_count":
                action_counts[
                    "UPDATE"
                ],

            "noop_count":
                action_counts[
                    "NOOP"
                ],

            "blocked_group_count":
                action_counts[
                    "BLOCKED"
                ],

            "unresolved_source_count":
                len(
                    unresolved_items
                ),

            "campaign_metadata_missing_count":
                (
                    len(
                        metadata_missing
                    )
                    if isinstance(
                        metadata_missing,
                        list,
                    )
                    else -1
                ),

            "campaign_period_conflict_count":
                (
                    len(
                        period_conflicts
                    )
                    if isinstance(
                        period_conflicts,
                        list,
                    )
                    else -1
                ),
        },

        "safety": {
            "projection_sha_verified":
                True,

            "live_database_read":
                False,

            "production_database_write":
                False,

            "wordpress_api_call":
                False,

            "wordpress_read":
                False,

            "wordpress_write":
                False,

            "wordpress_publish":
                False,

            "x_api_call":
                False,

            "x_post":
                False,

            "unmonetized_item_fallback_link":
                False,

            "expired_sale_unpublish":
                False,
        },

        "next_phase_contract": {
            "phase":
                "P4",

            "requires_human_approval":
                True,

            "requires_wordpress_stable_identity_readback":
                True,

            "wordpress_write_allowed_here":
                False,

            "unpublish_owned_by":
                "P5",
        },
    }

    plan_sha256 = sha256_bytes(
        canonical_json_bytes(
            plan
        )
    )

    plan[
        "plan_sha256"
    ] = plan_sha256

    return plan


def write_plan_atomically(
    *,
    plan: dict[str, Any],
    output_dir: Path,
) -> tuple[
    Path,
    str,
]:
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_sha = str(
        plan[
            "source_projection"
        ][
            "raw_sha256"
        ]
    )

    path = (
        output_dir
        / (
            source_sha
            + "-sale-wordpress-sync-dry-run-v1.json"
        )
    )

    payload = (
        json.dumps(
            plan,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    if path.is_file():
        existing = path.read_bytes()

        if existing == payload:
            return (
                path,
                "NOOP",
            )

        action = "UPDATE"

    else:
        action = "CREATE"

    fd, tmp_name = tempfile.mkstemp(
        prefix=(
            "."
            + path.name
            + "."
        ),
        suffix=".tmp",
        dir=str(
            output_dir
        ),
    )

    try:
        with os.fdopen(
            fd,
            "wb",
        ) as handle:
            handle.write(
                payload
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            tmp_name,
            path,
        )

    finally:
        if os.path.exists(
            tmp_name
        ):
            os.unlink(
                tmp_name
            )

    return (
        path,
        action,
    )
