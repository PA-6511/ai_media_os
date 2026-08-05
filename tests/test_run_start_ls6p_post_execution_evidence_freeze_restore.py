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
    spec = importlib.util.spec_from_file_location("ls6p_run", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6oc1_execution": tmp_path / "exchange/runtime/ls6oc1_execution.json",
        "ls6oc1_consumption": tmp_path / "exchange/locks/ls6oc1_consumption.json",
        "ls6oc1_run": tmp_path / "exchange/logs/ls6oc1_run.json",
        "ls6oc1_validation": tmp_path / "exchange/logs/ls6oc1_validation.json",
        "runtime_state": tmp_path / "exchange/runtime/runtime_state.json",
        "runtime_lock": tmp_path / "exchange/locks/runtime_lock.json",
        "credential_env": tmp_path / "credential.env",
        "verification_output": tmp_path / "exchange/runtime/verification.json",
        "freeze_restore_output": tmp_path / "exchange/runtime/freeze_restore.json",
        "rerun_lock_output": tmp_path / "exchange/locks/rerun_final.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }
    write_json(
        files["policy"],
        {
            "required_previous_phase": {
                "ls6oc1": {
                    "required_run_status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_EXECUTED_ONE_SHOT_DRAFT_ONLY",
                    "required_validation_status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATED_ONE_SHOT_DRAFT_ONLY",
                }
            },
            "target_post": {
                "post_id": 183,
                "expected_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_status": "draft",
                "created_count": 1,
                "max_items": 1,
            },
            "credential_policy": {"required_credential_keys": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]},
            "required_previous_phase": {
                "ls6oc1": {
                    "required_run_status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_EXECUTED_ONE_SHOT_DRAFT_ONLY",
                    "required_validation_status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATED_ONE_SHOT_DRAFT_ONLY"
                },
                "runtime_freeze": {
                    "active_state": "exchange/runtime/start_ls6m_runtime_freeze_active_state.json",
                    "active_lock": "exchange/locks/start_ls6m_runtime_freeze_active.lock.json"
                }
            },
            "next_phase": {"phase": "LS-6Q", "manual_review_required": True, "manual_publish_allowed_by_this_phase": False},
        },
    )
    write_json(
        files["ls6oc1_execution"],
        {
            "new_post_id": 183,
            "returned_post_status": "draft",
            "created_count": 1,
            "max_items": 1,
            "publish_executed": False,
            "future_schedule_executed": False,
            "wordpress_existing_post_update_executed": False,
            "post119_update_executed": False,
            "delete_executed": False,
        },
    )
    write_json(files["ls6oc1_consumption"], {"rerun_allowed": False})
    write_json(files["ls6oc1_run"], {"status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_EXECUTED_ONE_SHOT_DRAFT_ONLY"})
    write_json(files["ls6oc1_validation"], {"status": "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATED_ONE_SHOT_DRAFT_ONLY"})
    write_json(files["runtime_state"], {"runtime_freeze_active": True, "runtime_freeze_restored": False})
    write_json(files["runtime_lock"], {"locked": True})
    files["credential_env"].write_text(
        "WORDPRESS_BASE_URL=https://example.com\nWORDPRESS_USERNAME=wpuser\nWORDPRESS_APP_PASSWORD=secret\n",
        encoding="utf-8",
    )
    return files


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


