import json
import tempfile
from pathlib import Path

from core.self_builder_connector_selector import load_and_select, select_self_builder_connector


def test_default_local_config_passes():
    config = {
        "active_connector": "LOCAL_SELF_BUILDER",
        "allowed_connectors": ["LOCAL_SELF_BUILDER"],
        "vps_connector_enabled": False,
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_execute": False,
    }
    result = select_self_builder_connector(config)
    assert result["status"] == "PASS"
    assert result["selected_connector"] == "LOCAL_SELF_BUILDER"


def test_unknown_connector_aborts():
    config = {
        "active_connector": "EDGE_BUILDER",
        "allowed_connectors": ["LOCAL_SELF_BUILDER"],
        "vps_connector_enabled": False,
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_execute": False,
    }
    result = select_self_builder_connector(config)
    assert result["status"] == "ABORT"


def test_vps_active_without_enable_aborts():
    config = {
        "active_connector": "VPS_SELF_BUILDER",
        "allowed_connectors": ["LOCAL_SELF_BUILDER", "VPS_SELF_BUILDER"],
        "vps_connector_enabled": False,
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_execute": False,
    }
    result = select_self_builder_connector(config)
    assert result["status"] == "ABORT"


def test_execution_live_aborts():
    config = {
        "active_connector": "LOCAL_SELF_BUILDER",
        "allowed_connectors": ["LOCAL_SELF_BUILDER"],
        "vps_connector_enabled": False,
        "execution": "LIVE",
        "human_approval_required": True,
        "auto_execute": False,
    }
    result = select_self_builder_connector(config)
    assert result["status"] == "ABORT"


def test_auto_execute_true_aborts():
    config = {
        "active_connector": "LOCAL_SELF_BUILDER",
        "allowed_connectors": ["LOCAL_SELF_BUILDER"],
        "vps_connector_enabled": False,
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_execute": True,
    }
    result = select_self_builder_connector(config)
    assert result["status"] == "ABORT"


def test_load_and_select_from_temp_file():
    config = {
        "active_connector": "LOCAL_SELF_BUILDER",
        "allowed_connectors": ["LOCAL_SELF_BUILDER"],
        "vps_connector_enabled": False,
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_execute": False,
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "self_builder_connection.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        result = load_and_select(path)
        assert result["status"] == "PASS"
