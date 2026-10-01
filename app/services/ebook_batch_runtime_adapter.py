from __future__ import annotations

from pathlib import Path
import os
import re
from types import SimpleNamespace
from typing import Any


class HeadlessWordPressDraftExecutor:
    """
    Reuse the existing tested GUI WordPress draft item
    executor without invoking the HTTP/GUI layer.
    """

    def __init__(
        self,
        repository_root: str | Path,
    ) -> None:
        self.repository_root = Path(
            repository_root
        ).resolve()

    def __call__(
        self,
        ebook_item_id: str,
    ) -> Any:
        from scripts.new_release_multistore_app import (
            MultiStoreAppHandler,
        )

        class HandlerContext:
            def __init__(
                inner_self,
                repo_root: Path,
            ) -> None:
                inner_self._application = (
                    SimpleNamespace(
                        repo_root=repo_root
                    )
                )

            def _app(
                inner_self,
            ):
                return (
                    inner_self._application
                )

        context = HandlerContext(
            self.repository_root
        )

        return (
            MultiStoreAppHandler
            ._execute_bulk_wordpress_draft_item(
                context,
                str(ebook_item_id),
            )
        )


def _primary_author(
    value: str,
) -> str:
    return str(
        value or ""
    ).split(
        "|",
        1,
    )[0].strip()


def _x_title(
    title: str,
) -> str:
    value = " ".join(
        str(
            title or ""
        ).split()
    )

    value = re.sub(
        r"\s+(?:第)?\d+(?:巻)?$",
        "",
        value,
    )

    return value.strip()


def _x_volume(
    volume_label: str,
    title: str,
) -> str:
    value = " ".join(
        str(
            volume_label or ""
        ).split()
    )

    match = re.search(
        r"(\d+)",
        value,
    )

    if match:
        return (
            match.group(1)
            + "巻"
        )

    title_match = re.search(
        r"(?:第)?(\d+)(?:巻)?$",
        str(
            title or ""
        ).strip(),
    )

    if title_match:
        return (
            title_match.group(1)
            + "巻"
        )

    return value


class LocalXDraftExecutor:
    """
    Generate and persist an internal X draft.

    No X API call and no X post is performed by
    this adapter.
    """

    def __call__(
        self,
        ebook_item_id: str,
        wordpress_post_id: int,
        *,
        scheduled_at: Any = None,
        paid_partnership: bool = True,
    ) -> Any:
        from app.db.models import EbookItem
        from app.db.session import SessionLocal
        from app.services.workflow_approved_x_draft_read_service import (
            build_wordpress_article_url,
        )
        from app.services.x_draft_generation_service import (
            XDraftGenerationService,
            XDraftInput,
        )
        from app.services.x_post_draft_persistence_service import (
            XPostDraftPersistenceService,
            XPostDraftSaveRequest,
        )

        base_url = (
            os.environ.get(
                "WORDPRESS_BASE_URL"
            )
            or os.environ.get(
                "WP_BASE_URL"
            )
            or ""
        )

        with SessionLocal() as session:
            item = session.get(
                EbookItem,
                ebook_item_id,
            )

            if item is None:
                raise RuntimeError(
                    "x_draft_item_not_found"
                )

            release_date = getattr(
                item,
                "release_date",
                None,
            )

            if hasattr(
                release_date,
                "isoformat",
            ):
                release_value = (
                    release_date.isoformat()
                )
            else:
                release_value = str(
                    release_date or ""
                )

            raw_title = str(
                getattr(
                    item,
                    "title",
                    "",
                )
                or ""
            )

            draft_input = XDraftInput(
                ebook_item_id=str(
                    item.id
                ),
                title=_x_title(
                    raw_title
                ),
                volume_label=_x_volume(
                    str(
                        getattr(
                            item,
                            "volume_label",
                            "",
                        )
                        or ""
                    ),
                    raw_title,
                ),
                release_date=release_value,
                category=str(
                    getattr(
                        item,
                        "item_type",
                        "",
                    )
                    or ""
                ),
                author_name=_primary_author(
                    str(
                        getattr(
                            item,
                            "author_name",
                            "",
                        )
                        or ""
                    )
                ),
                article_url=(
                    build_wordpress_article_url(
                        wordpress_base_url=(
                            base_url
                        ),
                        wordpress_post_id=(
                            wordpress_post_id
                        ),
                    )
                ),
                wordpress_draft_id=int(
                    wordpress_post_id
                ),
                wordpress_status=(
                    "DRAFT"
                ),
            )

        draft_result = (
            XDraftGenerationService()
            .generate(
                draft_input
            )
        )

        with SessionLocal() as session:
            XPostDraftPersistenceService(
                session
            ).save(
                XPostDraftSaveRequest(
                    source_type="new_release",
                    source_id=(
                        draft_result.ebook_item_id
                    ),
                    ebook_item_id=(
                        draft_result.ebook_item_id
                    ),
                    feedback_id=(
                        draft_result.feedback_id
                    ),
                    generated_text=(
                        draft_result.generated_text
                    ),
                    scheduled_at=scheduled_at,
                    paid_partnership=(
                        paid_partnership
                    ),
                )
            )
            session.commit()

        return draft_result
