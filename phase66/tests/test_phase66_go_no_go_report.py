import json

from phase66.reporting.phase66_go_no_go_report import write_phase66_go_no_go_report


def _valid_payload() -> dict:
    return {
        "review_status": "APPROVED",
        "go_no_go": "GO",
        "can_execute": False,
        "execute_allowed": False,
        "next_step": "prepare_limited_dry_run_protocol_without_execution",
        "reasons": [],
        "selected_decision": "ALLOW_LIMITED_DRY_RUN_PREPARATION_ONLY",
    }


def test_write_report_fails_when_missing_key(tmp_path) -> None:
    payload = _valid_payload()
    payload.pop("selected_decision")
    result = write_phase66_go_no_go_report(payload, str(tmp_path / "phase66.json"))
    assert result["status"] == "FAIL"
    assert "missing keys" in result["reason"]


def test_write_report_fails_when_can_execute_true(tmp_path) -> None:
    payload = _valid_payload()
    payload["can_execute"] = True
    result = write_phase66_go_no_go_report(payload, str(tmp_path / "phase66.json"))
    assert result["status"] == "FAIL"
    assert result["reason"] == "can_execute must be False"


def test_write_report_fails_when_execute_allowed_true(tmp_path) -> None:
    payload = _valid_payload()
    payload["execute_allowed"] = True
    result = write_phase66_go_no_go_report(payload, str(tmp_path / "phase66.json"))
    assert result["status"] == "FAIL"
    assert result["reason"] == "execute_allowed must be False"


def test_write_report_pass(tmp_path) -> None:
    out = tmp_path / "phase66.json"
    result = write_phase66_go_no_go_report(_valid_payload(), str(out))
    assert result["status"] == "PASS"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["phase"] == "66"
    assert data["human_approval_required"] is True
    assert data["go_no_go"] == "GO"
