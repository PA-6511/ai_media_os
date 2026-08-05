from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_security_phase_sec_0_baseline import (
    REQUIRED_PROHIBITED_ACTIONS,
    REQUIRED_TRUE_FLAGS,
    validate_baseline,
)

CONFIG_PATH = ROOT / "config" / "security_phase_sec_0_baseline.json"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_phase_sec_0_baseline_passes() -> None:
    data = load_config()
    result = validate_baseline(data)

    assert result["phase_id"] == "PHASE_SEC_0"
    assert result["status"] == "PASS"
    assert result["production_status"] == "NO_GO"
    assert result["execution"] == "DRY_RUN"
    assert result["human_approval_required"] is True
    assert result["next_step"] == "phase_sec_1_or_manual_review"
    assert result["reasons"] == []


def test_phase_sec_0_required_true_flags_are_present() -> None:
    data = load_config()

    for flag in REQUIRED_TRUE_FLAGS:
        assert data.get(flag) is True


def test_phase_sec_0_prohibited_actions_are_present() -> None:
    data = load_config()
    prohibited_actions = data["prohibited_actions"]

    for action in REQUIRED_PROHIBITED_ACTIONS:
        assert action in prohibited_actions


def test_phase_sec_0_detects_production_unlock() -> None:
    data = load_config()
    data["production_status"] = "GO"

    result = validate_baseline(data)

    assert result["status"] == "FAIL"
    assert any("production_status" in reason for reason in result["reasons"])


def test_phase_sec_0_detects_missing_human_approval() -> None:
    data = load_config()
    data["human_approval_required"] = False

    result = validate_baseline(data)

    assert result["status"] == "FAIL"
    assert any("human_approval_required" in reason for reason in result["reasons"])


def test_phase_sec_0_detects_missing_ransomware_threat() -> None:
    data = load_config()
    data["assumed_threats"] = [
        threat for threat in data["assumed_threats"] if threat != "ransomware"
    ]

    result = validate_baseline(data)

    assert result["status"] == "FAIL"
    assert any("assumed_threats" in reason for reason in result["reasons"])
