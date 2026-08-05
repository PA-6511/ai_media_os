import json
from pathlib import Path
from typing import Any

from scripts import run_start_ls6b_wordpress_one_shot_draft_creation as runner


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_env(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "WORDPRESS_BASE_URL=https://example.com",
                "WORDPRESS_USERNAME=test_user",
                "WORDPRESS_APP_PASSWORD=test_pass",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def valid_policy() -> dict[str, Any]:
    return {
        "phase": "LS-6B",
        "execution_mode": "ONE_SHOT_WRITE_ALLOWED",
        "production_status": "LIMITED_GO_DRAFT_ONLY",
        "required_approval_label": "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY",
        "required_credential_keys": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "one_shot_scope": {
            "max_items": 1,
            "post_status": "draft",
            "publish_allowed": False,
            "future_schedule_allowed": False,
            "existing_post_update_allowed": False,
            "delete_allowed": False,
        },
        "current_phase_safety_flags": {
            "publish_allowed": False,
            "future_schedule_allowed": False,
            "existing_post_update_allowed": False,
            "delete_allowed": False,
            "amazon_api_call_allowed": False,
            "x_api_call_allowed": False,
            "x_post_allowed": False,
            "multiple_items_allowed": False,
            "credential_secret_output_allowed": False,
            "secret_length_output_allowed": False,
            "secret_hash_output_allowed": False,
        },
    }


def valid_payload() -> dict[str, Any]:
    return {
        "phase": "LS-4",
        "max_items": 1,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "payloads": [
            {
                "post_status": "draft",
                "title": "Sample",
                "content": "content",
                "category_or_tag_present": True,
            }
        ],
    }


def valid_status(status: str) -> dict[str, Any]:
    return {"status": status}


def valid_approval() -> dict[str, Any]:
    return {
        "approval_status": "HUMAN_APPROVED",
        "approval_label": "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY",
    }


def prepare_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "policy": tmp_path / "policy.json",
        "payload": tmp_path / "payload.json",
        "env": tmp_path / "credential.env",
        "ls3": tmp_path / "ls3.json",
        "ls4": tmp_path / "ls4.json",
        "ls5": tmp_path / "ls5.json",
        "ls6a": tmp_path / "ls6a.json",
        "ls6b_prep": tmp_path / "ls6b_prep.json",
        "approval": tmp_path / "approval.json",
        "lock": tmp_path / "lock.json",
    }
    write_json(paths["policy"], valid_policy())
    write_json(paths["payload"], valid_payload())
    write_env(paths["env"])
    write_json(paths["ls3"], valid_status("LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY"))
    write_json(paths["ls4"], valid_status("LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY"))
    write_json(paths["ls5"], valid_status("LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION"))
    write_json(paths["ls6a"], valid_status("LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION"))
    write_json(paths["ls6b_prep"], valid_status("LS6B_PREP_RUNNER_DESIGN_BLOCKED_PASS_NO_EXECUTION"))
    write_json(paths["approval"], valid_approval())
    return paths


def run_phase(tmp_path: Path, execute: bool, wp_post=None, mutate=None) -> dict[str, Any]:
    paths = prepare_inputs(tmp_path)
    if mutate:
        mutate(paths)
    return runner.run_phase(
        policy_path=paths["policy"],
        payload_path=paths["payload"],
        credential_env_path=paths["env"],
        ls3_result_path=paths["ls3"],
        ls4_result_path=paths["ls4"],
        ls5_result_path=paths["ls5"],
        ls6a_ready_result_path=paths["ls6a"],
        ls6b_prep_result_path=paths["ls6b_prep"],
        approval_path=paths["approval"],
        lock_path=paths["lock"],
        execute=execute,
        wp_post=wp_post,
    )


def test_no_execute_preflight_no_api_call(tmp_path: Path):
    called = {"v": False}

    def fake_wp(*_args, **_kwargs):
        called["v"] = True
        return 201, {"id": 1}, None

    result = run_phase(tmp_path, execute=False, wp_post=fake_wp)
    assert result["status"] == "LS6B_ONE_SHOT_DRAFT_CREATION_PREFLIGHT_PASS_NO_EXECUTION"
    assert result["wordpress_api_call_executed"] is False
    assert called["v"] is False


