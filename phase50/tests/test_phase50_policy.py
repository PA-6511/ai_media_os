from phase50.cutover_planning_design.phase50_policy import evaluate_phase50_policy


def _base_package() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "execute_allowed": False,
        "sandbox_scope_required": True,
        "single_file_scope_required": True,
    }


def _base_controls() -> dict:
    return {"cutover_planning_controls_does_not_execute": True}


def _base_stop() -> dict:
    return {
        "stop_conditions_required": True,
        "cutover_planning_stop_conditions_does_not_execute": True,
    }


def _base_evidence() -> dict:
    return {
        "evidence_required": True,
        "missing_evidence_blocks_progress": True,
        "cutover_planning_evidence_does_not_execute": True,
    }


def _base_gate() -> dict:
    return {"gate_required": True, "cutover_planning_gate_does_not_execute": True}


def test_policy_fails_when_max_files_invalid() -> None:
    pkg = _base_package()
    pkg["max_files_to_execute"] = 2
    result = evaluate_phase50_policy(pkg, _base_controls(), _base_stop(), _base_evidence(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    pkg = _base_package()
    pkg["execute_allowed"] = True
    result = evaluate_phase50_policy(pkg, _base_controls(), _base_stop(), _base_evidence(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_evidence_does_not_execute_false() -> None:
    evidence = _base_evidence()
    evidence["cutover_planning_evidence_does_not_execute"] = False
    result = evaluate_phase50_policy(_base_package(), _base_controls(), _base_stop(), evidence, _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_controls_does_not_execute_false() -> None:
    controls = _base_controls()
    controls["cutover_planning_controls_does_not_execute"] = False
    result = evaluate_phase50_policy(_base_package(), controls, _base_stop(), _base_evidence(), _base_gate())
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_gate_does_not_execute_false() -> None:
    gate = _base_gate()
    gate["cutover_planning_gate_does_not_execute"] = False
    result = evaluate_phase50_policy(_base_package(), _base_controls(), _base_stop(), _base_evidence(), gate)
    assert result["policy_status"] == "FAIL"


def test_policy_pass_with_valid_inputs() -> None:
    result = evaluate_phase50_policy(
        _base_package(), _base_controls(), _base_stop(), _base_evidence(), _base_gate()
    )
    assert result["policy_status"] == "PASS"
