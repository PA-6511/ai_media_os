from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.db.models import AffiliateDestinationProfile
from app.db.repositories.affiliate_destination_profile_repository import (
    AffiliateDestinationProfileRepository,
)
from app.services.dmm_affiliate_html_parser import (
    DmmAffiliateHtmlParseError,
    parse_dmm_product_url,
)


class DmmDestinationAffiliateLinkError(ValueError):
    pass


@dataclass(frozen=True)
class DmmDestinationAffiliateLink:
    profile_id: str
    destination_key: str
    destination_type: str
    display_name: str
    affiliate_url: str
    affiliate_id: str
    channel: str
    channel_id: str


class DmmDestinationAffiliateLinkService:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def generate(
        self,
        *,
        product_url: str,
        profile: AffiliateDestinationProfile,
    ) -> DmmDestinationAffiliateLink | None:
        if profile.provider != "dmm":
            raise DmmDestinationAffiliateLinkError("provider_must_be_dmm")
        if not profile.is_active or not str(profile.affiliate_id or "").strip():
            return None
        try:
            parsed = parse_dmm_product_url(product_url)
        except DmmAffiliateHtmlParseError as exc:
            raise DmmDestinationAffiliateLinkError(str(exc)) from exc
        channel = str(profile.channel or "").strip() or "toolbar"
        channel_id = str(profile.channel_id or "").strip() or "text"
        query = urlencode(
            {
                "lurl": parsed.product_url,
                "af_id": profile.affiliate_id,
                "ch": channel,
                "ch_id": channel_id,
            }
        )
        return DmmDestinationAffiliateLink(
            profile_id=profile.id,
            destination_key=profile.destination_key,
            destination_type=profile.destination_type,
            display_name=profile.display_name,
            affiliate_url=f"https://al.dmm.com/?{query}",
            affiliate_id=profile.affiliate_id,
            channel=channel,
            channel_id=channel_id,
        )

    def generate_for_active_profiles(
        self, *, product_url: str
    ) -> tuple[DmmDestinationAffiliateLink, ...]:
        if self.session is None:
            raise DmmDestinationAffiliateLinkError("session_is_required")
        generated: list[DmmDestinationAffiliateLink] = []
        profiles = AffiliateDestinationProfileRepository(
            self.session
        ).list_active(provider="dmm")
        for profile in profiles:
            link = self.generate(product_url=product_url, profile=profile)
            if link is not None:
                generated.append(link)
        return tuple(generated)
