from __future__ import annotations

from datetime import date, datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import threading
import urllib.error
import urllib.request

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.services.workflow_action_service import get_workflow_action_token


def _load_app_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "new_release_multistore_app.py"
    spec = importlib.util.spec_from_file_location("ebook_metadata_gui_app", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load GUI app module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


APP = _load_app_module()


def _start_server(repo_root: Path):
    server = APP.MultiStoreAppServer(
        ("127.0.0.1", 0), APP.MultiStoreAppHandler, repo_root=repo_root
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _stop_server(server, thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def _post_json(port: int, path: str, payload: dict[str, object]):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


@pytest.fixture
def metadata_gui(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'metadata-gui.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as session:
        target = EbookItem(
            source_name="new_release_catalog",
            source_item_id="target",
            isbn="9781234567897",
            title="SAKAMOTO DAYS 28",
            workflow_status="READY",
            review_status="NOT_REVIEWED",
            wordpress_status="DRAFT",
            wordpress_post_id=None,
            publish_ready=False,
            release_date=date(2026, 8, 4),
        )
        peer = EbookItem(
            source_name="rakuten_kobo",
            source_item_id="verified-peer",
            isbn="9781234567897",
            title="SAKAMOTO DAYS 第28巻",
            volume_label="第28巻",
            author_name="鈴木祐斗",
            publisher_name="集英社",
        )
        session.add_all((target, peer))
        session.flush()
        session.add(
            StoreOffer(
                ebook_item_id=peer.id,
                store_name="rakuten_kobo",
                store_item_id="RK-28",
                source_row_sha256="a" * 64,
                verified_at=datetime.now(timezone.utc),
                verification_method="RAKUTEN_KOBO_API_RESPONSE",
            )
        )
        session.commit()
        target_id = target.id

    import app.db.read_only_session as read_only_session
    import app.db.session as writable_session
    import app.integrations.wordpress_rest_client as wordpress_module
    import app.services.rakuten_kobo_collector as collector_module

    monkeypatch.setattr(read_only_session, "ReadOnlySessionLocal", factory)
    monkeypatch.setattr(writable_session, "SessionLocal", factory)

    def forbidden_client(*args: object, **kwargs: object) -> None:
        pytest.fail("external client must not be created by metadata GUI")

    monkeypatch.setattr(wordpress_module, "WordPressRestClient", forbidden_client)
    monkeypatch.setattr(collector_module, "RakutenKoboCollector", forbidden_client)

    server, thread = _start_server(tmp_path)
    try:
        yield engine, target_id, server.server_address[1], tmp_path
    finally:
        _stop_server(server, thread)
        engine.dispose()


def test_preview_api_returns_candidates_evidence_and_does_not_update(metadata_gui) -> None:
    engine, target_id, port, repo_root = metadata_gui
    status, payload = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/preview",
        {"csrf_token": get_workflow_action_token()},
    )

    assert status == 200
    assert payload["ebook_item_id"] == target_id
    assert payload["title"] == "SAKAMOTO DAYS 28"
    assert payload["operation"] == "PREVIEW"
    assert payload["dry_run"] is True
    assert payload["apply_possible"] is True
    assert payload["external_communication_attempted"] is False
    assert payload["wordpress_update_attempted"] is False
    assert payload["database_update_attempted"] is False
    assert payload["database_update_succeeded"] is False
    results = {result["field_name"]: result for result in payload["field_results"]}
    assert results["volume_label"]["candidate"] == "第28巻"
    assert results["author_name"]["candidate"] == "鈴木祐斗"
    assert results["publisher_name"]["candidate"] == "集英社"
    assert all(result["status"] == "READY" for result in results.values())

    evidence_path = Path(payload["evidence_path"])
    assert evidence_path.is_relative_to(repo_root)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["external_communication_attempted"] is False
    assert evidence["wordpress_update_attempted"] is False
    assert evidence["database_update_attempted"] is False
    assert evidence["database_update_succeeded"] is False
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        assert (target.volume_label, target.author_name, target.publisher_name) == (
            None,
            None,
            None,
        )


def test_apply_api_rejects_bad_confirmation_then_updates_only_metadata(metadata_gui) -> None:
    engine, target_id, port, _ = metadata_gui
    _, preview = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/preview",
        {"csrf_token": get_workflow_action_token()},
    )

    wrong_id_status, _ = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/apply",
        {
            "csrf_token": get_workflow_action_token(),
            "confirmed_fingerprint": preview["fingerprint"],
            "confirm_ebook_item_id": "other-item",
        },
    )
    wrong_fingerprint_status, wrong_fingerprint = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/apply",
        {
            "csrf_token": get_workflow_action_token(),
            "confirmed_fingerprint": "0" * 64,
            "confirm_ebook_item_id": target_id,
        },
    )
    assert wrong_id_status == 400
    assert wrong_fingerprint_status == 409
    assert wrong_fingerprint["error"]["code"] == "PREVIEW_CHANGED"
    assert wrong_fingerprint["metadata_status"] == "PREVIEW_CHANGED"
    assert wrong_fingerprint["database_update_attempted"] is False
    assert wrong_fingerprint["database_update_succeeded"] is False

    status, result = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/apply",
        {
            "csrf_token": get_workflow_action_token(),
            "confirmed_fingerprint": preview["fingerprint"],
            "confirm_ebook_item_id": target_id,
        },
    )
    assert status == 200
    assert result["operation"] == "APPLY"
    assert result["database_update_attempted"] is True
    assert result["database_update_succeeded"] is True
    assert result["external_communication_attempted"] is False
    assert result["wordpress_update_attempted"] is False
    assert {row["field_name"] for row in result["field_results"] if row["status"] == "APPLIED"} == {
        "volume_label",
        "author_name",
        "publisher_name",
    }

    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        assert (target.volume_label, target.author_name, target.publisher_name) == (
            "第28巻",
            "鈴木祐斗",
            "集英社",
        )
        assert target.title == "SAKAMOTO DAYS 28"
        assert target.isbn == "9781234567897"
        assert target.workflow_status == "READY"
        assert target.review_status == "NOT_REVIEWED"
        assert target.wordpress_status == "DRAFT"
        assert target.wordpress_post_id is None
        assert target.publish_ready is False
        assert str(target.release_date) == "2026-08-04"

    retry_status, _ = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/apply",
        {
            "csrf_token": get_workflow_action_token(),
            "confirmed_fingerprint": preview["fingerprint"],
            "confirm_ebook_item_id": target_id,
        },
    )
    assert retry_status == 409

    preview_status, completed = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/preview",
        {"csrf_token": get_workflow_action_token()},
    )
    assert preview_status == 200
    assert completed["metadata_status"] == "METADATA_ALREADY_COMPLETE"
    assert {row["status"] for row in completed["field_results"]} == {
        "ALREADY_MATCHED"
    }


