from phase19.evaluation.rollback_evaluator import evaluate_rollback_readiness


def test_rollback_fail_when_plan_missing() -> None:
    result = evaluate_rollback_readiness({})
    assert result["rollback_status"] == "FAIL"


def test_rollback_pass_when_dry_run_and_targets_present() -> None:
    plan = {
        "dry_run": True,
        "rollback_targets": ["sandbox/a.txt"],
    }
    result = evaluate_rollback_readiness(plan)
    assert result["rollback_status"] == "PASS"
