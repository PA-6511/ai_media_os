import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from read_human_review_decision import read_human_decision


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_decision(decision="APPROVE_DRY_RUN_ONLY"):
    return {
        "package_type": "human_decision",
        "source": "human_operator",
        "target": "core_consensus_ai",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": decision,
        "reason": "test decision",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def run_case(payload):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "human_decision.json"
        output_path = Path(tmpdir) / "human_decision_result.json"
        write_json(input_path, payload)
        result = read_human_decision(input_path, output_path)
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        return result, saved


def test_approve_dry_run_only_passes():
    result, saved = run_case(base_decision("APPROVE_DRY_RUN_ONLY"))
    assert result["status"] == "PASS"
    assert saved["next_step"] == "record_dry_run_evidence"


def test_request_fix_warns():
    result, saved = run_case(base_decision("REQUEST_FIX"))
    assert result["status"] == "WARN"
    assert saved["next_step"] == "request_fix"


def test_reject_fails():
    result, saved = run_case(base_decision("REJECT"))
    assert result["status"] == "FAIL"
    assert saved["next_step"] == "stop"


def test_abort_aborts():
    result, saved = run_case(base_decision("ABORT"))
    assert result["status"] == "ABORT"
    assert saved["next_step"] == "abort"


def test_unknown_decision_aborts():
    result, saved = run_case(base_decision("APPROVE_LIVE"))
    assert result["status"] == "ABORT"
    assert saved["next_step"] == "abort"


def test_execution_live_aborts():
    payload = base_decision()
    payload["execution"] = "LIVE"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_auto_post_true_aborts():
    payload = base_decision()
    payload["auto_post"] = True
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    payload = base_decision()
    payload["wordpress_write_executed"] = True
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_decision_result_json_is_generated():
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "human_decision.json"
        output_path = Path(tmpdir) / "human_decision_result.json"
        write_json(input_path, base_decision("APPROVE_DRY_RUN_ONLY"))
        read_human_decision(input_path, output_path)
        assert output_path.exists()


def test_production_flags_remain_false_in_output():
    _, saved = run_case(base_decision("APPROVE_DRY_RUN_ONLY"))
    assert saved["auto_post"] is False
    assert saved["auto_update"] is False
    assert saved["auto_delete"] is False
    assert saved["auto_export"] is False
    assert saved["wordpress_write_executed"] is False
    assert saved["slack_notification_executed"] is False
    assert saved["github_actions_triggered"] is False
