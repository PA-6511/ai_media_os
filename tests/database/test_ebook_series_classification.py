from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    EbookItem,
    EbookSeriesClassificationRule,
    StoreOffer,
    build_series_classification_identity,
)
from app.db.repositories.ebook_query_repository import EbookQueryRepository
from app.db.repositories.import_repository import ImportRepository
from app.gui.ebook_database_web import render_catalog_edit_form
from app.services.catalog_edit_service import CatalogEditService


def _engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'classification.db'}")
    Base.metadata.create_all(engine)
    return engine


def _catalog_item(
    session: Session,
    *,
    source_item_id: str = "item-1",
    title: str = "作品 第1巻",
    author_name: str | None = "著者",
    publisher_name: str | None = "出版社",
) -> tuple[EbookItem, StoreOffer]:
    item = EbookItem(
        source_name="test",
        source_item_id=source_item_id,
        title=title,
        normalized_title=title,
        volume_label="第1巻",
        author_name=author_name,
        publisher_name=publisher_name,
        item_type="tankobon",
        workflow_status="READY",
        review_status="APPROVED",
        publish_ready=True,
    )
    session.add(item)
    session.flush()
    offer = StoreOffer(
        ebook_item_id=item.id,
        store_name="rakuten_kobo",
        store_item_id=f"RK-{source_item_id}",
        product_url="https://product.example/item",
        affiliate_url="https://affiliate.example/item",
        price_amount=Decimal("500"),
        price_yen=500,
        currency="JPY",
    )
    session.add(offer)
    session.commit()
    return item, offer


