import json
import subprocess
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict:
    return json.loads(Path("config/start_ls6b_prep_one_shot_draft_creation_runner_policy.json").read_text(encoding="utf-8"))


def valid_plan() -> dict:
    return {
        "phase": "LS-6B-PREP",
        "status": "LS6B_PREP_RUNNER_PLAN_BLOCKED_NO_EXECUTION",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "target_next_phase": "LS-6B",
        "blocked_until_actual_human_approval": True,
        "required_actual_approval_status": "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION",
        "approval_label": "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY",
        "payload_preview": "exchange/logs/start_ls4_wordpress_draft_payload_preview.json",
        "max_items": 1,
        "post_status": "draft",
        "guards": {
            "publish_allowed": False,
            "future_schedule_allowed": False,
            "existing_post_update_allowed": False,
            "delete_allowed": False,
            "freeze_after_run": True,
            "rollback_pointer_required": True,
            "post_id_evidence_required_after_execution": True,
        },
        "current_phase_execution": {
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "publish_executed": False,
            "credential_env_read_executed": False,
            "approval_token_consumed": False,
        },
        "future_execution_contract": {
            "must_revalidate_actual_human_approval": True,
            "must_revalidate_payload_preview": True,
            "must_revalidate_credential_ready": True,
            "must_reject_multiple_payloads": True,
            "must_reject_non_draft_status": True,
            "must_reject_publish_update_delete": True,
            "must_record_post_id": True,
            "must_record_rollback_pointer": True,
            "must_freeze_after_run": True,
        },
        "next_phase": {
            "phase": "LS-6B",
            "execution_allowed": False,
        },
    }


def valid_ls3_result() -> dict:
    return {"status": "LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY"}


def valid_ls4_result() -> dict:
    return {"status": "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY"}


def valid_ls5_result() -> dict:
    return {"status": "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION"}


def valid_ls6a_template_result() -> dict:
    return {"status": "LS6A_TEMPLATE_PASS_NO_ACTUAL_APPROVAL"}


def valid_ls6a_not_ready_result() -> dict:
    return {"status": "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"}


def valid_payload() -> dict:
    return {
        "phase": "LS-4",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "max_items": 1,
        "payloads": [
            {"post_status": "draft", "title": "t", "content": "c"}
        ],
    }


