import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_decision_reason import validate_reason_file, validate_reason_payload


def base_payload() -> dict:
    return {
        "package_type": "decision_package",
        "status": "WARN",
        "reason": "manual review required for low-confidence output",
        "execution": "DRY_RUN",
        "human_review_required": True,
        "production_status": "NO_GO",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
    }


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_warn_requires_reason():
    payload = base_payload()
    payload["reason"] = ""

    result = validate_reason_payload(payload, package_type="decision_package")

    assert result["status"] == "FAIL"
    assert "reason" in result["reason"]


def test_fail_requires_reason():
    payload = base_payload()
    payload["status"] = "FAIL"
    payload.pop("reason")

    result = validate_reason_payload(payload, package_type="review_result")

    assert result["status"] == "FAIL"
    assert "required" in result["reason"]


def test_abort_requires_reason():
    payload = base_payload()
    payload["status"] = "ABORT"
    payload.pop("reason")

    result = validate_reason_payload(payload, package_type="approval_evidence")

    assert result["status"] == "FAIL"


def test_pass_without_reason_or_summary_is_warn():
    payload = base_payload()
    payload["status"] = "PASS"
    payload.pop("reason")

    result = validate_reason_payload(payload, package_type="decision_package")

    assert result["status"] == "WARN"
    assert "summary_reason" in result["reason"] or "reason" in result["reason"]


def test_pass_with_summary_reason_is_pass():
    payload = base_payload()
    payload["status"] = "PASS"
    payload.pop("reason")
    payload["summary_reason"] = "all checks passed under dry-run constraints"

    result = validate_reason_payload(payload, package_type="decision_package")

    assert result["status"] == "PASS"


def test_dangerous_operation_is_abort():
    payload = base_payload()
    payload["auto_post"] = True

    result = validate_reason_payload(payload, package_type="decision_package")

    assert result["status"] == "ABORT"
    assert "dangerous" in result["reason"]


def test_validate_reason_file_writes_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "decision.json"
        output_path = Path(tmpdir) / "reason_validation_result.json"
        write_json(input_path, base_payload())

        result = validate_reason_file(input_path=input_path, output_path=output_path)

        assert result["status"] == "PASS"
        assert output_path.exists()
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert saved["production_status"] == "NO_GO"
        assert saved["human_review_required"] is True