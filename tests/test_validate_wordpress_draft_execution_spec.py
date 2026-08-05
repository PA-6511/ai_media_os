import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_wordpress_draft_execution_spec import run_validation, validate_execution_spec


def base_payload() -> dict:
    return {
        "phase": "Phase 6-5",
        "name": "wordpress_draft_execution_spec",
        "spec_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_rest_api": {
            "post_allowed": False,
            "put_allowed": False,
            "patch_allowed": False,
            "delete_allowed": False,
        },
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "auto_publish": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
        "future_reserved_decision_token": {
            "token": "APPROVE_DRAFT_CREATE_ONLY",
            "currently_allowed": False,
            "meaning": "reserved",
        },
        "single_item_limit": {
            "enabled": True,
            "max_items": 1,
            "bulk_run_allowed": False,
        },
        "allowed_future_scope": {
            "create_wordpress_draft_only": True,
            "publish": False,
            "update_existing_post": False,
            "delete_post": False,
            "export": False,
        },
    }


def test_valid_payload_passes():
    result = validate_execution_spec(base_payload())
    assert result["status"] == "PASS_DRY_RUN_ONLY"


def test_human_approval_false_aborts():
    payload = copy.deepcopy(base_payload())
    payload["human_approval_required"] = False
    result = validate_execution_spec(payload)
    assert result["status"] == "ABORT"


def test_rest_post_true_aborts():
    payload = copy.deepcopy(base_payload())
    payload["wordpress_rest_api"]["post_allowed"] = True
    result = validate_execution_spec(payload)
    assert result["status"] == "ABORT"


def test_reserved_currently_allowed_true_aborts():
    payload = copy.deepcopy(base_payload())
    payload["future_reserved_decision_token"]["currently_allowed"] = True
    result = validate_execution_spec(payload)
    assert result["status"] == "ABORT"


def test_max_items_two_aborts():
    payload = copy.deepcopy(base_payload())
    payload["single_item_limit"]["max_items"] = 2
    result = validate_execution_spec(payload)
    assert result["status"] == "ABORT"


def test_publish_true_aborts():
    payload = copy.deepcopy(base_payload())
    payload["allowed_future_scope"]["publish"] = True
    result = validate_execution_spec(payload)
    assert result["status"] == "ABORT"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        inp = Path(td) / "in.json"
        out = Path(td) / "out.json"
        inp.write_text(json.dumps(base_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        result = run_validation(inp, out)
        assert result["status"] == "PASS_DRY_RUN_ONLY"
        assert out.exists()
