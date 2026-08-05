from phase21.planning.manual_approval_requirements import build_manual_approval_requirements


def test_manual_approval_requirements_include_non_apply_guard() -> None:
    requirements = build_manual_approval_requirements({})
    assert requirements["approval_required"] is True
    assert requirements["approve_does_not_apply"] is True
    assert "APPROVE_PHASE22_PLANNING_ONLY" in requirements["allowed_decisions"]
