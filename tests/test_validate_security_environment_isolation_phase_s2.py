from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_environment_isolation_phase_s2 import (
    validate_security_environment_isolation_phase_s2,
)


CONFIG_PATH = ROOT / "config" / "security_environment_isolation_phase_s2.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    result = validate_security_environment_isolation_phase_s2(load_config())
    assert result["validator_result"] == "PASS"


def test_missing_required_key_fail() -> None:
    data = load_config()
    del data["environments"]
    result = validate_security_environment_isolation_phase_s2(data)
    assert result["validator_result"] == "FAIL"


def test_env_file_type_error_fail() -> None:
    data = load_config()
    data["environments"]["dev"]["env_file"] = 123
    result = validate_security_environment_isolation_phase_s2(data)
    assert result["validator_result"] == "FAIL"


def test_execution_live_abort() -> None:
    data = load_config()
    data["execution"] = "LIVE"
    result = validate_security_environment_isolation_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_production_go_abort() -> None:
    data = load_config()
    data["production_status"] = "GO"
    result = validate_security_environment_isolation_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_unlock_token_abort() -> None:
    data = load_config()
    data["unlock_token"] = "FORBIDDEN"
    result = validate_security_environment_isolation_phase_s2(data)
    assert result["validator_result"] == "ABORT"
