from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_read_only_policy_phase_s2 import (
    validate_security_read_only_policy_phase_s2,
)


CONFIG_PATH = ROOT / "config" / "security_read_only_policy_phase_s2.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    result = validate_security_read_only_policy_phase_s2(load_config())
    assert result["validator_result"] == "PASS"


def test_wordpress_mode_not_read_only_fail() -> None:
    data = load_config()
    data["wordpress_mode"] = "WRITE_ENABLED"
    result = validate_security_read_only_policy_phase_s2(data)
    assert result["validator_result"] == "FAIL"


def test_wordpress_write_executed_abort() -> None:
    data = load_config()
    data["wordpress_write_executed"] = True
    result = validate_security_read_only_policy_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_allow_scheduler_execution_abort() -> None:
    data = load_config()
    data["allow_scheduler_execution"] = True
    result = validate_security_read_only_policy_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_allow_external_api_write_abort() -> None:
    data = load_config()
    data["allow_external_api_write"] = True
    result = validate_security_read_only_policy_phase_s2(data)
    assert result["validator_result"] == "ABORT"


def test_auto_post_abort() -> None:
    data = load_config()
    data["auto_post"] = True
    result = validate_security_read_only_policy_phase_s2(data)
    assert result["validator_result"] == "ABORT"