def run_validator(
    tmp_path: Path,
    *,
    policy: dict | None = None,
    plan: dict | None = None,
    ls3: dict | None = None,
    ls4: dict | None = None,
    ls5: dict | None = None,
    ls6a_template: dict | None = None,
    ls6a_not_ready: dict | None = None,
    payload: dict | None = None,
) -> dict:
    policy_path = tmp_path / "policy.json"
    plan_path = tmp_path / "plan.json"
    ls3_path = tmp_path / "ls3.json"
    ls4_path = tmp_path / "ls4.json"
    ls5_path = tmp_path / "ls5.json"
    ls6a_template_path = tmp_path / "ls6a_template.json"
    ls6a_not_ready_path = tmp_path / "ls6a_not_ready.json"
    payload_path = tmp_path / "payload.json"
    output_path = tmp_path / "result.json"
    report_path = tmp_path / "report.md"

    write_json(policy_path, policy or valid_policy())
    write_json(plan_path, plan or valid_plan())
    write_json(ls3_path, ls3 or valid_ls3_result())
    write_json(ls4_path, ls4 or valid_ls4_result())
    write_json(ls5_path, ls5 or valid_ls5_result())
    write_json(ls6a_template_path, ls6a_template or valid_ls6a_template_result())
    write_json(ls6a_not_ready_path, ls6a_not_ready or valid_ls6a_not_ready_result())
    write_json(payload_path, payload or valid_payload())

    cmd = [
        "python3",
        "scripts/validate_start_ls6b_prep_one_shot_draft_creation_runner.py",
        "--policy",
        str(policy_path),
        "--plan",
        str(plan_path),
        "--ls3-result",
        str(ls3_path),
        "--ls4-result",
        str(ls4_path),
        "--ls5-result",
        str(ls5_path),
        "--ls6a-template-result",
        str(ls6a_template_path),
        "--ls6a-not-ready-result",
        str(ls6a_not_ready_path),
        "--payload",
        str(payload_path),
        "--output",
        str(output_path),
        "--report",
        str(report_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_policy_valid_and_flags_false():
    policy = valid_policy()
    assert policy["phase"] == "LS-6B-PREP"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["production_status"] == "NO_GO"
    for value in policy["current_phase_safety_flags"].values():
        assert value is False


def test_prepare_script_generates_blocked_plan(tmp_path):
    policy_path = tmp_path / "policy.json"
    output_path = tmp_path / "plan.json"
    write_json(policy_path, valid_policy())

    subprocess.run(
        [
            "python3",
            "scripts/prepare_start_ls6b_one_shot_draft_creation_runner.py",
            "--policy",
            str(policy_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    plan = json.loads(output_path.read_text(encoding="utf-8"))
    assert plan["status"] == "LS6B_PREP_RUNNER_PLAN_BLOCKED_NO_EXECUTION"
    assert plan["blocked_until_actual_human_approval"] is True
    assert plan["next_phase"]["execution_allowed"] is False


def test_valid_inputs_pass_blocked_design(tmp_path):
    result = run_validator(tmp_path)
    assert result["status"] == "LS6B_PREP_RUNNER_DESIGN_BLOCKED_PASS_NO_EXECUTION"
    assert result["runner_plan_ready"] is True


def test_ls6a_not_ready_status_mismatch_not_ready(tmp_path):
    bad = valid_ls6a_not_ready_result()
    bad["status"] = "WRONG"
    result = run_validator(tmp_path, ls6a_not_ready=bad)
    assert result["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"


def test_plan_execution_allowed_true_not_ready(tmp_path):
    plan = valid_plan()
    plan["next_phase"]["execution_allowed"] = True
    result = run_validator(tmp_path, plan=plan)
    assert result["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"


def test_plan_post_status_or_max_items_invalid_not_ready(tmp_path):
    plan = valid_plan()
    plan["post_status"] = "publish"
    result = run_validator(tmp_path, plan=plan)
    assert result["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"

    plan2 = valid_plan()
    plan2["max_items"] = 2
    result2 = run_validator(tmp_path, plan=plan2)
    assert result2["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"


def test_plan_guard_publish_update_delete_schedule_true_not_ready(tmp_path):
    for key in [
        "publish_allowed",
        "future_schedule_allowed",
        "existing_post_update_allowed",
        "delete_allowed",
    ]:
        plan = valid_plan()
        plan["guards"][key] = True
        result = run_validator(tmp_path, plan=plan)
        assert result["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"


def test_plan_current_phase_execution_true_not_ready(tmp_path):
    plan = valid_plan()
    plan["current_phase_execution"]["wordpress_api_call_executed"] = True
    result = run_validator(tmp_path, plan=plan)
    assert result["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"

    plan2 = valid_plan()
    plan2["current_phase_execution"]["wordpress_write_executed"] = True
    result2 = run_validator(tmp_path, plan=plan2)
    assert result2["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"


def test_future_execution_contract_false_not_ready(tmp_path):
    plan = valid_plan()
    plan["future_execution_contract"]["must_revalidate_payload_preview"] = False
    result = run_validator(tmp_path, plan=plan)
    assert result["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"


def test_previous_status_mismatch_not_ready(tmp_path):
    bad_ls3 = valid_ls3_result()
    bad_ls3["status"] = "WRONG"
    result = run_validator(tmp_path, ls3=bad_ls3)
    assert result["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"

    bad_ls4 = valid_ls4_result()
    bad_ls4["status"] = "WRONG"
    result2 = run_validator(tmp_path, ls4=bad_ls4)
    assert result2["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"

    bad_ls5 = valid_ls5_result()
    bad_ls5["status"] = "WRONG"
    result3 = run_validator(tmp_path, ls5=bad_ls5)
    assert result3["status"] == "LS6B_PREP_RUNNER_DESIGN_NOT_READY"
