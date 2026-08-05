from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_freeze_control_phase_s1 import validate_freeze_control_phase_s1


CONFIG_PATH = ROOT / "config" / "freeze_control_phase_s1.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    data = load_config()
    result = validate_freeze_control_phase_s1(data)
    assert result["validator_result"] == "PASS"
    assert result["freeze_state"] == "NO_GO_LOCKED"


def test_missing_freeze_key_fail() -> None:
    data = load_config()
    del data["freeze_enabled"]
    result = validate_freeze_control_phase_s1(data)
    assert result["validator_result"] == "FAIL"
    assert any("freeze_enabled" in reason for reason in result["fail_reasons"])


def test_live_mode_abort() -> None:
    data = load_config()
    data["execution"] = "LIVE"
    result = validate_freeze_control_phase_s1(data)
    assert result["validator_result"] == "ABORT"
    assert any("execution=LIVE" in reason for reason in result["abort_reasons"])


def test_wordpress_write_true_abort() -> None:
    data = load_config()
    data["allow_wordpress_write"] = True
    result = validate_freeze_control_phase_s1(data)
    assert result["validator_result"] == "ABORT"
    assert any("allow_wordpress_write=true" in reason for reason in result["abort_reasons"])


def test_scheduler_true_abort() -> None:
    data = load_config()
    data["allow_scheduler"] = True
    result = validate_freeze_control_phase_s1(data)
    assert result["validator_result"] == "ABORT"
    assert any("allow_scheduler=true" in reason for reason in result["abort_reasons"])


def test_production_go_abort() -> None:
    data = load_config()
    data["production_status"] = "GO"
    result = validate_freeze_control_phase_s1(data)
    assert result["validator_result"] == "ABORT"
    assert any("production_status=GO" in reason for reason in result["abort_reasons"])


def test_unlock_token_abort() -> None:
    data = load_config()
    data["unlock_token"] = "NOT_ALLOWED"
    result = validate_freeze_control_phase_s1(data)
    assert result["validator_result"] == "ABORT"
    assert any("unlock token" in reason for reason in result["abort_reasons"])
