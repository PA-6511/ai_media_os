import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from read_slack_draft_approval_dry_run import run_reader, validate_slack_approval


def base_payload() -> dict:
    return {
        "phase": "Phase 6-7",
        "source": "SLACK_APPROVAL_DRY_RUN",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": "APPROVE_DRY_RUN_ONLY",
        "reserved_future_decision": "APPROVE_DRAFT_CREATE_ONLY",
        "reserved_future_decision_currently_allowed": False,
        "target_item_count": 1,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "publish_allowed": False,
    }


def test_approve_dry_run_only_passes():
    result = validate_slack_approval(base_payload())
    assert result["status"] == "PASS_DRY_RUN_ONLY"


def test_request_fix_warns():
    payload = copy.deepcopy(base_payload())
    payload["decision"] = "REQUEST_FIX"
    result = validate_slack_approval(payload)
    assert result["status"] == "WARN"


def test_reject_fails():
    payload = copy.deepcopy(base_payload())
    payload["decision"] = "REJECT"
    result = validate_slack_approval(payload)
    assert result["status"] == "FAIL"


def test_abort_aborts():
    payload = copy.deepcopy(base_payload())
    payload["decision"] = "ABORT"
    result = validate_slack_approval(payload)
    assert result["status"] == "ABORT"


def test_approve_draft_create_only_aborts():
    payload = copy.deepcopy(base_payload())
    payload["decision"] = "APPROVE_DRAFT_CREATE_ONLY"
    result = validate_slack_approval(payload)
    assert result["status"] == "ABORT"


def test_unknown_aborts():
    payload = copy.deepcopy(base_payload())
    payload["decision"] = "UNKNOWN"
    result = validate_slack_approval(payload)
    assert result["status"] == "ABORT"


def test_target_item_count_two_aborts():
    payload = copy.deepcopy(base_payload())
    payload["target_item_count"] = 2
    result = validate_slack_approval(payload)
    assert result["status"] == "ABORT"


def test_reserved_future_currently_allowed_true_aborts():
    payload = copy.deepcopy(base_payload())
    payload["reserved_future_decision_currently_allowed"] = True
    result = validate_slack_approval(payload)
    assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    payload = copy.deepcopy(base_payload())
    payload["wordpress_write_executed"] = True
    result = validate_slack_approval(payload)
    assert result["status"] == "ABORT"


def test_auto_post_true_aborts():
    payload = copy.deepcopy(base_payload())
    payload["auto_post"] = True
    result = validate_slack_approval(payload)
    assert result["status"] == "ABORT"


def test_publish_allowed_true_aborts():
    payload = copy.deepcopy(base_payload())
    payload["publish_allowed"] = True
    result = validate_slack_approval(payload)
    assert result["status"] == "ABORT"


def test_run_reader_writes_output():
    with tempfile.TemporaryDirectory() as td:
        inp = Path(td) / "in.json"
        out = Path(td) / "out.json"
        inp.write_text(json.dumps(base_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        result = run_reader(inp, out)
        assert out.exists()
        assert result["status"] == "PASS_DRY_RUN_ONLY"
