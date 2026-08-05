from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
import re
from urllib.parse import quote, urlsplit

from sqlalchemy.orm import Session

from app.db.models import CatalogEditHistory, EbookItem
from app.db.repositories.affiliate_destination_profile_repository import (
    AffiliateDestinationProfileRepository,
)
from app.db.repositories.store_offer_affiliate_link_repository import (
    StoreOfferAffiliateLinkRepository,
)
from app.db.repositories.store_offer_repository import StoreOfferRepository
from app.services.affiliate_account_settings_service import (
    AffiliateAccountSettingsService,
)
from app.services.catalog_edit_service import CURRENCY_PATTERN, parse_price
from app.services.dmm_affiliate_html_parser import (
    DmmAffiliateHtmlParseError,
    parse_dmm_input,
)
from app.services.dmm_destination_affiliate_link_service import (
    DmmDestinationAffiliateLinkService,
)


class DmmManualOfferError(ValueError):
    pass


@dataclass(frozen=True)
class DmmDestinationLinkPreview:
    profile_id: str
    destination_key: str
    destination_type: str
    display_name: str
    configured: bool
    active: bool
    generation_available: bool
    affiliate_url: str = ""
    affiliate_id: str = ""
    channel: str = ""
    channel_id: str = ""


@dataclass(frozen=True)
class DmmManualOfferPreview:
    ebook_item_id: str
    store_item_id: str
    product_url: str
    affiliate_url: str
    price_amount: Decimal | None
    currency: str | None
    product_name: str = ""
    affiliate_id: str = ""
    product_group_id: str = ""
    service: str = "book"
    channel: str = ""
    channel_id: str = ""
    warnings: tuple[str, ...] = ()
    blocking_warnings: tuple[str, ...] = ()
    source_type: str = "manual_fields"
    verification_method: str = "MANUAL_WEB_EDIT"
    source_affiliate_url: str = ""
    matched_destination_key: str = ""
    matched_destination_type: str = ""
    matched_destination_name: str = ""
    destination_links: tuple[DmmDestinationLinkPreview, ...] = ()

    @property
    def registration_allowed(self) -> bool:
        return not self.blocking_warnings


@dataclass(frozen=True)
class DmmManualOfferResult:
    preview: DmmManualOfferPreview
    offer_id: str
    changed_fields: tuple[str, ...]
    unchanged: bool
    affiliate_link_ids: tuple[str, ...] = ()


