from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_api_permission_map_phase_s2 import (
    validate_security_api_permission_map_phase_s2,
)


CONFIG_PATH = ROOT / "config" / "security_api_permission_map_phase_s2.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    result = validate_security_api_permission_map_phase_s2(load_config())
    assert result["validator_result"] == "PASS"


def test_write_permission_allowed_fail() -> None:
    data = load_config()
    data["openai_permissions"]["post_write"] = "allowed"
    result = validate_security_api_permission_map_phase_s2(data)
    assert result["validator_result"] == "FAIL"


def test_shared_token_across_roles_false_fail() -> None:
    data = load_config()
    data["shared_token_across_roles_forbidden"] = False
    result = validate_security_api_permission_map_phase_s2(data)
    assert result["validator_result"] == "FAIL"


def test_execution_live_abort() -> None:
    data = load_config()
    data["execution"] = "LIVE"
    result = validate_security_api_permission_map_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_publish_allowed_true_abort() -> None:
    data = load_config()
    data["publish_allowed"] = True
    result = validate_security_api_permission_map_phase_s2(data)
    assert result["validator_result"] == "ABORT"
