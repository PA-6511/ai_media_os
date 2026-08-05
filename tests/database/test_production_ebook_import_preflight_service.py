from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.services.csv_import_service import CsvImportService
from app.services.production_ebook_import_preflight_service import (
    PRODUCTION_CREATE_ONLY,
    ProductionCreateOnlyImportError,
    ProductionEbookImportPreflightService,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = (
    ROOT
    / "exchange/manual_input/lv999_21/20260723/"
    "lv999_21_corrected_import.csv"
)
CONTRACT = ROOT / "config/canonical_ebook_import_csv_contract.json"
MANIFEST = ARTIFACT.with_suffix(".manifest.json")
EVIDENCE = ARTIFACT.with_name("lv999_21_url_runtime_validation.json")


def read_row(path: Path = ARTIFACT) -> tuple[list[str], dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), {
            key: str(value or "") for key, value in rows[0].items()
        }


def write_row(path: Path, header: list[str], row: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerow(row)


def prepare_case(
    tmp_path: Path,
    *,
    row_updates: dict[str, str] | None = None,
    header_updates: list[str] | None = None,
) -> tuple[Path, Path]:
    header, row = read_row()
    if row_updates:
        row.update(row_updates)
    if header_updates is not None:
        header = header_updates
    artifact = tmp_path / "candidate.csv"
    write_row(artifact, header, row)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["artifact_path"] = str(artifact)
    manifest["artifact_sha256"] = sha256_file(artifact)
    manifest_path = tmp_path / "candidate.manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact, manifest_path


def create_engine_and_database(tmp_path: Path):
    database = tmp_path / "database.sqlite"
    engine = create_engine(f"sqlite+pysqlite:///{database}", future=True)
    Base.metadata.create_all(engine)
    return database, engine


def strict_import(
    session: Session,
    artifact: Path,
    manifest: Path,
):
    return ProductionEbookImportPreflightService(session).import_file(
        artifact,
        contract_path=CONTRACT,
        manifest_path=manifest,
        runtime_evidence_path=EVIDENCE,
        import_mode=PRODUCTION_CREATE_ONLY,
    )


def database_snapshot(session: Session) -> tuple[list[tuple], list[tuple]]:
    items = [
        (
            item.id,
            item.source_item_id,
            item.isbn,
            item.title,
            item.volume_label,
            item.updated_at,
        )
        for item in session.scalars(select(EbookItem).order_by(EbookItem.id))
    ]
    offers = [
        (
            offer.id,
            offer.ebook_item_id,
            offer.store_name,
            offer.store_item_id,
            offer.product_url,
            offer.affiliate_url,
            offer.price_yen,
            offer.last_checked_at,
        )
        for offer in session.scalars(select(StoreOffer).order_by(StoreOffer.id))
    ]
    return items, offers


def test_create_only_import_succeeds_with_expected_initial_state(
    tmp_path: Path,
) -> None:
    artifact, manifest = prepare_case(tmp_path)
    database, engine = create_engine_and_database(tmp_path)
    with Session(engine) as session:
        result = strict_import(session, artifact, manifest)
        assert result.mode == PRODUCTION_CREATE_ONLY
        assert result.url_runtime_validation == "PASS"
        assert result.summary.created == 1
        assert result.summary.offer_created == 1
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EbookItem)) == 1
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 1
        item = session.scalar(select(EbookItem))
        offer = session.scalar(select(StoreOffer))
        assert item is not None and offer is not None
        assert item.source_item_id == "rakuten-kobo-4335914300320"
        assert item.isbn == "9784041176788"
        assert item.title == "LV999の村人"
        assert item.volume_label == "第21巻"
        assert item.item_type == "tankobon"
        assert item.is_excluded is False
        assert item.workflow_status == "NEW"
        assert item.review_status == "NOT_REVIEWED"
        assert item.wordpress_status == "NOT_CREATED"
        assert item.x_status == "NOT_CREATED"
        assert item.publish_ready is False
        assert offer.store_name == "rakuten_kobo"
        assert offer.store_item_id == "4335914300320"
        assert offer.price_yen == 924
    assert database.is_file()
    engine.dispose()


def test_normal_csv_upsert_behavior_is_preserved(tmp_path: Path) -> None:
    artifact, _ = prepare_case(tmp_path)
    _, engine = create_engine_and_database(tmp_path)
    with Session(engine) as session:
        first = CsvImportService(session).import_file(artifact, dry_run=False)
    header, row = read_row(artifact)
    row["price"] = "925"
    write_row(artifact, header, row)
    with Session(engine) as session:
        second = CsvImportService(session).import_file(artifact, dry_run=False)
        offer = session.scalar(select(StoreOffer))
        assert second.updated == 1
        assert second.offer_updated == 1
        assert offer is not None and offer.price_yen == 925
    engine.dispose()


