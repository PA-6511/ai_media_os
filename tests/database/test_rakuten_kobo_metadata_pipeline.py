from __future__ import annotations

import csv
import json
import socket
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.services.csv_import_service import CsvImportService
from app.services.ebook_metadata_autofill_service import (
    EbookMetadataAutofillService,
)
from scripts import new_release_multistore_app
from scripts.database import import_new_release_multistore_to_sqlite
from src.rakuten_kobo_csv import (
    CSV_FIELDNAMES,
    normalize_author_name,
    normalize_isbn13,
    response_to_csv_rows,
    write_response_csv,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "rakuten_kobo_api_response.json"
)
OFFICIAL_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "rakuten_kobo_official_ebook_search_response.json"
)
VERIFIED_AT = "2026-08-01T09:00:00+09:00"


def _response() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _official_response() -> dict:
    return json.loads(OFFICIAL_FIXTURE.read_text(encoding="utf-8"))


def _engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'pipeline.db'}")
    Base.metadata.create_all(engine)
    return engine


def test_kobo_response_uses_author_and_publisher_name_without_label() -> None:
    row = response_to_csv_rows(
        _response(), batch_id="RK_FIXTURE", verified_at=VERIFIED_AT
    )[0]

    assert row["author_name"] == "原作：佐藤 太郎|作画：山田花子"
    assert row["publisher_name"] == "A&B 出版"
    assert "コミックス" not in row["publisher_name"]
    assert row["isbn13"] == "9781234567897"
    assert row["item_number"] == "2000012345678"
    assert len(row["source_row_sha256"]) == 64
    assert row["verified_at"] == VERIFIED_AT
    assert row["verification_method"] == "RAKUTEN_KOBO_API_RESPONSE"


def test_label_only_is_not_used_as_publisher() -> None:
    response = _response()
    item = response["Items"][0]["Item"]
    del item["publisherName"]

    row = response_to_csv_rows(
        response, batch_id="RK_FIXTURE", verified_at=VERIFIED_AT
    )[0]

    assert item["label"] == "A&amp;Bコミックス"
    assert row["publisher_name"] == ""


def test_official_response_without_isbn_remains_discovery_only() -> None:
    row = response_to_csv_rows(
        _official_response(),
        batch_id="RK_OFFICIAL_FIXTURE",
        verified_at=VERIFIED_AT,
    )[0]

    assert row["title"] == "SAKAMOTO DAYS 28"
    assert row["author_name"] == "鈴木祐斗"
    assert row["publisher_name"] == "集英社"
    assert row["item_number"] == "4321000000028"
    assert row["isbn13"] == ""
    assert row["item_number"] != row["isbn13"]
    assert row["release_date"] == "2026-08-01"
    assert row["rakuten_kobo_price"] == "543"
    assert row["rakuten_kobo_url"] == (
        "https://books.rakuten.co.jp/rk/official-fixture/"
    )
    assert row["image_url"].endswith("medium.jpg")
    assert len(row["source_row_sha256"]) == 64
    assert row["verified_at"] == VERIFIED_AT


def test_isbnless_official_kobo_item_is_not_an_autofill_source(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    with Session(engine) as session:
        target = EbookItem(
            source_name="catalog",
            source_item_id="target-isbnless",
            title="SAKAMOTO DAYS 28",
        )
        kobo_item = EbookItem(
            source_name="rakuten_kobo",
            source_item_id="4321000000028",
            title="SAKAMOTO DAYS 28",
            author_name="鈴木祐斗",
            publisher_name="集英社",
            isbn=None,
        )
        session.add_all((target, kobo_item))
        session.flush()
        session.add(
            StoreOffer(
                ebook_item_id=kobo_item.id,
                store_name="rakuten_kobo",
                store_item_id="4321000000028",
                source_row_sha256="a" * 64,
                verified_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                verification_method="RAKUTEN_KOBO_API_RESPONSE",
            )
        )
        session.commit()

        preview = EbookMetadataAutofillService(session).preview(target.id)

    assert preview.result_for("author_name").status == "SOURCE_NOT_FOUND"
    assert preview.result_for("publisher_name").status == "SOURCE_NOT_FOUND"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("単独 著者", "単独 著者"),
        ("著者A／著者B／著者A", "著者A|著者B"),
        (["原作：著者A", "作画：著者B", "原作：著者A"], "原作：著者A|作画：著者B"),
    ],
)
def test_author_normalization_preserves_order_roles_and_deduplicates(
    value: object, expected: str
) -> None:
    assert normalize_author_name(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("9781234567897", "9781234567897"),
        ("978-1-2345-6789-7", "9781234567897"),
        (" 978 1234567897 ", "9781234567897"),
        ("978　1234567897", "9781234567897"),
        ("978－1‐2345‑6789−7", "9781234567897"),
        (None, ""),
        ("", ""),
    ],
)
def test_normalize_isbn13(value: object, expected: str) -> None:
    assert normalize_isbn13(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "978123456789",
        "97812345678970",
        "978123456789X",
        "9781234567890",
    ],
)
def test_normalize_isbn13_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_isbn13(value)


