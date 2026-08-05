import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls7a_human_review_result_evidence_policy.json").read_text(encoding="utf-8"))


def valid_review() -> dict[str, Any]:
    return json.loads(Path("exchange/human_review/start_ls7a_post119_human_review_decision.json").read_text(encoding="utf-8"))


def valid_ls6b_result() -> dict[str, Any]:
    return {
        "status": "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN",
        "post_id": 119,
        "post_status": "draft",
        "payload_count": 1,
        "max_items": 1,
        "publish_executed": False,
        "future_schedule_executed": False,
        "existing_post_update_executed": False,
        "delete_executed": False,
    }


def valid_ls6b_validation() -> dict[str, Any]:
    return {"validation_status": "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED"}


def valid_lock() -> dict[str, Any]:
    return {"locked": True, "post_id": 119, "post_status": "draft", "rerun_allowed": False}


def run_validator(
    tmp_path: Path,
    *,
    policy: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    ls6b_result: dict[str, Any] | None = None,
    ls6b_validation: dict[str, Any] | None = None,
    lock: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p_policy = tmp_path / "policy.json"
    p_review = tmp_path / "review.json"
    p_ls6b_result = tmp_path / "ls6b_result.json"
    p_ls6b_validation = tmp_path / "ls6b_validation.json"
    p_lock = tmp_path / "lock.json"
    p_output = tmp_path / "result.json"
    p_report = tmp_path / "report.md"

    write_json(p_policy, policy or valid_policy())
    write_json(p_review, review or valid_review())
    write_json(p_ls6b_result, ls6b_result or valid_ls6b_result())
    write_json(p_ls6b_validation, ls6b_validation or valid_ls6b_validation())
    write_json(p_lock, lock or valid_lock())

    subprocess.run(
        [
            "python3",
            "scripts/validate_start_ls7a_human_review_result_evidence.py",
            "--policy",
            str(p_policy),
            "--review",
            str(p_review),
            "--ls6b-result",
            str(p_ls6b_result),
            "--ls6b-validation-result",
            str(p_ls6b_validation),
            "--ls6b-lock",
            str(p_lock),
            "--output",
            str(p_output),
            "--report",
            str(p_report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return json.loads(p_output.read_text(encoding="utf-8"))


def test_policy_valid_and_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-7A"
    assert policy["status"] == "HUMAN_REVIEW_EVIDENCE_ONLY"
    assert policy["execution_mode"] == "REVIEW_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_valid_inputs_recorded(tmp_path: Path):
    result = run_validator(tmp_path)
    assert result["status"] == "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED"


def test_ls6b_not_success_not_ready(tmp_path: Path):
    ls6b = valid_ls6b_result()
    ls6b["status"] = "WRONG"
    result = run_validator(tmp_path, ls6b_result=ls6b)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"


def test_ls6b_post_id_not_119_not_ready(tmp_path: Path):
    ls6b = valid_ls6b_result()
    ls6b["post_id"] = 120
    result = run_validator(tmp_path, ls6b_result=ls6b)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"


def test_ls6b_post_status_not_draft_not_ready(tmp_path: Path):
    ls6b = valid_ls6b_result()
    ls6b["post_status"] = "publish"
    result = run_validator(tmp_path, ls6b_result=ls6b)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"


def test_ls6b_validation_status_mismatch_not_ready(tmp_path: Path):
    v = valid_ls6b_validation()
    v["validation_status"] = "WRONG"
    result = run_validator(tmp_path, ls6b_validation=v)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"


def test_lock_invalid_not_ready(tmp_path: Path):
    l = valid_lock()
    l["rerun_allowed"] = True
    result = run_validator(tmp_path, lock=l)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"

    l2 = valid_lock()
    l2["locked"] = False
    result2 = run_validator(tmp_path, lock=l2)
    assert result2["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"


def test_publish_decision_not_do_not_publish_not_ready(tmp_path: Path):
    review = valid_review()
    review["publish_decision"] = "".join(["P", "U", "B", "L", "I", "S", "H"])
    result = run_validator(tmp_path, review=review)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"


def test_manual_publish_allowed_true_not_ready(tmp_path: Path):
    review = valid_review()
    review["manual_publish_allowed"] = bool(1)
    result = run_validator(tmp_path, review=review)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"


def test_observed_issues_missing_not_ready(tmp_path: Path):
    review = valid_review()
    review["observed_issues"] = ["sample_title"]
    result = run_validator(tmp_path, review=review)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"


def test_current_phase_execution_true_not_ready(tmp_path: Path):
    review = valid_review()
    review["current_phase_execution"]["publish_executed"] = True
    result = run_validator(tmp_path, review=review)
    assert result["status"] == "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY"