def test_ls6a_not_ready_does_not_call_api(tmp_path: Path):
    called = {"v": False}

    def fake_wp(*_args, **_kwargs):
        called["v"] = True
        return 201, {"id": 1}, None

    def mutate(paths: dict[str, Path]):
        write_json(paths["ls6a"], valid_status("WRONG_STATUS"))

    result = run_phase(tmp_path, execute=True, wp_post=fake_wp, mutate=mutate)
    assert result["status"] == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP"
    assert called["v"] is False


def test_payload_more_than_one_does_not_call_api(tmp_path: Path):
    called = {"v": False}

    def fake_wp(*_args, **_kwargs):
        called["v"] = True
        return 201, {"id": 1}, None

    def mutate(paths: dict[str, Path]):
        p = valid_payload()
        p["payloads"].append({"post_status": "draft", "title": "2", "content": "2"})
        write_json(paths["payload"], p)

    result = run_phase(tmp_path, execute=True, wp_post=fake_wp, mutate=mutate)
    assert result["status"] == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP"
    assert called["v"] is False


def test_non_draft_does_not_call_api(tmp_path: Path):
    called = {"v": False}

    def fake_wp(*_args, **_kwargs):
        called["v"] = True
        return 201, {"id": 1}, None

    def mutate(paths: dict[str, Path]):
        p = valid_payload()
        p["payloads"][0]["post_status"] = "publish"
        write_json(paths["payload"], p)

    result = run_phase(tmp_path, execute=True, wp_post=fake_wp, mutate=mutate)
    assert result["status"] == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP"
    assert called["v"] is False


def test_lock_blocks_api_call(tmp_path: Path):
    called = {"v": False}

    def fake_wp(*_args, **_kwargs):
        called["v"] = True
        return 201, {"id": 1}, None

    def mutate(paths: dict[str, Path]):
        write_json(
            paths["lock"],
            {
                "locked": True,
                "reason": "ONE_SHOT_DRAFT_ALREADY_CREATED",
                "rerun_allowed": False,
            },
        )

    result = run_phase(tmp_path, execute=True, wp_post=fake_wp, mutate=mutate)
    assert result["status"] == "LS6B_ONE_SHOT_ALREADY_EXECUTED_LOCKED"
    assert called["v"] is False


def test_mock_201_success_creates_lock(tmp_path: Path):
    def fake_wp(*_args, **_kwargs):
        return 201, {"id": 123, "status": "draft"}, None

    paths = prepare_inputs(tmp_path)
    result = runner.run_phase(
        policy_path=paths["policy"],
        payload_path=paths["payload"],
        credential_env_path=paths["env"],
        ls3_result_path=paths["ls3"],
        ls4_result_path=paths["ls4"],
        ls5_result_path=paths["ls5"],
        ls6a_ready_result_path=paths["ls6a"],
        ls6b_prep_result_path=paths["ls6b_prep"],
        approval_path=paths["approval"],
        lock_path=paths["lock"],
        execute=True,
        wp_post=fake_wp,
    )
    assert result["status"] == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN"
    assert result["post_id"] == 123
    assert paths["lock"].exists()


def test_mock_500_safe_stop_token_not_consumed(tmp_path: Path):
    def fake_wp(*_args, **_kwargs):
        return 500, None, "HTTP_ERROR"

    result = run_phase(tmp_path, execute=True, wp_post=fake_wp)
    assert result["status"] == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP"
    assert result["approval_token_consumed"] is False


def test_result_has_no_secret_fields(tmp_path: Path):
    result = run_phase(tmp_path, execute=False)
    dumped = json.dumps(result, ensure_ascii=False)
    assert "test_pass" not in dumped
    assert "WORDPRESS_APP_PASSWORD" not in dumped
