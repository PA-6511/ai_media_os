from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_external_api_intent_observer_phase_s3 import (  # noqa: E402
    validate_security_external_api_intent_observer_phase_s3,
)


CONFIG_PATH = ROOT / "config" / "security_external_api_intent_observer_phase_s3.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_known_api_intent_pass() -> None:
    result = validate_security_external_api_intent_observer_phase_s3(load_config())
    assert result["validator_result"] == "PASS"


def test_unknown_api_intent_warn() -> None:
    data = load_config()
    data["sample_intent"] = "unknown_api_call"
    result = validate_security_external_api_intent_observer_phase_s3(data)
    assert result["validator_result"] == "WARN"


def test_denied_api_intent_fail() -> None:
    data = load_config()
    data["sample_intent"] = "wordpress_publish"
    result = validate_security_external_api_intent_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_external_api_call_executed_abort() -> None:
    data = load_config()
    data["external_api_call_executed"] = True
    result = validate_security_external_api_intent_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_destructive_api_call_allowed_abort() -> None:
    data = load_config()
    data["destructive_api_call_allowed"] = True
    result = validate_security_external_api_intent_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_auto_revoke_execute_abort() -> None:
    data = load_config()
    data["actions"]["auto_revoke_execute"] = True
    result = validate_security_external_api_intent_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"