def test_converter_writes_canonical_columns_and_preserves_source_hash(
    tmp_path: Path,
) -> None:
    output = tmp_path / "kobo.csv"
    rows = write_response_csv(
        _response(),
        output_path=output,
        batch_id="RK_FIXTURE",
        verified_at=VERIFIED_AT,
    )
    with output.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        persisted = list(reader)
        assert tuple(reader.fieldnames or ()) == CSV_FIELDNAMES
    assert persisted[0]["author_name"] == rows[0]["author_name"]
    assert persisted[0]["publisher_name"] == rows[0]["publisher_name"]
    assert persisted[0]["source_row_sha256"] == rows[0]["source_row_sha256"]


def test_saved_response_to_temp_sqlite_to_autofill_preview_is_verified_and_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_external(*_args: object, **_kwargs: object) -> None:
        pytest.fail("external communication or WordPress client use is forbidden")

    monkeypatch.setattr(socket, "socket", forbidden_external)
    monkeypatch.setattr(socket, "create_connection", forbidden_external)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden_external)
    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        forbidden_external,
    )

    csv_path = tmp_path / "kobo.csv"
    converted = write_response_csv(
        _response(),
        output_path=csv_path,
        batch_id="RK_FIXTURE",
        verified_at=VERIFIED_AT,
    )
    expected_sha = converted[0]["source_row_sha256"]
    upload_dir = tmp_path / "gui-upload"

    def write_gui_upload(raw_bytes: bytes, suffix: str = ".csv"):
        upload_dir.mkdir()
        upload_path = upload_dir / f"upload{suffix}"
        upload_path.write_bytes(raw_bytes)
        return upload_dir, upload_path

    monkeypatch.setattr(
        new_release_multistore_app,
        "_write_secure_temp_csv",
        write_gui_upload,
    )
    gui_bundle = new_release_multistore_app.prevalidate_csv_upload(
        filename="rakuten_kobo_fixture.csv",
        raw_bytes=csv_path.read_bytes(),
        input_type="collected",
    )
    assert gui_bundle["summary"]["ready_count"] == 1
    assert gui_bundle["summary"]["unknown_columns"] == []
    ready_payload = gui_bundle["raw_result"]["ready_payloads"][0]
    canonical_rows = import_new_release_multistore_to_sqlite.ready_payload_rows(
        ready_payload
    )
    canonical_csv = tmp_path / "canonical.csv"
    with canonical_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=import_new_release_multistore_to_sqlite.CANONICAL_FIELDNAMES,
        )
        writer.writeheader()
        writer.writerows(canonical_rows)

    engine = _engine(tmp_path)
    with Session(engine) as session:
        target = EbookItem(
            source_name="catalog",
            source_item_id="target",
            isbn="9781234567897",
            title="検証作品 2",
            item_type="tankobon",
        )
        session.add(target)
        session.commit()
        target_id = target.id

        summary = CsvImportService(session).import_file(
            canonical_csv,
            dry_run=False,
        )
        assert summary.created == 1
        offer = session.scalar(
            select(StoreOffer).where(
                StoreOffer.source_row_sha256 == expected_sha
            )
        )
        assert offer is not None
        assert offer.store_name == "rakuten_kobo"
        assert offer.verified_at is not None
        assert offer.verification_method == "RAKUTEN_KOBO_API_RESPONSE"

        service = EbookMetadataAutofillService(session)
        preview = service.preview(target_id)
        assert preview.result_for("author_name").status == "READY"
        assert preview.result_for("author_name").confidence == "VERIFIED"
        assert preview.result_for("publisher_name").status == "READY"
        assert preview.result_for("publisher_name").confidence == "VERIFIED"
        assert preview.result_for("volume_label").candidate == "第2巻"
        assert service.database_update_attempted is False

        session.expire_all()
        unchanged = session.get(EbookItem, target_id)
        assert unchanged is not None
        assert unchanged.author_name is None
        assert unchanged.publisher_name is None
        assert unchanged.volume_label is None
        assert unchanged.wordpress_post_id is None


def test_old_csv_without_metadata_or_verification_columns_remains_importable(
    tmp_path: Path,
) -> None:
    path = tmp_path / "old.csv"
    path.write_text(
        "source_item_id,title,store_name,store_item_id,product_url\n"
        "old-1,旧CSV作品,rakuten_kobo,RK-OLD,https://books.rakuten.co.jp/rk/old/\n",
        encoding="utf-8",
    )
    engine = _engine(tmp_path)
    with Session(engine) as session:
        summary = CsvImportService(session).import_file(path, dry_run=False)
        assert summary.created == 1
        item = session.scalar(select(EbookItem))
        assert item is not None
        assert item.author_name is None
        assert item.publisher_name is None
