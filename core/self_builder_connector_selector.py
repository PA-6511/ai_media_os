"""Self-builder connector selector (Phase 5-1).

目的:
- LOCAL_SELF_BUILDER / VPS_SELF_BUILDER の切替口を先に用意する
- ただし Phase 5-1 では DRY_RUN 以外を許可しない
- auto_execute は常に false を要求する
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "config/self_builder_connection.json"

ALLOWED_CONNECTORS = {"LOCAL_SELF_BUILDER", "VPS_SELF_BUILDER"}


def _abort(reason: str) -> dict:
    return {
        "status": "ABORT",
        "reason": reason,
        "execution": "DRY_RUN",
        "selected_connector": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def load_connection_config(config_path: Path | None = None) -> dict:
    path = Path(config_path or DEFAULT_CONFIG)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def select_self_builder_connector(config: dict) -> dict:
    active = config.get("active_connector")
    allowed = config.get("allowed_connectors", [])
    vps_enabled = config.get("vps_connector_enabled")

    if active not in ALLOWED_CONNECTORS:
        return _abort(f"unknown active_connector: {active!r}")

    if not isinstance(allowed, list) or not allowed:
        return _abort("allowed_connectors must be a non-empty list")

    if any(conn not in ALLOWED_CONNECTORS for conn in allowed):
        return _abort(f"allowed_connectors contains unknown value: {allowed!r}")

    if active not in allowed:
        return _abort("active_connector must be included in allowed_connectors")

    # Phase 5-1 固定条件
    if str(config.get("execution", "")).upper() != "DRY_RUN":
        return _abort("execution must be DRY_RUN")

    if config.get("human_approval_required") is not True:
        return _abort("human_approval_required must be true")

    if config.get("auto_execute") is not False:
        return _abort("auto_execute must be false")

    # VPS は切替口のみ許可。enabled=true かつ DRY_RUN 条件下でも実行解放はしない。
    if active == "VPS_SELF_BUILDER" and vps_enabled is not True:
        return _abort("VPS_SELF_BUILDER requires vps_connector_enabled=true")

    return {
        "status": "PASS",
        "reason": "connector selection is valid for DRY_RUN",
        "execution": "DRY_RUN",
        "selected_connector": active,
        "vps_connector_enabled": bool(vps_enabled),
        "human_approval_required": True,
        "auto_execute": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def load_and_select(config_path: Path | None = None) -> dict:
    config = load_connection_config(config_path)
    return select_self_builder_connector(config)
