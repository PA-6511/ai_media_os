from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("ls6oc1_run", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_base_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "final_ready": tmp_path / "exchange/logs/final_ready.json",
        "final_confirmation": tmp_path / "exchange/human_review/final_confirmation.json",
        "ls6ob_preflight": tmp_path / "exchange/runtime/ls6ob_preflight.json",
        "ls6ob_run": tmp_path / "exchange/logs/ls6ob_run.json",
        "ls6ob_validation": tmp_path / "exchange/logs/ls6ob_validation.json",
        "ls6oa_ready": tmp_path / "exchange/logs/ls6oa_ready.json",
        "ls6oa_go": tmp_path / "exchange/human_review/ls6oa_go.json",
        "one_shot_lock": tmp_path / "exchange/locks/one_shot_lock.json",
        "ls6n_final": tmp_path / "exchange/runtime/ls6n_final.json",
        "credential_presence": tmp_path / "exchange/runtime/credential_presence.json",
        "runtime_state": tmp_path / "exchange/runtime/runtime_state.json",
        "runtime_lock": tmp_path / "exchange/locks/runtime_lock.json",
        "ls6i_validation": tmp_path / "exchange/logs/ls6i_validation.json",
        "ls6c_payload": tmp_path / "exchange/logs/ls6c_payload.json",
        "ls6c_result": tmp_path / "exchange/logs/ls6c_result.json",
        "ls6b_lock": tmp_path / "exchange/locks/ls6b_lock.json",
        "credential_env": tmp_path / "credential.env",
        "execution_output": tmp_path / "exchange/runtime/execution_result.json",
        "consumption_lock_output": tmp_path / "exchange/locks/consumption.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(files["policy"], {"phase": "LS-6O-C-1"})
    write_json(
        files["final_ready"],
        {
            "status": "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_READY_NO_EXECUTION",
            "confirmation_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        },
    )
    write_json(
        files["final_confirmation"],
        {
            "confirmation_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
            "confirm_final_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
            "decision": {
                "final_execute_now_consumed": False,
                "required_confirm_final_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
            },
        },
    )
    write_json(
        files["policy"],
        {
            "phase": "LS-6O-C-1",
            "required_previous_phase": {"ls6oc0": {"required_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"}},
            "actual_execution_policy": {"required_confirm_final_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"},
        },
    )
    write_json(files["ls6ob_preflight"], {"status": "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE"})
    write_json(files["ls6ob_run"], {"status": "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE"})
    write_json(files["ls6ob_validation"], {"status": "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_WRITE"})
    write_json(files["ls6oa_ready"], {"status": "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION"})
    write_json(
        files["ls6oa_go"],
        {
            "go_label": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY",
            "decision": {"actual_wordpress_go_consumed": False},
        },
    )
    write_json(
        files["one_shot_lock"],
        {"one_shot_actual_execution_lock_active": True, "one_shot_actual_execution_lock_consumed": False},
    )
    write_json(files["ls6n_final"], {"status": "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE"})
    write_json(files["credential_presence"], {"required_keys_present": True, "required_keys_non_empty": True})
    write_json(files["runtime_state"], {"runtime_freeze_active": True, "runtime_freeze_restored": False})
    write_json(files["runtime_lock"], {"locked": True})
    write_json(files["ls6i_validation"], {"status": "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION"})
    write_json(
        files["ls6c_payload"],
        {
            "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
            "payload_count": 1,
            "max_items": 1,
            "payloads": [
                {
                    "title": "2.5次元の誘惑",
                    "post_status": "draft",
                    "content": '<a href="https://www.amazon.co.jp/dp/B07X2G67B4?tag=t">x</a>',
                }
            ],
        },
    )
    write_json(files["ls6c_result"], {"status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"})
    write_json(files["ls6b_lock"], {"rerun_allowed": False})
    files["credential_env"].write_text(
        "WORDPRESS_BASE_URL=https://example.com\n"
        "WORDPRESS_USERNAME=wpuser\n"
        "WORDPRESS_APP_PASSWORD=super-secret-pass\n",
        encoding="utf-8",
    )
    return files


def run_main(monkeypatch, files: dict[str, Path], *, execute_now: bool, confirm_label: str, urlopen_impl) -> int:
    module = load_module(Path("scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py"))

    args = [
        "prog",
        "--policy",
        str(files["policy"]),
        "--final-execute-now-ready-result",
        str(files["final_ready"]),
        "--final-execute-now-confirmation",
        str(files["final_confirmation"]),
        "--ls6ob-preflight-result",
        str(files["ls6ob_preflight"]),
        "--ls6ob-run-result",
        str(files["ls6ob_run"]),
        "--ls6ob-validation-result",
        str(files["ls6ob_validation"]),
        "--ls6oa-ready-result",
        str(files["ls6oa_ready"]),
        "--ls6oa-go",
        str(files["ls6oa_go"]),
        "--one-shot-lock",
        str(files["one_shot_lock"]),
        "--ls6n-final-preflight",
        str(files["ls6n_final"]),
        "--credential-presence-result",
        str(files["credential_presence"]),
        "--runtime-freeze-state",
        str(files["runtime_state"]),
        "--runtime-freeze-lock",
        str(files["runtime_lock"]),
        "--ls6i-validation-result",
        str(files["ls6i_validation"]),
        "--ls6c-payload",
        str(files["ls6c_payload"]),
        "--ls6c-result",
        str(files["ls6c_result"]),
        "--ls6b-lock",
        str(files["ls6b_lock"]),
        "--credential-env",
        str(files["credential_env"]),
        "--execution-output",
        str(files["execution_output"]),
        "--consumption-lock-output",
        str(files["consumption_lock_output"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
        "--confirm-final-label",
        confirm_label,
    ]
    if execute_now:
        args.append("--execute-now")

    monkeypatch.setattr(module.request, "urlopen", urlopen_impl)
    monkeypatch.setattr(sys, "argv", args)
    return module.main()


class DummyResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_missing_final_execute_now_returns_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    files["final_ready"].unlink()

    called = {"n": 0}

    def fake_urlopen(req, timeout=30):
        called["n"] += 1
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=False,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY_MISSING_FINAL_EXECUTE_NOW"
    assert called["n"] == 0


def test_missing_execute_now_flag_returns_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)

    called = {"n": 0}

    def fake_urlopen(req, timeout=30):
        called["n"] += 1
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=False,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY_MISSING_EXECUTE_NOW_FLAG"
    assert called["n"] == 0


def test_wrong_confirm_label_returns_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)

    called = {"n": 0}

    def fake_urlopen(req, timeout=30):
        called["n"] += 1
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="WRONG_LABEL",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY"
    assert called["n"] == 0


def test_confirm_label_helper_allows_stripped_cli_label(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    module = load_module(Path("scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py"))
    errors = module.validate_final_execute_now_labels(
        cli_label="  FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY  ",
        final_confirmation=read_json(files["final_confirmation"]),
        final_ready=read_json(files["final_ready"]),
        policy=read_json(files["policy"]),
    )
    assert errors == []


def test_confirm_label_helper_rejects_wrong_label(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    module = load_module(Path("scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py"))
    errors = module.validate_final_execute_now_labels(
        cli_label="WRONG_LABEL",
        final_confirmation=read_json(files["final_confirmation"]),
        final_ready=read_json(files["final_ready"]),
        policy=read_json(files["policy"]),
    )
    assert errors


def test_confirm_label_helper_rejects_ready_result_mismatch(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    ready = read_json(files["final_ready"])
    ready["confirmation_label"] = "WRONG_LABEL"
    write_json(files["final_ready"], ready)
    module = load_module(Path("scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py"))
    errors = module.validate_final_execute_now_labels(
        cli_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        final_confirmation=read_json(files["final_confirmation"]),
        final_ready=read_json(files["final_ready"]),
        policy=read_json(files["policy"]),
    )
    assert errors


def test_confirm_label_helper_rejects_confirmation_decision_mismatch(tmp_path: Path) -> None:
    files = make_base_files(tmp_path)
    confirmation = read_json(files["final_confirmation"])
    confirmation["decision"]["required_confirm_final_label"] = "WRONG_LABEL"
    write_json(files["final_confirmation"], confirmation)
    module = load_module(Path("scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py"))
    errors = module.validate_final_execute_now_labels(
        cli_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        final_confirmation=read_json(files["final_confirmation"]),
        final_ready=read_json(files["final_ready"]),
        policy=read_json(files["policy"]),
    )
    assert errors


def test_valid_mocked_wordpress_response_executes(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)

    def fake_urlopen(req, timeout=30):
        return DummyResponse(201, {"id": 123, "status": "draft", "link": "https://example.com/?p=123"})

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0

    out = read_json(files["output"])
    exe = read_json(files["execution_output"])
    lock = read_json(files["consumption_lock_output"])

    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_EXECUTED_ONE_SHOT_DRAFT_ONLY"
    assert exe["status"] == "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATED_DRAFT_ONLY"
    assert exe["new_post_id"] == 123
    assert exe["returned_post_status"] == "draft"
    assert exe["created_count"] == 1
    assert exe["publish_executed"] is False
    assert exe["wordpress_existing_post_update_executed"] is False
    assert exe["runtime_freeze_restored"] is False
    assert lock["locked"] is True
    assert lock["rerun_allowed"] is False


def test_wordpress_http_500_returns_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    module = load_module(Path("scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py"))

    def fake_urlopen(req, timeout=30):
        raise module.HTTPError(req.full_url, 500, "error", None, None)

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED"


def test_wordpress_response_status_not_draft_returns_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)

    def fake_urlopen(req, timeout=30):
        return DummyResponse(201, {"id": 123, "status": "publish", "link": "https://example.com/?p=123"})

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED"


def test_missing_new_post_id_returns_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)

    def fake_urlopen(req, timeout=30):
        return DummyResponse(201, {"status": "draft", "link": "https://example.com/?p=123"})

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED"


def test_max_items_gt_1_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["max_items"] = 2
    write_json(files["ls6c_payload"], payload)

    def fake_urlopen(req, timeout=30):
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY"


def test_payload_asin_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["payloads"][0]["content"] = '<a href="https://www.amazon.co.jp/dp/XXXXXXXXXX?tag=t">x</a>'
    write_json(files["ls6c_payload"], payload)

    def fake_urlopen(req, timeout=30):
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY"


def test_post_status_not_draft_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    payload = read_json(files["ls6c_payload"])
    payload["payloads"][0]["post_status"] = "publish"
    write_json(files["ls6c_payload"], payload)

    def fake_urlopen(req, timeout=30):
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY"


def test_one_shot_lock_consumed_true_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    lock = read_json(files["one_shot_lock"])
    lock["one_shot_actual_execution_lock_consumed"] = True
    write_json(files["one_shot_lock"], lock)

    def fake_urlopen(req, timeout=30):
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY"


def test_runtime_freeze_restored_true_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    st = read_json(files["runtime_state"])
    st["runtime_freeze_restored"] = True
    write_json(files["runtime_state"], st)

    def fake_urlopen(req, timeout=30):
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY"


def test_missing_credential_key_fails_before_api_call(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    files["credential_env"].write_text(
        "WORDPRESS_BASE_URL=https://example.com\nWORDPRESS_USERNAME=wpuser\n",
        encoding="utf-8",
    )

    called = {"n": 0}

    def fake_urlopen(req, timeout=30):
        called["n"] += 1
        raise AssertionError("urlopen should not be called")

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    out = read_json(files["output"])
    assert out["status"] == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED"
    assert called["n"] == 0


def test_credential_values_not_exposed_in_results(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)
    secret = "super-secret-pass"

    def fake_urlopen(req, timeout=30):
        return DummyResponse(201, {"id": 200, "status": "draft", "link": "https://example.com/?p=200"})

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0

    run_text = files["output"].read_text(encoding="utf-8")
    exe_text = files["execution_output"].read_text(encoding="utf-8")
    assert secret not in run_text
    assert secret not in exe_text


def test_authorization_header_not_exposed(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)

    def fake_urlopen(req, timeout=30):
        return DummyResponse(201, {"id": 201, "status": "draft", "link": "https://example.com/?p=201"})

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0

    run_text = files["output"].read_text(encoding="utf-8")
    exe_text = files["execution_output"].read_text(encoding="utf-8")
    assert "Authorization" not in run_text
    assert "Authorization" not in exe_text
    assert "Basic " not in run_text
    assert "Basic " not in exe_text


def test_consumption_lock_created(tmp_path: Path, monkeypatch) -> None:
    files = make_base_files(tmp_path)

    def fake_urlopen(req, timeout=30):
        return DummyResponse(201, {"id": 321, "status": "draft", "link": "https://example.com/?p=321"})

    code = run_main(
        monkeypatch,
        files,
        execute_now=True,
        confirm_label="FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        urlopen_impl=fake_urlopen,
    )
    assert code == 0
    assert files["consumption_lock_output"].exists()

    lock = read_json(files["consumption_lock_output"])
    assert lock["rerun_allowed"] is False
