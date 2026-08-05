import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_phase8_3_first_one_item_wordpress_draft_create as phase83


def base_policy() -> dict:
    return {
        "phase": "Phase 8-3",
        "name": "first_one_item_wordpress_draft_create_policy",
        "policy_status": "CONTROLLED_ONE_ITEM_EXECUTION",
        "production_status": "LIMITED_DRAFT_CREATE_ONLY",
        "mode": "CONTROLLED_EXECUTION",
        "execution": "LIVE_DRAFT_CREATE_ONLY",
        "human_approval_required": True,
        "wordpress_draft_creation": "ALLOW_ONE_DRAFT_ONLY",
        "wordpress_api_call_allowed": True,
        "wordpress_write_executed_default": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "bulk_execution": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_1_explicit_human_approval_result.json",
            "exchange/logs/phase8_2_final_live_preflight_result.json",
        ],
        "required_statuses": {
            "phase8_1": "APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY",
            "phase8_2": "FINAL_PREFLIGHT_PASS_READY_FOR_PHASE8_3_SINGLE_DRAFT_CREATE",
        },
        "required_env": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "wordpress_request": {
            "method": "POST",
            "endpoint": "/wp-json/wp/v2/posts",
            "status": "draft",
            "max_posts": 1,
        },
        "retry_policy": {
            "retry_allowed": False,
            "max_retries": 0,
        },
        "post_create_validation": {
            "require_post_id": True,
            "require_status_draft": True,
            "reject_status_publish": True,
            "require_link_or_guid": True,
        },
    }


def base_request() -> dict:
    return {
        "target_item_count": 1,
        "approval_token": "APPROVE_DRAFT_CREATE_ONLY",
        "title": "サンプル",
        "body": "PR：本記事には広告が含まれます。",
    }


def run_case(tmp_path: Path, monkeypatch, policy=None, request=None, phase81="APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY", phase82="FINAL_PREFLIGHT_PASS_READY_FOR_PHASE8_3_SINGLE_DRAFT_CREATE", missing_evidence=False):
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(request or base_request())

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    request_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

    if not missing_evidence:
        e1 = tmp_path / p["required_evidence"][0]
        e2 = tmp_path / p["required_evidence"][1]
        e1.parent.mkdir(parents=True, exist_ok=True)
        e2.parent.mkdir(parents=True, exist_ok=True)
        e1.write_text(json.dumps({"status": phase81}), encoding="utf-8")
        e2.write_text(json.dumps({"status": phase82}), encoding="utf-8")

    return phase83.run_first_one_item_draft_create(policy_path, request_path, out_json, out_md)


def test_credentials_missing_not_executed(tmp_path: Path, monkeypatch):
    for key in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)

    called = {"count": 0}

    def fake_post(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("requests.post should not be called")

    monkeypatch.setattr(phase83.requests, "post", fake_post)
    r = run_case(tmp_path, monkeypatch)
    assert r["status"] == "NOT_EXECUTED_MISSING_CREDENTIALS"
    assert r["wordpress_api_call_attempted"] is False
    assert called["count"] == 0


def test_phase82_evidence_missing_abort(tmp_path: Path, monkeypatch):
    r = run_case(tmp_path, monkeypatch, missing_evidence=True)
    assert r["status"] == "ABORT"


def test_phase82_wrong_status_abort(tmp_path: Path, monkeypatch):
    r = run_case(tmp_path, monkeypatch, phase82="FAIL")
    assert r["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path, monkeypatch):
    p = base_policy()
    p["publish_allowed"] = True
    r = run_case(tmp_path, monkeypatch, policy=p)
    assert r["status"] == "ABORT"


def test_update_allowed_true_abort(tmp_path: Path, monkeypatch):
    p = base_policy()
    p["update_allowed"] = True
    r = run_case(tmp_path, monkeypatch, policy=p)
    assert r["status"] == "ABORT"


def test_delete_allowed_true_abort(tmp_path: Path, monkeypatch):
    p = base_policy()
    p["delete_allowed"] = True
    r = run_case(tmp_path, monkeypatch, policy=p)
    assert r["status"] == "ABORT"


def test_bulk_execution_true_abort(tmp_path: Path, monkeypatch):
    p = base_policy()
    p["bulk_execution"] = True
    r = run_case(tmp_path, monkeypatch, policy=p)
    assert r["status"] == "ABORT"


def test_target_count_two_abort(tmp_path: Path, monkeypatch):
    r = base_request()
    r["target_item_count"] = 2
    out = run_case(tmp_path, monkeypatch, request=r)
    assert out["status"] == "ABORT"


def test_payload_status_publish_abort(tmp_path: Path, monkeypatch):
    p = base_policy()
    p["wordpress_request"]["status"] = "publish"
    out = run_case(tmp_path, monkeypatch, policy=p)
    assert out["status"] == "ABORT"


def test_post_201_draft_success(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "app")

    class Resp:
        status_code = 201

        @staticmethod
        def json():
            return {"id": 123, "status": "draft", "link": "https://example.com/?p=123"}

    monkeypatch.setattr(phase83.requests, "post", lambda *args, **kwargs: Resp())
    out = run_case(tmp_path, monkeypatch)
    assert out["status"] == "DRAFT_CREATED_PENDING_HUMAN_REVIEW"
    assert out["wordpress_write_executed"] is True
    assert out["publish_allowed"] is False
    assert out["target_item_count"] == 1


def test_post_200_draft_success(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "app")

    class Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"id": 124, "status": "draft", "guid": {"rendered": "https://example.com/?p=124"}}

    monkeypatch.setattr(phase83.requests, "post", lambda *args, **kwargs: Resp())
    out = run_case(tmp_path, monkeypatch)
    assert out["status"] == "DRAFT_CREATED_PENDING_HUMAN_REVIEW"


def test_response_publish_abort(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "app")

    class Resp:
        status_code = 201

        @staticmethod
        def json():
            return {"id": 125, "status": "publish", "link": "https://example.com/?p=125"}

    monkeypatch.setattr(phase83.requests, "post", lambda *args, **kwargs: Resp())
    out = run_case(tmp_path, monkeypatch)
    assert out["status"] == "ABORT"


def test_response_missing_id_freeze(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "app")

    class Resp:
        status_code = 201

        @staticmethod
        def json():
            return {"status": "draft", "link": "https://example.com/?p=126"}

    monkeypatch.setattr(phase83.requests, "post", lambda *args, **kwargs: Resp())
    out = run_case(tmp_path, monkeypatch)
    assert out["status"] == "DRAFT_CREATE_FAILED_FREEZE_REQUIRED"


def test_http_500_freeze(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "app")

    class Resp:
        status_code = 500

        @staticmethod
        def json():
            return {"error": "server"}

    monkeypatch.setattr(phase83.requests, "post", lambda *args, **kwargs: Resp())
    out = run_case(tmp_path, monkeypatch)
    assert out["status"] == "DRAFT_CREATE_FAILED_FREEZE_REQUIRED"


def test_requests_exception_freeze(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "app")

    def raise_exc(*args, **kwargs):
        raise phase83.requests.RequestException("boom")

    monkeypatch.setattr(phase83.requests, "post", raise_exc)
    out = run_case(tmp_path, monkeypatch)
    assert out["status"] == "DRAFT_CREATE_FAILED_FREEZE_REQUIRED"
