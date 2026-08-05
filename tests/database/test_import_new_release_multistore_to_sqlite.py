from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from scripts.database import import_new_release_multistore_to_sqlite as runner


SAFETY = {
    "external_network_performed": False,
    "wordpress_write_performed": False,
    "wordpress_publish_performed": False,
    "input_status_fixed_to_draft": True,
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _ready_payload(batch_id: str, index: int) -> dict:
    item_id = f"READY_{index:04d}"
    return {
        "schema_version": "2.0.0",
        "phase_id": "LS-NEW-BATCH-MULTISTORE-V2-IMPORT",
        "input_contract_id": "FRESH_NEW_RELEASE_COMIC_MULTISTORE_INPUT_V2",
        "source_schema_id": "NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2",
        "batch_id": batch_id,
        "content_item_id": item_id,
        "article_type": "electronic_book_new_release",
        "primary_category": "コミック",
        "title": f"新刊コミック {index}",
        "display_title": f"新刊コミック {index}",
        "volume_label": f"第{index}巻",
        "release_date": "2026-08-01",
        "publisher": "テスト出版",
        "authors": ["著者A"],
        "identifiers": {},
        "store_navigation": [
            {
                "key": "rakuten_kobo",
                "label": "楽天Koboで確認",
                "url": f"https://books.rakuten.co.jp/{item_id.lower()}/",
            }
        ],
        "wordpress": {
            "status": "draft",
            "write_allowed": False,
            "publish_allowed": False,
        },
        "safety": {
            **SAFETY,
            "human_review_required_before_write": True,
        },
    }


def _build_batch(
    tmp_path: Path,
    *,
    ready_count: int = 466,
    blocked_count: int = 39,
    warning_count: int = 466,
) -> Path:
    repository_root = tmp_path / "repo"
    batch_id = "RK_202608_TEST"
    batch_dir = (
        repository_root
        / "exchange"
        / "inputs"
        / "new_release"
        / "batches"
        / batch_id
    )
    item_paths: list[str] = []
    for index in range(ready_count):
        payload = _ready_payload(batch_id, index)
        item_path = (
            batch_dir
            / "items"
            / f"{payload['content_item_id']}.input.json"
        )
        _write_json(item_path, payload)
        item_paths.append(str(item_path.resolve()))

    blocked_rows = [
        {
            "row_number": ready_count + index + 2,
            "item_id": f"BLOCKED_{index:04d}",
            "batch_id": batch_id,
            "error": {
                "code": "SINGLE_EPISODE_FORBIDDEN",
                "message": "single episode is blocked",
                "field": "edition_type",
            },
        }
        for index in range(blocked_count)
    ]
    blocked_path = (
        repository_root
        / "exchange"
        / "reviews"
        / "new_release"
        / "batches"
        / f"{batch_id}.multistore_blocked.json"
    )
    result_log_path = (
        repository_root
        / "exchange"
        / "logs"
        / f"{batch_id}.multistore_import_result.json"
    )
    manifest_path = batch_dir / "manifest.json"
    manifest = {
        "status": "PASS_WITH_BLOCKED_ROWS",
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "warning_count": warning_count,
        "batch_ids": [batch_id],
        "manifest_path": str(manifest_path.resolve()),
        "blocked_path": str(blocked_path.resolve()),
        "result_log_path": str(result_log_path.resolve()),
        "item_paths": item_paths,
        "safety": SAFETY,
    }
    blocked = {
        "status": "PASS_WITH_BLOCKED_ROWS",
        "batch_id": batch_id,
        "blocked_path": str(blocked_path.resolve()),
        "blocked_rows": blocked_rows,
        "warning_count": warning_count,
        "safety": SAFETY,
    }
    result_log = {
        "status": "PASS_WITH_BLOCKED_ROWS",
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "warning_count": warning_count,
        "batch_ids": [batch_id],
        "manifest_path": str(manifest_path.resolve()),
        "blocked_path": str(blocked_path.resolve()),
        "result_log_path": str(result_log_path.resolve()),
        "safety": SAFETY,
    }
    _write_json(manifest_path, manifest)
    _write_json(blocked_path, blocked)
    _write_json(result_log_path, result_log)
    return manifest_path


def _database(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    return engine


def _counts(engine) -> tuple[int, int]:
    with Session(engine) as session:
        return (
            session.scalar(select(func.count()).select_from(EbookItem)) or 0,
            session.scalar(select(func.count()).select_from(StoreOffer)) or 0,
        )


def test_load_realistic_manifest_preserves_ready_blocked_and_warning_evidence(
    tmp_path: Path,
) -> None:
    batch = runner.load_ready_batch(_build_batch(tmp_path))

    assert batch.ready_input_count == 466
    assert len(batch.ready_payloads) == 466
    assert batch.blocked_count == 39
    assert len(batch.blocked_rows) == 39
    assert batch.warning_count == 466
    assert batch.blocked_reasons == (
        {
            "code": "SINGLE_EPISODE_FORBIDDEN",
            "message": "single episode is blocked",
            "field": "edition_type",
            "count": 39,
        },
    )


def test_dry_run_processes_only_466_ready_items_without_database_changes(
    tmp_path: Path,
) -> None:
    batch = runner.load_ready_batch(_build_batch(tmp_path))
    engine = _database(tmp_path)

    with Session(engine) as session:
        summary = runner.import_ready_batch(session, batch)

    assert summary.ready_input_count == 466
    assert summary.blocked_count == 39
    assert summary.warning_count == 466
    assert summary.processed == 466
    assert summary.created == 466
    assert summary.updated == 0
    assert summary.unchanged == 0
    assert summary.created + summary.updated + summary.unchanged == 466
    assert summary.offer_created == 466
    assert summary.offer_updated == 0
    assert summary.failed == 0
    assert summary.database_write_performed is False
    assert summary.external_network_performed is False
    assert _counts(engine) == (0, 0)


def test_execute_commits_ready_only_preserves_existing_rows_and_is_idempotent(
    tmp_path: Path,
) -> None:
    batch = runner.load_ready_batch(_build_batch(tmp_path))
    engine = _database(tmp_path)
    with Session(engine) as session:
        for index in range(4):
            session.add(
                EbookItem(
                    source_name="existing",
                    source_item_id=f"existing-{index}",
                    title=f"Existing {index}",
                    item_type="tankobon",
                )
            )
        session.commit()

    with Session(engine) as session:
        first = runner.import_ready_batch(session, batch, execute=True)
    assert first.created == 466
    assert first.updated == 0
    assert first.unchanged == 0
    assert first.database_write_performed is True
    assert _counts(engine) == (470, 466)

    with Session(engine) as session:
        second = runner.import_ready_batch(session, batch, execute=True)
    assert second.created == 0
    assert second.updated == 0
    assert second.unchanged == 466
    assert second.created + second.updated + second.unchanged == 466
    assert second.offer_created == 0
    assert second.offer_updated == 0
    assert second.offer_unchanged == 466
    assert second.database_write_performed is False
    assert _counts(engine) == (470, 466)

    with Session(engine) as session:
        existing_titles = session.scalars(
            select(EbookItem.title).where(EbookItem.source_name == "existing")
        ).all()
        imported = session.scalars(
            select(EbookItem).where(
                EbookItem.source_name == "new_release_multistore"
            )
        ).all()
        amazon_offers = session.scalars(
            select(StoreOffer).where(StoreOffer.store_name == "amazon")
        ).all()
    assert existing_titles == [f"Existing {index}" for index in range(4)]
    assert len(imported) == 466
    assert all(item.wordpress_status == "DRAFT" for item in imported)
    assert amazon_offers == []


def test_not_found_amazon_remains_absent_and_is_never_synthesized(
    tmp_path: Path,
) -> None:
    batch = runner.load_ready_batch(_build_batch(tmp_path, ready_count=1, blocked_count=0, warning_count=1))
    rows = runner.ready_payload_rows(batch.ready_payloads[0])

    assert batch.ready_payloads[0]["identifiers"] == {}
    assert [row["store_name"] for row in rows] == ["rakuten_kobo"]
    assert all("amazon" not in row["store_item_id"] for row in rows)
    assert all(row["affiliate_url"] == "" for row in rows)


def test_mid_import_failure_rolls_back_every_ready_item(tmp_path: Path) -> None:
    batch = runner.load_ready_batch(
        _build_batch(tmp_path, ready_count=3, blocked_count=1, warning_count=3)
    )
    broken_payloads = [dict(payload) for payload in batch.ready_payloads]
    broken_payloads[1]["release_date"] = "not-a-date"
    broken_batch = replace(batch, ready_payloads=tuple(broken_payloads))
    engine = _database(tmp_path)

    with Session(engine) as session:
        with pytest.raises(ValueError, match="Ready artifact import failed"):
            runner.import_ready_batch(session, broken_batch, execute=True)

    assert _counts(engine) == (0, 0)


def test_commit_is_called_only_for_execute(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch = runner.load_ready_batch(
        _build_batch(tmp_path, ready_count=1, blocked_count=0, warning_count=1)
    )

    class FakeSession:
        def __init__(self) -> None:
            self.commit_calls = 0
            self.rollback_calls = 0

        def commit(self) -> None:
            self.commit_calls += 1

        def rollback(self) -> None:
            self.rollback_calls += 1

    class FakeRepository:
        def __init__(self, _session) -> None:
            pass

        def import_row(self, _row):
            return SimpleNamespace(
                created=True,
                updated=False,
                unchanged=False,
                offer_created=True,
                offer_updated=False,
                offer_unchanged=False,
            )

    monkeypatch.setattr(runner, "ImportRepository", FakeRepository)
    dry_session = FakeSession()
    runner.import_ready_batch(dry_session, batch)
    assert dry_session.commit_calls == 0
    assert dry_session.rollback_calls == 1

    execute_session = FakeSession()
    runner.import_ready_batch(execute_session, batch, execute=True)
    assert execute_session.commit_calls == 1
    assert execute_session.rollback_calls == 0


def test_main_defaults_to_dry_run_and_reports_requested_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = _build_batch(tmp_path)
    engine = _database(tmp_path)
    monkeypatch.setattr(runner, "SessionLocal", lambda: Session(engine))

    assert runner.main(["--batch-dir", str(manifest_path.parent)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "DRY_RUN"
    assert result["ready_input_count"] == 466
    assert result["blocked_count"] == 39
    assert result["warning_count"] == 466
    assert result["processed"] == 466
    assert result["created"] == 466
    assert result["updated"] == 0
    assert result["unchanged"] == 0
    assert result["offer_created"] == 466
    assert result["offer_updated"] == 0
    assert result["failed"] == 0
    assert result["database_write_performed"] is False
    assert result["external_network_performed"] is False
    assert result["blocked_reasons"][0]["count"] == 39
    assert _counts(engine) == (0, 0)


def test_legacy_csv_execute_is_refused_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_csv = tmp_path / "unvalidated.csv"
    input_csv.write_text("item_id,title,release_date\n1,Title,2026-08-01\n")
    monkeypatch.setattr(
        runner,
        "SessionLocal",
        lambda: pytest.fail("database must not be opened"),
    )

    with pytest.raises(RuntimeError, match="Legacy CSV --execute is refused"):
        runner.main([str(input_csv), "--execute"])


@pytest.mark.parametrize("mutation", ["missing", "corrupt", "wrong_count"])
def test_invalid_manifest_is_rejected_before_database_access(
    tmp_path: Path,
    mutation: str,
) -> None:
    manifest_path = _build_batch(tmp_path, ready_count=1, blocked_count=0, warning_count=1)
    if mutation == "missing":
        manifest_path.unlink()
    elif mutation == "corrupt":
        manifest_path.write_text("{broken", encoding="utf-8")
    else:
        manifest = json.loads(manifest_path.read_text())
        manifest["ready_count"] = 2
        _write_json(manifest_path, manifest)

    with pytest.raises(runner.ManifestValidationError):
        runner.load_ready_batch(manifest_path)


def test_manifest_item_path_cannot_escape_batch_items_directory(tmp_path: Path) -> None:
    manifest_path = _build_batch(tmp_path, ready_count=1, blocked_count=0, warning_count=1)
    manifest = json.loads(manifest_path.read_text())
    outside = manifest_path.parents[5] / "outside.input.json"
    _write_json(outside, _ready_payload("RK_202608_TEST", 0))
    manifest["item_paths"] = [str(outside.resolve())]
    _write_json(manifest_path, manifest)

    with pytest.raises(
        runner.ManifestValidationError,
        match="escapes the batch items directory",
    ):
        runner.load_ready_batch(manifest_path)
