from __future__ import annotations

import importlib.util
import json
import logging
import os
import re
from types import ModuleType, SimpleNamespace
import threading
import socket
import subprocess
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from app.services.workflow_action_service import (
    get_workflow_action_token,
)


def _load_app_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "new_release_multistore_app.py"
    spec = importlib.util.spec_from_file_location("new_release_multistore_app", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load app module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


app = _load_app_module()


@pytest.fixture(autouse=True)
def isolate_gui_rendering_from_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route redirects render with explicit fixtures, never production data."""

    import app.gui.ebook_database_web as web

    monkeypatch.setattr(
        web,
        "load_pending_review_ready_approvals",
        lambda _ids: {},
    )
    monkeypatch.setattr(
        web,
        "load_approved_review_ready_approvals",
        lambda _ids: {},
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_draft_execution_states",
        lambda _ids: {},
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_schedule_states",
        lambda _ids: {},
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_category_context",
        lambda _rows: web.WordPressCategoryPageContext(
            categories=[],
            item_states={},
        ),
    )


def _dashboard_fixture() -> dict:
    return {
        "cards": {
            "today_release": 0,
            "tomorrow_release": 0,
            "this_week_release": 0,
            "this_month_release": 0,
            "missing_price": 0,
            "missing_affiliate": 0,
            "excluded": 0,
        },
        "dates": {
            "today": "2026-07-20",
            "tomorrow": "2026-07-21",
            "week_end": "2026-07-26",
            "month_start": "2026-07-01",
            "month_end": "2026-07-31",
        },
        "database": {
            "total_items": 0,
            "store_count": 0,
            "latest_import_at": None,
        },
    }


def _search_row(**overrides):
    values = {
        "id": "ebook-1",
        "source_item_id": "4310000000001",
        "title": "GIANT KILLING",
        "volume_label": "第66巻",
        "author_name": "ツジトモ",
        "publisher_name": "講談社",
        "release_date": "2026-07-20",
        "item_type": "tankobon",
        "store_names": "rakuten_kobo",
        "prices": "rakuten_kobo:792",
        "affiliate_count": 1,
        "amazon_affiliate_ready": False,
        "rakuten_kobo_affiliate_ready": True,
        "dmm_affiliate_ready": False,
        "affiliate_ready_count": 1,
        "workflow_status": "READY",
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": "",
        "x_status": "NOT_CREATED",
        "affiliate_status": "READY",
        "image_status": "UNCHECKED",
        "review_status": "APPROVED",
        "publish_ready": False,
        "last_error": "",
        "is_excluded": False,
    }
    values.update(overrides)
    return values


def _sample_csv_text() -> str:
    return (
        "batch_id,item_id,title,release_date,category,rakuten_kobo_url,image_url,wordpress_status,schema_id,record_status,publish_ready,pr_required,price_notice_required,dmm_match_status,amazon_match_status,source_row_sha256\n"
        "BATCH1,ITEM1,タイトルA,2026-07-13,comic,https://books.rakuten.co.jp/rk1,https://example.com/img.jpg,draft,NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2,READY_FOR_DRAFT,true,true,true,,,sha256\n"
    )


def _fake_engine_result() -> dict:
    return {
        "status": "PASS",
        "ready_payloads": [
            {
                "content_item_id": "ITEM1",
                "title": "Title A",
                "batch_id": "BATCH1",
            }
        ],
        "blocked_rows": [],
        "warnings": [],
        "ready_count": 1,
        "blocked_count": 0,
        "warning_count": 0,
        "batch_ids": ["BATCH1"],
        "safety": {
            "wordpress_write_performed": False,
            "wordpress_publish_performed": False,
            "external_network_performed": False,
            "input_status_fixed_to_draft": True,
        },
    }


def _engine_result_for_batch(batch_id: str) -> dict:
    result = _fake_engine_result()
    result["batch_ids"] = [batch_id]
    result["ready_payloads"][0]["batch_id"] = batch_id
    return result


def _bridge_raw_result() -> dict:
    return {
        "status": "PASS",
        "source_csv_path": "/tmp/sample.csv",
        "ready_payloads": [
            {
                "batch_id": "test_batch",
                "content_item_id": "test_item_001",
                "title": "Bridge Title",
            }
        ],
        "blocked_rows": [],
        "warnings": [],
        "structure_errors": [],
        "batch_ids": ["test_batch"],
        "ready_count": 1,
        "blocked_count": 0,
        "warning_count": 0,
        "safety": {
            "wordpress_write_performed": False,
            "wordpress_publish_performed": False,
            "external_network_performed": False,
            "input_status_fixed_to_draft": True,
        },
    }


def _realistic_batch_result(
    *,
    batch_id: str = "RK_202608_TEST",
    ready_count: int = 466,
    blocked_count: int = 39,
) -> dict:
    warnings = [
        {
            "code": "AMAZON_OMITTED_PENDING_MANUAL_CONFIRMATION",
            "message": "Amazon link is omitted pending manual confirmation.",
            "item_id": f"ready-{index:03d}",
        }
        for index in range(ready_count)
    ]
    return {
        "status": "PASS_WITH_BLOCKED_ROWS",
        "source_csv_path": "/tmp/realistic.csv",
        "ready_payloads": [
            {
                "batch_id": batch_id,
                "content_item_id": f"ready-{index:03d}",
                "title": f"新刊 {index}",
                "wordpress": {"status": "draft"},
                "identifiers": {},
                "store_navigation": [
                    {
                        "key": "rakuten_kobo",
                        "url": f"https://books.rakuten.co.jp/ready-{index:03d}",
                    }
                ],
            }
            for index in range(ready_count)
        ],
        "blocked_rows": [
            {
                "row_number": ready_count + index + 2,
                "item_id": f"blocked-{index:03d}",
                "batch_id": batch_id,
                "error": {
                    "code": "SINGLE_EPISODE_FORBIDDEN",
                    "message": "single episode is blocked",
                },
            }
            for index in range(blocked_count)
        ],
        "warnings": warnings,
        "structure_errors": [],
        "batch_ids": [batch_id],
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "warning_count": len(warnings),
        "safety": {
            "wordpress_write_performed": False,
            "wordpress_publish_performed": False,
            "external_network_performed": False,
            "input_status_fixed_to_draft": True,
        },
    }


def _old_ls_csv_text() -> str:
    return (
        "batch_id,item_id,title,release_date,category,rakuten_kobo_url,image_url\n"
        "BATCH_OLD_1,ITEM_OLD_1,旧形式タイトル,2026-07-13,comic,https://books.rakuten.co.jp/old1,https://example.com/old1.jpg\n"
    )


def test_collected_csv_can_prevalidate(monkeypatch):
    called = {}
    raw_result = _fake_engine_result()

    def fake_import(path):
        called["path"] = Path(path)
        return raw_result

    monkeypatch.setattr(app, "import_multistore_csv", fake_import)
    bundle = app.prevalidate_csv_upload("collected.csv", _sample_csv_text().encode("utf-8"), "collected")
    assert bundle["raw_result"] is raw_result
    assert bundle["summary"] is not raw_result
    assert bundle["summary"]["ready_count"] == 1
    assert called["path"].exists()


def test_manual_utf8_csv_can_validate(monkeypatch):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _fake_engine_result())
    bundle = app.prevalidate_csv_upload("manual.csv", _sample_csv_text().encode("utf-8"), "manual")
    prepared = bundle["prepared"]
    assert prepared.detected_encoding == "utf-8"
    assert prepared.converted_to_utf8_bom is False


def test_utf8_bom_csv_can_validate(monkeypatch):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _fake_engine_result())
    raw = b"\xef\xbb\xbf" + _sample_csv_text().encode("utf-8")
    bundle = app.prevalidate_csv_upload("bom.csv", raw, "manual")
    prepared = bundle["prepared"]
    assert prepared.detected_encoding == "utf-8-sig"


def test_manual_cp932_is_converted_to_temporary_utf8_bom(monkeypatch):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _fake_engine_result())
    raw_cp932 = _sample_csv_text().encode("cp932")
    bundle = app.prevalidate_csv_upload("manual.csv", raw_cp932, "manual")
    prepared = bundle["prepared"]
    written = prepared.csv_path.read_bytes()
    assert prepared.detected_encoding == "cp932"
    assert prepared.converted_to_utf8_bom is True
    assert prepared.csv_path.as_posix().startswith("/tmp/multistore_app_")
    assert written.startswith(b"\xef\xbb\xbf")


def test_original_csv_is_not_overwritten(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _fake_engine_result())
    original = tmp_path / "input.csv"
    original_raw = _sample_csv_text().encode("cp932")
    original.write_bytes(original_raw)
    before = original.read_bytes()
    app.prevalidate_csv_upload(original.name, before, "manual")
    after = original.read_bytes()
    assert before == after


def test_non_csv_is_rejected():
    with pytest.raises(app.AppError):
        app.prepare_uploaded_csv("not_csv.txt", b"abc", "collected")


def test_nul_is_rejected():
    with pytest.raises(app.AppError):
        app.prepare_uploaded_csv("a.csv", b"a\x00b", "collected")


def test_import_without_explicit_confirmation_is_rejected(tmp_path):
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": app.summarize_result(_fake_engine_result())}
    session.raw_result = _fake_engine_result()
    with pytest.raises(app.AppError):
        app.import_with_session_guard(session, tmp_path, explicit_confirmation=False)


def test_same_batch_double_import_in_same_session_is_rejected(monkeypatch, tmp_path):
    calls = {"n": 0}

    def fake_writer(result, repo_root):
        calls["n"] += 1
        return {"ok": True, "repo_root": str(repo_root), "result": result}

    monkeypatch.setattr(app, "write_import_artifacts", fake_writer)
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": app.summarize_result(_fake_engine_result())}
    session.raw_result = _fake_engine_result()
    first = app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)
    assert first["ok"] is True
    assert session.imported_batch_ids == {"BATCH1"}
    with pytest.raises(app.AppError, match="同じbatch_idの二重インポート") as exc_info:
        app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)
    assert exc_info.value.status == app.HTTPStatus.CONFLICT
    assert calls["n"] == 1


def test_different_batch_is_allowed_in_same_session(monkeypatch, tmp_path):
    written_batch_ids = []

    def fake_writer(result, _repo_root):
        written_batch_ids.extend(result["batch_ids"])
        return {"ok": True}

    monkeypatch.setattr(app, "write_import_artifacts", fake_writer)
    session = app.SessionData("sid", "tok", 10_000_000.0)

    for batch_id in ("BATCH_A", "BATCH_B"):
        raw_result = _engine_result_for_batch(batch_id)
        session.validation_bundle = {"summary": app.summarize_result(raw_result)}
        session.raw_result = raw_result
        app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)

    assert written_batch_ids == ["BATCH_A", "BATCH_B"]
    assert session.imported_batch_ids == {"BATCH_A", "BATCH_B"}


def test_new_rk_batch_is_allowed_after_different_batch_in_same_session(monkeypatch, tmp_path):
    imported = []

    def fake_writer(result, _repo_root):
        imported.append(result["batch_ids"][0])
        return {"ok": True}

    monkeypatch.setattr(app, "write_import_artifacts", fake_writer)
    session = app.SessionData("sid", "tok", 10_000_000.0)

    for batch_id in ("RK_PREVIOUS", "RK_202608_20260730_235157"):
        raw_result = _engine_result_for_batch(batch_id)
        session.validation_bundle = {"summary": app.summarize_result(raw_result)}
        session.raw_result = raw_result
        app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)

    assert imported == ["RK_PREVIOUS", "RK_202608_20260730_235157"]
    assert "RK_202608_20260730_235157" in session.imported_batch_ids


def test_import_rejects_multiple_batch_ids_before_writer_call(monkeypatch, tmp_path):
    monkeypatch.setattr(
        app,
        "write_import_artifacts",
        lambda *_args, **_kwargs: pytest.fail("writer must not be called"),
    )
    raw_result = _engine_result_for_batch("BATCH_A")
    raw_result["batch_ids"] = ["BATCH_A", "BATCH_B"]
    raw_result["blocked_rows"] = [
        {
            "row_number": 3,
            "item_id": "ITEM2",
            "batch_id": "BATCH_B",
            "error": {"code": "BLOCKED", "message": "blocked"},
        }
    ]
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": app.summarize_result(raw_result)}
    session.raw_result = raw_result

    with pytest.raises(app.AppError, match="batch_idは1件だけ"):
        app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)

    assert session.imported_batch_ids == set()


def test_test_output_destination_is_tmp_path_only(monkeypatch, tmp_path):
    captured = {}

    def fake_writer(result, repo_root):
        captured["repo_root"] = Path(repo_root)
        return {"ok": True}

    monkeypatch.setattr(app, "write_import_artifacts", fake_writer)
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": app.summarize_result(_fake_engine_result())}
    session.raw_result = _fake_engine_result()
    app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)
    assert captured["repo_root"] == tmp_path


def test_wordpress_write_is_not_called_in_prevalidation(monkeypatch):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _fake_engine_result())
    bundle = app.prevalidate_csv_upload("collected.csv", _sample_csv_text().encode("utf-8"), "collected")
    safety = bundle["raw_result"]["safety"]
    assert safety["wordpress_write_performed"] is False
    assert safety["wordpress_publish_performed"] is False


def test_external_network_is_not_performed(monkeypatch):
    def blocked_network(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "create_connection", blocked_network)
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _fake_engine_result())
    bundle = app.prevalidate_csv_upload("collected.csv", _sample_csv_text().encode("utf-8"), "collected")
    assert bundle["raw_result"]["safety"]["external_network_performed"] is False


def test_import_passes_raw_result_to_writer_not_summary(monkeypatch, tmp_path):
    raw_result = _bridge_raw_result()
    summary = app.summarize_result(raw_result)
    captured = {}

    def fake_writer(result, repo_root):
        captured["result"] = result
        captured["repo_root"] = Path(repo_root)
        assert result is raw_result
        assert result is not summary
        assert result["batch_ids"] == ["test_batch"]
        assert result["ready_payloads"][0]["batch_id"] == "test_batch"
        return {
            "item_paths": [str(Path(repo_root) / "exchange" / "inputs" / "new_release" / "batches" / "test_batch" / "items" / "test_item_001.input.json")],
            "manifest_records": [{"batch_ids": ["test_batch"]}],
            "blocked_records": [],
            "result_log_records": [],
        }

    monkeypatch.setattr(app, "write_import_artifacts", fake_writer)
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": summary}
    session.raw_result = raw_result
    session.summary = summary

    write_result = app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)
    assert captured["repo_root"] == tmp_path
    assert write_result["item_paths"]
    assert "unknown_batch" not in "\n".join(write_result["item_paths"])


def test_writer_exception_does_not_mark_session_imported(monkeypatch, tmp_path):
    def fail_writer(_result, _repo_root):
        raise PermissionError("simulated artifact permission failure")

    monkeypatch.setattr(app, "write_import_artifacts", fail_writer)
    raw_result = _bridge_raw_result()
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": app.summarize_result(raw_result)}
    session.raw_result = raw_result

    with pytest.raises(PermissionError, match="simulated artifact permission failure"):
        app.import_with_session_guard(
            session,
            tmp_path,
            explicit_confirmation=True,
        )

    assert session.imported_batch_ids == set()


def test_failed_batch_can_be_retried_in_same_session(monkeypatch, tmp_path):
    calls = {"n": 0}

    def fail_once_then_succeed(_result, _repo_root):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated rollback")
        return {"ok": True}

    monkeypatch.setattr(app, "write_import_artifacts", fail_once_then_succeed)
    raw_result = _engine_result_for_batch("BATCH_B")
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": app.summarize_result(raw_result)}
    session.raw_result = raw_result

    with pytest.raises(RuntimeError, match="simulated rollback"):
        app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)
    assert session.imported_batch_ids == set()

    result = app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)
    assert result["ok"] is True
    assert session.imported_batch_ids == {"BATCH_B"}


def test_session_history_is_added_only_after_persistent_write_succeeds(monkeypatch, tmp_path):
    session = app.SessionData("sid", "tok", 10_000_000.0)
    raw_result = _engine_result_for_batch("BATCH_COMMIT")
    session.validation_bundle = {"summary": app.summarize_result(raw_result)}
    session.raw_result = raw_result

    def fake_committing_writer(_result, _repo_root):
        assert session.imported_batch_ids == set()
        return {"committed": True}

    monkeypatch.setattr(app, "write_import_artifacts", fake_committing_writer)

    result = app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)

    assert result["committed"] is True
    assert session.imported_batch_ids == {"BATCH_COMMIT"}


def test_import_rejects_missing_raw_result_without_writer_call(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "write_import_artifacts", lambda *_args, **_kwargs: pytest.fail("writer must not be called"))
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": {"ready_count": 1}}
    session.raw_result = None

    with pytest.raises(app.AppError, match="事前検証結果の原本が保持されていない"):
        app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)


def test_import_rejects_summary_only_structure_without_writer_call(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "write_import_artifacts", lambda *_args, **_kwargs: pytest.fail("writer must not be called"))
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": {"ready_count": 0, "blocked_count": 0, "warning_count": 0}}
    session.raw_result = {"ready_count": 0, "blocked_count": 0, "warning_count": 0}

    with pytest.raises(app.AppError, match="事前検証結果の原本が保持されていない"):
        app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)


def test_structure_error_with_zero_ready_has_schema_message_not_raw_missing():
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.validation_bundle = {"summary": {"ready_count": 0}}
    session.raw_result = {
        "status": "ERROR",
        "ready_payloads": [],
        "blocked_rows": [],
        "warnings": [],
        "structure_errors": [{"code": "CSV_HEADER_MISSING_COLUMNS", "message": "missing"}],
        "ready_count": 0,
        "blocked_count": 0,
        "warning_count": 0,
        "batch_ids": [],
    }
    with pytest.raises(app.AppError, match="CSV形式が新刊マルチストアV2入力仕様と一致していません"):
        app.import_with_session_guard(session, Path("/tmp"), explicit_confirmation=True)


def test_template_csv_is_utf8_bom():
    raw = app.generate_template_csv_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")


def test_page_has_manual_csv_option():
    session = app.SessionData("sid", "tok", 10_000_000.0)
    html_text = app.render_page_html(session, {})
    assert "手動調整CSV" in html_text


def test_page_has_import_button():
    session = app.SessionData("sid", "tok", 10_000_000.0)
    html_text = app.render_page_html(session, {})
    assert "Block AIへインポートボタン" in html_text


def test_prevalidation_page_aggregates_only_amazon_unconfirmed_warnings(tmp_path):
    amazon_warning = {
        "code": "AMAZON_OMITTED_PENDING_MANUAL_CONFIRMATION",
        "message": "Amazon link is omitted pending manual confirmation.",
    }
    other_warning = {
        "code": "OTHER_WARNING",
        "message": "Other warning remains visible.",
    }
    raw_result = _fake_engine_result()
    raw_result.update(
        {
            "status": "PASS_WITH_WARNINGS",
            "warnings": [amazon_warning.copy(), other_warning, amazon_warning.copy()],
            "warning_count": 3,
        }
    )
    prepared = app.PreparedUpload(
        original_filename="input.csv",
        input_type="manual",
        detected_encoding="utf-8",
        converted_to_utf8_bom=False,
        temp_dir=tmp_path,
        csv_path=tmp_path / "input.csv",
    )
    summary = app.summarize_result(raw_result)
    bundle = {"prepared": prepared, "raw_result": raw_result, "summary": summary}
    session = app.SessionData("sid", "tok", 10_000_000.0)

    html_text = app.render_page_html(session, {"validation": bundle})

    assert html_text.count("Amazon未確認: 2件") == 1
    assert "AMAZON_OMITTED_PENDING_MANUAL_CONFIRMATION" not in html_text
    assert "OTHER_WARNING: Other warning remains visible." in html_text
    assert "警告件数: 3" in html_text
    assert raw_result["warnings"] == [amazon_warning, other_warning, amazon_warning]
    assert summary["warnings"] == raw_result["warnings"]


def test_import_result_page_summarizes_466_items_without_expanding_paths():
    item_paths = [f"/sensitive/items/item-{index:03d}.input.json" for index in range(466)]
    write_result = {
        "status": "PASS_WITH_BLOCKED_ROWS",
        "ready_count": 466,
        "blocked_count": 39,
        "warning_count": 466,
        "batch_ids": ["RK_202608_TEST"],
        "item_paths": item_paths,
        "manifest_records": [
            {
                "manifest_path": "/safe/batch/manifest.json",
                "batch_ids": ["RK_202608_TEST"],
                "blocked_count": 39,
                "warning_count": 466,
            }
        ],
        "blocked_records": [{"blocked_path": "/safe/review/blocked.json"}],
        "result_log_records": [{"result_log_path": "/safe/log/result.json"}],
    }
    session = app.SessionData("sid", "tok", 10_000_000.0)

    html_text = app.render_page_html(session, {"import_result": write_result})

    assert "インポート成功件数: 466" in html_text
    assert "除外件数: 39" in html_text
    assert "警告件数: 466" in html_text
    assert "batch_id: RK_202608_TEST" in html_text
    assert "/safe/batch/manifest.json" in html_text
    assert "/safe/review/blocked.json" in html_text
    assert "/safe/log/result.json" in html_text
    assert ".input.json" not in html_text


def test_page_disables_import_when_not_importable():
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.summary = {"importable": False}
    html_text = app.render_page_html(session, {})
    assert "Block AIへインポートボタン" in html_text
    assert "button type=\"submit\" disabled" in html_text
    assert "checkbox\" name=\"explicit_confirmation\" value=\"true\" disabled" in html_text


def test_detect_old_format_candidate_by_filename(monkeypatch):
    monkeypatch.setattr(
        app,
        "import_multistore_csv",
        lambda _path: {
            "status": "ERROR",
            "ready_payloads": [],
            "blocked_rows": [],
            "warnings": [],
            "structure_errors": [{"code": "CSV_HEADER_MISSING_COLUMNS", "message": "missing"}],
            "ready_count": 0,
            "blocked_count": 0,
            "warning_count": 0,
            "batch_ids": [],
            "safety": {
                "wordpress_write_performed": False,
                "wordpress_publish_performed": False,
                "external_network_performed": False,
                "input_status_fixed_to_draft": True,
            },
        },
    )
    bundle = app.prevalidate_csv_upload(
        "example_ls_new_batch_input.csv",
        _old_ls_csv_text().encode("utf-8"),
        "manual",
    )
    assert bundle["summary"]["old_format_candidate"] is True


def test_structure_errors_and_missing_columns_are_shown_on_page(monkeypatch):
    def fake_import(_path):
        return {
            "status": "ERROR",
            "ready_payloads": [],
            "blocked_rows": [],
            "warnings": [],
            "structure_errors": [
                {
                    "code": "CSV_HEADER_MISSING_COLUMNS",
                    "message": "Missing required columns: wordpress_status",
                }
            ],
            "ready_count": 0,
            "blocked_count": 0,
            "warning_count": 0,
            "batch_ids": [],
            "safety": {
                "wordpress_write_performed": False,
                "wordpress_publish_performed": False,
                "external_network_performed": False,
                "input_status_fixed_to_draft": True,
            },
        }

    monkeypatch.setattr(app, "import_multistore_csv", fake_import)
    bundle = app.prevalidate_csv_upload("invalid_ls_new_batch_input.csv", _old_ls_csv_text().encode("utf-8"), "manual")
    session = app.SessionData("sid", "tok", 10_000_000.0)
    session.summary = bundle["summary"]
    html_text = app.render_page_html(session, {"validation": bundle})
    assert "CSV構造エラー一覧" in html_text
    assert "CSV_HEADER_MISSING_COLUMNS" in html_text
    assert "不足必須列一覧" in html_text
    assert "wordpress_status" in html_text
    assert "未知列一覧" in html_text
    assert "V2形式へ変換プレビュー" in html_text


def test_old_format_conversion_preview_fills_fixed_values_and_sha256(monkeypatch):
    calls = {"n": 0}

    def fake_import(_path):
        calls["n"] += 1
        return _bridge_raw_result()

    monkeypatch.setattr(app, "import_multistore_csv", fake_import)
    bundle = app.prevalidate_csv_upload("sample_ls_new_batch_input.csv", _old_ls_csv_text().encode("utf-8"), "manual")
    preview = app.build_old_format_conversion_preview(bundle["prepared"])
    converted = preview["converted_csv_bytes"]
    assert converted.startswith(b"\xef\xbb\xbf")
    csv_text = converted.decode("utf-8-sig")
    assert "NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2" in csv_text
    assert ",draft," in csv_text
    assert ",READY_FOR_DRAFT," in csv_text
    assert ",true,true,true," in csv_text
    assert "NOT_FOUND" in csv_text
    assert "volume" in csv_text
    assert calls["n"] >= 2


def test_old_format_conversion_excludes_row_when_required_is_missing(monkeypatch):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _bridge_raw_result())
    old_text = (
        "batch_id,item_id,title,release_date,category,rakuten_kobo_url,image_url\n"
        "BATCH_OLD_1,ITEM_OLD_1,,2026-07-13,comic,https://books.rakuten.co.jp/old1,https://example.com/old1.jpg\n"
    )
    bundle = app.prevalidate_csv_upload("sample_ls_new_batch_input.csv", old_text.encode("utf-8"), "manual")
    preview = app.build_old_format_conversion_preview(bundle["prepared"])
    assert preview["excluded_row_count"] == 1
    assert preview["converted_row_count"] == 0
    assert preview["preview_rows"][0]["status"] == "REQUIRES_REVIEW"
    assert "title" in preview["preview_rows"][0]["missing_required"]


def test_conversion_preview_does_not_overwrite_original_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _bridge_raw_result())
    original = tmp_path / "ls_new_batch_input.csv"
    original.write_text(_old_ls_csv_text(), encoding="utf-8")
    before = original.read_text(encoding="utf-8")
    bundle = app.prevalidate_csv_upload(original.name, before.encode("utf-8"), "manual")
    app.build_old_format_conversion_preview(bundle["prepared"])
    after = original.read_text(encoding="utf-8")
    assert before == after


def test_prevalidation_and_conversion_preview_do_not_register_batch(monkeypatch, tmp_path):
    raw_result = _engine_result_for_batch("BATCH_B")
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: raw_result)
    monkeypatch.setattr(
        app,
        "write_import_artifacts",
        lambda _result, _repo_root: {"ok": True},
    )
    session = app.SessionData("sid", "tok", 10_000_000.0)

    bundle = app.prevalidate_csv_upload(
        "sample_ls_new_batch_input.csv",
        _old_ls_csv_text().encode("utf-8"),
        "manual",
    )
    session.validation_bundle = bundle
    session.raw_result = bundle["raw_result"]
    session.summary = bundle["summary"]
    assert session.imported_batch_ids == set()

    preview = app.build_old_format_conversion_preview(bundle["prepared"])
    session.validation_bundle = preview["converted_bundle"]
    session.raw_result = preview["converted_bundle"]["raw_result"]
    session.summary = preview["converted_bundle"]["summary"]
    assert session.imported_batch_ids == set()

    app.import_with_session_guard(session, tmp_path, explicit_confirmation=True)
    assert session.imported_batch_ids == {"BATCH_B"}


def test_direct_script_invocation_help_from_repo_root():
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        ["python3", "scripts/new_release_multistore_app.py", "--help"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert proc.returncode == 0
    assert "--repo-root" in proc.stdout


def test_daily_summary_selection_rejects_bad_csrf_and_keeps_return_query(tmp_path):
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, _token = _open_session(port)
        status, location = _post_daily_summary_selection(
            port=port,
            cookie=cookie,
            csrf_token="invalid",
            return_to=(
                "/database-search?keyword=GIANT&page=2&summary_date=2026-08-03"
            ),
        )
        assert status == 303
        assert "keyword=GIANT" in location
        assert "page=2" in location
        assert "summary_date=2026-08-03" in location
        assert "daily_summary_result=invalid_token" in location
    finally:
        _stop_server(server, thread)


def test_daily_summary_selection_saves_and_redirects_with_filters(
    monkeypatch, tmp_path
):
    from datetime import date
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    from app.db.models import DailySummarySelection, EbookItem

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            EbookItem(
                id="ebook-1",
                source_name="test",
                source_item_id="ebook-1",
                title="新刊",
                release_date=date(2026, 8, 3),
            )
        )
        session.commit()
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: Session(engine))

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, location = _post_daily_summary_selection(
            port=port,
            cookie=cookie,
            csrf_token=token,
            return_to=(
                "/database-search?keyword=GIANT&page=2&summary_date=2026-08-03"
                "&affiliate_status=partially_registered"
                "&amazon_affiliate_status=unregistered"
                "&rakuten_kobo_affiliate_status=registered"
                "&dmm_affiliate_status=registered"
            ),
        )
        assert status == 303
        assert "keyword=GIANT" in location
        assert "page=2" in location
        assert "summary_date=2026-08-03" in location
        assert "affiliate_status=partially_registered" in location
        assert "amazon_affiliate_status=unregistered" in location
        assert "rakuten_kobo_affiliate_status=registered" in location
        assert "dmm_affiliate_status=registered" in location
        assert "daily_summary_result=selection_saved" in location
        with Session(engine) as session:
            selection = session.scalar(select(DailySummarySelection))
            assert selection is not None
            assert selection.inclusion_state == "HUMAN_INCLUDED"
    finally:
        _stop_server(server, thread)


def _start_server(tmp_path):
    server = app.MultiStoreAppServer(("127.0.0.1", 0), app.MultiStoreAppHandler, repo_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _stop_server(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def _open_session(port: int) -> tuple[str, str]:
    req = urllib.request.Request(f"http://127.0.0.1:{port}/")
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        cookie = resp.headers.get("Set-Cookie", "").split(";", 1)[0]
    token_match = re.search(r'name="op_token" value="([^"]+)"', body)
    if token_match is None:
        raise AssertionError("op_token not found")
    return cookie, token_match.group(1)


def test_bulk_affiliate_selection_token_expires_and_rejects_reuse() -> None:
    session = app.SessionStore().create(now_ts=100.0)
    token = session.issue_bulk_affiliate_token(
        selected_ebook_item_ids=["item-1"],
        filters_query="keyword=Book&page=2",
        return_to="/database-search?keyword=Book&page=2",
        now_ts=100.0,
    )

    assert token.expires_at - token.issued_at == 15 * 60
    assert session.get_bulk_affiliate_token(token.token, now_ts=999.0) is token
    token.used = True
    with pytest.raises(app.AppError, match="BULK_AFFILIATE_TOKEN_REUSED"):
        session.get_bulk_affiliate_token(token.token, now_ts=1000.0)
    token.used = False
    with pytest.raises(app.AppError, match="BULK_AFFILIATE_TOKEN_EXPIRED"):
        session.get_bulk_affiliate_token(token.token, now_ts=1001.0)
    with pytest.raises(app.AppError, match="BULK_AFFILIATE_INVALID_TOKEN"):
        session.get_bulk_affiliate_token(token.token + "tampered", now_ts=100.0)


def test_bulk_affiliate_prepare_dry_run_apply_and_reuse_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from datetime import date
    from urllib.parse import urlencode

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base
    from app.db.models import EbookItem, StoreOffer

    engine = create_engine(f"sqlite:///{tmp_path / 'bulk-route.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as database_session:
        item = EbookItem(
            source_name="bulk-route-test",
            source_item_id="bulk-route-1",
            title="Bulk Route Book",
            normalized_title="Bulk Route Book",
            volume_label="1巻",
            author_name="Author",
            publisher_name="Publisher",
            release_date=date(2026, 8, 3),
            item_type="tankobon",
            is_excluded=False,
        )
        database_session.add(item)
        database_session.commit()
        item_id = item.id

    import app.db.read_only_session as read_only_module
    import app.db.session as session_module

    monkeypatch.setattr(read_only_module, "ReadOnlySessionLocal", factory)
    monkeypatch.setattr(session_module, "SessionLocal", factory)

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, csrf_token = _open_session(port)
        prepare_fields = {
            "csrf_token": csrf_token,
            "selected_ebook_item_ids": [item_id],
            "keyword": "Bulk Route",
            "page": "1",
            "return_to": "/database-search?keyword=Bulk+Route&page=1",
        }
        prepare_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/database-bulk-affiliate/prepare",
            method="POST",
            data=urlencode(prepare_fields, doseq=True).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
            },
        )
        opener = urllib.request.build_opener(_NoRedirect())
        with pytest.raises(urllib.error.HTTPError) as prepare_error:
            opener.open(prepare_request)
        assert prepare_error.value.code == 303
        location = prepare_error.value.headers["Location"]
        assert location.startswith("/database-bulk-affiliate?token=")
        assert item_id not in location
        assert "affiliate_url" not in location

        page_request = urllib.request.Request(
            f"http://127.0.0.1:{port}{location}",
            headers={"Cookie": cookie},
        )
        with urllib.request.urlopen(page_request) as response:
            page = response.read().decode("utf-8")
            assert response.status == 200
        assert "アフィリエイト一括登録確認" in page
        assert "Bulk Route Book" in page
        assert "/database-search?keyword=Bulk+Route&amp;page=1" in page
        selection_token = re.search(
            r'name="selection_token" value="([^"]+)"', page
        ).group(1)
        expected_hashes = {
            store_name: re.search(
                rf'name="offer__{item_id}__{store_name}__expected_hash" value="([^"]+)"',
                page,
            ).group(1)
            for store_name in ("amazon", "rakuten_kobo", "dmm")
        }
        offer_fields = {
            "csrf_token": csrf_token,
            "selection_token": selection_token,
            f"offer__{item_id}__amazon__store_item_id": "B0H7Z26WWB",
            f"offer__{item_id}__amazon__product_url": "https://www.amazon.co.jp/dp/B0H7Z26WWB",
            f"offer__{item_id}__amazon__affiliate_url": "https://www.amazon.co.jp/dp/B0H7Z26WWB?tag=ktkr77-22",
            f"offer__{item_id}__amazon__price": "700",
            f"offer__{item_id}__amazon__image_url": "",
        }
        for store_name, expected_hash in expected_hashes.items():
            offer_fields[
                f"offer__{item_id}__{store_name}__expected_hash"
            ] = expected_hash

        dry_run_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/database-bulk-affiliate/dry-run",
            method="POST",
            data=urlencode(offer_fields).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
            },
        )
        with urllib.request.urlopen(dry_run_request) as response:
            dry_run = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
        assert dry_run["ok"] is True
        assert dry_run["create_count"] == 1
        assert dry_run["items"][0]["stores"]["amazon"]["status"] == "CREATE_READY"
        assert "https://" not in json.dumps(dry_run)
        with factory() as database_session:
            assert database_session.scalars(select(StoreOffer)).all() == []

        apply_fields = {
            **offer_fields,
            "dry_run_input_hash": dry_run["input_hash"],
            "operation_confirmation": "true",
        }
        apply_request = urllib.request.Request(
            f"http://127.0.0.1:{port}/database-bulk-affiliate/apply",
            method="POST",
            data=urlencode(apply_fields).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
            },
        )
        with pytest.raises(urllib.error.HTTPError) as apply_error:
            opener.open(apply_request)
        assert apply_error.value.code == 303
        assert apply_error.value.headers["Location"].startswith(
            "/database-bulk-affiliate/result?token="
        )
        with factory() as database_session:
            offers = database_session.scalars(select(StoreOffer)).all()
            assert len(offers) == 1
            assert offers[0].store_name == "amazon"
            assert offers[0].price_yen == 700

        with pytest.raises(urllib.error.HTTPError) as reused_error:
            opener.open(apply_request)
        assert reused_error.value.code == 400
        assert "既に完了" in reused_error.value.read().decode("utf-8")
        with factory() as database_session:
            assert len(database_session.scalars(select(StoreOffer)).all()) == 1
    finally:
        _stop_server(server, thread)
        engine.dispose()


def _post_bulk_selection(
    *,
    port: int,
    cookie: str,
    fields: dict[str, object],
) -> tuple[int, dict[str, object]]:
    from urllib.parse import urlencode

    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/database-bulk-selection/validate",
        method="POST",
        data=urlencode(fields, doseq=True).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def test_bulk_selection_validation_api_is_read_only_and_recalculates_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from datetime import date
    from hashlib import sha256

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db.base import Base
    from app.db.models import EbookItem
    from app.db.read_only_session import create_sqlite_read_only_session_factory

    database_path = tmp_path / "bulk-selection-api.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    active_ids = [str(uuid.uuid4()) for _index in range(201)]
    filtered_out_id = str(uuid.uuid4())
    excluded_id = str(uuid.uuid4())
    with Session(engine) as session:
        session.add_all(
            [
                EbookItem(
                    id=item_id,
                    source_name="bulk-api-test",
                    source_item_id=f"bulk-{index:03d}",
                    title=f"Bulk Book {index:03d}",
                    normalized_title=f"Bulk Book {index:03d}",
                    author_name="Author",
                    publisher_name="Publisher",
                    release_date=date(2026, 8, 3),
                    item_type="tankobon",
                    workflow_status="READY",
                    review_status="APPROVED",
                    wordpress_status="NOT_CREATED",
                    is_excluded=False,
                )
                for index, item_id in enumerate(active_ids)
            ]
            + [
                EbookItem(
                    id=filtered_out_id,
                    source_name="bulk-api-test",
                    source_item_id="other",
                    title="Other Book",
                    normalized_title="Other Book",
                    item_type="tankobon",
                    is_excluded=False,
                ),
                EbookItem(
                    id=excluded_id,
                    source_name="bulk-api-test",
                    source_item_id="excluded",
                    title="Bulk Excluded",
                    normalized_title="Bulk Excluded",
                    item_type="tankobon",
                    is_excluded=True,
                ),
            ]
        )
        session.commit()
    engine.dispose()
    before_hash = sha256(database_path.read_bytes()).hexdigest()
    read_only_factory = create_sqlite_read_only_session_factory(database_path)
    monkeypatch.setattr(
        "app.db.read_only_session.ReadOnlySessionLocal",
        read_only_factory,
    )

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        base_fields: dict[str, object] = {
            "csrf_token": token,
            "keyword": "Bulk",
            "affiliate_status": "all",
            "amazon_affiliate_status": "all",
            "rakuten_kobo_affiliate_status": "all",
            "dmm_affiliate_status": "all",
            "page": "1",
        }

        for selected_count in (1, 3, 5):
            status, payload = _post_bulk_selection(
                port=port,
                cookie=cookie,
                fields={
                    **base_fields,
                    "selected_ebook_item_ids": active_ids[:selected_count],
                    "affiliate_registration_capability": "ALREADY_REGISTERED",
                    "wordpress_draft_capability": "INVALID_STATE",
                    "wordpress_schedule_capability": "READY",
                },
            )
            assert status == 200
            assert payload["ok"] is True
            assert payload["selected_count"] == selected_count
            assert payload["items"][0]["affiliate_registration_capability"] == "NEEDS_INPUT"
            assert payload["items"][0]["wordpress_draft_capability"] == "READY"
            assert payload["items"][0]["wordpress_schedule_capability"] == "NOT_DRAFT"

        error_cases = [
            ({}, "BULK_SELECTION_EMPTY"),
            ({"selected_ebook_item_ids": active_ids[:6]}, "BULK_SELECTION_LIMIT_EXCEEDED"),
            ({"selected_ebook_item_ids": [active_ids[0], active_ids[0]]}, "BULK_SELECTION_DUPLICATE_ID"),
            ({"selected_ebook_item_ids": ["not-a-uuid"]}, "BULK_SELECTION_INVALID_ID"),
            ({"selected_ebook_item_ids": [str(uuid.uuid4())]}, "BULK_SELECTION_ITEM_NOT_FOUND"),
            ({"selected_ebook_item_ids": [filtered_out_id]}, "BULK_SELECTION_NOT_IN_CURRENT_RESULT"),
            (
                {
                    "selected_ebook_item_ids": [active_ids[0]],
                    "affiliate_status": "all_registered",
                },
                "BULK_SELECTION_NOT_IN_CURRENT_RESULT",
            ),
            (
                {
                    "selected_ebook_item_ids": [active_ids[0]],
                    "amazon_affiliate_status": "registered",
                },
                "BULK_SELECTION_NOT_IN_CURRENT_RESULT",
            ),
            ({"selected_ebook_item_ids": [excluded_id]}, "BULK_SELECTION_EXCLUDED"),
            (
                {"selected_ebook_item_ids": [active_ids[0]], "page": "2"},
                "BULK_SELECTION_NOT_IN_CURRENT_PAGE",
            ),
        ]
        for overrides, expected_code in error_cases:
            status, payload = _post_bulk_selection(
                port=port,
                cookie=cookie,
                fields={**base_fields, **overrides},
            )
            assert status == 400
            assert payload["ok"] is False
            assert payload["errors"][0]["code"] == expected_code

        for csrf_fields in ({"csrf_token": "invalid"}, {"csrf_token": None}):
            fields = {
                **base_fields,
                "selected_ebook_item_ids": [active_ids[0]],
                **csrf_fields,
            }
            if fields["csrf_token"] is None:
                fields.pop("csrf_token")
            status, payload = _post_bulk_selection(
                port=port,
                cookie=cookie,
                fields=fields,
            )
            assert status == 403
            assert payload["errors"][0]["code"] == "BULK_SELECTION_CSRF_FAILED"
    finally:
        _stop_server(server, thread)

    assert sha256(database_path.read_bytes()).hexdigest() == before_hash


def test_bulk_selection_validation_api_hides_query_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "app.db.read_only_session.ReadOnlySessionLocal",
        lambda: (_ for _ in ()).throw(RuntimeError("private database detail")),
    )
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, payload = _post_bulk_selection(
            port=port,
            cookie=cookie,
            fields={
                "csrf_token": token,
                "selected_ebook_item_ids": [str(uuid.uuid4())],
                "page": "1",
            },
        )
        assert status == 500
        assert payload["errors"][0] == {
            "code": "BULK_SELECTION_QUERY_FAILED",
            "message": "選択内容を確認できませんでした",
        }
        assert "private database detail" not in json.dumps(payload)
    finally:
        _stop_server(server, thread)


def _post_manual_store_offer(
    *,
    port: int,
    cookie: str,
    csrf_token: str,
    confirmed: bool = True,
) -> tuple[int, str]:
    from urllib.parse import urlencode

    fields = {
        "csrf_token": csrf_token,
        "ebook_item_id": "ebook-manual-offer",
        "store_name": "rakuten_kobo",
        "product_url": "https://books.rakuten.co.jp/rk/1234567890/",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/hgc/abc123/",
        "price": "550",
        "currency": "JPY",
        "availability_status": "FOUND",
        "observed_at": "2026-08-03T10:20:30",
        "return_to": "/database-search?keyword=Dolls&page=2",
    }
    if confirmed:
        fields["confirmed"] = "true"
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/database-manual-store-offer",
        method="POST",
        data=urlencode(fields).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        opener.open(request)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers["Location"]
    raise AssertionError("manual store offer POST did not redirect")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def test_post_manual_store_offer_validates_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    from app.db.models import CatalogEditHistory, EbookItem, StoreOffer

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(EbookItem(
            id="ebook-manual-offer",
            source_name="manual",
            source_item_id="manual-offer-1",
            title="Dolls",
            workflow_status="NEW",
            review_status="NOT_REVIEWED",
            wordpress_status="NOT_CREATED",
        ))
        session.commit()
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: Session(engine))

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)

        status, location = _post_manual_store_offer(
            port=port,
            cookie=cookie,
            csrf_token="wrong-token",
        )
        assert status == 303
        assert "manual_store_offer_result=INVALID_CSRF" in location

        status, location = _post_manual_store_offer(
            port=port,
            cookie=cookie,
            csrf_token=token,
            confirmed=False,
        )
        assert status == 303
        assert "manual_store_offer_result=CONFIRMATION_REQUIRED" in location

        for _ in range(2):
            status, location = _post_manual_store_offer(
                port=port,
                cookie=cookie,
                csrf_token=token,
            )
            assert status == 303
            assert "keyword=Dolls" in location
            assert "page=2" in location
            assert "manual_store_offer_result=MANUAL_STORE_OFFER_CREATED" in location

        with Session(engine) as session:
            assert session.scalar(
                select(func.count()).select_from(StoreOffer)
            ) == 1
            assert session.scalar(
                select(func.count()).select_from(CatalogEditHistory)
            ) == 1
    finally:
        _stop_server(server, thread)
        engine.dispose()


def _post_daily_summary_selection(
    *, port: int, cookie: str, csrf_token: str, return_to: str
) -> tuple[int, str]:
    from urllib.parse import urlencode

    body = urlencode(
        {
            "csrf_token": csrf_token,
            "ebook_item_id": "ebook-1",
            "summary_date": "2026-08-03",
            "included": "true",
            "return_to": return_to,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/database-daily-summary-selection",
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request) as response:
            return response.status, response.headers.get("Location", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location", "")


def _post_daily_summary_action(
    *,
    port: int,
    cookie: str,
    csrf_token: str,
    summary_date: str | None,
    operation: str = "auto_select",
) -> tuple[int, str]:
    from urllib.parse import urlencode

    fields = {
        "csrf_token": csrf_token,
        "operation": operation,
        "return_to": (
            "/database-search?keyword=GIANT&release_date_from=2026-08-03"
            "&release_date_to=2026-08-03&item_type=tankobon"
            "&store_name=rakuten_kobo&page=2"
        ),
    }
    if summary_date is not None:
        fields["summary_date"] = summary_date
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/database-daily-summary-action",
        method="POST",
        data=urlencode(fields).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request) as response:
            return response.status, response.headers.get("Location", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location", "")


def test_daily_summary_auto_select_uses_posted_date_and_keeps_filters(
    monkeypatch, tmp_path
) -> None:
    from datetime import date
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    from app.db.models import DailySummarySelection, EbookItem

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            EbookItem(
                id="august-3-item",
                source_name="test",
                source_item_id="august-3-item",
                title="8月3日の新刊",
                release_date=date(2026, 8, 3),
                workflow_status="READY",
                review_status="APPROVED",
                wordpress_status="PUBLISHED",
                wordpress_post_id="303",
            )
        )
        session.commit()
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: Session(engine))

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, location = _post_daily_summary_action(
            port=port,
            cookie=cookie,
            csrf_token=token,
            summary_date="2026-08-03",
        )
        assert status == 303
        parsed = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
        assert parsed["summary_date"] == ["2026-08-03"]
        for name in (
            "keyword",
            "release_date_from",
            "release_date_to",
            "item_type",
            "store_name",
            "page",
        ):
            assert name in parsed
        with Session(engine) as session:
            selection = session.scalar(select(DailySummarySelection))
            assert selection is not None
            assert selection.summary_date == date(2026, 8, 3)
            assert selection.summary_date != date(2026, 8, 2)
    finally:
        _stop_server(server, thread)


@pytest.mark.parametrize("summary_date", [None, "not-a-date"])
def test_daily_summary_bulk_action_rejects_missing_or_invalid_date(
    monkeypatch, tmp_path, summary_date
) -> None:
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    from app.db.models import DailySummarySelection

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: Session(engine))
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, location = _post_daily_summary_action(
            port=port,
            cookie=cookie,
            csrf_token=token,
            summary_date=summary_date,
        )
        assert status == 303
        assert "daily_summary_result=invalid_request" in location
        with Session(engine) as session:
            assert session.scalar(
                select(func.count()).select_from(DailySummarySelection)
            ) == 0
    finally:
        _stop_server(server, thread)


def test_daily_summary_dry_run_redirect_keeps_posted_date(
    monkeypatch, tmp_path
) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: Session(engine))

    class FakeDraftService:
        def __init__(self, session, wordpress_client):
            pass

        def execute(self, *, summary_date, dry_run):
            assert summary_date.isoformat() == "2026-08-03"
            assert dry_run is True
            return SimpleNamespace(generation_allowed=True)

    monkeypatch.setattr(
        "app.services.daily_summary_wordpress_draft_service.DailySummaryWordPressDraftService",
        FakeDraftService,
    )
    monkeypatch.setattr(
        app.MultiStoreAppHandler,
        "_daily_summary_wordpress_client",
        lambda self: object(),
    )
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, location = _post_daily_summary_action(
            port=port,
            cookie=cookie,
            csrf_token=token,
            summary_date="2026-08-03",
            operation="generate_dry_run",
        )
        assert status == 303
        parsed = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
        assert parsed["summary_date"] == ["2026-08-03"]
        assert parsed["daily_summary_result"] == ["dry_run_ready"]
    finally:
        _stop_server(server, thread)


def _session_id_from_cookie(cookie: str) -> str:
    return cookie.split("=", 1)[1]


def _multipart_payload(
    *,
    token: str,
    input_type: str,
    filename: str | None,
    file_bytes: bytes | None,
    file_content_type: str = "text/csv",
) -> tuple[bytes, str]:
    boundary = f"----pytest-boundary-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    def add_text(name: str, value: str) -> None:
        chunks.append(
            (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                f"{value}\r\n"
            ).encode("utf-8")
        )

    add_text("op_token", token)
    add_text("input_type", input_type)

    if filename is not None and file_bytes is not None:
        header = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"csv_file\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {file_content_type}\r\n\r\n"
        ).encode("utf-8")
        chunks.append(header + file_bytes + b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def _post_prevalidate(
    *,
    port: int,
    cookie: str,
    token: str,
    input_type: str,
    filename: str | None,
    file_bytes: bytes | None,
    file_content_type: str = "text/csv",
) -> tuple[int, str]:
    payload, boundary = _multipart_payload(
        token=token,
        input_type=input_type,
        filename=filename,
        file_bytes=file_bytes,
        file_content_type=file_content_type,
    )
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/prevalidate",
        method="POST",
        data=payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Cookie": cookie,
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _post_import(*, port: int, cookie: str, token: str, explicit_confirmation: bool = True) -> tuple[int, str]:
    body = f"op_token={token}&explicit_confirmation={'true' if explicit_confirmation else 'false'}".encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/import",
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _prevalidate_for_import(port: int, cookie: str, token: str) -> None:
    status, _body = _post_prevalidate(
        port=port,
        cookie=cookie,
        token=token,
        input_type="collected",
        filename="realistic.csv",
        file_bytes=_sample_csv_text().encode("utf-8"),
    )
    assert status == 200


def test_http_import_realistic_counts_succeeds_without_expanding_item_paths(
    monkeypatch,
    tmp_path,
):
    raw_result = _realistic_batch_result()
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: raw_result)
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        _prevalidate_for_import(port, cookie, token)

        status, body = _post_import(
            port=port,
            cookie=cookie,
            token=token,
        )

        assert status == 200
        assert "インポート成功件数: 466" in body
        assert "除外件数: 39" in body
        assert "警告件数: 466" in body
        assert "Amazon未確認: 466件" in body
        assert ".input.json" not in body
        item_dir = (
            tmp_path
            / "exchange"
            / "inputs"
            / "new_release"
            / "batches"
            / "RK_202608_TEST"
            / "items"
        )
        assert len(list(item_dir.glob("*.input.json"))) == 466
        blocked_path = (
            tmp_path
            / "exchange"
            / "reviews"
            / "new_release"
            / "batches"
            / "RK_202608_TEST.multistore_blocked.json"
        )
        result_log_path = (
            tmp_path
            / "exchange"
            / "logs"
            / "RK_202608_TEST.multistore_import_result.json"
        )
        assert len(json.loads(blocked_path.read_text())["blocked_rows"]) == 39
        assert json.loads(result_log_path.read_text())["warning_count"] == 466
        session = server.session_store.get(_session_id_from_cookie(cookie))
        assert session is not None
        assert session.imported_batch_ids == {"RK_202608_TEST"}
    finally:
        _stop_server(server, thread)


def test_http_import_complete_batch_returns_explicit_conflict(
    monkeypatch,
    tmp_path,
):
    raw_result = _bridge_raw_result()
    app.write_import_artifacts(raw_result, tmp_path)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: raw_result)
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        _prevalidate_for_import(port, cookie, token)

        status, body = _post_import(port=port, cookie=cookie, token=token)

        assert status == 409
        assert "このbatch_idはインポート済み" in body
        assert "test_batch" in body
        assert "internal server error" not in body
        after = {
            path.relative_to(tmp_path): path.read_bytes()
            for path in tmp_path.rglob("*")
            if path.is_file()
        }
        assert after == before
        session = server.session_store.get(_session_id_from_cookie(cookie))
        assert session is not None
        assert session.imported_batch_ids == set()
    finally:
        _stop_server(server, thread)


def test_http_import_partial_batch_returns_explicit_conflict(
    monkeypatch,
    tmp_path,
):
    raw_result = _bridge_raw_result()
    partial_dir = (
        tmp_path
        / "exchange"
        / "inputs"
        / "new_release"
        / "batches"
        / "test_batch"
    )
    partial_dir.mkdir(parents=True)
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: raw_result)
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        _prevalidate_for_import(port, cookie, token)

        status, body = _post_import(port=port, cookie=cookie, token=token)

        assert status == 409
        assert "部分書き込みを検出したため停止" in body
        assert "internal server error" not in body
        assert list(partial_dir.iterdir()) == []
        session = server.session_store.get(_session_id_from_cookie(cookie))
        assert session is not None
        assert session.imported_batch_ids == set()
    finally:
        _stop_server(server, thread)


def test_http_import_writer_exception_is_safe_and_does_not_mark_session(
    monkeypatch,
    tmp_path,
):
    raw_result = _bridge_raw_result()
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: raw_result)

    def fail_writer(_result, _repo_root):
        raise PermissionError("private filesystem detail")

    monkeypatch.setattr(app, "write_import_artifacts", fail_writer)
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        _prevalidate_for_import(port, cookie, token)

        status, body = _post_import(port=port, cookie=cookie, token=token)

        assert status == 500
        assert "request_id=" in body
        assert "private filesystem detail" not in body
        assert "Traceback" not in body
        session = server.session_store.get(_session_id_from_cookie(cookie))
        assert session is not None
        assert session.imported_batch_ids == set()
    finally:
        _stop_server(server, thread)


def test_http_import_render_failure_keeps_successful_import_in_session_history(
    monkeypatch,
    tmp_path,
):
    raw_result = _bridge_raw_result()
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: raw_result)
    monkeypatch.setattr(
        app,
        "write_import_artifacts",
        lambda _result, _repo_root: {
            "ready_count": 1,
            "blocked_count": 0,
            "warning_count": 0,
            "batch_ids": ["test_batch"],
            "item_paths": ["/internal/item.input.json"],
            "manifest_records": [],
            "blocked_records": [],
            "result_log_records": [],
        },
    )
    original_render = app.render_page_html

    def fail_import_result_render(session, page_state):
        if page_state.get("import_result") is not None:
            raise RuntimeError("simulated large result render failure")
        return original_render(session, page_state)

    monkeypatch.setattr(app, "render_page_html", fail_import_result_render)
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        _prevalidate_for_import(port, cookie, token)

        status, body = _post_import(port=port, cookie=cookie, token=token)

        assert status == 500
        assert "request_id=" in body
        assert "simulated large result render failure" not in body
        session = server.session_store.get(_session_id_from_cookie(cookie))
        assert session is not None
        assert session.imported_batch_ids == {"test_batch"}
    finally:
        _stop_server(server, thread)


def _post_wordpress_draft(
    *,
    port: int,
    cookie: str,
    item_id: str,
    token: str,
    return_to: str = "/database-search",
    explicit_confirmation: str | None = "create_wordpress_draft",
    include_csrf: bool = True,
    extra_fields: dict[str, str] | None = None,
) -> tuple[int, str]:
    from urllib.parse import urlencode

    fields = {
        "ebook_item_id": item_id,
        "return_to": return_to,
    }
    if include_csrf:
        fields["csrf_token"] = token
    if explicit_confirmation is not None:
        fields["explicit_confirmation"] = explicit_confirmation
    fields.update(extra_fields or {})
    body = urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/database-wordpress-draft",
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def _post_wordpress_schedule(
    *,
    port: int,
    cookie: str,
    token: str,
    operation: str = "SCHEDULE",
    include_csrf: bool = True,
    cancel: bool = False,
    return_to: str = "/database-search",
) -> tuple[int, str]:
    from urllib.parse import urlencode

    fields = {
        "ebook_item_id": "ebook-1",
        "wordpress_post_id": "264",
        "return_to": return_to,
        "operation": operation,
    }
    if not cancel:
        fields["wordpress_category_id"] = "43"
        if operation != "CATEGORY_UPDATE":
            fields["publish_at"] = "2026-08-03T07:00"
    if include_csrf:
        fields["csrf_token"] = token
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/database-wordpress-schedule"
        + ("-cancel" if cancel else ""),
        method="POST",
        data=urlencode(fields).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    with urllib.request.urlopen(request) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def test_post_wordpress_schedule_calls_service_once_and_shows_success(
    monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_USERNAME", "tester")
    monkeypatch.setenv("WORDPRESS_APPLICATION_PASSWORD", "dummy-password")
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: _FakeSessionContext(_build_route_item()))
    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        lambda **_kwargs: SimpleNamespace(),
    )

    def fake_schedule(self, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(operation="SCHEDULE")

    monkeypatch.setattr(
        "app.services.wordpress_post_schedule_service.WordPressPostScheduleService.schedule_post",
        fake_schedule,
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 0,
    )
    server, thread = _start_server(tmp_path)
    try:
        cookie, token = _open_session(server.server_address[1])
        status, body = _post_wordpress_schedule(
            port=server.server_address[1],
            cookie=cookie,
            token=token,
        )
        assert status == 200
        assert len(calls) == 1
        assert calls[0]["ebook_item_id"] == "ebook-1"
        assert calls[0]["wordpress_post_id"] == "264"
        assert calls[0]["publish_at_local"] == "2026-08-03T07:00"
        assert calls[0]["category_id"] == "43"
        assert "WordPressカテゴリーと予約投稿を設定しました" in body
    finally:
        _stop_server(server, thread)


def test_post_wordpress_schedule_rejects_invalid_csrf_before_service(
    monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(
        "app.services.wordpress_post_schedule_service.WordPressPostScheduleService.schedule_post",
        lambda self, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 0,
    )
    server, thread = _start_server(tmp_path)
    try:
        cookie, _token = _open_session(server.server_address[1])
        status, body = _post_wordpress_schedule(
            port=server.server_address[1],
            cookie=cookie,
            token="invalid",
        )
        assert status == 200
        assert calls == []
        assert "確認トークンが一致しない" in body
    finally:
        _stop_server(server, thread)


def test_post_wordpress_schedule_cancel_calls_cancel_once(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_USERNAME", "tester")
    monkeypatch.setenv("WORDPRESS_APPLICATION_PASSWORD", "dummy-password")
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: _FakeSessionContext(_build_route_item()))
    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        lambda **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "app.services.wordpress_post_schedule_service.WordPressPostScheduleService.cancel_schedule",
        lambda self, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 0,
    )
    server, thread = _start_server(tmp_path)
    try:
        cookie, token = _open_session(server.server_address[1])
        status, body = _post_wordpress_schedule(
            port=server.server_address[1],
            cookie=cookie,
            token=token,
            operation="CANCEL_SCHEDULE",
            cancel=True,
        )
        assert status == 200
        assert calls == [{"ebook_item_id": "ebook-1", "wordpress_post_id": "264"}]
        assert "WordPress予約を解除し、下書きへ戻しました" in body
    finally:
        _stop_server(server, thread)


def test_post_wordpress_category_update_calls_service_once(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_USERNAME", "tester")
    monkeypatch.setenv("WORDPRESS_APPLICATION_PASSWORD", "dummy-password")
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: _FakeSessionContext(_build_route_item()))
    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        lambda **_kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "app.services.wordpress_post_schedule_service.WordPressPostScheduleService.update_category",
        lambda self, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 0,
    )
    server, thread = _start_server(tmp_path)
    try:
        cookie, token = _open_session(server.server_address[1])
        status, body = _post_wordpress_schedule(
            port=server.server_address[1],
            cookie=cookie,
            token=token,
            operation="CATEGORY_UPDATE",
        )
        assert status == 200
        assert calls == [{
            "ebook_item_id": "ebook-1",
            "wordpress_post_id": "264",
            "category_id": "43",
        }]
        assert "WordPress投稿カテゴリーを更新しました" in body
    finally:
        _stop_server(server, thread)


@pytest.mark.parametrize(
    ("fails", "expected_notice"),
    [
        (False, "WordPressカテゴリーと予約投稿を設定しました"),
        (True, "指定カテゴリーはWordPressに存在しません"),
    ],
)
def test_schedule_redirect_rebuilds_original_search_context(
    monkeypatch,
    tmp_path,
    fails,
    expected_notice,
):
    import app.gui.ebook_database_web as web
    from app.integrations.wordpress_rest_client import WordPressCategory
    from app.services.wordpress_post_schedule_service import WordPressPostScheduleError

    searched = []
    row = _search_row(
        wordpress_status="DRAFT",
        wordpress_post_id="264",
    )
    category = WordPressCategory(43, "コミック新刊", "comic-new-release", 1)
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_USERNAME", "tester")
    monkeypatch.setenv("WORDPRESS_APPLICATION_PASSWORD", "dummy-password")
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: _FakeSessionContext(_build_route_item()))
    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        lambda **_kwargs: SimpleNamespace(),
    )

    def fake_schedule(self, **_kwargs):
        if fails:
            raise WordPressPostScheduleError("category_not_found", "missing")
        return SimpleNamespace(operation="SCHEDULE_WITH_CATEGORY")

    monkeypatch.setattr(
        "app.services.wordpress_post_schedule_service.WordPressPostScheduleService.schedule_post",
        fake_schedule,
    )
    monkeypatch.setattr(web, "load_dashboard_summary", lambda: _dashboard_fixture())
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 400)
    monkeypatch.setattr(
        web,
        "search_database_rows",
        lambda state: searched.append(state) or [row],
    )
    monkeypatch.setattr(web, "load_wordpress_schedule_states", lambda _ids: {})
    monkeypatch.setattr(web, "load_wordpress_category_context", lambda _rows: web.WordPressCategoryPageContext(
        categories=[category],
        item_states={"ebook-1": {"remote_status": "draft", "current_categories": [category]}},
    ))
    return_to = (
        "/database-search?keyword=GIANT&page=2&item_type=tankobon"
        "&store_name=rakuten_kobo&include_excluded=true"
        "&missing_price=true&missing_affiliate=true"
    )
    server, thread = _start_server(tmp_path)
    try:
        cookie, token = _open_session(server.server_address[1])
        status, body = _post_wordpress_schedule(
            port=server.server_address[1],
            cookie=cookie,
            token=token,
            return_to=return_to,
        )
        assert status == 200
        assert expected_notice in body
        assert "カテゴリーを設定して予約投稿" in body
        state = searched[-1]
        assert state.keyword == "GIANT"
        assert state.page == 2
        assert state.item_type == "tankobon"
        assert state.store_name == "rakuten_kobo"
        assert state.include_excluded is True
        assert state.missing_price is True
        assert state.missing_affiliate is True
    finally:
        _stop_server(server, thread)


def test_schedule_rejects_token_from_different_session(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "app.services.wordpress_post_schedule_service.WordPressPostScheduleService.schedule_post",
        lambda self, **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 0,
    )
    server, thread = _start_server(tmp_path)
    try:
        _old_cookie, old_token = _open_session(server.server_address[1])
        current_cookie, _current_token = _open_session(server.server_address[1])
        status, body = _post_wordpress_schedule(
            port=server.server_address[1],
            cookie=current_cookie,
            token=old_token,
        )
        assert status == 200
        assert calls == []
        assert "確認トークンが一致しない" in body
    finally:
        _stop_server(server, thread)


def test_get_root_returns_200_http(tmp_path):
    server, thread = _start_server(tmp_path)
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/")
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
    finally:
        _stop_server(server, thread)


def test_database_search_shows_wordpress_draft_button_when_ready(monkeypatch):
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(web, "load_dashboard_summary", lambda: _dashboard_fixture())
    monkeypatch.setattr(web, "search_database_rows", lambda _state: [_search_row()])
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1)
    monkeypatch.setattr(
        web,
        "load_approved_review_ready_approvals",
        lambda _ids: {
            "ebook-1": vars(_approved_request("ebook-1"))
        },
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_draft_execution_states",
        lambda _ids: {},
    )

    page = web.render_database_search_page("")

    assert "WordPress下書き作成" in page
    assert 'action="/database-wordpress-draft"' in page
    assert "承認後に作成できます" not in page
    assert "下書き作成済み" not in page


def test_database_search_disables_wordpress_draft_button_when_unapproved(monkeypatch):
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(web, "load_dashboard_summary", lambda: _dashboard_fixture())
    monkeypatch.setattr(
        web,
        "search_database_rows",
        lambda _state: [_search_row(review_status="IN_REVIEW")],
    )
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1)
    monkeypatch.setattr(
        web,
        "load_approved_review_ready_approvals",
        lambda _ids: {},
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_draft_execution_states",
        lambda _ids: {},
    )

    page = web.render_database_search_page("")

    assert "WordPress下書き作成（承認後）" in page
    assert (
        'type="submit"\n    class="workflow-action-button"\n'
        '    >WordPress下書き作成</button>'
        not in page
    )


def test_database_search_shows_created_label_when_post_exists(monkeypatch):
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(web, "load_dashboard_summary", lambda: _dashboard_fixture())
    monkeypatch.setattr(
        web,
        "search_database_rows",
        lambda _state: [
            _search_row(
                wordpress_status="DRAFT",
                wordpress_post_id="201",
            )
        ],
    )
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1)
    monkeypatch.setattr(
        web,
        "load_approved_review_ready_approvals",
        lambda _ids: {},
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_draft_execution_states",
        lambda _ids: {},
    )

    page = web.render_database_search_page("")

    assert "下書き作成済み / post_id=201" in page
    assert 'action="/database-wordpress-draft"' not in page


def test_database_search_ignores_stale_completed_execution_state(monkeypatch):
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(web, "load_dashboard_summary", lambda: _dashboard_fixture())
    monkeypatch.setattr(
        web,
        "search_database_rows",
        lambda _state: [
            _search_row(
                wordpress_status="NOT_CREATED",
                wordpress_post_id=None,
            )
        ],
    )
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1)
    monkeypatch.setattr(
        web,
        "load_approved_review_ready_approvals",
        lambda _ids: {"ebook-1": vars(_approved_request("ebook-1"))},
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_draft_execution_states",
        lambda _ids: {
            "ebook-1": {
                "status": "WORDPRESS_DRAFT_CREATED",
                "wordpress_post_id": 212,
            }
        },
    )

    page = web.render_database_search_page("")

    assert "下書き作成済み" not in page
    assert "post_id=212" not in page
    assert ">WordPress下書き作成</button>" in page
    assert 'action="/database-wordpress-draft"' in page


class _FakeSessionContext:
    def __init__(self, item, approval_request=None):
        self.item = item
        self.approval_request = approval_request
        self.rollback_called = False
        self.commit_called = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, model, item_id):
        if (
            self.approval_request is not None
            and getattr(self.approval_request, "id", None) == item_id
        ):
            return self.approval_request
        if self.item is None:
            return None
        if getattr(self.item, "id", None) != item_id:
            return None
        return self.item

    def scalar(self, statement):
        return self.approval_request

    def expire_all(self):
        return None

    def commit(self):
        self.commit_called = True

    def rollback(self):
        self.rollback_called = True


def _patch_session_local(monkeypatch, fake_session) -> None:
    fake_session_module = ModuleType("app.db.session")
    fake_session_module.SessionLocal = lambda: fake_session
    monkeypatch.setitem(sys.modules, "app.db.session", fake_session_module)


def _patch_amazon_affiliate_id(
    monkeypatch,
    tracking_id: str = "ktkr77-22",
) -> None:
    fake_affiliate_module = ModuleType(
        "app.services.affiliate_account_settings_service"
    )

    class AffiliateAccountSettingsService:
        def __init__(self, session):
            self.session = session

        def get_affiliate_id(self, service_name: str):
            return tracking_id

    fake_affiliate_module.AffiliateAccountSettingsService = (
        AffiliateAccountSettingsService
    )
    monkeypatch.setitem(
        sys.modules,
        "app.services.affiliate_account_settings_service",
        fake_affiliate_module,
    )


def _build_route_item(**overrides):
    offer = SimpleNamespace(
        store_name="rakuten_kobo",
        store_item_id="4310000000001",
        affiliate_url="https://books.rakuten.co.jp/rk/affiliate/",
        product_url="https://books.rakuten.co.jp/rk/example/",
    )
    values = {
        "id": "ebook-1",
        "title": "GIANT KILLING",
        "volume_label": "第66巻",
        "author_name": "ツジトモ",
        "publisher_name": "講談社",
        "release_date": "2026-07-20",
        "item_type": "tankobon",
        "source_item_id": "4310000000001",
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": None,
        "offers": [offer],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _approved_request(item_id="ebook-1", **overrides):
    values = {
        "id": "approval-1",
        "ebook_item_id": item_id,
        "approval_type": "REVIEW_READY",
        "status": "APPROVED",
        "decided_at": "2026-07-22T00:00:00+00:00",
        "expected_current_status": "REVIEW",
        "requested_status": "READY",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_post_wordpress_draft_calls_service_once_and_shows_result(monkeypatch, tmp_path):
    from app.gui import ebook_database_web as web
    from app.integrations.wordpress_rest_client import WordPressCategory

    item = _build_route_item()
    fake_session = _FakeSessionContext(item, _approved_request())
    calls = {"count": 0}
    displayed_row = {"value": _search_row()}
    category = WordPressCategory(43, "コミック新刊", "comic-new-release", 1)

    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_USERNAME", "tester")
    monkeypatch.setenv("WORDPRESS_APPLICATION_PASSWORD", "dummy-password")
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [displayed_row["value"]],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 1,
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_category_context",
        lambda _rows: web.WordPressCategoryPageContext(
            categories=[category],
            item_states={
                "ebook-1": {
                    "remote_status": "draft",
                    "current_categories": [category],
                }
            },
        ),
    )

    class FakeWordPressClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        FakeWordPressClient,
    )

    def fake_service(**kwargs):
        calls["count"] += 1
        assert kwargs["ebook_item_id"] == "ebook-1"
        displayed_row["value"] = _search_row(
            wordpress_status="DRAFT",
            wordpress_post_id="321",
        )
        return SimpleNamespace(
            status="DRAFT_CREATED",
            wordpress_post_id=321,
            wordpress_status="DRAFT",
            wordpress_link="https://example.test/?p=321",
            image_status="ATTACHED",
            image_media_id=444,
            image_media_url="https://example.test/uploads/cover.jpg",
            featured_media_set=True,
            publish_executed=False,
        )

    monkeypatch.setattr(
        "app.services.wordpress_draft_execution_service.execute_approved_wordpress_draft_once",
        fake_service,
    )

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_wordpress_draft(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
            return_to="/database-search?keyword=GIANT&page=2",
        )
        assert status == 200
        assert calls["count"] == 1
        assert "WordPress下書きを作成しました" in body
        assert "post_id=321" in body
        assert "image_status=ATTACHED" in body
        assert "WordPress予約・カテゴリー" in body
        assert "WordPress投稿: post_id=321" in body
        assert "カテゴリーを設定して予約投稿" in body
        assert 'action="/database-wordpress-schedule"' in body
        assert "keyword=GIANT" in body
        assert "page=2" in body
    finally:
        _stop_server(server, thread)


def test_post_wordpress_draft_passes_three_stores_with_dmm_blog_main(
    monkeypatch,
    tmp_path,
):
    offers = [
        SimpleNamespace(
            id="offer-dmm",
            store_name="dmm",
            store_item_id="b000example",
            affiliate_url="https://al.dmm.com/?af_id=x-main",
            product_url="https://book.dmm.com/product/123/b000example/",
            price_yen=715,
            price_amount=715,
            currency="JPY",
            availability_status="FOUND_CONFIRMED",
        ),
        SimpleNamespace(
            id="offer-rakuten",
            store_name="rakuten_kobo",
            store_item_id="4972000000001",
            affiliate_url="https://hb.afl.rakuten.co.jp/hgc/example/",
            product_url="https://books.rakuten.co.jp/rk/example/",
            price_yen=715,
            price_amount=715,
            currency="JPY",
            availability_status="FOUND_CONFIRMED",
        ),
        SimpleNamespace(
            id="offer-amazon",
            store_name="amazon",
            store_item_id="B012345678",
            affiliate_url="https://www.amazon.co.jp/dp/B012345678?tag=test-22",
            product_url="https://www.amazon.co.jp/dp/B012345678",
            price_yen=None,
            price_amount=None,
            currency=None,
            availability_status="FOUND_CONFIRMED",
        ),
    ]
    item = _build_route_item(offers=offers)
    fake_session = _FakeSessionContext(item, _approved_request())
    blog_url = "https://al.dmm.com/?af_id=blog-main"
    service_calls = []

    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_USERNAME", "tester")
    monkeypatch.setenv(
        "WORDPRESS_APPLICATION_PASSWORD", "dummy-password"
    )
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [_search_row()],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 1,
    )
    monkeypatch.setattr(
        "app.db.repositories.store_offer_affiliate_link_repository."
        "StoreOfferAffiliateLinkRepository.get_dmm_wordpress_link",
        lambda self, *, store_offer_id: SimpleNamespace(
            affiliate_url=blog_url
        ),
    )

    class FakeWordPressClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        FakeWordPressClient,
    )

    def fake_service(**kwargs):
        service_calls.append(kwargs)
        assert [
            candidate.store_name for candidate in kwargs["offers"]
        ] == ["amazon", "rakuten_kobo", "dmm"]
        assert kwargs["preferred_offer"].store_name == "amazon"
        dmm_offer = kwargs["offers"][2]
        assert dmm_offer.affiliate_url == blog_url
        assert "x-main" not in dmm_offer.affiliate_url
        refreshed = kwargs["refresh_current_state"]()
        assert len(refreshed) == 4
        assert refreshed[3].store_name == "amazon"
        return SimpleNamespace(
            status="DRAFT_CREATED",
            wordpress_post_id=321,
            wordpress_status="DRAFT",
            wordpress_link="https://example.test/?p=321",
            image_status="ATTACHED",
            image_media_id=444,
            image_media_url="https://example.test/uploads/cover.jpg",
            image_error_summary=None,
            featured_media_set=True,
            price_status="PRICE_READY",
            unified_price_yen=715,
            missing_price_stores=("amazon",),
            price_review_reasons=(),
            publish_executed=False,
        )

    monkeypatch.setattr(
        "app.services.wordpress_draft_execution_service."
        "execute_approved_wordpress_draft_once",
        fake_service,
    )

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, _token = _open_session(port)
        status, body = _post_wordpress_draft(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
        )
        assert status == 200
        assert len(service_calls) == 1
        assert "price_status=PRICE_READY" in body
        assert "missing_price_stores=amazon" in body
    finally:
        _stop_server(server, thread)


def test_post_wordpress_draft_rejects_when_post_id_exists(monkeypatch, tmp_path):
    item = _build_route_item(
        wordpress_status="DRAFT",
        wordpress_post_id="201",
    )
    fake_session = _FakeSessionContext(item)
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: fake_session)

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_wordpress_draft(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
        )
        assert status == 409
        assert "draft already exists" in body
    finally:
        _stop_server(server, thread)


def test_post_wordpress_draft_rejects_unapproved_item(monkeypatch, tmp_path):
    item = _build_route_item(review_status="IN_REVIEW")
    fake_session = _FakeSessionContext(item)
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: fake_session)

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_wordpress_draft(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
        )
        assert status == 400
        assert "review_status must be APPROVED" in body
    finally:
        _stop_server(server, thread)


def test_post_wordpress_draft_rejects_missing_bibliographic_metadata(
    monkeypatch, tmp_path
):
    item = _build_route_item(author_name=None, publisher_name=None)
    fake_session = _FakeSessionContext(item, _approved_request())
    calls = {"count": 0}
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: fake_session)

    def forbidden_service(**kwargs):
        calls["count"] += 1
        pytest.fail("WordPress service must not run for missing metadata")

    monkeypatch.setattr(
        "app.services.wordpress_draft_execution_service."
        "execute_approved_wordpress_draft_once",
        forbidden_service,
    )

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, _ = _open_session(port)
        status, body = _post_wordpress_draft(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
        )
        assert status == 400
        assert "METADATA_REVIEW_REQUIRED" in body
        assert "author_name" in body
        assert "publisher_name" in body
        assert calls["count"] == 0
        assert fake_session.commit_called is False
    finally:
        _stop_server(server, thread)


@pytest.mark.parametrize(
    "post_options",
    [
        {"include_csrf": False},
        {"token": "invalid-token"},
        {"explicit_confirmation": None},
        {"explicit_confirmation": "publish"},
        {"extra_fields": {"status": "publish"}},
    ],
)
def test_post_wordpress_draft_rejects_invalid_confirmation_before_service(
    monkeypatch,
    tmp_path,
    post_options,
):
    calls = {"count": 0}

    def forbidden_service(**kwargs):
        calls["count"] += 1
        pytest.fail("service must not run for invalid form protection")

    monkeypatch.setattr(
        "app.services.wordpress_draft_execution_service."
        "execute_approved_wordpress_draft_once",
        forbidden_service,
    )
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, _ = _open_session(port)
        options = {
            "port": port,
            "cookie": cookie,
            "item_id": "ebook-1",
            "token": get_workflow_action_token(),
        }
        options.update(post_options)
        status, _body = _post_wordpress_draft(**options)
        assert 400 <= status < 500
        assert calls["count"] == 0
    finally:
        _stop_server(server, thread)


def test_post_wordpress_draft_surfaces_review_required_without_publish(monkeypatch, tmp_path):
    item = _build_route_item()
    fake_session = _FakeSessionContext(item, _approved_request())
    calls = {"count": 0}

    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_USERNAME", "tester")
    monkeypatch.setenv("WORDPRESS_APPLICATION_PASSWORD", "dummy-password")
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: fake_session)
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [_search_row()],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 1,
    )

    class FakeWordPressClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        FakeWordPressClient,
    )

    def fake_service(**kwargs):
        calls["count"] += 1
        return SimpleNamespace(
            status="DRAFT_CREATED_IMAGE_REVIEW_REQUIRED",
            wordpress_post_id=654,
            wordpress_status="DRAFT",
            wordpress_link="https://example.test/?p=654",
            image_status="REVIEW_REQUIRED",
            image_media_id=None,
            image_media_url=None,
            featured_media_set=False,
            publish_executed=False,
        )

    monkeypatch.setattr(
        "app.services.wordpress_draft_execution_service.execute_approved_wordpress_draft_once",
        fake_service,
    )

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_wordpress_draft(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
        )
        assert status == 200
        assert calls["count"] == 1
        assert "書影確認が必要" in body
        assert "image_status=REVIEW_REQUIRED" in body
        assert "featured_media_set=false" in body
    finally:
        _stop_server(server, thread)


@pytest.mark.parametrize(
    ("input_type", "filename", "raw_bytes"),
    [
        ("collected", "ok_utf8.csv", _sample_csv_text().encode("utf-8")),
        ("manual", "ok_utf8_bom.csv", b"\xef\xbb\xbf" + _sample_csv_text().encode("utf-8")),
        ("manual", "ok_cp932.csv", _sample_csv_text().encode("cp932")),
    ],
)
def test_prevalidate_csv_variants_do_not_return_500(monkeypatch, tmp_path, input_type, filename, raw_bytes):
    called = {}

    def fake_import(csv_path):
        called["path"] = Path(csv_path)
        return _fake_engine_result()

    monkeypatch.setattr(app, "import_multistore_csv", fake_import)
    monkeypatch.setattr(app, "write_import_artifacts", lambda *_args, **_kwargs: pytest.fail("import must not run"))

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_prevalidate(
            port=port,
            cookie=cookie,
            token=token,
            input_type=input_type,
            filename=filename,
            file_bytes=raw_bytes,
        )
        assert status == 200
        assert "事前検証結果" in body
        assert called["path"].as_posix().startswith("/tmp/multistore_app_")
    finally:
        _stop_server(server, thread)


def test_prevalidate_missing_csv_returns_safe_4xx(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _fake_engine_result())

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_prevalidate(
            port=port,
            cookie=cookie,
            token=token,
            input_type="collected",
            filename=None,
            file_bytes=None,
        )
        assert 400 <= status < 500
        assert "CSVファイルを選択してください" in body
    finally:
        _stop_server(server, thread)


def test_prevalidate_non_csv_returns_safe_4xx(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _fake_engine_result())

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_prevalidate(
            port=port,
            cookie=cookie,
            token=token,
            input_type="collected",
            filename="not_csv.txt",
            file_bytes=b"a,b\n1,2\n",
            file_content_type="text/plain",
        )
        assert 400 <= status < 500
        assert ".csv ファイルのみアップロードできます。" in body
    finally:
        _stop_server(server, thread)


def test_prevalidate_invalid_csv_is_validation_error_not_500(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: (_ for _ in ()).throw(app.AppError("CSV形式不正")))

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_prevalidate(
            port=port,
            cookie=cookie,
            token=token,
            input_type="collected",
            filename="bad.csv",
            file_bytes=_sample_csv_text().encode("utf-8"),
        )
        assert 400 <= status < 500
        assert "CSV形式不正" in body
    finally:
        _stop_server(server, thread)


def test_unexpected_exception_logs_traceback_and_response_hides_details(monkeypatch, tmp_path, capsys):
    def raise_unexpected(_path):
        raise RuntimeError("secret details")

    monkeypatch.setattr(app, "import_multistore_csv", raise_unexpected)
    logger = logging.getLogger(app.__name__)
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(logging.ERROR)
    original_level = logger.level
    original_propagate = logger.propagate
    logger.setLevel(logging.ERROR)
    logger.propagate = False
    logger.addHandler(stream_handler)

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_prevalidate(
            port=port,
            cookie=cookie,
            token=token,
            input_type="collected",
            filename="ok.csv",
            file_bytes=_sample_csv_text().encode("utf-8"),
        )
        captured = capsys.readouterr()
        assert status == 500
        assert "Traceback" not in body
        assert "secret details" not in body
        assert "request_id=" in body
        assert "Unexpected error during /prevalidate" in captured.err
        assert "Traceback" in captured.err
        assert "RuntimeError: secret details" in captured.err
    finally:
        logger.removeHandler(stream_handler)
        logger.setLevel(original_level)
        logger.propagate = original_propagate
        _stop_server(server, thread)


def test_http_import_stops_with_4xx_when_raw_result_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "import_multistore_csv", lambda _path: _bridge_raw_result())
    monkeypatch.setattr(app, "write_import_artifacts", lambda *_args, **_kwargs: pytest.fail("writer must not be called"))

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        pre_status, _ = _post_prevalidate(
            port=port,
            cookie=cookie,
            token=token,
            input_type="collected",
            filename="ok.csv",
            file_bytes=_sample_csv_text().encode("utf-8"),
        )
        assert pre_status == 200

        session_id = _session_id_from_cookie(cookie)
        session = server.session_store.get(session_id)
        assert session is not None
        session.raw_result = None

        status, body = _post_import(port=port, cookie=cookie, token=token, explicit_confirmation=True)
        assert 400 <= status < 500
        assert "事前検証結果の原本が保持されていないため、成果物生成を停止しました。CSVを再検証してください。" in body
    finally:
        _stop_server(server, thread)


def test_http_convert_preview_generates_downloadable_utf8_bom_csv(monkeypatch, tmp_path):
    def fake_import(_path):
        return {
            "status": "ERROR",
            "ready_payloads": [],
            "blocked_rows": [],
            "warnings": [],
            "structure_errors": [{"code": "CSV_HEADER_MISSING_COLUMNS", "message": "missing"}],
            "ready_count": 0,
            "blocked_count": 0,
            "warning_count": 0,
            "batch_ids": [],
            "safety": {
                "wordpress_write_performed": False,
                "wordpress_publish_performed": False,
                "external_network_performed": False,
                "input_status_fixed_to_draft": True,
            },
        }

    monkeypatch.setattr(app, "import_multistore_csv", fake_import)
    monkeypatch.setattr(app, "write_import_artifacts", lambda *_args, **_kwargs: pytest.fail("writer must not be called"))

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, token = _open_session(port)
        status, body = _post_prevalidate(
            port=port,
            cookie=cookie,
            token=token,
            input_type="manual",
            filename="sample_ls_new_batch_input.csv",
            file_bytes=_old_ls_csv_text().encode("utf-8"),
        )
        assert status == 200
        assert "V2形式へ変換プレビュー" in body

        convert_req = urllib.request.Request(
            f"http://127.0.0.1:{port}/convert-preview",
            method="POST",
            data=f"op_token={token}".encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
            },
        )
        with urllib.request.urlopen(convert_req) as convert_resp:
            convert_body = convert_resp.read().decode("utf-8", errors="replace")
            assert convert_resp.status == 200
            assert "V2変換プレビュー" in convert_body

        get_req = urllib.request.Request(f"http://127.0.0.1:{port}/converted.csv", headers={"Cookie": cookie})
        with urllib.request.urlopen(get_req) as converted_resp:
            converted_bytes = converted_resp.read()
            assert converted_resp.status == 200
            assert converted_bytes.startswith(b"\xef\xbb\xbf")
    finally:
        _stop_server(server, thread)


# ============================================================
# Amazon manual offer HTTP route
# ============================================================


def _post_amazon_offer(
    *,
    port: int,
    cookie: str,
    item_id: str,
    token: str,
    asin: str = "B0H7Z26WWB",
    tracking_id: str = "ktkr77-22",
    return_to: str = "/database-search",
    operation: str = "",
) -> tuple[int, str]:
    from urllib.parse import urlencode

    body = urlencode(
        {
            "csrf_token": token,
            "ebook_item_id": item_id,
            "asin": asin,
            "tracking_id": tracking_id,
            "return_to": return_to,
            "operation": operation,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/database-amazon-offer",
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return (
                resp.status,
                resp.read().decode(
                    "utf-8",
                    errors="replace",
                ),
            )
    except urllib.error.HTTPError as exc:
        return (
            exc.code,
            exc.read().decode(
                "utf-8",
                errors="replace",
            ),
        )


def _patch_database_search_page(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.gui.ebook_database_web.load_dashboard_summary",
        lambda: _dashboard_fixture(),
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.search_database_rows",
        lambda _state: [_search_row()],
    )
    monkeypatch.setattr(
        "app.gui.ebook_database_web.count_database_rows",
        lambda _state: 1,
    )


def test_post_catalog_edit_normalizes_authors_and_renders_saved_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from decimal import Decimal
    from urllib.parse import urlencode

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base
    from app.db.models import EbookItem, StoreOffer

    engine = create_engine(f"sqlite:///{tmp_path / 'catalog-edit.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        item = EbookItem(
            source_name="test",
            source_item_id="item-1",
            title="作品 タイトル",
            volume_label="第1巻",
            author_name="旧作者",
            publisher_name="旧出版社",
        )
        session.add(item)
        session.flush()
        item_id = item.id
        session.add(
            StoreOffer(
                ebook_item_id=item_id,
                store_name="rakuten_kobo",
                store_item_id="RK-1",
                product_url="https://product.example/rk",
                price_amount=Decimal("500"),
                price_yen=500,
                currency="JPY",
            )
        )
        session.commit()

    session_module = ModuleType("app.db.session")
    session_module.SessionLocal = factory
    monkeypatch.setitem(sys.modules, "app.db.session", session_module)

    import app.gui.ebook_database_web as web

    monkeypatch.setattr(web, "load_dashboard_summary", _dashboard_fixture)

    def current_rows(_state):
        with factory() as session:
            saved = session.get(EbookItem, item_id)
            assert saved is not None
            return [
                _search_row(
                    id=item_id,
                    title=saved.title,
                    volume_label=saved.volume_label,
                    author_name=saved.author_name,
                    publisher_name=saved.publisher_name,
                    rakuten_kobo_offer={
                        "price_amount": Decimal("500"),
                        "currency": "JPY",
                    },
                )
            ]

    monkeypatch.setattr(web, "search_database_rows", current_rows)
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1)

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, _session_token = _open_session(port)
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/database-catalog-edit",
            method="POST",
            data=urlencode(
                {
                    "csrf_token": get_workflow_action_token(),
                    "ebook_item_id": item_id,
                    "return_to": "/database-search",
                    "volume_label": "第 2 巻",
                    "authors": "作者 A | 作者　B",
                    "publisher": "新 出版社",
                    "price": "500",
                    "currency": "JPY",
                    "reason": "作者表記の修正",
                }
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": cookie,
            },
        )
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert response.url.endswith(
                "/database-search?catalog_edit_result=success"
            )

        with factory() as session:
            saved = session.get(EbookItem, item_id)
            assert saved is not None
            assert saved.author_name == "作者A|作者B"
            assert saved.publisher_name == "新 出版社"
            assert saved.volume_label == "第 2 巻"
            assert saved.title == "作品 タイトル"

        assert "作者A|作者B" in body
        assert 'name="authors" maxlength="255" value="作者A|作者B"' in body
        assert 'name="publisher" maxlength="255" value="新 出版社"' in body
    finally:
        _stop_server(server, thread)
        engine.dispose()


def test_post_amazon_offer_preview_links_urls_without_saving(
    monkeypatch,
    tmp_path,
):
    item = _build_route_item()
    fake_session = _FakeSessionContext(item)
    _patch_session_local(monkeypatch, fake_session)
    _patch_amazon_affiliate_id(monkeypatch)
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, _session_token = _open_session(port)
        status, body = _post_amazon_offer(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
            operation="preview",
        )

        assert status == 200
        assert fake_session.commit_called is False
        assert "Amazonリンク保存前プレビュー" in body
        assert (
            '<a href="https://www.amazon.co.jp/dp/B0H7Z26WWB" '
            'target="_blank" rel="noopener noreferrer">'
            'https://www.amazon.co.jp/dp/B0H7Z26WWB</a>'
        ) in body
        assert (
            '<a href="https://www.amazon.co.jp/dp/B0H7Z26WWB/ref=nosim?tag=ktkr77-22" '
            'target="_blank" rel="noopener noreferrer">'
            'https://www.amazon.co.jp/dp/B0H7Z26WWB/ref=nosim?tag=ktkr77-22</a>'
        ) in body
        assert 'name="confirmed"' in body
        assert "確認して保存" in body
    finally:
        _stop_server(server, thread)


def test_preview_url_link_escapes_and_rejects_unsafe_values() -> None:
    safe_url = "https://example.test/item?a=1&b=2"
    rendered = app._render_preview_url(safe_url)

    assert (
        'href="https://example.test/item?a=1&amp;b=2" '
        'target="_blank" rel="noopener noreferrer"'
    ) in rendered
    assert ">https://example.test/item?a=1&amp;b=2</a>" in rendered
    assert '<a href="http://example.test/item"' in app._render_preview_url(
        "http://example.test/item"
    )
    for unsafe_url in (
        "javascript:alert(1)",
        "data:text/html,unsafe",
        "file:///tmp/unsafe",
        "example.test/item",
        "https://",
        "https://example.test:invalid/item",
        "https://example.test/has space",
        "",
    ):
        assert "<a " not in app._render_preview_url(unsafe_url)
    empty_rendered = app._render_preview_url("", empty_text="（URL入力）")
    assert empty_rendered == "（URL入力）"
    assert "<a " not in empty_rendered
    assert app._render_preview_url("javascript:<script>") == (
        "javascript:&lt;script&gt;"
    )


def test_post_amazon_offer_saves_once_and_shows_result(
    monkeypatch,
    tmp_path,
):
    item = _build_route_item()
    fake_session = _FakeSessionContext(item)
    calls = {"count": 0}

    _patch_session_local(monkeypatch, fake_session)
    _patch_amazon_affiliate_id(monkeypatch)
    _patch_database_search_page(monkeypatch)

    def fake_save(
        self,
        *,
        ebook_item_id,
        asin,
        tracking_id,
    ):
        calls["count"] += 1

        assert ebook_item_id == "ebook-1"
        assert asin == "B0H7Z26WWB"
        assert tracking_id == "ktkr77-22"

        return SimpleNamespace(
            ebook_item_id=ebook_item_id,
            asin=asin,
            product_url=(
                "https://www.amazon.co.jp/"
                "dp/B0H7Z26WWB"
            ),
            affiliate_url=(
                "https://www.amazon.co.jp/"
                "dp/B0H7Z26WWB/ref=nosim"
                "?tag=ktkr77-22"
            ),
            offer_id="amazon-offer-1",
        )

    monkeypatch.setattr(
        "app.services.amazon_manual_offer_service."
        "AmazonManualOfferService.save",
        fake_save,
    )

    server, thread = _start_server(tmp_path)

    try:
        port = server.server_address[1]
        cookie, _session_token = _open_session(port)

        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        token = get_workflow_action_token()

        status, body = _post_amazon_offer(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=token,
        )

        # urllib follows the 303 redirect to database-search.
        assert status == 200
        assert calls["count"] == 1
        assert fake_session.commit_called is True
        assert fake_session.rollback_called is False
        assert (
            "Amazonアフィリエイトリンクを保存しました。"
            in body
        )
        assert "ASIN=B0H7Z26WWB" in body
    finally:
        _stop_server(server, thread)


def test_post_amazon_offer_rejects_invalid_asin(
    monkeypatch,
    tmp_path,
):
    item = _build_route_item()
    fake_session = _FakeSessionContext(item)

    _patch_session_local(monkeypatch, fake_session)
    _patch_amazon_affiliate_id(monkeypatch)
    _patch_database_search_page(monkeypatch)

    server, thread = _start_server(tmp_path)

    try:
        port = server.server_address[1]
        cookie, _session_token = _open_session(port)

        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        token = get_workflow_action_token()

        status, body = _post_amazon_offer(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=token,
            asin="BAD-ASIN",
        )

        assert status == 200
        assert fake_session.commit_called is False
        assert fake_session.rollback_called is True
        assert (
            "ASINまたはトラッキングIDの形式が不正です。"
            in body
        )
    finally:
        _stop_server(server, thread)


def test_post_amazon_offer_rejects_invalid_tracking_id(
    monkeypatch,
    tmp_path,
):
    item = _build_route_item()
    fake_session = _FakeSessionContext(item)

    _patch_session_local(monkeypatch, fake_session)
    _patch_amazon_affiliate_id(monkeypatch, tracking_id="invalid")
    _patch_database_search_page(monkeypatch)

    server, thread = _start_server(tmp_path)

    try:
        port = server.server_address[1]
        cookie, _session_token = _open_session(port)

        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        token = get_workflow_action_token()

        status, body = _post_amazon_offer(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=token,
        )

        assert status == 200
        assert fake_session.commit_called is False
        assert fake_session.rollback_called is True
        assert (
            "ASINまたはトラッキングIDの形式が不正です。"
            in body
        )

        fake_session.commit_called = False
        fake_session.rollback_called = False

        _patch_amazon_affiliate_id(monkeypatch, tracking_id="")

        status, body = _post_amazon_offer(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=token,
        )

        assert status == 200
        assert fake_session.commit_called is False
        assert fake_session.rollback_called is False
    finally:
        _stop_server(server, thread)


def test_post_amazon_offer_rejects_invalid_csrf_token(
    monkeypatch,
    tmp_path,
):
    item = _build_route_item()
    fake_session = _FakeSessionContext(item)
    calls = {"count": 0}

    _patch_session_local(monkeypatch, fake_session)
    _patch_database_search_page(monkeypatch)

    def should_not_save(self, **kwargs):
        calls["count"] += 1
        pytest.fail(
            "Amazon service must not run for invalid CSRF token"
        )

    monkeypatch.setattr(
        "app.services.amazon_manual_offer_service."
        "AmazonManualOfferService.save",
        should_not_save,
    )

    server, thread = _start_server(tmp_path)

    try:
        port = server.server_address[1]
        cookie, _token = _open_session(port)

        status, body = _post_amazon_offer(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token="invalid-token",
        )

        assert status == 200
        assert calls["count"] == 0
        assert fake_session.commit_called is False
        assert fake_session.rollback_called is False
        assert (
            "確認トークンが一致しないため保存を拒否しました。"
            in body
        )
    finally:
        _stop_server(server, thread)


def test_post_amazon_offer_rejects_missing_item(
    monkeypatch,
    tmp_path,
):
    fake_session = _FakeSessionContext(None)
    calls = {"count": 0}

    _patch_session_local(monkeypatch, fake_session)
    _patch_amazon_affiliate_id(monkeypatch)
    _patch_database_search_page(monkeypatch)

    def should_not_save(self, **kwargs):
        calls["count"] += 1
        pytest.fail(
            "Amazon service must not run when item is missing"
        )

    monkeypatch.setattr(
        "app.services.amazon_manual_offer_service."
        "AmazonManualOfferService.save",
        should_not_save,
    )

    server, thread = _start_server(tmp_path)

    try:
        port = server.server_address[1]
        cookie, _session_token = _open_session(port)

        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        token = get_workflow_action_token()

        status, body = _post_amazon_offer(
            port=port,
            cookie=cookie,
            item_id="missing-ebook",
            token=token,
        )

        assert status == 200
        assert calls["count"] == 0
        assert fake_session.commit_called is False
        assert fake_session.rollback_called is False
        assert (
            "対象の電子書籍データが見つかりません。"
            in body
        )
    finally:
        _stop_server(server, thread)


def test_post_amazon_offer_rolls_back_on_service_exception(
    monkeypatch,
    tmp_path,
):
    item = _build_route_item()
    fake_session = _FakeSessionContext(item)

    _patch_session_local(monkeypatch, fake_session)
    _patch_amazon_affiliate_id(monkeypatch)
    _patch_database_search_page(monkeypatch)

    def raise_unexpected(self, **kwargs):
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(
        "app.services.amazon_manual_offer_service."
        "AmazonManualOfferService.save",
        raise_unexpected,
    )

    server, thread = _start_server(tmp_path)

    try:
        port = server.server_address[1]
        cookie, _session_token = _open_session(port)

        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        token = get_workflow_action_token()

        status, body = _post_amazon_offer(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=token,
        )

        assert status == 200
        assert fake_session.commit_called is False
        assert fake_session.rollback_called is True
        assert (
            "Amazonリンクの保存中にエラーが発生しました。"
            in body
        )
        assert "simulated database failure" not in body
        assert "Traceback" not in body
    finally:
        _stop_server(server, thread)


# ============================================================
# DMM affiliate HTML preview HTTP route
# ============================================================


def _post_dmm_offer_preview(
    *, port: int, cookie: str, item_id: str, token: str, dmm_input: str
) -> tuple[int, str]:
    from urllib.parse import urlencode

    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/database-dmm-offer",
        method="POST",
        data=urlencode(
            {
                "csrf_token": token,
                "ebook_item_id": item_id,
                "return_to": "/database-search",
                "operation": "preview",
                "dmm_input": dmm_input,
                "price": "",
                "currency": "JPY",
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
        },
    )
    with urllib.request.urlopen(request) as response:
        return response.status, response.read().decode("utf-8")


def test_post_dmm_html_preview_shows_result_without_saving(
    monkeypatch, tmp_path
):
    fake_session = _FakeSessionContext(_build_route_item())
    _patch_session_local(monkeypatch, fake_session)
    calls = {"preview": 0, "save": 0}

    def fake_preview(self, **kwargs):
        calls["preview"] += 1
        assert kwargs["ebook_item_id"] == "ebook-1"
        assert kwargs["dmm_input"].startswith("<a href=")
        return SimpleNamespace(
            product_name="GIANT KILLING 第66巻",
            product_group_id="4493998",
            store_item_id="b000fhftx08481",
            product_url=(
                "https://book.dmm.com/product/4493998/b000fhftx08481/"
            ),
            affiliate_url="https://al.dmm.com/?lurl=example",
            source_affiliate_url="https://al.dmm.com/?source=1",
            affiliate_id="xuanyilugang-008",
            matched_destination_name="メインブログ",
            destination_links=(
                SimpleNamespace(
                    display_name="メインブログ",
                    destination_key="blog_main",
                    configured=True,
                    active=True,
                    generation_available=True,
                ),
                SimpleNamespace(
                    display_name="公式X",
                    destination_key="x_main",
                    configured=True,
                    active=True,
                    generation_available=True,
                ),
            ),
            service="book",
            channel="toolbar",
            channel_id="text",
            price_amount=None,
            currency="JPY",
            warnings=(),
            registration_allowed=True,
        )

    def must_not_save(self, **kwargs):
        calls["save"] += 1
        pytest.fail("preview must not save a DMM offer")

    monkeypatch.setattr(
        "app.services.dmm_manual_offer_service."
        "DmmManualOfferService.preview_input",
        fake_preview,
    )
    monkeypatch.setattr(
        "app.services.dmm_manual_offer_service.DmmManualOfferService.save",
        must_not_save,
    )
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, _ = _open_session(port)
        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        status, body = _post_dmm_offer_preview(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
            dmm_input='<a href="https://al.dmm.com/">GIANT KILLING</a>',
        )

        assert status == 200
        assert calls == {"preview": 1, "save": 0}
        assert fake_session.commit_called is False
        assert "DMMリンク解析結果プレビュー" in body
        assert "b000fhftx08481" in body
        assert "一致した掲載先" in body
        assert "メインブログ" in body
        assert "公式X" in body
        assert body.count("生成可能") == 2
        assert "この内容で登録" in body
        for url in (
            "https://book.dmm.com/product/4493998/b000fhftx08481/",
            "https://al.dmm.com/?source=1",
            "https://al.dmm.com/?lurl=example",
        ):
            assert (
                f'<a href="{url}" target="_blank" '
                f'rel="noopener noreferrer">{url}</a>'
            ) in body
        assert 'name="confirmed"' in body
    finally:
        _stop_server(server, thread)


def test_post_dmm_html_preview_hides_save_when_warning_blocks(
    monkeypatch, tmp_path
):
    fake_session = _FakeSessionContext(_build_route_item())
    _patch_session_local(monkeypatch, fake_session)

    def fake_preview(self, **kwargs):
        return SimpleNamespace(
            product_name="別作品",
            product_group_id="4493998",
            store_item_id="b000fhftx08481",
            product_url=(
                "https://book.dmm.com/product/4493998/b000fhftx08481/"
            ),
            affiliate_url="https://al.dmm.com/?lurl=example",
            source_affiliate_url="https://al.dmm.com/?source=1",
            affiliate_id="other-999",
            matched_destination_name="",
            destination_links=(
                SimpleNamespace(
                    display_name="メインブログ",
                    destination_key="blog_main",
                    configured=True,
                    active=True,
                    generation_available=True,
                ),
                SimpleNamespace(
                    display_name="公式X",
                    destination_key="x_main",
                    configured=False,
                    active=False,
                    generation_available=False,
                ),
            ),
            service="book",
            channel="toolbar",
            channel_id="text",
            price_amount=None,
            currency="JPY",
            warnings=("affiliate_profile_not_found", "title_mismatch"),
            registration_allowed=False,
        )

    monkeypatch.setattr(
        "app.services.dmm_manual_offer_service."
        "DmmManualOfferService.preview_input",
        fake_preview,
    )
    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        cookie, _ = _open_session(port)
        from app.services.workflow_action_service import (
            get_workflow_action_token,
        )

        _, body = _post_dmm_offer_preview(
            port=port,
            cookie=cookie,
            item_id="ebook-1",
            token=get_workflow_action_token(),
            dmm_input='<a href="https://al.dmm.com/">別作品</a>',
        )

        assert "一致するDMM掲載先設定がない" in body
        assert "選択中の作品タイトルと大きく異なる" in body
        assert "警告を解消するまで登録できません" in body
        assert "この内容で登録" not in body
    finally:
        _stop_server(server, thread)


def _post_destination_profile(
    *,
    port: int,
    destination_key: str,
    destination_type: str,
    affiliate_id: str,
) -> tuple[int, str]:
    from urllib.parse import urlencode

    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/affiliate-settings",
        method="POST",
        data=urlencode(
            {
                "csrf_token": get_workflow_action_token(),
                "operation": "save_destination_profile",
                "provider": "dmm",
                "destination_key": destination_key,
                "destination_type": destination_type,
                "affiliate_id": affiliate_id,
                "channel": "toolbar",
                "channel_id": "text",
                "is_active": "true",
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request) as response:
        return response.status, response.read().decode("utf-8")


def test_affiliate_settings_route_saves_blog_and_x_independently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base
    from app.db.models import AffiliateDestinationProfile

    engine = create_engine(f"sqlite:///{tmp_path / 'profiles.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session_module = ModuleType("app.db.session")
    session_module.SessionLocal = factory
    monkeypatch.setitem(sys.modules, "app.db.session", session_module)

    server, thread = _start_server(tmp_path)
    try:
        port = server.server_address[1]
        status, body = _post_destination_profile(
            port=port,
            destination_key="blog_main",
            destination_type="wordpress",
            affiliate_id="blog-user-008",
        )
        assert status == 200
        assert "アフィリエイト設定を保存しました" in body
        with factory() as session:
            profiles = session.scalars(
                select(AffiliateDestinationProfile)
            ).all()
            assert [(profile.destination_key, profile.affiliate_id) for profile in profiles] == [
                ("blog_main", "blog-user-008")
            ]

        status, _ = _post_destination_profile(
            port=port,
            destination_key="x_main",
            destination_type="x",
            affiliate_id="x-user-009",
        )
        assert status == 200
        with factory() as session:
            profiles = session.scalars(
                select(AffiliateDestinationProfile).order_by(
                    AffiliateDestinationProfile.destination_key
                )
            ).all()
            assert [
                (profile.destination_key, profile.affiliate_id)
                for profile in profiles
            ] == [
                ("blog_main", "blog-user-008"),
                ("x_main", "x-user-009"),
            ]
    finally:
        _stop_server(server, thread)
        engine.dispose()