def test_create_only_summary_failure_rolls_back_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact, manifest = prepare_case(tmp_path)
    _, engine = create_engine_and_database(tmp_path)
    original_import_file = CsvImportService.import_file

    def return_inconsistent_summary(
        service: CsvImportService,
        input_path: Path,
        *,
        dry_run: bool = True,
        commit: bool = True,
    ):
        summary = original_import_file(
            service,
            input_path,
            dry_run=dry_run,
            commit=commit,
        )
        summary.updated = 1
        return summary

    monkeypatch.setattr(
        CsvImportService,
        "import_file",
        return_inconsistent_summary,
    )
    with Session(engine) as session:
        with pytest.raises(ProductionCreateOnlyImportError) as raised:
            strict_import(session, artifact, manifest)
        assert raised.value.code == "IMPORT_CREATE_ONLY_SUMMARY_INVALID"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EbookItem)) == 0
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0
    engine.dispose()


DuplicateSeed = Callable[[dict[str, str]], dict[str, str]]


def _source_duplicate(row: dict[str, str]) -> dict[str, str]:
    return row


def _isbn_duplicate(row: dict[str, str]) -> dict[str, str]:
    return {
        **row,
        "source_item_id": "seed-isbn",
        "title": "ISBNだけ同じ別作品",
        "volume_label": "第1巻",
        "store_item_id": "seed-isbn-offer",
        "item_url": "https://example.com/isbn-seed",
        "affiliate_url": "https://example.com/isbn-seed-affiliate",
        "isbn": "978-4-04-117678-8",
    }


def _title_volume_duplicate(row: dict[str, str]) -> dict[str, str]:
    return {
        **row,
        "source_item_id": "seed-title-volume",
        "isbn": "9780000000001",
        "store_item_id": "seed-title-volume-offer",
        "item_url": "https://example.com/title-volume-seed",
        "affiliate_url": "https://example.com/title-volume-seed-affiliate",
        "title": "  LV999の村人  ",
        "volume_label": "　第21巻　",
    }


def _store_item_duplicate(row: dict[str, str]) -> dict[str, str]:
    return {
        **row,
        "source_item_id": "seed-store-item",
        "isbn": "9780000000002",
        "title": "店舗IDだけ同じ別作品",
        "volume_label": "第1巻",
        "item_url": "https://example.com/store-item-seed",
        "affiliate_url": "https://example.com/store-item-seed-affiliate",
    }


def _product_url_duplicate(row: dict[str, str]) -> dict[str, str]:
    return {
        **row,
        "source_item_id": "seed-product-url",
        "isbn": "9780000000003",
        "title": "商品URLだけ同じ別作品",
        "volume_label": "第1巻",
        "store_item_id": "seed-product-url-offer",
        "affiliate_url": "https://example.com/product-url-seed-affiliate",
        "item_url": row["item_url"].rstrip("/") + "#details",
    }


def _affiliate_url_duplicate(row: dict[str, str]) -> dict[str, str]:
    return {
        **row,
        "source_item_id": "seed-affiliate-url",
        "isbn": "9780000000004",
        "title": "アフィリエイトURLだけ同じ別作品",
        "volume_label": "第1巻",
        "store_item_id": "seed-affiliate-url-offer",
        "item_url": "https://example.com/affiliate-url-seed",
    }


@pytest.mark.parametrize(
    ("seed_builder", "error_code"),
    [
        (_source_duplicate, "DUPLICATE_SOURCE_ITEM_ID"),
        (_isbn_duplicate, "DUPLICATE_ISBN"),
        (_title_volume_duplicate, "DUPLICATE_TITLE_VOLUME"),
        (_store_item_duplicate, "DUPLICATE_STORE_ITEM"),
        (_product_url_duplicate, "DUPLICATE_PRODUCT_URL"),
        (_affiliate_url_duplicate, "DUPLICATE_AFFILIATE_URL"),
    ],
)
def test_create_only_duplicate_guards_reject_without_mutation(
    tmp_path: Path,
    seed_builder: DuplicateSeed,
    error_code: str,
) -> None:
    artifact, manifest = prepare_case(tmp_path)
    header, original_row = read_row(artifact)
    seed_path = tmp_path / "seed.csv"
    write_row(seed_path, header, seed_builder(original_row))
    _, engine = create_engine_and_database(tmp_path)
    with Session(engine) as session:
        CsvImportService(session).import_file(seed_path, dry_run=False)
    with Session(engine) as session:
        before = database_snapshot(session)
    with Session(engine) as session:
        with pytest.raises(ProductionCreateOnlyImportError) as raised:
            strict_import(session, artifact, manifest)
        assert raised.value.code == error_code
    with Session(engine) as session:
        assert database_snapshot(session) == before
        assert session.scalar(select(func.count()).select_from(EbookItem)) == 1
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 1
    engine.dispose()


