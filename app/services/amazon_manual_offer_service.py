from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.ebook import StoreOffer
from app.db.models import CatalogEditHistory, EbookItem
from app.db.repositories.store_offer_repository import StoreOfferRepository
from app.services.amazon_manual_link_service import AmazonManualLinkService


@dataclass(frozen=True)
class AmazonManualOfferResult:
    ebook_item_id: str
    asin: str
    product_url: str
    affiliate_url: str
    offer_id: str
    unchanged: bool = False


class AmazonManualOfferService:
    """ASINからAmazonリンクを生成し、store_offersへ保存する。"""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.link_service = AmazonManualLinkService()
        self.offer_repository = StoreOfferRepository(session)

    def save(
        self,
        *,
        ebook_item_id: str,
        asin: str,
        tracking_id: str,
    ) -> AmazonManualOfferResult:
        link = self.link_service.generate(
            asin=asin,
            tracking_id=tracking_id,
        )

        item = self.session.get(EbookItem, ebook_item_id)
        if item is None:
            raise ValueError("item_not_found")
        offer, changes = self.offer_repository.upsert_manual_offer(
            ebook_item_id=ebook_item_id,
            store_name="amazon",
            store_item_id=link.asin,
            product_url=link.product_url,
            affiliate_url=link.affiliate_url,
        )

        audit_changes = {
            f"amazon.{field_name}": values
            for field_name, values in changes.items()
        }
        if audit_changes:
            if item.review_status != "NOT_REVIEWED":
                audit_changes["review_status"] = (
                    item.review_status,
                    "NOT_REVIEWED",
                )
                item.review_status = "NOT_REVIEWED"
            if item.publish_ready:
                audit_changes["publish_ready"] = (True, False)
                item.publish_ready = False
            for field_name, (before, after) in audit_changes.items():
                self.session.add(
                    CatalogEditHistory(
                        ebook_item_id=item.id,
                        field_name=field_name,
                        before_value=None if before is None else str(before),
                        after_value=None if after is None else str(after),
                        change_reason="Amazon manual offer registration",
                        changed_by="human:local_gui",
                    )
                )
            self.session.flush()

        return AmazonManualOfferResult(
            ebook_item_id=ebook_item_id,
            asin=link.asin,
            product_url=link.product_url,
            affiliate_url=link.affiliate_url,
            offer_id=offer.id,
            unchanged=not audit_changes,
        )
