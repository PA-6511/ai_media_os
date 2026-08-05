from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from app.integrations.wordpress_rest_client import (
    WordPressDraftResponse,
    WordPressRestClient,
)
from app.services.new_release_featured_image_lite import (
    NewReleaseFeaturedImageInput,
    attach_featured_image_to_new_release_draft,
)
from app.services.x_r13_wordpress_draft_gate import (
    X13WordPressDraftGateInput,
    evaluate_x_r13_wordpress_draft_gate,
)
from app.services.x_r13_wordpress_draft_payload_adapter import (
    X13WordPressDraftInput,
    build_x_r13_wordpress_draft_payload,
)
from app.services.x_r15_public_cover_source import (
    fetch_x15_public_cover,
)


X_R13_EBOOK_ITEM_ID = (
    "e2029b2f-f44a-462f-abc8-86c4bc74b818"
)
X_R13_REQUEST_ID = (
    "39c15d3d-d79d-443a-9a56-92d3e3ff429c"
)


class X13WordPressDraftRunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class X13WordPressDraftRunResult:
    ebook_item_id: str
    post_id: int
    status: str
    link: str | None
    state_changed: bool
    committed: bool
    image_status: str = "SKIPPED_NO_COVER_SOURCE"
    image_media_id: int | None = None
    image_media_url: str | None = None
    featured_media_set: bool = False
    publish_executed: bool = False
    image_error_summary: str | None = None


def _value(source: Any, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)

    return getattr(source, name)


def _optional_value(source: Any, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)

    return getattr(source, name, None)


def _first_nonempty(*values: Any) -> str:
    for value in values:
        normalized = str(value or "").strip()

        if normalized:
            return normalized

    return ""


def _safe_cover_filename(source_item_id: str) -> str:
    normalized = "".join(
        char.lower()
        if char.isalnum() or char in {"-", "_"}
        else "-"
        for char in source_item_id.strip()
    ).strip("-")

    if not normalized:
        normalized = "cover"

    return f"{normalized}.jpg"


def _summarize_image_error(error: Exception) -> str:
    detail = str(error).strip()

    if detail:
        return f"{type(error).__name__}: {detail}"[:240]

    return type(error).__name__


def execute_x_r13_wordpress_draft_once(
    *,
    item: Any,
    approval_request: Any,
    offer: Any,
    client: Any,
    state_repository: Any,
    commit: Callable[[], None],
    rollback: Callable[[], None],
    actor: str = "block:ebook:x-r13-wordpress-draft",
    cover_fetcher: Any = fetch_x15_public_cover,
) -> X13WordPressDraftRunResult:
    try:
        affiliate_url = str(
            _value(offer, "affiliate_url") or ""
        ).strip()

        gate_input = X13WordPressDraftGateInput(
            ebook_item_id=str(_value(item, "id")),
            workflow_status=str(_value(item, "workflow_status")),
            review_status=str(_value(item, "review_status")),
            publish_ready=bool(_value(item, "publish_ready")),
            wordpress_status=str(_value(item, "wordpress_status")),
            wordpress_post_id=_value(item, "wordpress_post_id"),
            request_status=str(_value(approval_request, "status")),
            approval_type=str(_value(approval_request, "approval_type")),
            item_type=str(_value(item, "item_type")),
            store_name=str(_value(offer, "store_name")),
            link_route="DIRECT_AFFILIATE",
            affiliate_url=affiliate_url,
        )

        decision = evaluate_x_r13_wordpress_draft_gate(gate_input)

        if not decision.ready:
            raise X13WordPressDraftRunnerError(
                "WordPress draft gate did not return ready"
            )

        payload_input = X13WordPressDraftInput(
            ebook_item_id=str(_value(item, "id")),
            title=str(_value(item, "title")),
            volume_label=str(_value(item, "volume_label")),
            author_name=str(_value(item, "author_name")),
            publisher_name=str(_value(item, "publisher_name")),
            release_date=_value(item, "release_date"),
            item_type=str(_value(item, "item_type")),
            store_name=str(_value(offer, "store_name")),
            store_item_id=str(_value(offer, "store_item_id")),
            affiliate_url=affiliate_url,
        )

        payload = build_x_r13_wordpress_draft_payload(payload_input)
        response: WordPressDraftResponse = client.create_draft(payload)

        if response.status != "draft":
            raise X13WordPressDraftRunnerError(
                "WordPress response is not draft"
            )

        state_changed = state_repository.mark_wordpress_draft_created(
            item,
            response.post_id,
            changed_by=actor,
            note=(
                "X-R13 approved WordPress draft created and reconciled."
            ),
        )

        commit()

    except Exception:
        rollback()
        raise

    image_status = "SKIPPED_NO_COVER_SOURCE"
    image_media_id = None
    image_media_url = None
    image_featured_media_set = False
    image_error_summary = None

    try:
        product_page_url = _first_nonempty(
            _optional_value(offer, "product_url"),
            _optional_value(offer, "product_page_url"),
            _optional_value(offer, "page_url"),
        )

        image_result = attach_featured_image_to_new_release_draft(
            input_data=NewReleaseFeaturedImageInput(
                ebook_item_id=str(_value(item, "id")),
                source_item_id=_first_nonempty(
                    _optional_value(item, "source_item_id"),
                    _optional_value(offer, "store_item_id"),
                ),
                wordpress_post_id=response.post_id,
                product_page_url=product_page_url,
                filename=_safe_cover_filename(
                    _first_nonempty(
                        _optional_value(item, "source_item_id"),
                        _optional_value(offer, "store_item_id"),
                        str(response.post_id),
                    )
                ),
                item=item,
                offer=offer,
            ),
            client=client,
            cover_fetcher=cover_fetcher,
        )
        image_status = image_result.status
        image_media_id = image_result.media_id
        image_media_url = image_result.media_url
        image_featured_media_set = (
            image_result.featured_media_set
        )
        image_error_summary = image_result.error_summary
    except Exception as exc:
        image_status = "REVIEW_REQUIRED"
        image_featured_media_set = False
        image_error_summary = _summarize_image_error(exc)

    return X13WordPressDraftRunResult(
        ebook_item_id=str(_value(item, "id")),
        post_id=response.post_id,
        status=response.status,
        link=response.link,
        state_changed=bool(state_changed),
        committed=True,
        image_status=image_status,
        image_media_id=image_media_id,
        image_media_url=image_media_url,
        featured_media_set=image_featured_media_set,
        publish_executed=False,
        image_error_summary=image_error_summary,
    )


