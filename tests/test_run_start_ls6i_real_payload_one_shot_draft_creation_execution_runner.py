import json
import subprocess
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_policy() -> dict[str, Any]:
    return json.loads(Path("config/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_policy.json").read_text(encoding="utf-8"))


def valid_ls6h_result() -> dict[str, Any]:
    return {
        "status": "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVED_NO_EXECUTION",
        "actual_execute_approval": True,
        "execute_approval_label": "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_ONLY",
        "execute_approval_label_consumed": False,
    }


def valid_ls6h_approval() -> dict[str, Any]:
    return {
        "execute_approval_status": "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE",
    }


def valid_ls6g_result() -> dict[str, Any]:
    return {
        "status": "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION",
        "final_preflight_passed": True,
        "execution_allowed": False,
    }


def valid_ls6f_plan() -> dict[str, Any]:
    return {
        "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "runner_plan_ready": True,
        "runner_execution_allowed": False,
        "runner_executed": False,
    }


def valid_ls6f_result() -> dict[str, Any]:
    return {
        "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "runner_plan_ready": True,
        "runner_execution_allowed": False,
        "runner_executed": False,
    }


def valid_ls6c_payload() -> dict[str, Any]:
    return {
        "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
        "payload_ready": True,
        "payload_count": 1,
        "max_items": 1,
        "payloads": [
            {
                "title": "2.5次元の誘惑",
                "post_status": "draft",
                "content_format": "html",
                "content": "<a href=\"https://www.amazon.co.jp/dp/B07X2G67B4?tag=ktkr77-22\">Amazon</a>",
                "markdown_link_present": False,
                "html_link_present": True,
                "sample_content_detected": False,
            }
        ],
    }


