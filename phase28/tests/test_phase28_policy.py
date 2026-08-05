from phase28.gate.phase28_policy import evaluate_phase28_policy


def _base_gate() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "gate_required": True,
    }


def _base_schema() -> dict:
    return {"approval_required": True, "allow_does_not_execute": True}


def _base_evidence() -> dict:
    return {"evidence_required": True, "evidence_does_not_execute": True}


def test_policy_fails_when_max_files_invalid() -> None:
    gate = _base_gate()
    gate["max_files_to_execute"] = 2
    result = evaluate_phase28_policy(gate, _base_schema(), _base_evidence())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    gate = _base_gate()
    gate["execute_allowed"] = True
    result = evaluate_phase28_policy(gate, _base_schema(), _base_evidence())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_allow_does_not_execute_false() -> None:
    schema = _base_schema()
    schema["allow_does_not_execute"] = False
    result = evaluate_phase28_policy(_base_gate(), schema, _base_evidence())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_evidence_does_not_execute_false() -> None:
    evidence = _base_evidence()
    evidence["evidence_does_not_execute"] = False
    result = evaluate_phase28_policy(_base_gate(), _base_schema(), evidence)
    assert result["policy_status"] == "FAIL"
