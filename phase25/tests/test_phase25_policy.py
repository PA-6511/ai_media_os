from phase25.planning.phase25_policy import evaluate_phase25_policy


def _base_plan() -> dict:
    return {
        "mode": "DRY_RUN",
        "human_approval_required": True,
        "max_files_to_execute": 1,
        "planned_target_files": ["target.py"],
        "execute_allowed": False,
        "auto_merge_allowed": False,
        "delete_allowed": False,
        "production_execute_allowed": False,
        "manual_approval_required": True,
    }


def _base_evidence() -> dict:
    return {
        "evidence_required": True,
        "evidence_does_not_execute": True,
    }


def test_policy_fails_when_max_files_invalid() -> None:
    plan = _base_plan()
    plan["max_files_to_execute"] = 2
    result = evaluate_phase25_policy(plan, _base_evidence(), {"status": "EXECUTION_CHECKLIST_READY"})
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_execute_allowed_true() -> None:
    plan = _base_plan()
    plan["execute_allowed"] = True
    result = evaluate_phase25_policy(plan, _base_evidence(), {"status": "EXECUTION_CHECKLIST_READY"})
    assert result["policy_status"] == "FAIL"


def test_policy_fails_when_evidence_does_not_execute_false() -> None:
    evidence = _base_evidence()
    evidence["evidence_does_not_execute"] = False
    result = evaluate_phase25_policy(_base_plan(), evidence, {"status": "EXECUTION_CHECKLIST_READY"})
    assert result["policy_status"] == "FAIL"