def valid_ls6c_result() -> dict[str, Any]:
    return {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"}


def run_runner(tmp_path: Path, *, overrides: dict[str, Any] | None = None, use_execute: bool = False) -> subprocess.CompletedProcess[str]:
    overrides = overrides or {}
    p_policy = tmp_path / "policy.json"
    p_ls6h_result = tmp_path / "ls6h_result.json"
    p_ls6h_approval = tmp_path / "ls6h_approval.json"
    p_ls6g_result = tmp_path / "ls6g_result.json"
    p_ls6f_plan = tmp_path / "ls6f_plan.json"
    p_ls6f_result = tmp_path / "ls6f_result.json"
    p_ls6c_payload = tmp_path / "ls6c_payload.json"
    p_ls6c_result = tmp_path / "ls6c_result.json"
    p_output = tmp_path / "preflight.json"
    p_report = tmp_path / "preflight.md"

    write_json(p_policy, overrides.get("policy", valid_policy()))
    if overrides.get("skip_ls6h_result") is not True:
        write_json(p_ls6h_result, overrides.get("ls6h_result", valid_ls6h_result()))
    write_json(p_ls6h_approval, overrides.get("ls6h_approval", valid_ls6h_approval()))
    write_json(p_ls6g_result, overrides.get("ls6g_result", valid_ls6g_result()))
    write_json(p_ls6f_plan, overrides.get("ls6f_plan", valid_ls6f_plan()))
    write_json(p_ls6f_result, overrides.get("ls6f_result", valid_ls6f_result()))
    write_json(p_ls6c_payload, overrides.get("ls6c_payload", valid_ls6c_payload()))
    write_json(p_ls6c_result, overrides.get("ls6c_result", valid_ls6c_result()))

    cmd = [
        "python3",
        "scripts/run_start_ls6i_real_payload_one_shot_draft_creation_execution_runner.py",
        "--policy",
        str(p_policy),
        "--ls6h-approved-result",
        str(p_ls6h_result),
        "--ls6h-approval",
        str(p_ls6h_approval),
        "--ls6g-result",
        str(p_ls6g_result),
        "--ls6f-runner-plan",
        str(p_ls6f_plan),
        "--ls6f-result",
        str(p_ls6f_result),
        "--ls6c-payload",
        str(p_ls6c_payload),
        "--ls6c-result",
        str(p_ls6c_result),
        "--output",
        str(p_output),
        "--report",
        str(p_report),
    ]
    if use_execute:
        cmd.append("--execute")

    return subprocess.run(cmd, capture_output=True, text=True)


def read_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_inputs_preflight_pass(tmp_path: Path):
    cp = run_runner(tmp_path)
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["status"] == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_PREFLIGHT_ONLY_NO_EXECUTION"


def test_missing_ls6h_result_not_ready(tmp_path: Path):
    cp = run_runner(tmp_path, overrides={"skip_ls6h_result": True})
    assert cp.returncode != 0


def test_ls6h_status_not_pass_not_ready(tmp_path: Path):
    bad = valid_ls6h_result()
    bad["status"] = "WRONG"
    cp = run_runner(tmp_path, overrides={"ls6h_result": bad})
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["status"] == "LS6I_EXECUTION_RUNNER_IMPLEMENTATION_PREFLIGHT_NOT_READY"


def test_ls6g_final_preflight_false_not_ready(tmp_path: Path):
    bad = valid_ls6g_result()
    bad["final_preflight_passed"] = False
    cp = run_runner(tmp_path, overrides={"ls6g_result": bad})
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["status"] == "LS6I_EXECUTION_RUNNER_IMPLEMENTATION_PREFLIGHT_NOT_READY"


def test_ls6f_runner_executed_true_not_ready(tmp_path: Path):
    bad = valid_ls6f_plan()
    bad["runner_executed"] = True
    cp = run_runner(tmp_path, overrides={"ls6f_plan": bad})
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["status"] == "LS6I_EXECUTION_RUNNER_IMPLEMENTATION_PREFLIGHT_NOT_READY"


def test_ls6c_payload_count_gt_one_not_ready(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payload_count"] = 2
    cp = run_runner(tmp_path, overrides={"ls6c_payload": bad})
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["status"] == "LS6I_EXECUTION_RUNNER_IMPLEMENTATION_PREFLIGHT_NOT_READY"


def test_payload_post_status_not_draft_not_ready(tmp_path: Path):
    bad = valid_ls6c_payload()
    bad["payloads"][0]["post_status"] = "publish"
    cp = run_runner(tmp_path, overrides={"ls6c_payload": bad})
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["status"] == "LS6I_EXECUTION_RUNNER_IMPLEMENTATION_PREFLIGHT_NOT_READY"


def test_execute_approval_label_consumed_true_not_ready(tmp_path: Path):
    bad = valid_ls6h_result()
    bad["execute_approval_label_consumed"] = True
    cp = run_runner(tmp_path, overrides={"ls6h_result": bad})
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["status"] == "LS6I_EXECUTION_RUNNER_IMPLEMENTATION_PREFLIGHT_NOT_READY"


def test_execute_option_immediate_error(tmp_path: Path):
    cp = run_runner(tmp_path, use_execute=True)
    assert cp.returncode != 0
    assert "--execute is not supported" in (cp.stderr + cp.stdout)


def test_output_safety_flags_all_false(tmp_path: Path):
    cp = run_runner(tmp_path)
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    keys = [
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_creation_executed",
        "post119_update_executed",
        "publish_executed",
        "credential_env_read_executed",
        "approval_token_consumed",
        "approval_label_consumed",
        "execute_approval_label_consumed",
        "runner_executed",
        "actual_execution_executed",
        "ls6b_rerun_executed",
    ]
    for key in keys:
        assert result[key] is False


def test_credential_env_read_executed_false(tmp_path: Path):
    cp = run_runner(tmp_path)
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["credential_env_read_executed"] is False


def test_actual_execution_executed_false(tmp_path: Path):
    cp = run_runner(tmp_path)
    assert cp.returncode == 0
    result = read_result(tmp_path / "preflight.json")
    assert result["actual_execution_executed"] is False