def test_preview_api_returns_404_and_rejects_invalid_json(metadata_gui) -> None:
    _, _, port, _ = metadata_gui
    missing_status, missing = _post_json(
        port,
        "/api/ebooks/not-found/metadata/preview",
        {"csrf_token": get_workflow_action_token()},
    )
    invalid_status, invalid = _post_json(
        port,
        "/api/ebooks/not-found/metadata/preview",
        {"csrf_token": get_workflow_action_token(), "unexpected": True},
    )
    assert missing_status == 404
    assert missing["error"]["code"] == "ITEM_NOT_FOUND"
    assert invalid_status == 400
    assert invalid["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize(
    ("changes", "expected_reason"),
    [
        ({"review_status": "APPROVED"}, "REVIEW_STATUS_PROTECTED"),
        ({"publish_ready": True}, "PUBLISH_READY_PROTECTED"),
        ({"wordpress_post_id": "205"}, "WORDPRESS_DRAFT_EXISTS"),
    ],
)
def test_preview_blocks_protected_workflow_state_without_changes(
    metadata_gui,
    changes: dict[str, object],
    expected_reason: str,
) -> None:
    engine, target_id, port, _ = metadata_gui
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        for field_name, value in changes.items():
            setattr(target, field_name, value)
        session.commit()
        session.refresh(target)
        before = {
            column.name: getattr(target, column.name)
            for column in EbookItem.__table__.columns
        }

    status, payload = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/preview",
        {"csrf_token": get_workflow_action_token()},
    )

    assert status == 200
    assert payload["apply_possible"] is False
    assert payload["metadata_status"] == "WORKFLOW_STATE_PROTECTED"
    assert expected_reason in payload["protection_reasons"]
    assert payload["database_update_attempted"] is False
    assert payload["database_update_succeeded"] is False
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        assert {
            column.name: getattr(target, column.name)
            for column in EbookItem.__table__.columns
        } == before


