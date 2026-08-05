from pathlib import Path

from phase18.verify.apply_verify import verify_apply_result


def test_verify_apply_result_pass_when_only_sandbox_paths(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    execution_result = {
        "status": "PASS",
        "applied_files": [str(sandbox / "a.txt")],
        "blocked_files": [],
    }

    result = verify_apply_result(execution_result, str(sandbox))
    assert result["verify_status"] == "PASS"
    assert result["can_promote_to_next"] is True


def test_verify_apply_result_fail_when_outside_path_detected(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    execution_result = {
        "status": "PASS",
        "applied_files": [str(outside / "x.txt")],
        "blocked_files": [],
    }

    result = verify_apply_result(execution_result, str(sandbox))
    assert result["verify_status"] == "FAIL"
    assert result["can_promote_to_next"] is False