def run_main(monkeypatch, files: dict[str, Path], *, verify: bool, restore: bool, urlopen_impl) -> int:
    module = load_module(Path("scripts/run_start_ls6p_post_execution_evidence_freeze_restore.py"))
    args = [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6oc1-execution-result", str(files["ls6oc1_execution"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_consumption"]),
        "--ls6oc1-run-result", str(files["ls6oc1_run"]),
        "--ls6oc1-validation-result", str(files["ls6oc1_validation"]),
        "--runtime-freeze-state", str(files["runtime_state"]),
        "--runtime-freeze-lock", str(files["runtime_lock"]),
        "--credential-env", str(files["credential_env"]),
        "--wordpress-draft-verification-output", str(files["verification_output"]),
        "--runtime-freeze-restore-output", str(files["freeze_restore_output"]),
        "--rerun-prevention-lock-output", str(files["rerun_lock_output"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    if verify:
        args.append("--verify-wordpress-draft")
    if restore:
        args.append("--restore-runtime-freeze")
    monkeypatch.setattr(module.request, "urlopen", urlopen_impl)
    monkeypatch.setattr(sys, "argv", args)
    return module.main()


def test_missing_verify_flag_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    code = run_main(monkeypatch, files, verify=False, restore=True, urlopen_impl=lambda req, timeout=30: None)
    assert code == 0
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY_MISSING_VERIFY_FLAG"


def test_missing_restore_flag_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    code = run_main(monkeypatch, files, verify=True, restore=False, urlopen_impl=lambda req, timeout=30: None)
    assert code == 0
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY_MISSING_RESTORE_FLAG"


def test_ls6oc1_execution_missing_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    files["ls6oc1_execution"].unlink()
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert code == 0
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"


def test_validation_status_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    write_json(files["ls6oc1_validation"], {"status": "WRONG"})
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"


def test_new_post_id_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6oc1_execution"])
    payload["new_post_id"] = 999
    write_json(files["ls6oc1_execution"], payload)
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"


def test_created_count_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6oc1_execution"])
    payload["created_count"] = 2
    write_json(files["ls6oc1_execution"], payload)
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"


def test_returned_status_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6oc1_execution"])
    payload["returned_post_status"] = "publish"
    write_json(files["ls6oc1_execution"], payload)
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"


def test_consumption_rerun_allowed_true_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    write_json(files["ls6oc1_consumption"], {"rerun_allowed": True})
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"


def test_runtime_freeze_active_false_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    write_json(files["runtime_state"], {"runtime_freeze_active": False, "runtime_freeze_restored": False})
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"


def test_runtime_freeze_restored_true_before_ls6p_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    write_json(files["runtime_state"], {"runtime_freeze_active": True, "runtime_freeze_restored": True})
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_NOT_READY"


def test_credential_key_missing_failed_before_get(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    files["credential_env"].write_text("WORDPRESS_BASE_URL=https://example.com\nWORDPRESS_USERNAME=wpuser\n", encoding="utf-8")
    called = {"n": 0}
    def fake(req, timeout=30):
        called["n"] += 1
        raise AssertionError
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=fake)
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_FAILED"
    assert called["n"] == 0


def test_wordpress_get_http_500_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    module = load_module(Path("scripts/run_start_ls6p_post_execution_evidence_freeze_restore.py"))
    def fake(req, timeout=30):
        raise module.HTTPError(req.full_url, 500, "err", None, None)
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=fake)
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_FAILED"


def test_wordpress_get_id_mismatch_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 999, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_FAILED"


def test_wordpress_get_status_not_draft_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "publish", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert read_json(files["output"])["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_FAILED"


def test_valid_mocked_wordpress_get_passed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    code = run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    out = read_json(files["output"])
    assert out["status"] == "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_PASSED"


def test_post_put_patch_delete_not_called(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    methods = []
    def fake(req, timeout=30):
        methods.append(req.get_method())
        return DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}})
    run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=fake)
    assert methods == ["GET"]


def test_credential_values_not_exposed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    text = files["output"].read_text(encoding="utf-8")
    assert "WORDPRESS_APP_PASSWORD" not in text
    assert "super-secret-pass" not in text
    assert "Authorization" not in files["output"].read_text(encoding="utf-8")


def test_runtime_freeze_restore_result_generated(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert files["freeze_restore_output"].exists()


def test_rerun_prevention_final_lock_generated(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(monkeypatch, files, verify=True, restore=True, urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}))
    assert files["rerun_lock_output"].exists()