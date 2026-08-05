import json
import tempfile
from pathlib import Path

from scripts.run_phase7_5c_single_draft_create_live_manual import run_live_manual

VALID_TOKEN = "APPROVE_SINGLE_DRAFT_CREATE_LIVE_ONE_TIME"


class DummyResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _write_p75b(path: Path, **overrides):
    data = {
        "status": "PASS",
        "approval_token": VALID_TOKEN,
        "approval_token_valid": True,
        "all_remaining_items_confirmed": True,
        "token_constraints_valid": True,
        "token_constraints": {
            "one_time_only": True,
            "expires_minutes": 30,
            "post_status": "draft",
            "post_count_limit": 1,
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "export_allowed": False,
        },
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_payload(path: Path, **overrides):
    data = {
        "title": "テスト下書きタイトル",
        "content": "<p>テスト本文</p>",
        "status": "draft",
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_execute_live_success_with_mock_post():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75b = td / "p75b.json"
        payload = td / "payload.json"
        out = td / "result.json"
        _write_p75b(p75b)
        _write_payload(payload)

        def post_ok(url, json, auth, timeout):
            assert json["status"] == "draft"
            assert timeout == 20
            return DummyResponse(201, {"id": 12345, "status": "draft"})

        result = run_live_manual(
            p75b,
            payload,
            out,
            execute_live=True,
            wordpress_base_url="https://example.com",
            wp_username="user",
            wp_app_password="pass",
            post_func=post_ok,
        )

        assert result["status"] == "PASS"
        assert result["wordpress_write_executed"] is True
        assert result["created_post_id"] == 12345
        assert result["relocked_after_execution"] is True


def test_missing_phase7_5b_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        payload = td / "payload.json"
        out = td / "result.json"
        _write_payload(payload)

        result = run_live_manual(
            td / "missing.json",
            payload,
            out,
            execute_live=True,
            wordpress_base_url="https://example.com",
            wp_username="user",
            wp_app_password="pass",
            post_func=lambda *a, **k: DummyResponse(201, {"id": 1, "status": "draft"}),
        )

        assert result["status"] == "ABORT"


def test_invalid_constraints_aborts():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75b = td / "p75b.json"
        payload = td / "payload.json"
        out = td / "result.json"
        _write_p75b(
            p75b,
            token_constraints={
                "one_time_only": True,
                "expires_minutes": 30,
                "post_status": "publish",
                "post_count_limit": 1,
                "publish_allowed": False,
                "update_allowed": False,
                "delete_allowed": False,
                "export_allowed": False,
            },
        )
        _write_payload(payload)

        result = run_live_manual(
            p75b,
            payload,
            out,
            execute_live=True,
            wordpress_base_url="https://example.com",
            wp_username="user",
            wp_app_password="pass",
            post_func=lambda *a, **k: DummyResponse(201, {"id": 1, "status": "draft"}),
        )

        assert result["status"] == "ABORT"


def test_execute_live_false_aborts_and_writes_log():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75b = td / "p75b.json"
        payload = td / "payload.json"
        out = td / "result.json"
        _write_p75b(p75b)
        _write_payload(payload)

        result = run_live_manual(p75b, payload, out, execute_live=False)

        assert result["status"] == "ABORT"
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "ABORT"
        assert saved["wordpress_write_executed"] is False


def test_live_execution_failure_response_records_evidence():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75b = td / "p75b.json"
        payload = td / "payload.json"
        out = td / "result.json"
        _write_p75b(p75b)
        _write_payload(payload)

        result = run_live_manual(
            p75b,
            payload,
            out,
            execute_live=True,
            wordpress_base_url="https://example.com",
            wp_username="user",
            wp_app_password="pass",
            post_func=lambda *a, **k: DummyResponse(500, {"message": "server error"}),
        )

        assert result["status"] == "FAIL"
        assert result["wordpress_write_executed"] is False
        assert result["live_execution_attempted"] is True
        assert result["relocked_after_execution"] is True


def test_output_contains_forbidden_action_flags_false_on_success():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p75b = td / "p75b.json"
        payload = td / "payload.json"
        out = td / "result.json"
        _write_p75b(p75b)
        _write_payload(payload)

        result = run_live_manual(
            p75b,
            payload,
            out,
            execute_live=True,
            wordpress_base_url="https://example.com",
            wp_username="user",
            wp_app_password="pass",
            post_func=lambda *a, **k: DummyResponse(201, {"id": 99, "status": "draft"}),
        )

        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["publish_allowed"] is False
        assert saved["update_allowed"] is False
        assert saved["delete_allowed"] is False
        assert saved["export_allowed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
