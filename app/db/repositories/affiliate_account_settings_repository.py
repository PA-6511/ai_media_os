from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


SUPPORTED_SERVICES = ("amazon", "rakuten_kobo", "dmm")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class AffiliateAccountSetting:
    service_name: str
    affiliate_id: str | None
    url_template: str | None
    enabled: bool
    updated_at: str
    updated_by: str


class AffiliateAccountSettingsRepository:
    """Persist affiliate IDs without logging their values.

    The column-aware SQL keeps read compatibility with the legacy four-column
    SQLite table until the additive Alembic migration is applied.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def _column_names(self) -> set[str]:
        return {
            column["name"]
            for column in inspect(self.session.connection()).get_columns(
                "affiliate_account_settings"
            )
        }

    def _history_available(self) -> bool:
        return inspect(self.session.connection()).has_table(
            "affiliate_setting_history"
        )

    def list_all(self) -> list[AffiliateAccountSetting]:
        return [
            self._row_to_setting(row)
            for row in self.session.execute(
                text(
                    f"SELECT {self._select_columns()} "
                    "FROM affiliate_account_settings ORDER BY service_name"
                )
            )
        ]

    def get(self, *, service_name: str) -> AffiliateAccountSetting | None:
        normalized = self._normalize_service_name(service_name)
        row = self.session.execute(
            text(
                f"SELECT {self._select_columns()} "
                "FROM affiliate_account_settings "
                "WHERE service_name = :service_name"
            ),
            {"service_name": normalized},
        ).one_or_none()
        return None if row is None else self._row_to_setting(row)

    def save(
        self,
        *,
        service_name: str,
        affiliate_id: str = "",
        url_template: str = "",
        enabled: bool = True,
        changed_by: str = "human:local_gui",
        change_reason: str = "affiliate settings web edit",
    ) -> AffiliateAccountSetting:
        normalized = self._normalize_service_name(service_name)
        current = self.get(service_name=normalized)
        normalized_id = affiliate_id.strip()
        normalized_template = url_template.strip()
        desired_id = normalized_id or (current.affiliate_id if current else None)
        desired_template = normalized_template or (
            current.url_template if current else None
        )
        if not desired_id and not desired_template:
            raise ValueError("affiliate_id or url_template is required")
        return self._write(
            service_name=normalized,
            affiliate_id=desired_id,
            url_template=desired_template,
            enabled=bool(enabled),
            changed_by=changed_by,
            change_reason=change_reason,
            current=current,
        )

    def unregister(
        self,
        *,
        service_name: str,
        changed_by: str = "human:local_gui",
        change_reason: str = "explicit affiliate setting deletion",
    ) -> AffiliateAccountSetting:
        normalized = self._normalize_service_name(service_name)
        return self._write(
            service_name=normalized,
            affiliate_id=None,
            url_template=None,
            enabled=False,
            changed_by=changed_by,
            change_reason=change_reason,
            current=self.get(service_name=normalized),
        )

    def _write(
        self,
        *,
        service_name: str,
        affiliate_id: str | None,
        url_template: str | None,
        enabled: bool,
        changed_by: str,
        change_reason: str,
        current: AffiliateAccountSetting | None,
    ) -> AffiliateAccountSetting:
        columns = self._column_names()
        now = utc_now_iso()
        insert_columns = ["service_name", "affiliate_id", "enabled", "updated_at"]
        values = [":service_name", ":affiliate_id", ":enabled", ":updated_at"]
        updates = [
            "affiliate_id = excluded.affiliate_id",
            "enabled = excluded.enabled",
            "updated_at = excluded.updated_at",
        ]
        parameters: dict[str, object] = {
            "service_name": service_name,
            "affiliate_id": affiliate_id,
            "enabled": int(enabled),
            "updated_at": now,
        }
        if "url_template" in columns:
            insert_columns.append("url_template")
            values.append(":url_template")
            updates.append("url_template = excluded.url_template")
            parameters["url_template"] = url_template
        if "updated_by" in columns:
            insert_columns.append("updated_by")
            values.append(":updated_by")
            updates.append("updated_by = excluded.updated_by")
            parameters["updated_by"] = changed_by

        self.session.execute(
            text(
                "INSERT INTO affiliate_account_settings ("
                + ", ".join(insert_columns)
                + ") VALUES ("
                + ", ".join(values)
                + ") ON CONFLICT(service_name) DO UPDATE SET "
                + ", ".join(updates)
            ),
            parameters,
        )

        if self._history_available():
            before = current or AffiliateAccountSetting(
                service_name, None, None, False, "", ""
            )
            for field_name, before_value, after_value in (
                ("affiliate_id", before.affiliate_id, affiliate_id),
                ("url_template", before.url_template, url_template),
                ("enabled", str(before.enabled), str(enabled)),
            ):
                if before_value == after_value:
                    continue
                self.session.execute(
                    text(
                        "INSERT INTO affiliate_setting_history "
                        "(id, service_name, field_name, before_value, "
                        "after_value, change_reason, changed_at, changed_by) "
                        "VALUES (:id, :service_name, :field_name, :before_value, "
                        ":after_value, :change_reason, :changed_at, :changed_by)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "service_name": service_name,
                        "field_name": field_name,
                        "before_value": before_value,
                        "after_value": after_value,
                        "change_reason": change_reason,
                        "changed_at": now,
                        "changed_by": changed_by,
                    },
                )

        saved = self.get(service_name=service_name)
        if saved is None:
            raise RuntimeError("affiliate setting was not saved")
        return saved

    def _select_columns(self) -> str:
        columns = self._column_names()
        return ", ".join(
            (
                "service_name",
                "affiliate_id",
                "url_template" if "url_template" in columns else "NULL AS url_template",
                "enabled",
                "updated_at",
                "updated_by" if "updated_by" in columns else "'system' AS updated_by",
            )
        )

    @staticmethod
    def _row_to_setting(row: object) -> AffiliateAccountSetting:
        return AffiliateAccountSetting(
            service_name=str(row.service_name),
            affiliate_id=str(row.affiliate_id) if row.affiliate_id is not None else None,
            url_template=str(row.url_template) if row.url_template is not None else None,
            enabled=bool(row.enabled),
            updated_at=str(row.updated_at),
            updated_by=str(row.updated_by),
        )

    @staticmethod
    def _normalize_service_name(service_name: str) -> str:
        normalized = str(service_name or "").strip().lower()
        if normalized not in SUPPORTED_SERVICES:
            raise ValueError("unsupported service_name")
        return normalized
