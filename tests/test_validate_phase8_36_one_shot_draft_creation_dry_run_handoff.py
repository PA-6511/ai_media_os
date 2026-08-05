import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_phase8_36_one_shot_draft_creation_dry_run_handoff import validate


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_policy(tmp: Path) -> Path:
    p = tmp / "config/policy.json"
    _write(p, {
        "phase": "8-36",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
    })
    return p


def _make_request(tmp: Path, override: "str | None" = None) -> Path:
    r = tmp / "exchange/examples/req.json"
    _write(r, {"mode": "CONNECTION_TEST", "execution": "DRY_RUN", "phase8_35_status_override": override})
    return r


def test_blocked_when_credentials_not_ready(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path, "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_NOT_READY_NO_EXECUTION")
    output = tmp_path / "exchange/logs/result.json"

    # No phase8_35 / phase8_29_31 files → uses override
    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_35_path=tmp_path / "MISSING_phase8_35.json",
        phase8_29_31_path=tmp_path / "MISSING_phase8_29_31.json",
    )
    # override says not ready → BLOCKED
    assert result["status"] == "PHASE8_36_DRY_RUN_HANDOFF_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
    assert result["credentials_ready"] is False
    assert result["wordpress_write_executed"] is False
    assert result["wordpress_api_call_attempted"] is False
    assert result["executed_external_changes"] == 0
    assert output.exists()


def test_ready_when_phase8_35_ready(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path, None)
    output = tmp_path / "exchange/logs/result.json"

    phase8_35 = tmp_path / "exchange/logs/phase8_35.json"
    _write(phase8_35, {"status": "PHASE8_35_FINAL_CONFIRMATION_READY_FOR_DRY_RUN_HANDOFF_NO_EXECUTION"})

    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_35_path=phase8_35,
        phase8_29_31_path=tmp_path / "MISSING_phase8_29_31.json",
    )
    assert result["status"] == "PHASE8_36_DRY_RUN_HANDOFF_READY_NO_EXECUTION"
    assert result["credentials_ready"] is True
    assert result["handoff_allowed"] is True
    assert result["wordpress_write_executed"] is False


def test_abort_missing_evidence(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path, None)
    output = tmp_path / "exchange/logs/result.json"

    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_35_path=tmp_path / "MISSING1.json",
        phase8_29_31_path=tmp_path / "MISSING2.json",
    )
    assert result["status"] == "PHASE8_36_DRY_RUN_HANDOFF_ABORT_MISSING_PHASE8_35_EVIDENCE_NO_EXECUTION"
    assert result["executed_external_changes"] == 0


def test_safety_flags_always_false(tmp_path: Path):
    policy = _make_policy(tmp_path)
    request = _make_request(tmp_path, "WHATEVER")
    output = tmp_path / "exchange/logs/result.json"

    result = validate(
        policy_path=policy,
        request_path=request,
        output_path=output,
        phase8_35_path=tmp_path / "MISSING.json",
        phase8_29_31_path=tmp_path / "MISSING2.json",
    )
    for key in (
        "wordpress_write_executed", "wordpress_draft_created", "wordpress_api_call_attempted",
        "execution_allowed", "publish_allowed", "secret_values_output",
        "secret_lengths_output", "secret_masks_output", "secret_hashes_output",
    ):
        assert result[key] is False, f"{key} should be False"
    assert result["executed_external_changes"] == 0
