from __future__ import annotations

from dataclasses import dataclass


X_R13_EBOOK_ITEM_ID = (
    "e2029b2f-f44a-462f-abc8-86c4bc74b818"
)


class X13WordPressDraftGateError(ValueError):
    pass


@dataclass(frozen=True)
class X13WordPressDraftGateInput:
    ebook_item_id: str
    workflow_status: str
    review_status: str
    publish_ready: bool
    wordpress_status: str
    wordpress_post_id: str | None
    request_status: str
    approval_type: str
    item_type: str
    store_name: str
    link_route: str
    affiliate_url: str


@dataclass(frozen=True)
class X13WordPressDraftGateDecision:
    ready: bool
    decision: str
    ebook_item_id: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise X13WordPressDraftGateError(message)


def evaluate_x_r13_wordpress_draft_gate(
    value: X13WordPressDraftGateInput,
) -> X13WordPressDraftGateDecision:
    _require(
        value.ebook_item_id == X_R13_EBOOK_ITEM_ID,
        "candidate does not match X-R13",
    )
    _require(
        value.workflow_status == "READY",
        "workflow_status must be READY",
    )
    _require(
        value.review_status == "APPROVED",
        "review_status must be APPROVED",
    )
    _require(
        value.publish_ready is False,
        "publish_ready must remain false",
    )
    _require(
        value.wordpress_status == "NOT_CREATED",
        "wordpress_status must be NOT_CREATED",
    )
    _require(
        value.wordpress_post_id is None,
        "wordpress_post_id must be empty",
    )
    _require(
        value.request_status == "APPROVED",
        "approval request must be APPROVED",
    )
    _require(
        value.approval_type == "REVIEW_READY",
        "approval type must be REVIEW_READY",
    )
    _require(
        value.item_type == "tankobon",
        "item_type must be tankobon",
    )
    _require(
        value.store_name.strip().upper() == "RAKUTEN_KOBO",
        "store must be RAKUTEN_KOBO",
    )
    _require(
        value.link_route == "DIRECT_AFFILIATE",
        "link route must be DIRECT_AFFILIATE",
    )
    _require(
        value.affiliate_url.startswith("https://"),
        "affiliate URL must use HTTPS",
    )

    return X13WordPressDraftGateDecision(
        ready=True,
        decision=(
            "READY_FOR_ONE_SHOT_WORDPRESS_DRAFT_"
            "CREATION_APPROVAL_PREP_ONLY"
        ),
        ebook_item_id=value.ebook_item_id,
    )
