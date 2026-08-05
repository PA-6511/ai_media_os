from phase67.preparation_evidence_design.phase67_policy import evaluate_phase67_policy


def _base_package() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "can_execute": False,
        "execute_allowed": False,
        "max_files_to_execute": 1,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
    }


def _base_controls() -> dict:
    return {"preparation_controls_does_not_execute": True}


def _base_evidence() -> dict:
    return {
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "preparation_evidence_does_not_execute": True,
    }


def _base_gate() -> dict:
    return {"gate_required": True, "manual_preparation_gate_does_not_execute": True}


def test_policy_fails_when_can_execute_true() -> None:
    package = _base_package()
    package["can_execute"] = True
    result = evaluate_phase67_policy(package, _base_controls(), _base_evidence(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    package = _base_package()
    package["execute_allowed"] = True
    result = evaluate_phase67_policy(package, _base_controls(), _base_evidence(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_controls_guard_false() -> None:
    controls = _base_controls()
    controls["preparation_controls_does_not_execute"] = False
    result = evaluate_phase67_policy(_base_package(), controls, _base_evidence(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_evidence_guard_false() -> None:
    evidence = _base_evidence()
    evidence["preparation_evidence_does_not_execute"] = False
    result = evaluate_phase67_policy(_base_package(), _base_controls(), evidence, _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_pass_with_valid_inputs() -> None:
    result = evaluate_phase67_policy(
        _base_package(), _base_controls(), _base_evidence(), _base_gate()
    )
    assert result["policy_status"] == "PASS"