def _load_execution_authorization(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(value, dict):
        raise X13WordPressDraftRunnerError(
            "execution authorization must be an object"
        )

    required = {
        "ebook_item_id": X_R13_EBOOK_ITEM_ID,
        "execution_allowed": True,
        "wordpress_write_allowed": True,
        "one_shot": True,
    }

    for key, expected in required.items():
        if value.get(key) != expected:
            raise X13WordPressDraftRunnerError(
                f"execution authorization mismatch: {key}"
            )

    return value


def run_production_once(
    *,
    execution_authorization_path: Path,
) -> X13WordPressDraftRunResult:
    _load_execution_authorization(execution_authorization_path)

    from sqlalchemy import select

    from app.db.models.ebook import EbookItem, StoreOffer
    from app.db.models.workflow_approval import WorkflowApprovalRequest
    from app.db.repositories.workflow_state_repository import (
        WorkflowStateRepository,
    )
    from app.db.session import SessionLocal

    base_url = (
        os.environ.get("WORDPRESS_BASE_URL")
        or os.environ.get("WP_BASE_URL")
        or ""
    )
    username = (
        os.environ.get("WORDPRESS_USERNAME")
        or os.environ.get("WP_USERNAME")
        or ""
    )
    password = (
        os.environ.get("WORDPRESS_APPLICATION_PASSWORD")
        or os.environ.get("WP_APPLICATION_PASSWORD")
        or ""
    )

    client = WordPressRestClient(
        base_url=base_url,
        username=username,
        application_password=password,
    )

    session = SessionLocal()

    try:
        item = session.get(EbookItem, X_R13_EBOOK_ITEM_ID)

        if item is None:
            raise X13WordPressDraftRunnerError(
                "X-R13 ebook item was not found"
            )

        approval_request = session.get(
            WorkflowApprovalRequest,
            X_R13_REQUEST_ID,
        )

        if approval_request is None:
            raise X13WordPressDraftRunnerError(
                "X-R13 approval request was not found"
            )

        offer = session.scalar(
            select(StoreOffer).where(
                StoreOffer.ebook_item_id == X_R13_EBOOK_ITEM_ID,
                StoreOffer.store_name.in_(
                    ["RAKUTEN_KOBO", "rakuten_kobo"]
                ),
            )
        )

        if offer is None:
            raise X13WordPressDraftRunnerError(
                "Rakuten Kobo offer was not found"
            )

        return execute_x_r13_wordpress_draft_once(
            item=item,
            approval_request=approval_request,
            offer=offer,
            client=client,
            state_repository=WorkflowStateRepository(session),
            commit=session.commit,
            rollback=session.rollback,
        )

    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create the approved X-R13 WordPress draft exactly once."
        )
    )
    parser.add_argument(
        "--execution-authorization",
        type=Path,
        required=True,
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    result = run_production_once(
        execution_authorization_path=arguments.execution_authorization
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
