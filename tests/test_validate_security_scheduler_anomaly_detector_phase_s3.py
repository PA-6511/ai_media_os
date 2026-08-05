from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_scheduler_anomaly_detector_phase_s3 import (  # noqa: E402
    validate_security_scheduler_anomaly_detector_phase_s3,
)


CONFIG_PATH = ROOT / "config" / "security_scheduler_anomaly_detector_phase_s3.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    result = validate_security_scheduler_anomaly_detector_phase_s3(load_config())
    assert result["validator_result"] == "PASS"


def test_retry_count_warn() -> None:
    data = load_config()
    data["sample_event"]["retry_count"] = 3
    result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    assert result["validator_result"] == "WARN"


def test_retry_count_fail() -> None:
    data = load_config()
    data["sample_event"]["retry_count"] = 5
    result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_retry_count_abort() -> None:
    data = load_config()
    data["sample_event"]["retry_count"] = 10
    result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_queue_depth_fail() -> None:
    data = load_config()
    data["sample_event"]["queue_depth"] = 50
    result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_cron_runs_per_hour_fail() -> None:
    data = load_config()
    data["sample_event"]["cron_runs_per_hour"] = 6
    result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_duplicate_run_fail() -> None:
    data = load_config()
    data["sample_event"]["duplicate_runs"] = 2
    result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_auto_freeze_execute_abort() -> None:
    data = load_config()
    data["actions"]["auto_freeze_execute"] = True
    result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_scheduler_stop_executed_abort() -> None:
    data = load_config()
    data["scheduler_stop_executed"] = True
    result = validate_security_scheduler_anomaly_detector_phase_s3(data)
    assert result["validator_result"] == "ABORT"
