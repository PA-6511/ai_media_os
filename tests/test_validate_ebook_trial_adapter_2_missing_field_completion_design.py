import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_ebook_trial_adapter_2_missing_field_completion_design import validate


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_case(tmp_path: Path):
    policy = _load(ROOT / "config/ebook_trial_adapter_2_missing_field_completion_design_policy.json")
    request = _load(ROOT / "exchange/examples/ebook_trial_adapter_2_missing_field_completion_design_request.example.json")

    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/request.json"
    output_path = tmp_path / "exchange/logs/result.json"
    adapter1_path = tmp_path / "exchange/logs/ebook_trial_adapter_1_readiness_result.json"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    adapter1_path.parent.mkdir(parents=True, exist_ok=True)

    policy["adapter1_evidence_path"] = "exchange/logs/ebook_trial_adapter_1_readiness_result.json"
    _write(policy_path, policy)
    _write(request_path, request)
    _write(adapter1_path, {"status": "EBOOK_TRIAL_ADAPTER_1_GAP_FOUND_BLOCKED_NO_EXECUTION"})
    return policy_path, request_path, output_path, adapter1_path


def test_pass_when_design_complete_and_adapter1_gap_exists(tmp_path: Path):
    policy_path, request_path, output_path, _ = _prepare_case(tmp_path)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_2_MISSING_FIELD_COMPLETION_DESIGN_PASS_DRY_RUN"
    assert result["missing_field_design"] == []
    assert result["invalid_layer_design"] == []
    assert result["wordpress_write_executed"] is False
    assert result["executed_external_changes"] == 0


def test_blocked_when_field_design_missing(tmp_path: Path):
    policy_path, request_path, output_path, _ = _prepare_case(tmp_path)
    request = _load(request_path)
    request["field_design"].pop("affiliate_disclosure_present", None)
    _write(request_path, request)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_2_BLOCKED_DESIGN_INCOMPLETE_NO_EXECUTION"
    assert "affiliate_disclosure_present" in result["missing_field_design"]


def test_abort_when_dangerous_flag_true(tmp_path: Path):
    policy_path, request_path, output_path, _ = _prepare_case(tmp_path)
    request = _load(request_path)
    request["wordpress_write_allowed"] = True
    _write(request_path, request)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_2_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    assert any("wordpress_write_allowed" in v for v in result["policy_violations"])


def test_abort_when_adapter1_evidence_missing(tmp_path: Path):
    policy_path, request_path, output_path, adapter1_path = _prepare_case(tmp_path)
    adapter1_path.unlink(missing_ok=True)

    result = validate(policy_path=policy_path, request_path=request_path, output_path=output_path)
    assert result["status"] == "EBOOK_TRIAL_ADAPTER_2_ABORT_POLICY_VIOLATION_NO_EXECUTION"
    assert "adapter1_evidence_missing" in result["policy_violations"]