def require_https(value: str, field_name: str) -> str:
    normalized = value.strip()
    parsed = urlsplit(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise DmmManualOfferError(f"{field_name} must be an https URL")
    return normalized


class DmmManualOfferService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def preview(
        self,
        *,
        ebook_item_id: str,
        product_url: str,
        content_id: str,
        price: str,
        currency: str,
        affiliate_mode: str,
        affiliate_url: str,
    ) -> DmmManualOfferPreview:
        if self.session.get(EbookItem, ebook_item_id) is None:
            raise DmmManualOfferError("item_not_found")
        normalized_product_url = require_https(product_url, "product_url")
        normalized_content_id = content_id.strip()
        amount = parse_price(price)
        normalized_currency = currency.strip().upper() or (
            "JPY" if amount is not None else ""
        )
        if amount is not None and not CURRENCY_PATTERN.fullmatch(normalized_currency):
            raise DmmManualOfferError("currency is invalid")

        if affiliate_mode == "direct":
            normalized_affiliate_url = require_https(
                affiliate_url, "affiliate_url"
            )
        elif affiliate_mode == "generated":
            effective = AffiliateAccountSettingsService(
                self.session
            ).get_effective(service_name="dmm")
            if not effective.enabled or not effective.affiliate_id:
                raise DmmManualOfferError("dmm_affiliate_id_not_configured")
            if not effective.url_template:
                raise DmmManualOfferError("dmm_url_template_not_configured")
            try:
                normalized_affiliate_url = effective.url_template.format(
                    affiliate_id=quote(effective.affiliate_id, safe=""),
                    product_url=quote(normalized_product_url, safe=""),
                    content_id=quote(normalized_content_id, safe=""),
                )
            except (KeyError, ValueError) as exc:
                raise DmmManualOfferError("dmm_url_template_invalid") from exc
            normalized_affiliate_url = require_https(
                normalized_affiliate_url, "generated affiliate_url"
            )
        else:
            raise DmmManualOfferError("affiliate_mode is invalid")

        return DmmManualOfferPreview(
            ebook_item_id=ebook_item_id,
            store_item_id=normalized_content_id or normalized_product_url,
            product_url=normalized_product_url,
            affiliate_url=normalized_affiliate_url,
            price_amount=amount,
            currency=normalized_currency or None,
        )

    def preview_input(
        self,
        *,
        ebook_item_id: str,
        dmm_input: str,
        price: str = "",
        currency: str = "JPY",
    ) -> DmmManualOfferPreview:
        item = self.session.get(EbookItem, ebook_item_id)
        if item is None:
            raise DmmManualOfferError("item_not_found")
        try:
            parsed = parse_dmm_input(dmm_input)
        except (DmmAffiliateHtmlParseError, ValueError) as exc:
            raise DmmManualOfferError(str(exc)) from exc

        amount = parse_price(price)
        normalized_currency = currency.strip().upper() or (
            "JPY" if amount is not None else ""
        )
        if amount is not None and not CURRENCY_PATTERN.fullmatch(
            normalized_currency
        ):
            raise DmmManualOfferError("currency is invalid")

        warnings = list(parsed.warnings)
        blocking_warnings: list[str] = []
        profile_repository = AffiliateDestinationProfileRepository(
            self.session
        )
        all_profiles = profile_repository.list_for_provider(provider="dmm")
        generator = DmmDestinationAffiliateLinkService(self.session)
        generated_by_profile_id = {
            link.profile_id: link
            for link in generator.generate_for_active_profiles(
                product_url=parsed.product_url
            )
        }
        profile_by_key = {
            profile.destination_key: profile for profile in all_profiles
        }
        ordered_profiles = []
        for destination_key in ("blog_main", "x_main"):
            profile = profile_by_key.get(destination_key)
            if profile is not None:
                ordered_profiles.append(profile)
        ordered_profiles.extend(
            profile
            for profile in all_profiles
            if profile.destination_key not in {"blog_main", "x_main"}
        )
        destination_links: list[DmmDestinationLinkPreview] = []
        fixed_destinations = (
            ("blog_main", "wordpress", "メインブログ"),
            ("x_main", "x", "公式X"),
        )
        for destination_key, destination_type, display_name in fixed_destinations:
            if destination_key not in profile_by_key:
                destination_links.append(
                    DmmDestinationLinkPreview(
                        profile_id="",
                        destination_key=destination_key,
                        destination_type=destination_type,
                        display_name=display_name,
                        configured=False,
                        active=False,
                        generation_available=False,
                    )
                )
        for profile in ordered_profiles:
            generated = generated_by_profile_id.get(profile.id)
            destination_links.append(
                DmmDestinationLinkPreview(
                    profile_id=profile.id,
                    destination_key=profile.destination_key,
                    destination_type=profile.destination_type,
                    display_name=profile.display_name,
                    configured=True,
                    active=profile.is_active,
                    generation_available=generated is not None,
                    affiliate_url=(
                        generated.affiliate_url if generated is not None else ""
                    ),
                    affiliate_id=(
                        generated.affiliate_id if generated is not None else ""
                    ),
                    channel=generated.channel if generated is not None else "",
                    channel_id=(
                        generated.channel_id if generated is not None else ""
                    ),
                )
            )
        destination_links.sort(
            key=lambda link: (
                {"blog_main": 0, "x_main": 1}.get(
                    link.destination_key, 2
                ),
                link.destination_key,
            )
        )

        matched_profile = None

        if parsed.source_type == "affiliate_html":
            matches = profile_repository.find_by_affiliate_id(
                provider="dmm", affiliate_id=parsed.affiliate_id
            )
            if not matches:
                warnings.append("affiliate_profile_not_found")
                blocking_warnings.append("affiliate_profile_not_found")
            elif len(matches) > 1:
                warnings.append("affiliate_profile_ambiguous")
                blocking_warnings.append("affiliate_profile_ambiguous")
            elif not matches[0].is_active:
                warnings.append("affiliate_profile_inactive")
                blocking_warnings.append("affiliate_profile_inactive")
            else:
                matched_profile = matches[0]

            if not self._titles_are_compatible(
                parsed.product_name,
                item.title,
                item.volume_label,
            ):
                warning = (
                    "product_name_missing"
                    if not parsed.product_name
                    else "title_mismatch"
                )
                warnings.append(warning)
                blocking_warnings.append(warning)
        else:
            if not generated_by_profile_id:
                warnings.append("dmm_destination_profile_not_configured")
                blocking_warnings.append(
                    "dmm_destination_profile_not_configured"
                )

        blog_link = next(
            (
                link
                for link in destination_links
                if link.destination_key == "blog_main"
                and link.destination_type == "wordpress"
                and link.generation_available
            ),
            None,
        )
        legacy_blog_url = blog_link.affiliate_url if blog_link else ""
        if (
            parsed.source_type == "affiliate_html"
            and matched_profile is not None
            and matched_profile.destination_key == "blog_main"
            and matched_profile.destination_type == "wordpress"
        ):
            legacy_blog_url = parsed.affiliate_url

        return DmmManualOfferPreview(
            ebook_item_id=ebook_item_id,
            store_item_id=parsed.product_id,
            product_url=parsed.product_url,
            affiliate_url=legacy_blog_url,
            price_amount=amount,
            currency=normalized_currency or None,
            product_name=parsed.product_name,
            affiliate_id=parsed.affiliate_id,
            product_group_id=parsed.product_group_id,
            service=parsed.service,
            channel=parsed.channel,
            channel_id=parsed.channel_id,
            warnings=tuple(dict.fromkeys(warnings)),
            blocking_warnings=tuple(dict.fromkeys(blocking_warnings)),
            source_type=parsed.source_type,
            verification_method="MANUAL_DMM_HTML_PARSE",
            source_affiliate_url=parsed.affiliate_url,
            matched_destination_key=(
                matched_profile.destination_key if matched_profile else ""
            ),
            matched_destination_type=(
                matched_profile.destination_type if matched_profile else ""
            ),
            matched_destination_name=(
                matched_profile.display_name if matched_profile else ""
            ),
            destination_links=tuple(destination_links),
        )

    @staticmethod
    def _titles_are_compatible(
        product_name: str,
        item_title: str,
        volume_label: str | None,
    ) -> bool:
        def normalize(value: str) -> str:
            return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).casefold()

        product = normalize(product_name)
        candidates = [normalize(item_title)]
        if volume_label:
            candidates.append(normalize(f"{item_title}{volume_label}"))
        for candidate in candidates:
            if not product or not candidate:
                continue
            if product in candidate or candidate in product:
                return True
            if SequenceMatcher(None, product, candidate).ratio() >= 0.55:
                return True
        return False

    def save(
        self,
        *,
        preview: DmmManualOfferPreview,
        confirmed: bool,
        reason: str = "DMM manual offer registration",
        changed_by: str = "human:local_gui",
    ) -> DmmManualOfferResult:
        if not confirmed:
            raise DmmManualOfferError("confirmation is required")
        if not preview.registration_allowed:
            raise DmmManualOfferError("registration_blocked_by_warning")
        item = self.session.get(EbookItem, preview.ebook_item_id)
        if item is None:
            raise DmmManualOfferError("item_not_found")
        offer, changes = StoreOfferRepository(
            self.session
        ).upsert_manual_offer(
            ebook_item_id=item.id,
            store_name="dmm",
            store_item_id=preview.store_item_id,
            product_url=preview.product_url,
            affiliate_url=preview.affiliate_url,
            price_amount=preview.price_amount,
            currency=preview.currency,
            verification_method=preview.verification_method,
        )
        audit_changes = {
            f"dmm.{field_name}": values
            for field_name, values in changes.items()
        }
        affiliate_link_ids: list[str] = []
        link_repository = StoreOfferAffiliateLinkRepository(self.session)
        generated_destinations = DmmDestinationAffiliateLinkService(
            self.session
        ).generate_for_active_profiles(
            product_url=offer.product_url or preview.product_url
        )
        for destination in generated_destinations:
            link, link_changes = link_repository.upsert(
                store_offer_id=offer.id,
                profile_id=destination.profile_id,
                affiliate_url=destination.affiliate_url,
                generation_method="DMM_DESTINATION_PROFILE",
                source_affiliate_id=destination.affiliate_id,
            )
            affiliate_link_ids.append(link.id)
            for field_name, values in link_changes.items():
                if field_name == "source_affiliate_id":
                    continue
                audit_changes[
                    "dmm.destination."
                    f"{destination.destination_key}.{field_name}"
                ] = values
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
                        change_reason=reason,
                        changed_by=changed_by,
                    )
                )
            self.session.flush()
        return DmmManualOfferResult(
            preview=preview,
            offer_id=offer.id,
            changed_fields=tuple(audit_changes),
            unchanged=not audit_changes,
            affiliate_link_ids=tuple(affiliate_link_ids),
        )
