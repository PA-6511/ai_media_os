from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_process_anomaly_observer_phase_s3 import (  # noqa: E402
    validate_security_process_anomaly_observer_phase_s3,
)


CONFIG_PATH = ROOT / "config" / "security_process_anomaly_observer_phase_s3.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_normal_pass() -> None:
    result = validate_security_process_anomaly_observer_phase_s3(load_config())
    assert result["validator_result"] == "PASS"


def test_unexpected_python_worker_warn() -> None:
    data = load_config()
    data["sample_intent"] = "unexpected_python_worker"
    result = validate_security_process_anomaly_observer_phase_s3(data)
    assert result["validator_result"] == "WARN"


def test_duplicated_runner_fail() -> None:
    data = load_config()
    data["sample_intent"] = "duplicated_runner"
    result = validate_security_process_anomaly_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_unknown_long_running_process_warn() -> None:
    data = load_config()
    data["sample_intent"] = "unknown_long_running_process"
    result = validate_security_process_anomaly_observer_phase_s3(data)
    assert result["validator_result"] == "WARN"


def test_unexpected_shell_command_fail() -> None:
    data = load_config()
    data["sample_intent"] = "unexpected_shell_command"
    result = validate_security_process_anomaly_observer_phase_s3(data)
    assert result["validator_result"] == "FAIL"


def test_process_kill_executed_abort() -> None:
    data = load_config()
    data["actions"]["process_kill_execute"] = True
    result = validate_security_process_anomaly_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_systemctl_executed_abort() -> None:
    data = load_config()
    data["systemctl_executed"] = True
    result = validate_security_process_anomaly_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"


def test_cron_stop_executed_abort() -> None:
    data = load_config()
    data["cron_stop_executed"] = True
    result = validate_security_process_anomaly_observer_phase_s3(data)
    assert result["validator_result"] == "ABORT"
