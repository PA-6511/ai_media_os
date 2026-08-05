import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_slack_approval_action import validate_slack_approval_action


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_payload() -> dict:
    return {
        "package_type": "slack_approval_action",
        "action": "approved",
        "decision_id": "phase6_7_dry_run_approval_001",
        "reason": "human approved after review",
        "source": "slack_button_dry_run",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "production_status": "NO_GO",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def run_case(payload: dict):
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        input_path = td / "slack_approval_action.json"
        output_path = td / "slack_approval_action_validation_result.json"
        write_json(input_path, payload)

        result = validate_slack_approval_action(str(input_path), str(output_path))
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        return result, saved


def test_approved_action_returns_pass():
    result, saved = run_case(base_payload())
    assert result["status"] == "PASS"
    assert saved["next_step"] == "record_approval_evidence"


def test_request_fix_returns_warn():
    payload = base_payload()
    payload["action"] = "request_fix"

    result, saved = run_case(payload)
    assert result["status"] == "WARN"
    assert saved["next_step"] == "request_fix"


def test_rejected_returns_fail():
    payload = base_payload()
    payload["action"] = "rejected"

    result, saved = run_case(payload)
    assert result["status"] == "FAIL"
    assert saved["next_step"] == "stop"


def test_blank_reason_returns_fail():
    payload = base_payload()
    payload["reason"] = "   "

    result, _ = run_case(payload)
    assert result["status"] == "FAIL"


def test_execution_live_returns_abort():
    payload = base_payload()
    payload["execution"] = "LIVE"

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_auto_post_true_returns_abort():
    payload = base_payload()
    payload["auto_post"] = True

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_invalid_source_returns_fail():
    payload = base_payload()
    payload["source"] = "slack_live"

    result, _ = run_case(payload)
    assert result["status"] == "FAIL"