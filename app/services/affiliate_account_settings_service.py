from __future__ import annotations

from dataclasses import dataclass
import os
import re

from sqlalchemy.orm import Session

from app.db.repositories.affiliate_account_settings_repository import (
    AffiliateAccountSetting,
    AffiliateAccountSettingsRepository,
)


SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:@/+\-=]{1,255}$")
ENVIRONMENT_KEYS = {
    "amazon": ("AMAZON_TRACKING_ID",),
    "dmm": ("DMM_AFFILIATE_ID",),
    "rakuten_kobo": ("RAKUTEN_AFFILIATE_ID",),
}


@dataclass(frozen=True)
class AffiliateAccountSettingView:
    service_name: str
    masked_affiliate_id: str
    configured: bool
    enabled: bool
    updated_at: str
    source: str
    url_template_configured: bool


@dataclass(frozen=True)
class EffectiveAffiliateSetting:
    service_name: str
    affiliate_id: str | None
    url_template: str | None
    enabled: bool
    source: str


class AffiliateAccountSettingsService:
    """Resolve environment-over-database settings for the local GUI."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AffiliateAccountSettingsRepository(session)

    def list_settings(self) -> list[AffiliateAccountSettingView]:
        by_service = {
            setting.service_name: setting
            for setting in self.repository.list_all()
        }
        return [
            self._to_view(service_name, by_service.get(service_name))
            for service_name in ("amazon", "dmm")
        ]

    def get_effective(self, *, service_name: str) -> EffectiveAffiliateSetting:
        database_setting = self.repository.get(service_name=service_name)
        for environment_key in ENVIRONMENT_KEYS.get(service_name, ()):
            value = os.getenv(environment_key, "").strip()
            if value:
                return EffectiveAffiliateSetting(
                    service_name=service_name,
                    affiliate_id=value,
                    url_template=(
                        os.getenv("DMM_AFFILIATE_URL_TEMPLATE", "").strip()
                        or (database_setting.url_template if database_setting else None)
                    ),
                    enabled=True,
                    source=f"environment:{environment_key}",
                )
        return EffectiveAffiliateSetting(
            service_name=service_name,
            affiliate_id=database_setting.affiliate_id if database_setting else None,
            url_template=(
                os.getenv("DMM_AFFILIATE_URL_TEMPLATE", "").strip()
                or (database_setting.url_template if database_setting else None)
            ),
            enabled=bool(database_setting and database_setting.enabled),
            source=(
                "environment:DMM_AFFILIATE_URL_TEMPLATE"
                if service_name == "dmm"
                and os.getenv("DMM_AFFILIATE_URL_TEMPLATE", "").strip()
                else "database"
            ),
        )

    def get_affiliate_id(self, *, service_name: str) -> str | None:
        effective = self.get_effective(service_name=service_name)
        return effective.affiliate_id if effective.enabled else None

    def register(
        self,
        *,
        service_name: str,
        affiliate_id: str = "",
        url_template: str = "",
        enabled: bool = True,
        changed_by: str = "human:local_gui",
    ) -> AffiliateAccountSettingView:
        normalized_id = affiliate_id.strip()
        if normalized_id and not SAFE_ID_PATTERN.fullmatch(normalized_id):
            raise ValueError("affiliate ID contains unsupported characters")
        if len(url_template.strip()) > 2000:
            raise ValueError("URL template is too long")
        if url_template.strip() and not url_template.strip().startswith("https://"):
            raise ValueError("URL template must use https")
        setting = self.repository.save(
            service_name=service_name,
            affiliate_id=normalized_id,
            url_template=url_template,
            enabled=enabled,
            changed_by=changed_by,
        )
        self.session.commit()
        return self._to_view(service_name, setting)

    def unregister(
        self,
        *,
        service_name: str,
        changed_by: str = "human:local_gui",
    ) -> AffiliateAccountSettingView:
        setting = self.repository.unregister(
            service_name=service_name,
            changed_by=changed_by,
        )
        self.session.commit()
        return self._to_view(service_name, setting)

    @staticmethod
    def mask_affiliate_id(value: str | None) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            return "未登録"
        if len(normalized) <= 4:
            return "*" * len(normalized)
        if len(normalized) <= 8:
            return normalized[:2] + ("*" * (len(normalized) - 4)) + normalized[-2:]
        return normalized[:3] + ("*" * (len(normalized) - 6)) + normalized[-3:]

    def _to_view(
        self,
        service_name: str,
        database_setting: AffiliateAccountSetting | None,
    ) -> AffiliateAccountSettingView:
        effective = self.get_effective(service_name=service_name)
        return AffiliateAccountSettingView(
            service_name=service_name,
            masked_affiliate_id=self.mask_affiliate_id(effective.affiliate_id),
            configured=bool(effective.affiliate_id),
            enabled=effective.enabled,
            updated_at=database_setting.updated_at if database_setting else "",
            source=effective.source,
            url_template_configured=bool(effective.url_template),
        )
