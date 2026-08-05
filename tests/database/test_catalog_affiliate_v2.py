from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    AffiliateSettingHistory,
    CatalogEditHistory,
    EbookItem,
    StoreOffer,
)
from app.services.affiliate_account_settings_service import (
    AffiliateAccountSettingsService,
)
from app.services.catalog_edit_service import (
    CatalogEditError,
    CatalogEditService,
)
from app.services.csv_import_service import CsvImportService
from app.services.dmm_manual_offer_service import (
    DmmManualOfferError,
    DmmManualOfferService,
)
from app.gui.ebook_database_web import (
    render_amazon_manual_offer_form,
    render_catalog_edit_form,
    render_dmm_manual_offer_form,
    render_metadata_autofill_form,
    render_metadata_autofill_preview_page,
)
from scripts.database.import_new_release_multistore_to_sqlite import (
    ready_payload_rows,
)
from src.new_release_multistore_input import build_payload


def _engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'catalog-v2.db'}")
    Base.metadata.create_all(engine)
    return engine


def test_csv_v2_saves_metadata_zero_price_currency_and_affiliate(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    csv_path = tmp_path / "v2.csv"
    csv_path.write_text(
        "source_name,source_item_id,title,store_item_id,volume_label,authors,"
        "publisher,series_name,rakuten_kobo_price,rakuten_kobo_currency,"
        "rakuten_kobo_url,rakuten_kobo_affiliate_url,source_row_sha256\n"
        "collector,RK-1,作品,RK-1,第1巻, 著者A | 著者B ,出版社,シリーズ,0,,"
        "https://books.example/item,https://affiliate.example/item,"
        + ("a" * 64)
        + "\n",
        encoding="utf-8",
    )
    with Session(engine) as session:
        summary = CsvImportService(session).import_file(csv_path, dry_run=False)
        assert summary.created == 1
    with Session(engine) as session:
        item = session.scalar(select(EbookItem))
        offer = session.scalar(select(StoreOffer))
        assert item is not None and offer is not None
        assert (item.volume_label, item.author_name, item.publisher_name) == (
            "第1巻",
            "著者A|著者B",
            "出版社",
        )
        assert item.series_name == "シリーズ"
        assert offer.store_name == "rakuten_kobo"
        assert offer.price_amount == Decimal("0.00")
        assert offer.price_yen == 0
        assert offer.currency == "JPY"
        assert offer.affiliate_url == "https://affiliate.example/item"
        assert offer.source_row_sha256 == "a" * 64


def test_web_v2_artifact_pipeline_preserves_optional_kobo_metadata(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    payload = build_payload(
        {
            "batch_id": "BATCH-1",
            "item_id": "RK-PIPELINE-1",
            "title": "パイプライン作品",
            "release_date": "2026-08-01",
            "category": "コミック",
            "rakuten_kobo_url": "https://books.example/rk-1",
            "image_url": "https://images.example/rk-1.jpg",
            "volume_number": "2",
            "author_name": "著者A|著者B",
            "publisher_name": "出版社",
            "series_name": "シリーズ",
            "item_price": "0",
            "currency_code": "JPY",
            "affiliate_url": "https://affiliate.example/rk-1",
            "source_row_sha256": "pipeline-sha",
        },
        2,
        "2026-07-31T00:00:00+00:00",
    )
    rows = ready_payload_rows(payload)
    assert rows[0]["price"] == "0"
    assert rows[0]["affiliate_url"] == "https://affiliate.example/rk-1"
    with Session(engine) as session:
        from app.db.repositories.import_repository import ImportRepository

        ImportRepository(session).import_row(rows[0])
        session.commit()
        item = session.scalar(select(EbookItem))
        offer = session.scalar(select(StoreOffer))
        assert item.series_name == "シリーズ"
        assert item.author_name == "著者A|著者B"
        assert offer.price_yen == 0
        assert offer.currency == "JPY"
        assert offer.source_row_sha256 == "pipeline-sha"


@pytest.mark.parametrize("price", ["-1", "not-a-price", "NaN"])
def test_csv_v2_rejects_invalid_prices(tmp_path: Path, price: str) -> None:
    engine = _engine(tmp_path)
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text(
        "source_item_id,title,rakuten_kobo_price\n"
        f"RK-1,作品,{price}\n",
        encoding="utf-8",
    )
    with Session(engine) as session:
        with pytest.raises(ValueError, match="row 2"):
            CsvImportService(session).import_file(csv_path, dry_run=False)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EbookItem)) == 0