@pytest.mark.parametrize(
    ("changes", "expected_reason"),
    [
        ({"review_status": "APPROVED"}, "REVIEW_STATUS_PROTECTED"),
        ({"publish_ready": True}, "PUBLISH_READY_PROTECTED"),
        ({"wordpress_post_id": "207"}, "WORDPRESS_DRAFT_EXISTS"),
    ],
)
def test_apply_revalidates_workflow_state_before_repository_call(
    metadata_gui,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, object],
    expected_reason: str,
) -> None:
    from app.db.repositories.ebook_metadata_autofill_repository import (
        EbookMetadataAutofillRepository,
    )

    engine, target_id, port, repo_root = metadata_gui
    _, preview = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/preview",
        {"csrf_token": get_workflow_action_token()},
    )
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        for field_name, value in changes.items():
            setattr(target, field_name, value)
        session.commit()

    def forbidden_apply(*args: object, **kwargs: object) -> None:
        pytest.fail("repository apply must not run for protected GUI state")

    monkeypatch.setattr(
        EbookMetadataAutofillRepository,
        "apply_empty_fields",
        forbidden_apply,
    )
    status, payload = _post_json(
        port,
        f"/api/ebooks/{target_id}/metadata/apply",
        {
            "csrf_token": get_workflow_action_token(),
            "confirmed_fingerprint": preview["fingerprint"],
            "confirm_ebook_item_id": target_id,
        },
    )

    assert status == 409
    assert payload["error"]["code"] == "WORKFLOW_STATE_PROTECTED"
    assert payload["metadata_status"] == "WORKFLOW_STATE_PROTECTED"
    assert expected_reason in payload["protection_reasons"]
    assert payload["database_update_attempted"] is False
    assert payload["database_update_succeeded"] is False
    evidence_path = Path(payload["evidence_path"])
    assert evidence_path.is_relative_to(repo_root)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert expected_reason in evidence["protection_reasons"]
    assert evidence["database_update_attempted"] is False
    assert evidence["database_update_succeeded"] is False
    with Session(engine) as session:
        target = session.get(EbookItem, target_id)
        assert target is not None
        assert (target.volume_label, target.author_name, target.publisher_name) == (
            None,
            None,
            None,
        )


def test_gui_script_contains_accessible_states_and_double_submit_guards() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "gui"
        / "ebook_metadata_autofill.js"
    ).read_text(encoding="utf-8")

    assert 'button.textContent = "読み込み中"' in script
    assert 'applyButton.textContent = "処理中"' in script
    assert "apply.disabled = !payload.apply_possible" in script
    assert "SQLへ反映" in script
    assert "状態:" in script
    assert "metadata-state-green" in script
    assert "metadata-state-yellow" in script
    assert "metadata-state-orange" in script
    assert "metadata-state-red" in script
    assert "metadata-state-gray" in script


def test_preview_prefills_only_basic_edit_fields_without_saving() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "gui"
        / "ebook_metadata_autofill.js"
    ).read_text(encoding="utf-8")
    selector = script.split("function previewPrefillValues", 1)[1].split(
        "function formHasUnsavedChanges", 1
    )[0]
    prefill = script.split("function prefillCatalogEditForm", 1)[1].split(
        "function renderResult", 1
    )[0]
    render = script.split("function renderResult", 1)[1].split(
        "async function postJson", 1
    )[0]

    assert '"基本情報を編集へ反映"' in render
    assert 'payload.operation === "PREVIEW"' in render
    assert "payload.apply_possible" not in render.split(
        '"基本情報を編集へ反映"', 1
    )[0].rsplit('payload.operation === "PREVIEW"', 1)[1]
    assert '["ALREADY_MATCHED", "EXISTING_VALUE_PRESERVED"]' in selector
    assert "values[result.field_name] = result.before" in selector
    assert '["CANDIDATE_AVAILABLE", "READY"]' in selector
    assert "values[result.field_name] = result.candidate" in selector
    assert 'result.status === "CONFLICT"' not in selector
    assert '["volume_label", "author_name", "publisher_name"]' in selector
    assert 'targetId.value !== payload.ebook_item_id' in prefill
    assert 'volume_label: "volume_label"' in prefill
    assert 'author_name: "authors"' in prefill
    assert 'publisher_name: "publisher"' in prefill
    assert 'window.confirm("現在の未保存内容をプレビュー値で置き換えますか？")' in prefill
    assert "formHasUnsavedChanges(form) &&" in prefill
    assert "details.open = true" in prefill
    assert "まだDBには保存されていません" in prefill
    assert "postJson(" not in prefill


def test_catalog_volume_normalizer_is_wired_to_blur_and_submit_only() -> None:
    script = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "gui"
        / "ebook_metadata_autofill.js"
    ).read_text(encoding="utf-8")
    normalizer = script.split("function normalizeVolumeLabel", 1)[1].split(
        "function normalizeCatalogVolumeInput", 1
    )[0]
    wiring = script.split(
        'if (document.documentElement.dataset.volumeLabelNormalizerBound', 1
    )[1].split("function stateClass", 1)[0]

    assert '.normalize("NFKC")' in normalizer
    assert "romanVolumeNumber" in normalizer
    assert "kanjiVolumeNumber" in normalizer
    assert "number > 0" in normalizer
    assert 'document.addEventListener("blur"' in wiring
    assert 'document.addEventListener("submit"' in wiring
    assert ".catalog-edit-form" in wiring
    assert 'input[name="volume_label"]' in wiring
    assert 'form.elements.namedItem("volume_label")' in wiring
    assert "volumeLabelNormalizerBound" in wiring
    assert "postJson(" not in wiring
    assert "fetch(" not in wiring
    assert "is_single_episode" not in wiring
    assert "is_split_edition" not in wiring
