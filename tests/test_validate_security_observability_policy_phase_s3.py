from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_observability_policy_phase_s3 import (  # noqa: E402
    validate_security_observability_policy_phase_s3,
)


CONFIG_PATH = ROOT / "config" / "security_observability_policy_phase_s3.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    result = validate_security_observability_policy_phase_s3(load_config())
    assert result["validator_result"] == "PASS"


def test_detector_only_false_aborts() -> None:
    data = load_config()
    data["detector_only"] = False
    result = validate_security_observability_policy_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_recommendation_only_false_aborts() -> None:
    data = load_config()
    data["recommendation_only"] = False
    result = validate_security_observability_policy_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_executor_action_allowed_true_aborts() -> None:
    data = load_config()
    data["executor_action_allowed"] = True
    result = validate_security_observability_policy_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_freeze_executed_true_aborts() -> None:
    data = load_config()
    data["freeze_executed"] = True
    result = validate_security_observability_policy_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_production_go_aborts() -> None:
    data = load_config()
    data["production_status"] = "GO"
    result = validate_security_observability_policy_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_execution_live_aborts() -> None:
    data = load_config()
    data["execution"] = "LIVE"
    result = validate_security_observability_policy_phase_s3(data)
    assert result["validator_result"] == "ABORT"
