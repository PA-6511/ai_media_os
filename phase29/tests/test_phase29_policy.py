from phase29.gate.phase29_policy import evaluate_phase29_policy


def _base_gate_input() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "execute_allowed": False,
    }


def _base_checklist() -> dict:
    return {"checklist_required": True, "checklist_does_not_execute": True}


def _base_evidence_gate() -> dict:
    return {"evidence_gate_required": True, "evidence_does_not_execute": True}


def test_policy_fails_when_max_files_invalid() -> None:
    gate_input = _base_gate_input()
    gate_input["max_files_to_execute"] = 2
    result = evaluate_phase29_policy(gate_input, _base_checklist(), _base_evidence_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    gate_input = _base_gate_input()
    gate_input["execute_allowed"] = True
    result = evaluate_phase29_policy(gate_input, _base_checklist(), _base_evidence_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_checklist_does_not_execute_false() -> None:
    checklist = _base_checklist()
    checklist["checklist_does_not_execute"] = False
    result = evaluate_phase29_policy(_base_gate_input(), checklist, _base_evidence_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_evidence_does_not_execute_false() -> None:
    evidence_gate = _base_evidence_gate()
    evidence_gate["evidence_does_not_execute"] = False
    result = evaluate_phase29_policy(_base_gate_input(), _base_checklist(), evidence_gate)
    assert result["policy_status"] == "FAIL"
