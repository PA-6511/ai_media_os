from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_wordpress_write_observer_phase_s3 import (  # noqa: E402
    validate_security_wordpress_write_observer_phase_s3,
)


CONFIG_PATH = ROOT / "config" / "security_wordpress_write_observer_phase_s3.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_read_only_normal_pass() -> None:
    result = validate_security_wordpress_write_observer_phase_s3(load_config())
    assert result["validator_result"] == "PASS"


def test_draft_create_intent_fail() -> None:
    data = load_config()
    data["sample_intent"] = "draft_create_intent"
    result = validate_security_wordpress_write_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_publish_intent_fail() -> None:
    data = load_config()
    data["sample_intent"] = "publish_intent"
    result = validate_security_wordpress_write_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_update_intent_fail() -> None:
    data = load_config()
    data["sample_intent"] = "update_intent"
    result = validate_security_wordpress_write_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_delete_intent_fail() -> None:
    data = load_config()
    data["sample_intent"] = "delete_intent"
    result = validate_security_wordpress_write_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_bulk_write_intent_fail() -> None:
    data = load_config()
    data["sample_intent"] = "bulk_write_intent"
    result = validate_security_wordpress_write_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_wordpress_write_executed_abort() -> None:
    data = load_config()
    data["wordpress_write_executed"] = True
    result = validate_security_wordpress_write_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_wordpress_api_call_execute_abort() -> None:
    data = load_config()
    data["actions"]["wordpress_api_call_execute"] = True
    result = validate_security_wordpress_write_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"
