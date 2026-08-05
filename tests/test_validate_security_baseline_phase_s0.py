from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_baseline_phase_s0 import validate_security_baseline_phase_s0


CONFIG_PATH = ROOT / "config" / "security_baseline_phase_s0.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_json_pass() -> None:
    data = load_config()
    result = validate_security_baseline_phase_s0(data)
    assert result["validator_result"] == "PASS"
    assert result["production_status"] == "NO_GO"
    assert result["execution"] == "DRY_RUN"


def test_missing_key_fail() -> None:
    data = load_config()
    del data["backup_required"]
    result = validate_security_baseline_phase_s0(data)
    assert result["validator_result"] == "FAIL"
    assert any("backup_required" in reason for reason in result["fail_reasons"])


def test_invalid_bool_type_fail() -> None:
    data = load_config()
    data["windows_update_required"] = "true"
    result = validate_security_baseline_phase_s0(data)
    assert result["validator_result"] == "FAIL"
    assert any("windows_update_required" in reason for reason in result["fail_reasons"])


def test_unlock_token_abort() -> None:
    data = load_config()
    data["unlock_token"] = "MANUAL_ONLY"
    result = validate_security_baseline_phase_s0(data)
    assert result["validator_result"] == "ABORT"
    assert any("unlock token" in reason for reason in result["abort_reasons"])


def test_publish_allowed_true_abort() -> None:
    data = load_config()
    data["publish_allowed"] = True
    result = validate_security_baseline_phase_s0(data)
    assert result["validator_result"] == "ABORT"
    assert any("publish_allowed=true" in reason for reason in result["abort_reasons"])
