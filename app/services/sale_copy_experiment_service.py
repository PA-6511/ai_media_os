"""Component-based copy experiments. Generates drafts, never posts."""
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from sqlalchemy import select
from app.db.models.sale_roundup import SaleExperiment, SaleCopyVariant
from app.services.sale_roundup_service import digest, utc
from app.services.x_draft_generation_service import XDraftResult, validate_article_url, load_contract
from app.services.x_post_draft_persistence_service import (
    XPostDraftPersistenceService,
    XPostDraftSaveRequest,
)
from app.services.xnr_roundup_content import _x_weighted_length
from app.services.sale_roundup_formatting_service import integer
from app.services.sale_store_policy import sale_store_display_name, validate_sale_snapshot_store

def generate_variants(
    session,
    experiment_id,
    article_url,
    *,
    wordpress_post_id,
    attachment_image_path=None,
    scheduled_at: datetime | None = None,
    paid_partnership: bool = True,
):
    exp=session.get(SaleExperiment,experiment_id)
    if not exp:
        raise ValueError("EXPERIMENT_NOT_FOUND")
    url=validate_article_url(article_url)
    if isinstance(wordpress_post_id,bool) or not isinstance(wordpress_post_id,int) or wordpress_post_id<=0:
        raise ValueError("WORDPRESS_DRAFT_ID_REQUIRED")
    if exp.wordpress_post_id and exp.wordpress_post_id!=wordpress_post_id:
        raise ValueError("WORDPRESS_DRAFT_ID_MISMATCH")
    snapshot=exp.snapshot
    campaign_store=validate_sale_snapshot_store(snapshot)
    store_display_name=sale_store_display_name(campaign_store)
    title=snapshot["title"][:38]
    maximum=max(integer(item["discount_percent"]) or 0 for item in snapshot["items"])
    maximum_points=max(integer(item.get("point_percent")) or 0 for item in snapshot["items"])
    end=min(utc(i["sale_end_at_utc"]) for i in snapshot["items"]).astimezone(timezone(timedelta(hours=9))).strftime("%m/%d %H:%M JSTまで")
    common=dict(discount_wording=f"対象作品 最大{maximum}%OFF",urgency=end,
                benefit=f"対象{len(snapshot['items'])}作品をまとめてチェック" + (f"／最大{maximum_points}%ポイント還元" if maximum_points else ""))
    choices=[
        dict(common,hook=f"{store_display_name}で{title}",cta="対象作品一覧はこちら",emoji_pattern="📚"),
        dict(common,hook=f"{store_display_name}で気になっていた作品をチェック",cta="セール詳細を見る",emoji_pattern=""),
        dict(common,hook=f"{store_display_name}で電子書籍セール開催中",cta="対象作品と価格を確認",emoji_pattern="👇"),
    ]
    fixed=load_contract()["output_contract"]["fixed_values"]
    output=[]
    draft_store = XPostDraftPersistenceService(
        session
    )
    for index,components in enumerate(choices,1):
        variant_id=digest([exp.id,index,components,url,wordpress_post_id])
        existing=session.get(SaleCopyVariant,variant_id)
        if existing:
            if attachment_image_path and existing.draft_request.get("attachment_candidate_image_path") != attachment_image_path:
                existing.draft_request=dict(existing.draft_request,attachment_candidate_image_path=attachment_image_path)

            existing_request = (
                existing.draft_request or {}
            )

            draft_store.save(
                XPostDraftSaveRequest(
                    source_type="sale",
                    source_id=variant_id,
                    generated_text=existing.text,
                    scheduled_at=scheduled_at,
                    paid_partnership=(
                        paid_partnership
                    ),
                    feedback_id=str(
                        existing_request.get(
                            "feedback_id"
                        )
                        or (
                            "sale-"
                            + variant_id
                        )
                    ),
                )
            )

            output.append(existing)
            continue
        parsed=urlsplit(url)
        query=[(k,v) for k,v in parse_qsl(parsed.query,keep_blank_values=True) if not k.startswith("utm_")]
        query.extend([("utm_source","x"),("utm_medium","social"),("utm_campaign",exp.id),("utm_content",variant_id)])
        tracked=urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(query),parsed.fragment))
        text="\n".join([components["emoji_pattern"]+components["hook"],components["discount_wording"],
                         components["urgency"],components["benefit"],components["cta"],tracked,"#PR"])
        if _x_weighted_length(text)>280:
            raise ValueError("X_WEIGHTED_LENGTH_EXCEEDED")
        request=dict(action="INITIALIZE",feedback_id="sale-"+variant_id,article_item_id=exp.campaign_id,
            wordpress_post_id=wordpress_post_id,template_id=f"sale-copy-v1-{index}",
            article_context=dict(title=snapshot["title"],article_url=tracked,wordpress_status="DRAFT",
                                 campaign_id=exp.campaign_id,experiment_id=exp.id),
            generated_text=text,wording_labels=list(components),experiment_id=exp.id,variant_id=variant_id,
            wording_components=components)
        if attachment_image_path:
            request["attachment_candidate_image_path"] = attachment_image_path
        result=XDraftResult(feedback_id=request["feedback_id"],ebook_item_id=exp.campaign_id,
            wordpress_draft_id=wordpress_post_id,template_id=request["template_id"],
            generated_text=text,character_count=len(text),contains_pr=True,selected_url=tracked,
            record_stage=fixed["record_stage"],x_status=fixed["x_status"],review_status=fixed["review_status"],
            initialize_request=request)
        variant=SaleCopyVariant(id=variant_id,experiment_id=exp.id,components=components,text=text,
            draft_request=dict(result.initialize_request,record_stage=result.record_stage,
                               x_status=result.x_status,review_status=result.review_status),
            review_status="PENDING")
        session.add(variant)

        draft_store.save(
            XPostDraftSaveRequest(
                source_type="sale",
                source_id=variant_id,
                generated_text=text,
                scheduled_at=scheduled_at,
                paid_partnership=(
                    paid_partnership
                ),
                feedback_id=(
                    result.feedback_id
                ),
            )
        )

        output.append(variant)
    session.flush()
    return output
