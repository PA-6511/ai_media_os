from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_env_access_observer_phase_s3 import (  # noqa: E402
    validate_security_env_access_observer_phase_s3,
)


CONFIG_PATH = ROOT / "config" / "security_env_access_observer_phase_s3.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_metadata_check_pass() -> None:
    result = validate_security_env_access_observer_phase_s3(load_config())
    assert result["validator_result"] == "PASS"


def test_secret_presence_check_pass() -> None:
    data = load_config()
    data["sample_intent"] = "secret_presence_check"
    result = validate_security_env_access_observer_phase_s3(data)
    assert result["validator_result"] == "PASS"


def test_secret_value_echo_fail() -> None:
    data = load_config()
    data["sample_intent"] = "secret_value_echo"
    result = validate_security_env_access_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_env_file_content_read_fail() -> None:
    data = load_config()
    data["sample_intent"] = "env_file_content_read"
    result = validate_security_env_access_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_plaintext_secret_logging_fail() -> None:
    data = load_config()
    data["sample_intent"] = "plaintext_secret_logging"
    result = validate_security_env_access_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_secret_value_output_allowed_abort() -> None:
    data = load_config()
    data["secret_value_output_allowed"] = True
    result = validate_security_env_access_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_token_value_output_allowed_abort() -> None:
    data = load_config()
    data["token_value_output_allowed"] = True
    result = validate_security_env_access_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"