def test_csv_blank_preserves_values_and_same_row_is_unchanged(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    csv_path = tmp_path / "update.csv"
    header = (
        "source_name,source_item_id,title,store_item_id,authors,publisher,"
        "rakuten_kobo_price,rakuten_kobo_currency,rakuten_kobo_affiliate_url\n"
    )
    csv_path.write_text(
        header + "collector,RK-1,作品,RK-1,著者,出版社,550,JPY,https://a.example/x\n",
        encoding="utf-8",
    )
    with Session(engine) as session:
        CsvImportService(session).import_file(csv_path, dry_run=False)
    csv_path.write_text(
        header + "collector,RK-1,作品,RK-1,,,,,\n",
        encoding="utf-8",
    )
    with Session(engine) as session:
        second = CsvImportService(session).import_file(csv_path, dry_run=False)
        assert second.unchanged == 1
        assert second.offer_unchanged == 1
    with Session(engine) as session:
        item = session.scalar(select(EbookItem))
        offer = session.scalar(select(StoreOffer))
        assert item.author_name == "著者"
        assert item.publisher_name == "出版社"
        assert offer.price_amount == Decimal("550.00")
        assert offer.affiliate_url == "https://a.example/x"


def _catalog_item(session: Session) -> tuple[EbookItem, StoreOffer]:
    item = EbookItem(
        source_name="test",
        source_item_id="item-1",
        title="作品",
        volume_label="1",
        author_name="旧著者",
        publisher_name="旧出版",
        review_status="APPROVED",
        publish_ready=True,
    )
    session.add(item)
    session.flush()
    offer = StoreOffer(
        ebook_item_id=item.id,
        store_name="rakuten_kobo",
        store_item_id="RK-1",
        product_url="https://product.example/rk",
        affiliate_url="https://affiliate.example/rk",
        price_amount=Decimal("500"),
        price_yen=500,
        currency="JPY",
    )
    session.add(offer)
    session.commit()
    return item, offer


def test_catalog_edit_audits_resets_review_and_preserves_urls(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        item, offer = _catalog_item(session)
        result = CatalogEditService(session).save(
            ebook_item_id=item.id,
            volume_label="第2巻",
            authors="著者A | 著者B",
            publisher="新出版",
            price="0",
            currency="jpy",
            reason="CSV内容の人手確認",
        )
        session.commit()
        assert result.unchanged is False
        assert item.review_status == "NOT_REVIEWED"
        assert item.publish_ready is False
        assert item.author_name == "著者A|著者B"
        assert offer.price_amount == Decimal("0")
        assert offer.product_url == "https://product.example/rk"
        assert offer.affiliate_url == "https://affiliate.example/rk"
        history_count = session.scalar(
            select(func.count()).select_from(CatalogEditHistory)
        )
        same = CatalogEditService(session).save(
            ebook_item_id=item.id,
            volume_label="第2巻",
            authors="著者A|著者B",
            publisher="新出版",
            price="0",
            currency="JPY",
            reason="再確認",
        )
        session.commit()
        assert same.unchanged is True
        assert session.scalar(
            select(func.count()).select_from(CatalogEditHistory)
        ) == history_count


def test_catalog_edit_rejects_unknown_item(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        with pytest.raises(CatalogEditError, match="item_not_found"):
            CatalogEditService(session).save(
                ebook_item_id="missing",
                volume_label="",
                authors="",
                publisher="",
                price="0",
                currency="JPY",
                reason="test",
            )


def test_settings_history_blank_preserve_environment_priority_and_explicit_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        service = AffiliateAccountSettingsService(session)
        service.register(service_name="amazon", affiliate_id="saved-22")
        service.register(service_name="amazon", affiliate_id="", enabled=True)
        assert service.get_affiliate_id(service_name="amazon") == "saved-22"
        monkeypatch.setenv("AMAZON_TRACKING_ID", "environment-22")
        effective = service.get_effective(service_name="amazon")
        assert effective.affiliate_id == "environment-22"
        assert effective.source == "environment:AMAZON_TRACKING_ID"
        monkeypatch.delenv("AMAZON_TRACKING_ID")
        service.unregister(service_name="amazon")
        assert service.get_affiliate_id(service_name="amazon") is None
        assert session.scalar(
            select(func.count()).select_from(AffiliateSettingHistory)
        ) >= 2


def test_dmm_preview_has_no_write_then_save_is_idempotent(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        item, _ = _catalog_item(session)
        settings = AffiliateAccountSettingsService(session)
        settings.register(
            service_name="dmm",
            affiliate_id="dmm-test-id",
            url_template=(
                "https://affiliate.example/dmm?aid={affiliate_id}&url={product_url}"
            ),
        )
        service = DmmManualOfferService(session)
        preview = service.preview(
            ebook_item_id=item.id,
            product_url="https://book.example/dmm/1",
            content_id="content-1",
            price="0",
            currency="JPY",
            affiliate_mode="generated",
            affiliate_url="",
        )
        assert session.scalar(
            select(func.count()).select_from(StoreOffer).where(
                StoreOffer.store_name == "dmm"
            )
        ) == 0
        with pytest.raises(DmmManualOfferError, match="confirmation"):
            service.save(preview=preview, confirmed=False)
        first = service.save(preview=preview, confirmed=True)
        session.commit()
        assert first.unchanged is False
        dmm_offer = session.scalar(
            select(StoreOffer).where(StoreOffer.store_name == "dmm")
        )
        assert dmm_offer is not None
        assert dmm_offer.availability_status == "FOUND_CONFIRMED"
        assert dmm_offer.verification_method == "MANUAL_WEB_EDIT"
        second = service.save(preview=preview, confirmed=True)
        session.commit()
        assert second.unchanged is True
        assert session.scalar(
            select(func.count()).select_from(StoreOffer).where(
                StoreOffer.store_name == "rakuten_kobo"
            )
        ) == 1


def test_dmm_rejects_non_https_direct_url(tmp_path: Path) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        item, _ = _catalog_item(session)
        with pytest.raises(DmmManualOfferError, match="https"):
            DmmManualOfferService(session).preview(
                ebook_item_id=item.id,
                product_url="http://book.example/dmm/1",
                content_id="",
                price="",
                currency="JPY",
                affiliate_mode="direct",
                affiliate_url="https://affiliate.example/dmm",
            )


def test_search_row_forms_use_post_csrf_and_saved_id_flow() -> None:
    row = {
        "id": "item-1",
        "title": "作品",
        "volume_label": "1",
        "author_name": "著者",
        "publisher_name": "出版社",
        "rakuten_kobo_offer": {
            "price_amount": "500.00",
            "currency": "JPY",
        },
    }
    catalog = render_catalog_edit_form(row)
    amazon = render_amazon_manual_offer_form(
        row,
        configured=True,
        setting_source="database",
    )
    dmm = render_dmm_manual_offer_form(
        row,
        generation_available=False,
    )
    metadata_autofill = render_metadata_autofill_form(row)
    assert 'method="post"' in catalog
    assert 'name="csrf_token"' in catalog
    assert 'name="item_id"' not in catalog
    assert 'name="ebook_item_id"' in catalog
    assert 'name="tracking_id"' not in amazon
    assert 'name="operation" value="preview"' in amazon
    assert "保存済みIDを使用" in amazon
    assert "DMMリンク登録" in dmm
    assert "DMM設定へ" in dmm
    assert '<textarea name="dmm_input"' in dmm
    assert "URLまたはDMMアフィリエイトHTML" in dmm
    assert "解析して確認" in dmm
    assert "基本情報更新" in metadata_autofill
    assert 'class="workflow-action-button metadata-autofill-button"' in metadata_autofill
    assert 'data-csrf-token=' in metadata_autofill
    assert 'data-ebook-item-id="item-1"' in metadata_autofill
    assert 'class="metadata-autofill-panel"' in metadata_autofill
    assert 'class="amazon-manual-offer catalog-edit-details"' in catalog
    assert 'class="amazon-manual-offer-form catalog-edit-form"' in catalog
    assert 'class="catalog-edit-prefill-notice"' in catalog


def test_metadata_autofill_preview_requires_explicit_confirmation() -> None:
    from app.db.repositories.ebook_metadata_autofill_repository import (
        EbookMetadataAutofillContext,
    )
    from app.services.ebook_metadata_autofill_service import (
        build_metadata_autofill_preview,
    )

    preview = build_metadata_autofill_preview(
        EbookMetadataAutofillContext(
            ebook_item_id="item-1",
            title="作品 15",
            volume_label=None,
            author_name=None,
            publisher_name=None,
            human_reviewed_fields=frozenset(),
            verified_records=(),
        )
    )
    page = render_metadata_autofill_preview_page(
        preview,
        csrf_token="token",
        return_to="/database-search",
    )
    assert "この画面の表示だけではDBを更新しません" in page
    assert "空欄 → 第15巻" in page
    assert "TITLE_SUFFIX" in page
    assert 'name="confirmed" value="true" required' in page
    assert 'name="preview_fingerprint"' in page
    assert "補完を確定" in page
    assert "キャンセル" in page