@pytest.mark.parametrize(
    ("is_single_episode", "is_split_edition"),
    [(True, False), (False, True), (True, True), (False, False)],
)
def test_catalog_edit_saves_independent_flags_without_other_changes(
    tmp_path: Path,
    is_single_episode: bool,
    is_split_edition: bool,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        item, offer = _catalog_item(session)
        unchanged_item_values = (
            item.title,
            item.volume_label,
            item.author_name,
            item.publisher_name,
            item.item_type,
            item.workflow_status,
            item.review_status,
            item.publish_ready,
        )
        unchanged_offer_values = (
            offer.product_url,
            offer.affiliate_url,
            offer.price_amount,
            offer.price_yen,
            offer.currency,
        )
        result = CatalogEditService(session).save(
            ebook_item_id=item.id,
            volume_label="第1巻",
            authors="著者",
            publisher="出版社",
            price="500",
            currency="JPY",
            reason="分類を人手確認",
            is_single_episode=is_single_episode,
            is_split_edition=is_split_edition,
            apply_to_future_series=False,
        )
        session.commit()

        assert result.unchanged is False
        assert item.is_single_episode is is_single_episode
        assert item.is_split_edition is is_split_edition
        assert item.classification_source == "manual"
        assert (
            item.title,
            item.volume_label,
            item.author_name,
            item.publisher_name,
            item.item_type,
            item.workflow_status,
            item.review_status,
            item.publish_ready,
        ) == unchanged_item_values
        assert (
            offer.product_url,
            offer.affiliate_url,
            offer.price_amount,
            offer.price_yen,
            offer.currency,
        ) == unchanged_offer_values
        assert session.scalar(
            select(func.count()).select_from(EbookSeriesClassificationRule)
        ) == 0


def test_series_rule_is_created_then_updated_by_exact_series_key(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        first, _ = _catalog_item(
            session,
            source_item_id="item-1",
            title="作品 第1巻",
        )
        first_result = CatalogEditService(session).save(
            ebook_item_id=first.id,
            volume_label="第1巻",
            authors="著者",
            publisher="出版社",
            price="500",
            currency="JPY",
            reason="同シリーズへ適用",
            is_single_episode=True,
            is_split_edition=False,
            apply_to_future_series=True,
        )
        session.commit()
        assert first_result.series_rule_saved is True

        second, _ = _catalog_item(
            session,
            source_item_id="item-2",
            title="作品 第2巻",
        )
        second_result = CatalogEditService(session).save(
            ebook_item_id=second.id,
            volume_label="第1巻",
            authors="著者",
            publisher="出版社",
            price="500",
            currency="JPY",
            reason="ルール更新",
            is_single_episode=False,
            is_split_edition=True,
            apply_to_future_series=True,
        )
        session.commit()

        rules = session.scalars(select(EbookSeriesClassificationRule)).all()
        assert second_result.series_rule_saved is True
        assert len(rules) == 1
        assert rules[0].is_single_episode is False
        assert rules[0].is_split_edition is True
        assert rules[0].source_ebook_item_id == second.id


@pytest.mark.parametrize(
    ("author_name", "publisher_name"),
    [(None, "出版社"), ("著者", None)],
)
def test_incomplete_identity_saves_item_but_skips_rule(
    tmp_path: Path,
    author_name: str | None,
    publisher_name: str | None,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        item, _ = _catalog_item(
            session,
            author_name=author_name,
            publisher_name=publisher_name,
        )
        result = CatalogEditService(session).save(
            ebook_item_id=item.id,
            volume_label="第1巻",
            authors=author_name or "",
            publisher=publisher_name or "",
            price="500",
            currency="JPY",
            reason="分類のみ保存",
            is_single_episode=True,
            is_split_edition=False,
            apply_to_future_series=True,
        )
        session.commit()
        assert item.is_single_episode is True
        assert item.classification_source == "manual"
        assert result.series_rule_skipped is True
        assert session.scalar(
            select(func.count()).select_from(EbookSeriesClassificationRule)
        ) == 0


def test_rule_failure_rolls_back_item_classification(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    item_id: str
    with Session(engine) as session:
        item, _ = _catalog_item(session)
        item_id = item.id

        @event.listens_for(session, "before_flush")
        def fail_rule_flush(
            current_session: Session,
            _flush_context: object,
            _instances: object,
        ) -> None:
            if any(
                isinstance(value, EbookSeriesClassificationRule)
                for value in current_session.new
            ):
                raise RuntimeError("simulated rule write failure")

        with pytest.raises(RuntimeError, match="rule write failure"):
            CatalogEditService(session).save(
                ebook_item_id=item.id,
                volume_label="第1巻",
                authors="著者",
                publisher="出版社",
                price="500",
                currency="JPY",
                reason="rollback確認",
                is_single_episode=True,
                is_split_edition=False,
                apply_to_future_series=True,
            )
        session.rollback()

    with Session(engine) as session:
        item = session.get(EbookItem, item_id)
        assert item is not None
        assert item.is_single_episode is None
        assert item.is_split_edition is None
        assert item.classification_source is None
        assert session.scalar(
            select(func.count()).select_from(EbookSeriesClassificationRule)
        ) == 0


def _rule(
    source_item: EbookItem,
    *,
    title: str,
    author_name: str,
    publisher_name: str,
    is_single_episode: bool = True,
    is_split_edition: bool = False,
) -> EbookSeriesClassificationRule:
    identity = build_series_classification_identity(
        title=title,
        author_name=author_name,
        publisher_name=publisher_name,
    )
    assert identity is not None
    return EbookSeriesClassificationRule(
        series_key=identity[0],
        normalized_base_title=identity[1],
        normalized_author_name=identity[2],
        normalized_publisher_name=identity[3],
        is_single_episode=is_single_episode,
        is_split_edition=is_split_edition,
        source_ebook_item_id=source_item.id,
        active=True,
    )


def test_new_import_applies_only_exact_active_rule_and_preserves_existing(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        seed, _ = _catalog_item(session, source_item_id="seed")
        session.add(
            _rule(
                seed,
                title="作品 第9巻",
                author_name="著者",
                publisher_name="出版社",
            )
        )
        session.commit()
        repository = ImportRepository(session)

        exact = repository.import_row(
            {
                "source_name": "import",
                "source_item_id": "exact",
                "title": "作品 第2巻",
                "authors": "著者",
                "publisher": "出版社",
            }
        )
        wrong_author = repository.import_row(
            {
                "source_name": "import",
                "source_item_id": "wrong-author",
                "title": "作品 第3巻",
                "authors": "別著者",
                "publisher": "出版社",
            }
        )
        wrong_publisher = repository.import_row(
            {
                "source_name": "import",
                "source_item_id": "wrong-publisher",
                "title": "作品 第4巻",
                "authors": "著者",
                "publisher": "別出版社",
            }
        )
        explicit = repository.import_row(
            {
                "source_name": "import",
                "source_item_id": "explicit",
                "title": "作品 第5巻",
                "authors": "著者",
                "publisher": "出版社",
                "is_single_episode": "false",
                "is_split_edition": "true",
            }
        )
        session.commit()

        exact_item = session.get(EbookItem, exact.ebook_item_id)
        assert exact_item is not None
        assert exact_item.is_single_episode is True
        assert exact_item.is_split_edition is False
        assert exact_item.classification_source == "series_rule"
        for item_id in (
            wrong_author.ebook_item_id,
            wrong_publisher.ebook_item_id,
        ):
            item = session.get(EbookItem, item_id)
            assert item is not None
            assert (
                item.is_single_episode,
                item.is_split_edition,
                item.classification_source,
            ) == (None, None, None)
        explicit_item = session.get(EbookItem, explicit.ebook_item_id)
        assert explicit_item is not None
        assert (
            explicit_item.is_single_episode,
            explicit_item.is_split_edition,
            explicit_item.classification_source,
        ) == (False, True, "manual")

        repository.import_row(
            {
                "source_name": "import",
                "source_item_id": "explicit",
                "title": "作品 第5巻",
                "authors": "著者",
                "publisher": "出版社",
            }
        )
        session.commit()
        assert (
            explicit_item.is_single_episode,
            explicit_item.is_split_edition,
            explicit_item.classification_source,
        ) == (False, True, "manual")

        unclassified = repository.import_row(
            {
                "source_name": "import",
                "source_item_id": "later",
                "title": "後発作品 第1巻",
                "authors": "後発著者",
                "publisher": "後発出版",
            }
        )
        session.commit()
        unclassified_item = session.get(EbookItem, unclassified.ebook_item_id)
        assert unclassified_item is not None
        assert unclassified_item.classification_source is None
        session.add(
            _rule(
                unclassified_item,
                title="後発作品 第2巻",
                author_name="後発著者",
                publisher_name="後発出版",
                is_single_episode=False,
                is_split_edition=True,
            )
        )
        session.commit()
        repository.import_row(
            {
                "source_name": "import",
                "source_item_id": "later",
                "title": "後発作品 第1巻",
                "authors": "後発著者",
                "publisher": "後発出版",
            }
        )
        session.commit()
        assert (
            unclassified_item.is_single_episode,
            unclassified_item.is_split_edition,
            unclassified_item.classification_source,
        ) == (None, None, None)


def test_classification_search_modes_have_matching_list_and_count(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        values = [
            ("normal", False, False),
            ("single", True, False),
            ("split", False, True),
            ("both", True, True),
            ("unclassified", None, None),
        ]
        for source_id, single, split in values:
            session.add(
                EbookItem(
                    source_name="search",
                    source_item_id=source_id,
                    title=source_id,
                    item_type="tankobon",
                    is_single_episode=single,
                    is_split_edition=split,
                    classification_source=(
                        None if single is None else "manual"
                    ),
                )
            )
        session.commit()
        repository = EbookQueryRepository(session)
        expected = {
            "normal": {"normal"},
            "single_episode": {"single", "both"},
            "split_edition": {"split", "both"},
            "single_or_split": {"single", "split", "both"},
            "unclassified": {"unclassified"},
        }
        for mode, expected_ids in expected.items():
            items = repository.search_items(item_type=mode)
            assert {item.source_item_id for item in items} == expected_ids
            assert repository.count_items(item_type=mode) == len(items)


def test_catalog_form_restores_flags_and_uses_existing_save_endpoint() -> None:
    html = render_catalog_edit_form(
        {
            "id": "item-1",
            "volume_label": "第1巻",
            "author_name": "著者",
            "publisher_name": "出版社",
            "is_single_episode": True,
            "is_split_edition": False,
            "rakuten_kobo_offer": {
                "price_amount": "500.00",
                "currency": "JPY",
            },
        }
    )
    assert 'method="post" action="/database-catalog-edit"' in html
    assert 'name="volume_label"' in html
    assert 'name="authors"' in html
    assert 'name="publisher"' in html
    assert (
        'name="is_single_episode" value="true" checked' in html
    )
    assert 'name="is_split_edition" value="true">' in html
    assert 'name="apply_to_future_series" value="true">' in html
