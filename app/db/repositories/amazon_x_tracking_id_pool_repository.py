from __future__ import annotations

from datetime import datetime, timezone
import re

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models.amazon_x_tracking_id_pool import (
    AmazonXTrackingIdPool,
)
from app.services.amazon_manual_link_service import (
    TRACKING_ID_PATTERN,
)


_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")

BLOCKED_SHARED_TRACKING_IDS = frozenset({
    "ktkr77-22",
    "watermelon2-22",
})


class AmazonXTrackingIdPoolError(ValueError):
    pass


class AmazonXTrackingIdPoolConflictError(
    AmazonXTrackingIdPoolError
):
    pass


def _tracking_id(value: object) -> str:
    normalized = str(value or "").strip()

    if not TRACKING_ID_PATTERN.fullmatch(normalized):
        raise AmazonXTrackingIdPoolError(
            "tracking_id_invalid"
        )

    return normalized


def validate_controlled_tracking_id(
    value: object,
) -> str:
    normalized = _tracking_id(
        value
    )

    if normalized in BLOCKED_SHARED_TRACKING_IDS:
        raise AmazonXTrackingIdPoolError(
            "shared_tracking_id_not_allowed"
        )

    return normalized


def _digest(
    value: object,
    *,
    field: str,
) -> str:
    normalized = str(value or "").strip()

    if not _SHA256_PATTERN.fullmatch(normalized):
        raise AmazonXTrackingIdPoolError(
            f"{field}_invalid"
        )

    return normalized


def _post_id(value: object) -> int:
    if isinstance(value, bool):
        raise AmazonXTrackingIdPoolError(
            "wordpress_post_id_invalid"
        )

    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise AmazonXTrackingIdPoolError(
            "wordpress_post_id_invalid"
        ) from exc

    if normalized <= 0:
        raise AmazonXTrackingIdPoolError(
            "wordpress_post_id_invalid"
        )

    return normalized


class AmazonXTrackingIdPoolRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def get_by_tracking_id(
        self,
        tracking_id: str,
    ) -> AmazonXTrackingIdPool | None:
        normalized = _tracking_id(
            tracking_id
        )

        return self.session.scalar(
            select(
                AmazonXTrackingIdPool
            ).where(
                AmazonXTrackingIdPool.tracking_id
                == normalized
            )
        )

    def get_by_variant_id(
        self,
        variant_id: str,
    ) -> AmazonXTrackingIdPool | None:
        normalized = _digest(
            variant_id,
            field="variant_id",
        )

        return self.session.scalar(
            select(
                AmazonXTrackingIdPool
            ).where(
                AmazonXTrackingIdPool.variant_id
                == normalized
            )
        )

    def list_available(
        self,
    ) -> list[AmazonXTrackingIdPool]:
        return list(
            self.session.scalars(
                select(
                    AmazonXTrackingIdPool
                )
                .where(
                    AmazonXTrackingIdPool.status
                    == "AVAILABLE",
                    AmazonXTrackingIdPool.tracking_id
                    .notin_(
                        BLOCKED_SHARED_TRACKING_IDS
                    ),
                )
                .order_by(
                    AmazonXTrackingIdPool.registered_at,
                    AmazonXTrackingIdPool.id,
                )
            )
        )

    def register_available(
        self,
        *,
        tracking_id: str,
    ) -> tuple[
        AmazonXTrackingIdPool,
        bool,
    ]:
        normalized = validate_controlled_tracking_id(
            tracking_id
        )

        existing = self.session.scalar(
            select(
                AmazonXTrackingIdPool
            ).where(
                AmazonXTrackingIdPool.tracking_id
                == normalized
            )
        )

        if existing is not None:
            if existing.status != "AVAILABLE":
                raise AmazonXTrackingIdPoolConflictError(
                    "tracking_id_already_consumed"
                )

            return existing, False

        row = AmazonXTrackingIdPool(
            tracking_id=normalized,
            status="AVAILABLE",
        )

        self.session.add(row)
        self.session.flush()

        return row, True

    def disable_available(
        self,
        *,
        tracking_id: str,
    ) -> AmazonXTrackingIdPool:
        row = self.get_by_tracking_id(
            tracking_id
        )

        if row is None:
            raise AmazonXTrackingIdPoolError(
                "tracking_id_not_found"
            )

        if row.status == "DISABLED":
            return row

        if row.status != "AVAILABLE":
            raise AmazonXTrackingIdPoolConflictError(
                "assigned_tracking_id_cannot_be_disabled"
            )

        row.status = "DISABLED"
        self.session.flush()

        return row

    def assign_next_available(
        self,
        *,
        experiment_id: str,
        variant_id: str,
        wordpress_post_id: int,
        now: datetime | None = None,
    ) -> tuple[
        AmazonXTrackingIdPool,
        bool,
    ]:
        normalized_experiment_id = _digest(
            experiment_id,
            field="experiment_id",
        )
        normalized_variant_id = _digest(
            variant_id,
            field="variant_id",
        )
        normalized_post_id = _post_id(
            wordpress_post_id
        )

        existing = self.session.scalar(
            select(
                AmazonXTrackingIdPool
            ).where(
                AmazonXTrackingIdPool.variant_id
                == normalized_variant_id
            )
        )

        if existing is not None:
            if (
                existing.status != "ASSIGNED"
                or existing.experiment_id
                != normalized_experiment_id
                or existing.wordpress_post_id
                != normalized_post_id
            ):
                raise AmazonXTrackingIdPoolConflictError(
                    "variant_assignment_conflict"
                )

            return existing, False

        candidate = self.session.scalar(
            select(
                AmazonXTrackingIdPool
            )
            .where(
                AmazonXTrackingIdPool.status
                == "AVAILABLE",
                AmazonXTrackingIdPool.tracking_id
                .notin_(
                    BLOCKED_SHARED_TRACKING_IDS
                ),
                AmazonXTrackingIdPool.experiment_id
                .is_(None),
                AmazonXTrackingIdPool.variant_id
                .is_(None),
                AmazonXTrackingIdPool.wordpress_post_id
                .is_(None),
                AmazonXTrackingIdPool.assigned_at
                .is_(None),
            )
            .order_by(
                AmazonXTrackingIdPool.registered_at,
                AmazonXTrackingIdPool.id,
            )
            .limit(1)
        )

        if candidate is None:
            raise AmazonXTrackingIdPoolError(
                "no_available_tracking_id"
            )

        assigned_at = (
            now
            if now is not None
            else datetime.now(timezone.utc)
        )

        result = self.session.execute(
            update(
                AmazonXTrackingIdPool
            )
            .where(
                AmazonXTrackingIdPool.id
                == candidate.id,
                AmazonXTrackingIdPool.status
                == "AVAILABLE",
                AmazonXTrackingIdPool.variant_id
                .is_(None),
            )
            .values(
                status="ASSIGNED",
                experiment_id=(
                    normalized_experiment_id
                ),
                variant_id=(
                    normalized_variant_id
                ),
                wordpress_post_id=(
                    normalized_post_id
                ),
                assigned_at=assigned_at,
            )
        )

        if result.rowcount != 1:
            raise AmazonXTrackingIdPoolConflictError(
                "assignment_conflict"
            )

        self.session.flush()
        self.session.refresh(candidate)

        return candidate, True
