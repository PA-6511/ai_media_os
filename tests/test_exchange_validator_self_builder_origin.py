import json
import os
import tempfile
from pathlib import Path

from core.exchange_validator import validate_package


def _write_temp(payload: dict) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    try:
        json.dump(payload, f, ensure_ascii=False)
        f.close()
        return Path(f.name)
    except Exception:
        f.close()
        os.unlink(f.name)
        raise


def _validate(payload: dict) -> dict:
    path = _write_temp(payload)
    try:
        return validate_package("decision_package", path)
    finally:
        os.unlink(path)


def base_decision_package() -> dict:
    return {
        "package_type": "decision_package",
        "source": "local_self_builder",
        "target": "ebook_affiliate_block",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "requested_action": "propose_article_template_update",
        "risk_level": "LOW",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "summary": "phase5 origin test",
    }


def test_without_self_builder_origin_stays_compatible():
    result = _validate(base_decision_package())
    assert result["status"] in {"PASS", "WARN"}, result


def test_local_self_builder_origin_passes():
    payload = base_decision_package()
    payload["self_builder_origin"] = {
        "type": "LOCAL_SELF_BUILDER",
        "location": "local",
        "execution_allowed": False,
        "vps_migration_ready": False,
    }
    result = _validate(payload)
    assert result["status"] in {"PASS", "WARN"}, result


def test_execution_allowed_true_aborts():
    payload = base_decision_package()
    payload["self_builder_origin"] = {
        "type": "LOCAL_SELF_BUILDER",
        "location": "local",
        "execution_allowed": True,
        "vps_migration_ready": False,
    }
    result = _validate(payload)
    assert result["status"] == "ABORT", result


def test_unknown_origin_type_aborts():
    payload = base_decision_package()
    payload["self_builder_origin"] = {
        "type": "EDGE_SELF_BUILDER",
        "location": "local",
        "execution_allowed": False,
        "vps_migration_ready": False,
    }
    result = _validate(payload)
    assert result["status"] == "ABORT", result


def test_unknown_location_aborts():
    payload = base_decision_package()
    payload["self_builder_origin"] = {
        "type": "LOCAL_SELF_BUILDER",
        "location": "edge",
        "execution_allowed": False,
        "vps_migration_ready": False,
    }
    result = _validate(payload)
    assert result["status"] == "ABORT", result


def test_vps_without_migration_ready_aborts():
    payload = base_decision_package()
    payload["self_builder_origin"] = {
        "type": "VPS_SELF_BUILDER",
        "location": "vps",
        "execution_allowed": False,
        "vps_migration_ready": False,
    }
    result = _validate(payload)
    assert result["status"] == "ABORT", result


def test_vps_with_live_execution_aborts():
    payload = base_decision_package()
    payload["execution"] = "LIVE"
    payload["self_builder_origin"] = {
        "type": "VPS_SELF_BUILDER",
        "location": "vps",
        "execution_allowed": False,
        "vps_migration_ready": True,
    }
    result = _validate(payload)
    assert result["status"] == "ABORT", result


def test_vps_without_human_approval_aborts():
    payload = base_decision_package()
    payload["human_approval_required"] = False
    payload["self_builder_origin"] = {
        "type": "VPS_SELF_BUILDER",
        "location": "vps",
        "execution_allowed": False,
        "vps_migration_ready": True,
    }
    result = _validate(payload)
    assert result["status"] == "ABORT", result


def test_vps_ready_dry_run_with_human_review_passes():
    payload = base_decision_package()
    payload["self_builder_origin"] = {
        "type": "VPS_SELF_BUILDER",
        "location": "vps",
        "execution_allowed": False,
        "vps_migration_ready": True,
    }
    result = _validate(payload)
    assert result["status"] in {"PASS", "WARN"}, result
