from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.amazon_x_tracking_id_pool import (
    AmazonXTrackingIdPool,
)
from app.db.repositories.amazon_x_tracking_id_pool_repository import (
    AmazonXTrackingIdPoolConflictError,
    AmazonXTrackingIdPoolError,
    AmazonXTrackingIdPoolRepository,
)


EXPERIMENT_A = "a" * 64
EXPERIMENT_B = "b" * 64
VARIANT_A = "c" * 64
VARIANT_B = "d" * 64


@pytest.fixture
def session():
    engine = create_engine("sqlite://")

    AmazonXTrackingIdPool.__table__.create(
        engine
    )

    with Session(
        engine,
        expire_on_commit=False,
    ) as session:
        yield session

    engine.dispose()


def test_register_available_is_idempotent(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    first, first_created = (
        repo.register_available(
            tracking_id="x-sale-01"
        )
    )

    second, second_created = (
        repo.register_available(
            tracking_id="x-sale-01"
        )
    )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert first.status == "AVAILABLE"


@pytest.mark.parametrize(
    "tracking_id",
    [
        "",
        "bad",
        "bad tracking-01",
        "invalid-xx",
    ],
)
def test_invalid_tracking_id_rejected(
    session,
    tracking_id,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    with pytest.raises(
        AmazonXTrackingIdPoolError
    ):
        repo.register_available(
            tracking_id=tracking_id
        )


def test_assign_next_available(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    registered, _ = (
        repo.register_available(
            tracking_id="x-sale-01"
        )
    )

    now = datetime(
        2026,
        10,
        11,
        12,
        0,
        tzinfo=timezone.utc,
    )

    assigned, created = (
        repo.assign_next_available(
            experiment_id=EXPERIMENT_A,
            variant_id=VARIANT_A,
            wordpress_post_id=3417,
            now=now,
        )
    )

    assert created is True
    assert assigned.id == registered.id
    assert assigned.status == "ASSIGNED"
    assert assigned.experiment_id == EXPERIMENT_A
    assert assigned.variant_id == VARIANT_A
    assert assigned.wordpress_post_id == 3417
    assert assigned.assigned_at is not None


def test_same_variant_assignment_is_idempotent(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    repo.register_available(
        tracking_id="x-sale-01"
    )

    first, first_created = (
        repo.assign_next_available(
            experiment_id=EXPERIMENT_A,
            variant_id=VARIANT_A,
            wordpress_post_id=3417,
        )
    )

    second, second_created = (
        repo.assign_next_available(
            experiment_id=EXPERIMENT_A,
            variant_id=VARIANT_A,
            wordpress_post_id=3417,
        )
    )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id


def test_same_variant_conflicting_binding_rejected(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    repo.register_available(
        tracking_id="x-sale-01"
    )

    repo.assign_next_available(
        experiment_id=EXPERIMENT_A,
        variant_id=VARIANT_A,
        wordpress_post_id=3417,
    )

    with pytest.raises(
        AmazonXTrackingIdPoolConflictError,
        match="variant_assignment_conflict",
    ):
        repo.assign_next_available(
            experiment_id=EXPERIMENT_B,
            variant_id=VARIANT_A,
            wordpress_post_id=3417,
        )


def test_no_available_tracking_id_rejected(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    with pytest.raises(
        AmazonXTrackingIdPoolError,
        match="no_available_tracking_id",
    ):
        repo.assign_next_available(
            experiment_id=EXPERIMENT_A,
            variant_id=VARIANT_A,
            wordpress_post_id=3417,
        )


def test_disabled_tracking_id_not_assigned(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    repo.register_available(
        tracking_id="x-sale-01"
    )

    disabled = repo.disable_available(
        tracking_id="x-sale-01"
    )

    assert disabled.status == "DISABLED"

    with pytest.raises(
        AmazonXTrackingIdPoolError,
        match="no_available_tracking_id",
    ):
        repo.assign_next_available(
            experiment_id=EXPERIMENT_A,
            variant_id=VARIANT_A,
            wordpress_post_id=3417,
        )


def test_assigned_tracking_id_never_disabled(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    repo.register_available(
        tracking_id="x-sale-01"
    )

    repo.assign_next_available(
        experiment_id=EXPERIMENT_A,
        variant_id=VARIANT_A,
        wordpress_post_id=3417,
    )

    with pytest.raises(
        AmazonXTrackingIdPoolConflictError,
        match=(
            "assigned_tracking_id_"
            "cannot_be_disabled"
        ),
    ):
        repo.disable_available(
            tracking_id="x-sale-01"
        )


def test_consumed_tracking_id_cannot_be_registered_again(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    repo.register_available(
        tracking_id="x-sale-01"
    )

    repo.assign_next_available(
        experiment_id=EXPERIMENT_A,
        variant_id=VARIANT_A,
        wordpress_post_id=3417,
    )

    with pytest.raises(
        AmazonXTrackingIdPoolConflictError,
        match="tracking_id_already_consumed",
    ):
        repo.register_available(
            tracking_id="x-sale-01"
        )


def test_invalid_binding_rejected(
    session,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    repo.register_available(
        tracking_id="x-sale-01"
    )

    with pytest.raises(
        AmazonXTrackingIdPoolError,
        match="experiment_id_invalid",
    ):
        repo.assign_next_available(
            experiment_id="bad",
            variant_id=VARIANT_A,
            wordpress_post_id=3417,
        )

    with pytest.raises(
        AmazonXTrackingIdPoolError,
        match="variant_id_invalid",
    ):
        repo.assign_next_available(
            experiment_id=EXPERIMENT_A,
            variant_id="bad",
            wordpress_post_id=3417,
        )

    with pytest.raises(
        AmazonXTrackingIdPoolError,
        match="wordpress_post_id_invalid",
    ):
        repo.assign_next_available(
            experiment_id=EXPERIMENT_A,
            variant_id=VARIANT_B,
            wordpress_post_id=0,
        )


@pytest.mark.parametrize(
    "tracking_id",
    [
        "ktkr77-22",
        "watermelon2-22",
    ],
)
def test_shared_tracking_id_rejected_at_repository(
    session,
    tracking_id,
) -> None:
    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    with pytest.raises(
        AmazonXTrackingIdPoolError,
        match="shared_tracking_id_not_allowed",
    ):
        repo.register_available(
            tracking_id=tracking_id
        )

    assert repo.list_available() == []


@pytest.mark.parametrize(
    "tracking_id",
    [
        "ktkr77-22",
        "watermelon2-22",
    ],
)
def test_preexisting_shared_available_row_not_assignable(
    session,
    tracking_id,
) -> None:
    session.add(
        AmazonXTrackingIdPool(
            tracking_id=tracking_id,
            status="AVAILABLE",
        )
    )
    session.flush()

    repo = AmazonXTrackingIdPoolRepository(
        session
    )

    assert repo.list_available() == []

    with pytest.raises(
        AmazonXTrackingIdPoolError,
        match="no_available_tracking_id",
    ):
        repo.assign_next_available(
            experiment_id=EXPERIMENT_A,
            variant_id=VARIANT_A,
            wordpress_post_id=3417,
        )
