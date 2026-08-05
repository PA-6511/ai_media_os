from __future__ import annotations

import pytest

from app.services.x_r13_wordpress_draft_gate import (
    X13WordPressDraftGateError,
    X13WordPressDraftGateInput,
    evaluate_x_r13_wordpress_draft_gate,
)


def build_gate_input(**overrides):
    values = {
        "ebook_item_id": (
            "e2029b2f-f44a-462f-abc8-86c4bc74b818"
        ),
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": None,
        "request_status": "APPROVED",
        "approval_type": "REVIEW_READY",
        "item_type": "tankobon",
        "store_name": "rakuten_kobo",
        "link_route": "DIRECT_AFFILIATE",
        "affiliate_url": "https://example.test/affiliate",
    }
    values.update(overrides)
    return X13WordPressDraftGateInput(**values)


def test_approved_candidate_passes_gate() -> None:
    decision = evaluate_x_r13_wordpress_draft_gate(
        build_gate_input()
    )

    assert decision.ready is True
    assert (
        decision.decision
        == (
            "READY_FOR_ONE_SHOT_WORDPRESS_DRAFT_"
            "CREATION_APPROVAL_PREP_ONLY"
        )
    )


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("workflow_status", "REVIEW", "workflow_status must be READY"),
        ("review_status", "IN_REVIEW", "review_status must be APPROVED"),
        ("wordpress_status", "DRAFT", "wordpress_status must be NOT_CREATED"),
        ("wordpress_post_id", "123", "wordpress_post_id must be empty"),
    ],
)
def test_invalid_candidate_state_is_rejected(
    field_name,
    value,
    message,
) -> None:
    with pytest.raises(X13WordPressDraftGateError, match=message):
        evaluate_x_r13_wordpress_draft_gate(
            build_gate_input(**{field_name: value})
        )


def test_non_direct_affiliate_route_is_rejected() -> None:
    with pytest.raises(
        X13WordPressDraftGateError,
        match="DIRECT_AFFILIATE",
    ):
        evaluate_x_r13_wordpress_draft_gate(
            build_gate_input(link_route="PRODUCT_URL")
        )
