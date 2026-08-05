import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_phase8_38_first_one_item_trial_preflight import validate


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_policy(tmp: Path) -> Path:
    p = tmp / "config/policy.json"
    _write(p, {
        "phase": "8-38",
        "phase8_36_evidence": "exchange/logs/n36.json",
        "phase8_37_evidence": "exchange/logs/n37.json",
    })
    return p


def _make_request(tmp: Path, **kwargs) -> Path:
    r = tmp / "exchange/examples/req.json"
    base = {"mode": "CONNECTION_TEST", "execution": "DRY_RUN"}
    base.update(kwargs)
    _write(r, base)
    return r


def test_blocked_missing_phase8_36(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path)
    output = tmp_path / "exchange/logs/result.json"

    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_36_path=tmp_path / "MISSING36.json",
        phase8_37_path=tmp_path / "MISSING37.json",
    )
    assert result["status"] == "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_MISSING_PHASE8_36_NO_EXECUTION"
    assert result["wordpress_write_executed"] is False
    assert result["executed_external_changes"] == 0


def test_blocked_credentials_not_ready(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path)
    output = tmp_path / "exchange/logs/result.json"

    p36 = tmp_path / "exchange/logs/n36.json"
    p37 = tmp_path / "exchange/logs/n37.json"
    _write(p36, {"status": "PHASE8_36_DRY_RUN_HANDOFF_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"})
    _write(p37, {"status": "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION"})

    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_36_path=p36,
        phase8_37_path=p37,
    )
    assert result["status"] == "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"


def test_blocked_target_not_selected(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path, target_item_selected=False)
    output = tmp_path / "exchange/logs/result.json"

    p36 = tmp_path / "exchange/logs/n36.json"
    p37 = tmp_path / "exchange/logs/n37.json"
    _write(p36, {"status": "PHASE8_36_DRY_RUN_HANDOFF_READY_NO_EXECUTION"})
    _write(p37, {"status": "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION"})

    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_36_path=p36,
        phase8_37_path=p37,
    )
    assert result["status"] == "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_TARGET_ITEM_NOT_SELECTED_NO_EXECUTION"


def test_ready_when_all_conditions_met(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path, target_item_selected=True)
    output = tmp_path / "exchange/logs/result.json"

    p36 = tmp_path / "exchange/logs/n36.json"
    p37 = tmp_path / "exchange/logs/n37.json"
    _write(p36, {"status": "PHASE8_36_DRY_RUN_HANDOFF_READY_NO_EXECUTION"})
    _write(p37, {"status": "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION"})

    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_36_path=p36,
        phase8_37_path=p37,
    )
    assert result["status"] == "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_READY_NO_EXECUTION"
    assert result["wordpress_write_executed"] is False
    assert result["secret_output_safe"] is True


def test_safety_flags_always_false(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path)
    output = tmp_path / "exchange/logs/result.json"

    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_36_path=tmp_path / "MISSING.json",
        phase8_37_path=tmp_path / "MISSING.json",
    )
    for key in (
        "wordpress_write_executed", "wordpress_draft_created",
        "rollback_executed", "freeze_executed",
        "secret_values_output", "secret_lengths_output",
    ):
        assert result[key] is False, f"{key} should be False"
    assert result["executed_external_changes"] == 0