@pytest.mark.parametrize(
    ("field", "url", "error_code"),
    [
        ("item_url", "http://example.com/book", "PRODUCT_URL_HTTPS_REQUIRED"),
        ("affiliate_url", "http://example.com/aff", "AFFILIATE_URL_HTTPS_REQUIRED"),
        ("item_url", "javascript:alert(1)", "PRODUCT_URL_HTTPS_REQUIRED"),
        ("item_url", "file:///tmp/book", "PRODUCT_URL_HTTPS_REQUIRED"),
        ("item_url", "https://localhost/book", "URL_LOCAL_PRIVATE_ADDRESS_FORBIDDEN"),
        ("item_url", "https://127.0.0.1/book", "URL_LOCAL_PRIVATE_ADDRESS_FORBIDDEN"),
        ("item_url", "https://192.168.1.5/book", "URL_LOCAL_PRIVATE_ADDRESS_FORBIDDEN"),
        ("item_url", "https://169.254.1.5/book", "URL_LOCAL_PRIVATE_ADDRESS_FORBIDDEN"),
        ("item_url", "https://user:pass@example.com/book", "URL_USERINFO_FORBIDDEN"),
        ("item_url", "https://example.com/book\nunsafe", "URL_CONTROL_CHARACTER_FORBIDDEN"),
    ],
)
def test_unsafe_urls_are_rejected_before_import(
    tmp_path: Path,
    field: str,
    url: str,
    error_code: str,
) -> None:
    artifact, manifest = prepare_case(tmp_path, row_updates={field: url})
    _, engine = create_engine_and_database(tmp_path)
    with Session(engine) as session:
        with pytest.raises(ProductionCreateOnlyImportError) as raised:
            strict_import(session, artifact, manifest)
        assert raised.value.code == error_code
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EbookItem)) == 0
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0
    engine.dispose()


def test_missing_contract_is_rejected(tmp_path: Path) -> None:
    artifact, manifest = prepare_case(tmp_path)
    _, engine = create_engine_and_database(tmp_path)
    with Session(engine) as session:
        with pytest.raises(ProductionCreateOnlyImportError) as raised:
            ProductionEbookImportPreflightService(session).import_file(
                artifact,
                contract_path=tmp_path / "missing-contract.json",
                manifest_path=manifest,
                runtime_evidence_path=EVIDENCE,
                import_mode=PRODUCTION_CREATE_ONLY,
            )
        assert raised.value.code == "IMPORT_SCHEMA_CONTRACT_REQUIRED"
    engine.dispose()


def test_parallel_create_only_imports_create_once(tmp_path: Path) -> None:
    artifact, manifest = prepare_case(tmp_path)
    _, engine = create_engine_and_database(tmp_path)

    def attempt() -> str:
        with Session(engine) as session:
            try:
                strict_import(session, artifact, manifest)
            except ProductionCreateOnlyImportError as exc:
                return exc.code
        return "PASS"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: attempt(), range(2)))

    assert sorted(outcomes) == ["DUPLICATE_SOURCE_ITEM_ID", "PASS"]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(EbookItem)) == 1
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 1
    engine.dispose()


def test_missing_manifest_is_rejected(tmp_path: Path) -> None:
    artifact, _ = prepare_case(tmp_path)
    _, engine = create_engine_and_database(tmp_path)
    with Session(engine) as session:
        with pytest.raises(ProductionCreateOnlyImportError) as raised:
            ProductionEbookImportPreflightService(session).import_file(
                artifact,
                contract_path=CONTRACT,
                manifest_path=tmp_path / "missing-manifest.json",
                runtime_evidence_path=EVIDENCE,
                import_mode=PRODUCTION_CREATE_ONLY,
            )
        assert raised.value.code == "IMPORT_MANIFEST_REQUIRED"
    engine.dispose()


def test_csv_sha256_mismatch_is_rejected(tmp_path: Path) -> None:
    artifact, manifest = prepare_case(tmp_path)
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    _, engine = create_engine_and_database(tmp_path)
    with Session(engine) as session:
        with pytest.raises(ProductionCreateOnlyImportError) as raised:
            strict_import(session, artifact, manifest)
        assert raised.value.code == "IMPORT_ARTIFACT_SHA256_MISMATCH"
    engine.dispose()


def test_header_mismatch_is_rejected(tmp_path: Path) -> None:
    header, _ = read_row()
    artifact, manifest = prepare_case(
        tmp_path,
        header_updates=header[:-1],
    )
    _, engine = create_engine_and_database(tmp_path)
    with Session(engine) as session:
        with pytest.raises(ProductionCreateOnlyImportError) as raised:
            strict_import(session, artifact, manifest)
        assert raised.value.code == "IMPORT_SCHEMA_HEADER_MISMATCH"
    engine.dispose()
