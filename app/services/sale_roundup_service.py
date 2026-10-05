"""Projection import and sale validation, independent of research and publishing."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from sqlalchemy import select, delete
from app.db.models.ebook_tag import EbookTag, EbookItemTag
from app.db.models.sale_roundup import SaleCampaign, SaleOffer, SaleExperiment
from app.services.sale_store_policy import (
    SaleStorePolicyError,
    normalize_sale_store,
    require_canonical_sale_store,
    sale_store_gate_reasons,
    validate_sale_affiliate_url,
    validate_sale_cover_url,
    validate_sale_product_url,
    validate_sale_snapshot_store,
)
from app.services.sale_wordpress_sync_planner import item_block_reasons, render_group_html, ready_item_model

def utc(value):
    if isinstance(value,str):
        value=datetime.fromisoformat(value.replace("Z","+00:00"))
    if not isinstance(value,datetime):
        raise ValueError("DATETIME_REQUIRED")
    # Existing sale projection serializes stored UTC datetimes without an offset.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def _json_safe(value):
    if isinstance(value,float) and not math.isfinite(value):
        return None
    if isinstance(value,dict):
        return {k:_json_safe(v) for k,v in value.items()}
    if isinstance(value,list):
        return [_json_safe(v) for v in value]
    return value

SALE_SCOPE_APPROVED_TAG_KEYS = frozenset({
    "shonen_manga",
    "seinen_manga",
    "shojo_manga",
    "josei_manga",
    "bl",
    "tl",
    "light_novel",
})


def sale_scope_reasons(session, item):
    """
    Sale Roundup publication scope only.

    Sale eligibility and site-content scope are deliberately separate.
    Unknown/unreviewed classification is retained as evidence but must not
    enter automatic WordPress/X draft generation.
    """
    item_type = str(item.get("item_type") or "").strip().lower()

    if item_type in {"tankobon", "light_novel"}:
        return []

    ebook_item_id = str(item.get("ebook_item_id") or "").strip()
    if not ebook_item_id:
        return ["SALE_SCOPE_REVIEW_REQUIRED"]

    approved_target_tag = session.scalar(
        select(EbookItemTag.id)
        .join(EbookTag, EbookTag.id == EbookItemTag.tag_id)
        .where(
            EbookItemTag.ebook_item_id == ebook_item_id,
            EbookItemTag.review_status == "APPROVED",
            EbookTag.is_active.is_(True),
            EbookTag.tag_key.in_(SALE_SCOPE_APPROVED_TAG_KEYS),
        )
        .limit(1)
    )

    if approved_target_tag is not None:
        return []

    return ["SALE_SCOPE_REVIEW_REQUIRED"]


def offer_reasons(item, starts, ends, now):
    try:
        reasons=item_block_reasons(item)
    except (ValueError,TypeError):
        reasons=["INVALID_URL"]
    if item.get("campaign_store") in {"rakuten_kobo","dmm","amazon"}:
        reasons=[reason for reason in reasons if reason not in {
            "STORE_NOT_SUPPORTED",
            "PRODUCT_URL_INVALID",
            "AFFILIATE_URL_NOT_READY",
            "COVER_IMAGE_NOT_READY",
        }]
    for name in ("sale_price","discount_percent"):
        value=item.get(name)
        if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):
            reasons.append(name.upper()+"_INVALID")
    price=item.get("sale_price")
    discount=item.get("discount_percent")
    if isinstance(price,(int,float)) and price<=0:
        reasons.append("SALE_PRICE_INVALID")
    if isinstance(discount,(int,float)) and not 0<discount<=100:
        reasons.append("DISCOUNT_INVALID")
    normal=item.get("normal_price_evidence_only")
    if isinstance(normal,(int,float)) and not isinstance(normal,bool):
        if not math.isfinite(normal) or normal<=0 or not isinstance(price,(int,float)) or abs((1-price/normal)*100-float(discount or 0))>1:
            reasons.append("DISCOUNT_PRICE_MISMATCH")
    try:
        start=utc(item.get("sale_start_at_utc") or starts)
        end=utc(item["sale_end_at_utc"])
        if not start<=now<end or end>ends or start<starts:
            reasons.append("SALE_PERIOD_INVALID_OR_EXPIRED")
    except (ValueError,TypeError,KeyError):
        reasons.append("SALE_PERIOD_INVALID")
    source=str(item.get("source_row_sha256") or "")
    if len(source)!=64 or any(c not in "0123456789abcdef" for c in source):
        reasons.append("SOURCE_SHA_INVALID")
    return sorted(set(reasons))

MIN_DISTINCT_SERIES_FOR_ROUNDUP = 5


def _sale_url_reasons(campaign_store, item):
    if campaign_store is None:
        return []
    try:
        validate_sale_product_url(campaign_store, item.get("product_url"))
        validate_sale_affiliate_url(
            campaign_store,
            item.get("affiliate_url"),
            item.get("affiliate_evidence"),
        )
        validate_sale_cover_url(campaign_store, item.get("cover_image_url"))
    except SaleStorePolicyError as exc:
        reason = str(exc)
        if reason == "SALE_STORE_REVIEW_REQUIRED":
            return [reason]
        return ["SALE_URL_POLICY_VIOLATION"]
    return []


def _store_diagnostics(campaign_store, evaluated_offers, eligible_offers):
    matched = [entry for entry in evaluated_offers if entry["store_matched"]]
    scope_allowed = [entry for entry in matched if entry["scope_allowed"]]
    eligible = [
        entry
        for entry in eligible_offers
        if entry["store_matched"] and not entry["reasons"]
    ]
    series = {
        str(entry["data"].get("series_name") or "").strip().casefold()
        for entry in eligible
        if str(entry["data"].get("series_name") or "").strip()
    }
    distinct_series_count = len(series)
    return {
        "CAMPAIGN_STORE": campaign_store or "SALE_STORE_REVIEW_REQUIRED",
        "TOTAL_STORE_MATCHED_ITEMS": len(matched),
        "STORE_MISMATCH_COUNT": sum(
            "SALE_STORE_MISMATCH" in entry["reasons"]
            for entry in evaluated_offers
        ),
        "SCOPE_ALLOWED_ITEM_COUNT": len(scope_allowed),
        "DISTINCT_SERIES_COUNT": distinct_series_count,
        "MIN_DISTINCT_SERIES_FOR_ROUNDUP": MIN_DISTINCT_SERIES_FOR_ROUNDUP,
        "SERIES_THRESHOLD_STATUS": (
            "MET"
            if distinct_series_count >= MIN_DISTINCT_SERIES_FOR_ROUNDUP
            else "BELOW_THRESHOLD"
        ),
        "SALE_ROUNDUP_INSUFFICIENT_SERIES": "DIAGNOSTIC_ONLY",
        "AUTO_REGEN_BLOCKED": (
            "YES" if campaign_store is None or not eligible else "NO"
        ),
    }


def _prepare_projection_import(session,document,*,now=None):
    now=utc(now or datetime.now(timezone.utc))
    if document.get("operation")!="SALE_PUBLICATION_PROJECTION_V1" or document.get("projection_ready_for_wordpress_dry_run") is not True:
        raise ValueError("PROJECTION_NOT_READY")
    generated=utc(document.get("generated_at_utc"))
    if not now-timedelta(hours=24)<=generated<=now+timedelta(minutes=5):
        raise ValueError("PROJECTION_STALE")
    groups=document.get("campaign_groups")
    if not isinstance(groups,list) or len(groups)>1000:
        raise ValueError("CAMPAIGN_GROUPS_INVALID")
    prepared={}
    diagnostics={}
    for group in groups:
        cid=str(group.get("campaign_id") or "").strip()
        title=str(group.get("campaign_title") or "").strip()
        if not cid or len(cid)>128 or not title or len(title)>500:
            raise ValueError("CAMPAIGN_ID_OR_TITLE_INVALID")
        starts,ends=utc(group.get("official_start_at_utc")),utc(group.get("official_end_at_utc"))
        if not starts<=now<ends:
            raise ValueError("CAMPAIGN_NOT_ACTIVE")
        items=group.get("items")
        if not isinstance(items,list) or len(items)>5000:
            raise ValueError("OFFERS_INVALID")
        raw_campaign_store=group.get("campaign_store")
        campaign_store=normalize_sale_store(raw_campaign_store)
        unique={}
        evaluated=[]
        for item in items:
            if not isinstance(item,dict):
                raise ValueError("OFFER_INVALID")
            data=_json_safe(item)
            canonical_offer_store=normalize_sale_store(item.get("store_name"))
            if campaign_store is None:
                data.pop("campaign_store",None)
            else:
                data["campaign_store"]=campaign_store
            data["store_name"]=canonical_offer_store
            gate_reasons=sale_store_gate_reasons(raw_campaign_store,item)
            scope_reasons=sale_scope_reasons(session,data)
            reasons=sorted(set(
                offer_reasons(data,starts,ends,now)
                + scope_reasons
                + gate_reasons
                + (_sale_url_reasons(campaign_store,data) if not gate_reasons else [])
            ))
            entry={
                "data":data,
                "reasons":reasons,
                "store_matched":not gate_reasons,
                "scope_allowed":not scope_reasons,
            }
            evaluated.append(entry)
            key=digest([cid,data.get("store_name"),data.get("store_item_id")])
            if key in unique:
                previous=unique[key]
                reasons=sorted(set(reasons+previous["reasons"]+(["CONFLICTING_DUPLICATE"] if previous["data"]!=data else [])))
                entry["reasons"]=reasons
            unique[key]=entry
        normalized=dict(title=title,starts_at=starts.isoformat(),ends_at=ends.isoformat(),
                        offers=sorted(
                            (key,(value["data"],value["reasons"]))
                            for key,value in unique.items()
                        ))
        if cid in prepared and prepared[cid]!=normalized:
            raise ValueError("CONFLICTING_CAMPAIGN")
        prepared[cid]=normalized
        diagnostics[cid]=_store_diagnostics(
            campaign_store,
            evaluated,
            list(unique.values()),
        )
    return prepared,diagnostics,generated,now


def projection_import_diagnostics(session,document,*,now=None):
    with session.no_autoflush:
        _,diagnostics,_,_=_prepare_projection_import(session,document,now=now)
    return diagnostics


def import_projection(session,document,*,now=None):
    prepared,_,generated,now=_prepare_projection_import(session,document,now=now)
    for cid,group in prepared.items():
        campaign=session.get(SaleCampaign,cid)
        if campaign and utc(campaign.source_generated_at)>generated:
            raise ValueError("OLDER_PROJECTION")
        if campaign is None:
            campaign=SaleCampaign(id=cid)
            session.add(campaign)
        campaign.title=group["title"]
        campaign.starts_at=group["starts_at"]
        campaign.ends_at=group["ends_at"]
        campaign.snapshot_hash=digest(group)
        campaign.imported_at=now.isoformat()
        campaign.source_generated_at=generated.isoformat()
        session.flush()
        session.execute(delete(SaleOffer).where(SaleOffer.campaign_id==cid))
        for key,(data,reasons) in group["offers"]:
            session.add(SaleOffer(id=key,campaign_id=cid,ebook_item_id=str(data.get("ebook_item_id") or ""),
                                  data=data,block_reasons=reasons))
    session.flush()
    return sorted(prepared)

def current_snapshot(session,campaign_id,*,now=None):
    now=utc(now or datetime.now(timezone.utc))
    campaign=session.get(SaleCampaign,campaign_id)
    if not campaign:
        raise ValueError("CAMPAIGN_NOT_FOUND")
    starts,ends=utc(campaign.starts_at),utc(campaign.ends_at)
    if not starts<=now<ends:
        raise ValueError("CAMPAIGN_NOT_ACTIVE")
    if now-utc(campaign.source_generated_at)>timedelta(hours=24):
        raise ValueError("PROJECTION_STALE")
    offers=session.scalars(select(SaleOffer).where(SaleOffer.campaign_id==campaign_id).order_by(SaleOffer.id)).all()
    valid=[o.data for o in offers if not o.block_reasons and not offer_reasons(o.data,starts,ends,now)]
    if not valid:
        raise ValueError("NO_VALID_OFFERS")
    campaign_stores={
        require_canonical_sale_store(item.get("campaign_store"))
        for item in valid
    }
    if len(campaign_stores)!=1:
        raise SaleStorePolicyError("SALE_STORE_MISMATCH")
    snapshot=dict(campaign_id=campaign.id,campaign_store=campaign_stores.pop(),
                  title=campaign.title,starts_at=campaign.starts_at,ends_at=campaign.ends_at,
                  source_hash=campaign.snapshot_hash,items=valid)
    validation_snapshot = snapshot
    if snapshot["campaign_store"] == "amazon":
        validation_snapshot = dict(
            snapshot,
            items=[
                dict(
                    item,
                    affiliate_url=(
                        item.get("affiliate_url") or item.get("product_url")
                    ),
                )
                for item in snapshot["items"]
            ],
        )
    validate_sale_snapshot_store(validation_snapshot)
    return snapshot

def prepare_roundup(session,campaign_id,*,now=None):
    snapshot=current_snapshot(session,campaign_id,now=now)
    identity=digest(snapshot)
    experiment=session.get(SaleExperiment,identity)
    if experiment:
        return experiment
    marker="<!-- sale-roundup:"+identity+" -->"
    wordpress_snapshot=dict(snapshot,items=[ready_item_model(i) for i in snapshot["items"]])
    content=render_group_html(snapshot=wordpress_snapshot)
    payload=dict(title=snapshot["title"],slug="sale-roundup-"+digest(campaign_id)[:32],status="draft",
                 content=marker+"\n<p>この記事には広告・アフィリエイトリンクが含まれます。価格・期間は購入時にご確認ください。</p>\n"+content)
    experiment=SaleExperiment(id=identity,campaign_id=campaign_id,snapshot_hash=identity,
                             snapshot=snapshot,payload=payload,wordpress_state="PREPARED")
    session.add(experiment)
    session.flush()
    return experiment


def render_legacy_3417_wordpress_html(
    *,
    post_id,
    campaign_id,
    experiment_id,
    existing_snapshot,
    existing_snapshot_hash,
    marker,
    featured_media_id,
    campaign_store,
    provenance,
):
    """Render the fixed legacy snapshot through an in-memory store context."""
    from app.services.sale_legacy_3417_compatibility import (
        validate_legacy_3417_store_context,
    )

    context = validate_legacy_3417_store_context(
        post_id=post_id,
        campaign_id=campaign_id,
        experiment_id=experiment_id,
        existing_snapshot=existing_snapshot,
        existing_snapshot_hash=existing_snapshot_hash,
        marker=marker,
        featured_media_id=featured_media_id,
        campaign_store=campaign_store,
        provenance=provenance,
    )
    temporary_render_snapshot = dict(existing_snapshot)
    temporary_render_snapshot["campaign_store"] = context.campaign_store
    return render_group_html(snapshot=temporary_render_snapshot)

def require_current_experiment(session,experiment,*,now=None):
    if digest(current_snapshot(session,experiment.campaign_id,now=now))!=experiment.snapshot_hash:
        raise ValueError("STALE_EXPERIMENT_REGENERATE")
