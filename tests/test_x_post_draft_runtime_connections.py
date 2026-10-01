from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace


def test_new_release_runtime_persists_generated_draft(
    monkeypatch,
):
    from app.services.ebook_batch_runtime_adapter import (
        LocalXDraftExecutor,
    )

    item = SimpleNamespace(
        id="book-001",
        title="テストコミック 1",
        volume_label="1",
        release_date=date(2026, 9, 28),
        item_type="COMIC",
        author_name="テスト著者",
    )

    sessions = []

    class FakeSession:
        def __init__(self):
            self.committed = False
            sessions.append(self)

        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc,
            tb,
        ):
            return False

        def get(
            self,
            model,
            key,
        ):
            return item

        def commit(self):
            self.committed = True

    monkeypatch.setattr(
        "app.db.session.SessionLocal",
        lambda: FakeSession(),
    )

    monkeypatch.setattr(
        "app.services."
        "workflow_approved_x_draft_read_service."
        "build_wordpress_article_url",
        lambda **kwargs: (
            "https://example.test/?p=123"
        ),
    )

    generated = SimpleNamespace(
        feedback_id="feedback-001",
        ebook_item_id="book-001",
        generated_text=(
            "テスト投稿 #PR "
            "https://example.test/?p=123"
        ),
    )

    class FakeGenerationService:
        def generate(
            self,
            draft_input,
        ):
            return generated

    monkeypatch.setattr(
        "app.services.x_draft_generation_service."
        "XDraftGenerationService",
        FakeGenerationService,
    )

    saved = []

    class FakePersistenceService:
        def __init__(self, session):
            self.session = session

        def save(self, request):
            saved.append(request)
            return SimpleNamespace(
                draft_id="draft-001"
            )

    monkeypatch.setattr(
        "app.services."
        "x_post_draft_persistence_service."
        "XPostDraftPersistenceService",
        FakePersistenceService,
    )

    scheduled_at = datetime(
        2026,
        9,
        28,
        12,
        15,
        tzinfo=timezone.utc,
    )

    result = LocalXDraftExecutor()(
        "book-001",
        123,
        scheduled_at=scheduled_at,
        paid_partnership=False,
    )

    assert result is generated
    assert len(saved) == 1

    request = saved[0]

    assert request.source_type == "new_release"
    assert request.source_id == "book-001"
    assert request.ebook_item_id == "book-001"
    assert request.feedback_id == "feedback-001"
    assert (
        request.generated_text
        == generated.generated_text
    )
    assert request.scheduled_at == scheduled_at
    assert request.paid_partnership is False

    assert len(sessions) == 2
    assert sessions[-1].committed is True


def test_sale_variants_persist_schedule_and_paid_flag(
    monkeypatch,
):
    import app.services.sale_copy_experiment_service as svc

    snapshot = {
        "title": "コミックセール",
        "items": [
            {
                "discount_percent": 50,
                "point_percent": 0,
                "sale_end_at_utc": (
                    "2026-10-01T15:00:00+00:00"
                ),
            },
        ],
    }

    experiment = SimpleNamespace(
        id="experiment-001",
        campaign_id="campaign-001",
        wordpress_post_id=123,
        snapshot=snapshot,
    )

    class FakeSession:
        def __init__(self):
            self.added = []

        def get(
            self,
            model,
            key,
        ):
            if model is svc.SaleExperiment:
                return experiment

            if model is svc.SaleCopyVariant:
                return None

            return None

        def add(
            self,
            value,
        ):
            self.added.append(value)

        def flush(self):
            return None

    monkeypatch.setattr(
        svc,
        "validate_article_url",
        lambda value: value,
    )

    monkeypatch.setattr(
        svc,
        "validate_sale_snapshot_store",
        lambda snapshot: "kobo",
    )

    monkeypatch.setattr(
        svc,
        "sale_store_display_name",
        lambda store: "楽天Kobo",
    )

    monkeypatch.setattr(
        svc,
        "integer",
        lambda value: (
            int(value)
            if value is not None
            else None
        ),
    )

    monkeypatch.setattr(
        svc,
        "utc",
        lambda value: datetime(
            2026,
            10,
            1,
            15,
            0,
            tzinfo=timezone.utc,
        ),
    )

    monkeypatch.setattr(
        svc,
        "digest",
        lambda values: (
            "variant-"
            + str(values[1])
        ),
    )

    monkeypatch.setattr(
        svc,
        "_x_weighted_length",
        lambda value: len(value),
    )

    monkeypatch.setattr(
        svc,
        "load_contract",
        lambda: {
            "output_contract": {
                "fixed_values": {
                    "record_stage": (
                        "DRAFT_GENERATED"
                    ),
                    "x_status": "DRAFT",
                    "review_status": (
                        "UNREVIEWED"
                    ),
                }
            }
        },
    )

    saved = []

    class FakePersistenceService:
        def __init__(self, session):
            self.session = session

        def save(self, request):
            saved.append(request)
            return SimpleNamespace(
                draft_id=(
                    "stored-"
                    + request.source_id
                )
            )

    monkeypatch.setattr(
        svc,
        "XPostDraftPersistenceService",
        FakePersistenceService,
    )

    scheduled_at = datetime(
        2026,
        9,
        28,
        18,
        30,
        tzinfo=timezone.utc,
    )

    variants = svc.generate_variants(
        FakeSession(),
        "experiment-001",
        "https://example.test/sale",
        wordpress_post_id=123,
        scheduled_at=scheduled_at,
        paid_partnership=False,
    )

    assert len(variants) == 3
    assert len(saved) == 3

    assert {
        request.source_id
        for request in saved
    } == {
        "variant-1",
        "variant-2",
        "variant-3",
    }

    for request in saved:
        assert request.source_type == "sale"
        assert request.feedback_id.startswith(
            "sale-variant-"
        )
        assert (
            request.scheduled_at
            == scheduled_at
        )
        assert (
            request.paid_partnership
            is False
        )
        assert request.generated_text
