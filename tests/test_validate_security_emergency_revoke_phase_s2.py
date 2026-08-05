from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_emergency_revoke_phase_s2 import (
    validate_security_emergency_revoke_phase_s2,
)


CONFIG_PATH = ROOT / "config" / "security_emergency_revoke_phase_s2.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    result = validate_security_emergency_revoke_phase_s2(load_config())
    assert result["validator_result"] == "PASS"


def test_auto_revoke_execute_abort() -> None:
    data = load_config()
    data["revoke_actions"]["auto_revoke_execute"] = True
    result = validate_security_emergency_revoke_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_external_api_call_execute_abort() -> None:
    data = load_config()
    data["revoke_actions"]["external_api_call_execute"] = True
    result = validate_security_emergency_revoke_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_production_status_go_abort() -> None:
    data = load_config()
    data["production_status"] = "GO"
    result = validate_security_emergency_revoke_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_unlock_token_abort() -> None:
    data = load_config()
    data["unlock_token"] = "FORBIDDEN"
    result = validate_security_emergency_revoke_phase_s2(data)
    assert result["validator_result"] == "ABORT"
