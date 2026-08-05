from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import DailySummaryRun
from app.db.repositories.daily_summary_run_repository import DailySummaryRunRepository
from app.services.daily_summary_html_builder import (
    DailySummaryHtmlBuilder,
    build_daily_summary_slug,
    build_daily_summary_title,
)
from app.services.daily_summary_query_service import (
    DailySummaryItem,
    DailySummaryQueryService,
)


class DailySummaryDraftError(RuntimeError):
    def __init__(self, code: str, message: str, warnings: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.code = code
        self.warnings = warnings


@dataclass(frozen=True)
class DailySummaryDraftPreview:
    summary_date: date
    summary_key: str
    title: str
    slug: str
    items: tuple[DailySummaryItem, ...]
    html: str
    input_hash: str
    action: str
    warnings: tuple[str, ...]
    generation_allowed: bool


class DailySummaryWordPressDraftService:
    def __init__(self, session: Session, *, wordpress_client: Any) -> None:
        self.session = session
        self.wordpress_client = wordpress_client
        self.query_service = DailySummaryQueryService(session)
        self.run_repository = DailySummaryRunRepository(session)
        self.html_builder = DailySummaryHtmlBuilder()

    @staticmethod
    def summary_key(summary_date: date) -> str:
        return f"daily-summary:{summary_date.isoformat()}"

    def preview(self, summary_date: date) -> DailySummaryDraftPreview:
        snapshot = self.query_service.build_snapshot(summary_date)
        warnings: list[str] = []
        if snapshot.selected_count == 0:
            warnings.append("掲載選択が0件です。")
        if snapshot.inconsistent_count:
            warnings.append(f"ローカル状態不整合: {snapshot.inconsistent_count}件")

        verified_items: list[DailySummaryItem] = []
        if not warnings:
            for item in snapshot.selected_items:
                try:
                    post_id = int(item.wordpress_post_id)
                    remote = self.wordpress_client.get_post_state(post_id=post_id)
                    meta = self.wordpress_client.get_post_affiliate_meta(post_id=post_id)
                except Exception:
                    warnings.append(f"WordPress状態取得失敗: {item.ebook_item_id}")
                    continue
                if remote.post_id != post_id or meta.post_id != post_id:
                    warnings.append(f"WordPress投稿ID不一致: {item.ebook_item_id}")
                    continue
                if remote.status != "publish":
                    warnings.append(f"個別記事が未公開: {item.ebook_item_id}")
                    continue
                image_url = None
                featured_media = int(getattr(remote, "featured_media", 0) or 0)
                if featured_media:
                    try:
                        image_url = self.wordpress_client.get_media(
                            media_id=featured_media
                        ).source_url
                    except Exception:
                        image_url = None
                verified_items.append(
                    self.query_service.with_remote_values(
                        item,
                        remote_status=remote.status,
                        internal_url=remote.link,
                        affiliate_meta=meta.meta,
                        image_url=image_url,
                    )
                )

        title = build_daily_summary_title(summary_date)
        slug = build_daily_summary_slug(summary_date)
        html_content = self.html_builder.build(
            summary_date=summary_date,
            items=tuple(verified_items) if not warnings else snapshot.selected_items,
        )
        key = self.summary_key(summary_date)
        hash_payload = json.dumps(
            {
                "summary_key": key,
                "title": title,
                "slug": slug,
                "item_ids": [item.ebook_item_id for item in verified_items],
                "html": html_content,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        input_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()
        run = self.run_repository.get_for_date(summary_date)
        action = "update" if run and run.wordpress_post_id else "create"
        if run and run.wordpress_status in {"future", "publish", "trash"}:
            warnings.append(f"既存日次まとめは{run.wordpress_status}のため自動更新できません。")
        return DailySummaryDraftPreview(
            summary_date=summary_date,
            summary_key=key,
            title=title,
            slug=slug,
            items=tuple(verified_items) if not warnings else snapshot.selected_items,
            html=html_content,
            input_hash=input_hash,
            action=action,
            warnings=tuple(warnings),
            generation_allowed=not warnings and bool(verified_items),
        )

    def execute(
        self, *, summary_date: date, dry_run: bool = True
    ) -> DailySummaryDraftPreview:
        preview = self.preview(summary_date)
        if not preview.generation_allowed:
            raise DailySummaryDraftError(
                "generation_blocked",
                "daily summary generation is blocked",
                preview.warnings,
            )
        run = self.run_repository.get_for_date(summary_date)
        previous_input_hash = run.input_hash if run is not None else None
        previous_execution_status = run.execution_status if run is not None else None
        if not dry_run and previous_execution_status in {
            "CREATING",
            "UPDATING",
            "FAILED",
        }:
            raise DailySummaryDraftError(
                "reconciliation_required",
                "previous execution requires manual reconciliation",
            )
        selected_ids = [item.ebook_item_id for item in preview.items]
        if run is None:
            run = DailySummaryRun(
                summary_date=summary_date,
                summary_key=preview.summary_key,
                selected_count=len(selected_ids),
                generated_count=0,
                selected_item_ids_json=json.dumps(selected_ids),
                input_hash=preview.input_hash,
                execution_status="PREVIEWED" if dry_run else "CREATING",
                operation="DAILY_SUMMARY_DRAFT_CREATE",
            )
        else:
            if run.summary_key != preview.summary_key:
                raise DailySummaryDraftError("summary_key_mismatch", "summary key mismatch")
            run.selected_count = len(selected_ids)
            run.selected_item_ids_json = json.dumps(selected_ids)
            run.operation = (
                "DAILY_SUMMARY_DRAFT_UPDATE" if run.wordpress_post_id
                else "DAILY_SUMMARY_DRAFT_CREATE"
            )
            if dry_run:
                run.execution_status = "PREVIEWED"
        run.input_hash = preview.input_hash
        run.error_code = None
        self.run_repository.save(run)
        if dry_run:
            self.run_repository.add_history(run=run, success=True)
            return preview

        same_input = bool(
            run.wordpress_post_id
            and previous_input_hash == preview.input_hash
            and previous_execution_status == "SUCCEEDED"
        )
        if run.wordpress_post_id and not same_input:
            run.execution_status = "UPDATING"
        self.session.commit()

        payload: dict[str, Any] = {
            "status": "draft",
            "title": preview.title,
            "slug": preview.slug,
            "content": preview.html,
            "meta": {
                "_ai_media_os_daily_summary_date": summary_date.isoformat(),
                "_ai_media_os_daily_summary_key": preview.summary_key,
                "_ai_media_os_daily_summary_marker": "1",
            },
        }
        try:
            if run.wordpress_post_id:
                post_id = int(run.wordpress_post_id)
                remote = self.wordpress_client.get_post_state(post_id=post_id)
                if remote.post_id != post_id:
                    raise DailySummaryDraftError("post_id_mismatch", "post id mismatch")
                if remote.status != "draft":
                    raise DailySummaryDraftError(
                        f"existing_{remote.status}", "existing summary is not draft"
                    )
                if same_input:
                    self.run_repository.add_history(run=run, success=True)
                    return preview
                response = self.wordpress_client.update_draft(post_id=post_id, payload=payload)
            else:
                response = self.wordpress_client.create_draft(payload)
            if response.status != "draft":
                raise DailySummaryDraftError("invalid_remote_status", "remote status is not draft")
            if run.wordpress_post_id and str(response.post_id) != run.wordpress_post_id:
                raise DailySummaryDraftError("post_id_mismatch", "response post id mismatch")
            run.wordpress_post_id = str(response.post_id)
            run.remote_response_id = str(response.post_id)
            run.wordpress_status = "draft"
            run.generated_count = len(selected_ids)
            run.execution_status = "SUCCEEDED"
            self.session.flush()
            self.run_repository.add_history(run=run, success=True)
        except Exception as exc:
            run.execution_status = "FAILED"
            run.error_code = str(getattr(exc, "code", "wordpress_error"))[:64]
            self.session.flush()
            self.run_repository.add_history(
                run=run, success=False, error_code=run.error_code
            )
            self.session.commit()
            raise
        return preview