from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_observability_event_replay_phase_s3_1 import (  # noqa: E402
    validate_security_observability_event_replay_phase_s3_1,
)


CONFIG_PATH = ROOT / "config" / "security_observability_event_replay_phase_s3_1.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    result = validate_security_observability_event_replay_phase_s3_1(load_config())
    assert result["validator_result"] == "PASS"


def test_execution_live_abort() -> None:
    data = load_config()
    data["execution"] = "LIVE"
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_production_go_abort() -> None:
    data = load_config()
    data["production_status"] = "GO"
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_detector_only_false_abort() -> None:
    data = load_config()
    data["detector_only"] = False
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_recommendation_only_false_abort() -> None:
    data = load_config()
    data["recommendation_only"] = False
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_executor_action_allowed_true_abort() -> None:
    data = load_config()
    data["executor_action_allowed"] = True
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_freeze_executed_true_abort() -> None:
    data = load_config()
    data["freeze_executed"] = True
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_revoke_executed_true_abort() -> None:
    data = load_config()
    data["revoke_executed"] = True
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_wordpress_write_executed_true_abort() -> None:
    data = load_config()
    data["wordpress_write_executed"] = True
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_external_api_call_executed_true_abort() -> None:
    data = load_config()
    data["external_api_call_executed"] = True
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "ABORT"


def test_expected_event_results_missing_fail() -> None:
    data = load_config()
    del data["expected_event_results"]
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "FAIL"


def test_expected_recommendations_missing_fail() -> None:
    data = load_config()
    del data["expected_recommendations"]
    result = validate_security_observability_event_replay_phase_s3_1(data)
    assert result["validator_result"] == "FAIL"
