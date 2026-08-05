from pathlib import Path

from phase18.apply.apply_executor import execute_apply_plan


def _base_apply_plan(sandbox: Path) -> dict:
    return {
        "status": "READY_TO_APPLY_DRY_RUN",
        "mode": "DRY_RUN",
        "sandbox_root": str(sandbox),
        "allowlist_root": str(sandbox),
        "planned_changes": [
            {
                "target_path": str(sandbox / "ok.txt"),
                "content": "hello",
                "operation": "create",
            }
        ],
    }


def _approved_gate() -> dict:
    return {
        "decision": "APPROVE",
        "status": "PASS",
        "gate_status": "PASS_APPROVED",
        "can_proceed": True,
    }


def test_approve_without_pass_approved_gate_is_skipped(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    plan = _base_apply_plan(sandbox)
    approval = {
        "decision": "APPROVE",
        "status": "PASS",
        "gate_status": "WARN_PENDING_REVIEW",
        "can_proceed": True,
    }

    result = execute_apply_plan(plan, approval)
    assert result["status"] == "SKIPPED"
    assert result["reason"] == "approval_gate_not_passed"


def test_approve_with_can_proceed_false_is_skipped(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    plan = _base_apply_plan(sandbox)
    approval = {
        "decision": "APPROVE",
        "status": "PASS",
        "gate_status": "PASS_APPROVED",
        "can_proceed": False,
    }

    result = execute_apply_plan(plan, approval)
    assert result["status"] == "SKIPPED"


def test_allowlist_outside_sandbox_is_policy_violation(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    sandbox.mkdir()
    outside.mkdir()

    plan = _base_apply_plan(sandbox)
    plan["allowlist_root"] = str(outside)

    result = execute_apply_plan(plan, _approved_gate())
    assert result["status"] == "POLICY_VIOLATION"
    assert result["reason"] == "allowlist_root_outside_sandbox"


def test_delete_operation_is_policy_violation(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    plan = _base_apply_plan(sandbox)
    plan["planned_changes"][0]["operation"] = "delete"

    result = execute_apply_plan(plan, _approved_gate())
    assert result["status"] == "POLICY_VIOLATION"


def test_create_or_update_only_passes(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    plan = _base_apply_plan(sandbox)
    plan["planned_changes"].append(
        {
            "target_path": str(sandbox / "ok2.txt"),
            "content": "world",
            "operation": "update",
        }
    )

    result = execute_apply_plan(plan, _approved_gate())
    assert result["status"] == "PASS"
    assert result["can_promote_to_next"] is True
    assert len(result["applied_files"]) == 2
