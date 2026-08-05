from pathlib import Path

from phase18.apply.apply_plan import build_apply_plan


def _ready_package(selected_candidate_id: str) -> dict:
    return {
        "status": "READY_FOR_HUMAN_REVIEW",
        "selected_candidate_id": selected_candidate_id,
        "comparison_result": {
            "planned_changes": [
                {
                    "target_path": "/tmp/sandbox/file.txt",
                    "content": "x",
                    "operation": "update",
                }
            ]
        },
    }


def test_apply_plan_fails_without_selected_candidate_id(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    result = build_apply_plan(_ready_package(""), str(sandbox), str(sandbox))
    assert result["status"] == "FAIL"


def test_apply_plan_policy_violation_when_allowlist_outside_sandbox(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    allowlist = tmp_path / "allowlist"
    sandbox.mkdir()
    allowlist.mkdir()

    result = build_apply_plan(_ready_package("minimal"), str(sandbox), str(allowlist))
    assert result["status"] == "POLICY_VIOLATION"


def test_apply_plan_requires_create_or_update_only(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    package = {
        "status": "READY_FOR_HUMAN_REVIEW",
        "selected_candidate_id": "minimal",
        "comparison_result": {
            "planned_changes": [
                {
                    "target_path": str(sandbox / "a.txt"),
                    "content": "x",
                    "operation": "delete",
                }
            ]
        },
    }

    result = build_apply_plan(package, str(sandbox), str(sandbox))
    assert result["status"] == "POLICY_VIOLATION"
