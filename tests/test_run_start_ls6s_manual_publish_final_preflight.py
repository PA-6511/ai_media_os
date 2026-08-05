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
    spec = importlib.util.spec_from_file_location("ls6s_run", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "ls6r_ready": tmp_path / "exchange/logs/ls6r_ready.json",
        "ls6r_approval": tmp_path / "exchange/human_review/ls6r_approval.json",
        "ls6q_ready": tmp_path / "exchange/logs/ls6q_ready.json",
        "ls6q_review": tmp_path / "exchange/human_review/ls6q_review.json",
        "ls6p_verify": tmp_path / "exchange/runtime/ls6p_verify.json",
        "ls6p_freeze": tmp_path / "exchange/runtime/ls6p_freeze.json",
        "ls6p_lock": tmp_path / "exchange/locks/ls6p_lock.json",
        "ls6p_validation": tmp_path / "exchange/logs/ls6p_validation.json",
        "ls6oc1_exec": tmp_path / "exchange/runtime/ls6oc1_exec.json",
        "ls6oc1_lock": tmp_path / "exchange/locks/ls6oc1_lock.json",
        "credential_env": tmp_path / "credential.env",
        "wp_result": tmp_path / "exchange/runtime/wp_result.json",
        "preflight_result": tmp_path / "exchange/runtime/preflight_result.json",
        "preflight_lock": tmp_path / "exchange/locks/preflight.lock.json",
        "output": tmp_path / "exchange/logs/run_result.json",
        "report": tmp_path / "reports/run_report.md",
    }

    write_json(
        files["policy"],
        {
            "phase": "LS-6S",
            "execution_mode": "FINAL_PREFLIGHT_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "required_previous_phase": {
                "ls6r": {
                    "required_ready_status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH",
                    "required_approval_status": "APPROVED_NO_PUBLISH_EXECUTION",
                    "required_approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
                    "required_approval_label_consumed": False,
                },
                "ls6q": {
                    "required_ready_status": "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_AND_MANUAL_PUBLISH_DECISION_READY_NO_PUBLISH",
                    "required_human_decision": "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY",
                },
                "ls6p": {
                    "required_validation_status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED"
                },
                "ls6oc1": {
                    "required_created_count": 1,
                    "required_returned_post_status": "draft",
                    "required_rerun_allowed": False,
                },
            },
            "target_post": {
                "post_id": 183,
                "post_link": "https://hoshido.jp/?p=183",
                "title": "2.5次元の誘惑",
                "asin": "B07X2G67B4",
                "expected_current_status": "draft",
                "created_count": 1,
            },
            "credential_policy": {
                "required_credential_keys": [
                    "WORDPRESS_BASE_URL",
                    "WORDPRESS_USERNAME",
                    "WORDPRESS_APP_PASSWORD",
                ]
            },
        },
    )

    write_json(
        files["ls6r_ready"],
        {
            "status": "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH",
            "approval_status": "APPROVED_NO_PUBLISH_EXECUTION",
            "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
            "approval_label_consumed": False,
            "manual_publish_executed": False,
            "next_phase": {"phase": "LS-6S"},
        },
    )
    write_json(
        files["ls6r_approval"],
        {
            "approval_status": "APPROVED_NO_PUBLISH_EXECUTION",
            "approval": {
                "approval_label": "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
                "approval_label_consumed": False,
                "manual_publish_executed": False,
            },
        },
    )
    write_json(
        files["ls6q_ready"],
        {
            "status": "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_AND_MANUAL_PUBLISH_DECISION_READY_NO_PUBLISH",
            "human_decision": "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY",
        },
    )
    write_json(files["ls6q_review"], {"human_decision": {"decision": "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY"}})
    write_json(files["ls6p_verify"], {"post_id": 183, "returned_post_status": "draft"})
    write_json(files["ls6p_freeze"], {"runtime_freeze_restored": True})
    write_json(files["ls6p_lock"], {"locked": True, "rerun_allowed": False})
    write_json(files["ls6p_validation"], {"status": "LS6P_POST_EXECUTION_EVIDENCE_FREEZE_RESTORE_VALIDATED", "post_id": 183, "runtime_freeze_restored": True})
    write_json(files["ls6oc1_exec"], {"new_post_id": 183, "created_count": 1, "returned_post_status": "draft"})
    write_json(files["ls6oc1_lock"], {"rerun_allowed": False})

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


def run_main(monkeypatch, files: dict[str, Path], *, verify: bool, record: bool, urlopen_impl) -> int:
    module = load_module(Path("scripts/run_start_ls6s_manual_publish_final_preflight.py"))
    args = [
        "prog",
        "--policy", str(files["policy"]),
        "--ls6r-ready-result", str(files["ls6r_ready"]),
        "--ls6r-approval-result", str(files["ls6r_approval"]),
        "--ls6q-ready-result", str(files["ls6q_ready"]),
        "--ls6q-review-result", str(files["ls6q_review"]),
        "--ls6p-draft-verification-result", str(files["ls6p_verify"]),
        "--ls6p-runtime-freeze-restore-result", str(files["ls6p_freeze"]),
        "--ls6p-rerun-prevention-lock", str(files["ls6p_lock"]),
        "--ls6p-validation-result", str(files["ls6p_validation"]),
        "--ls6oc1-execution-result", str(files["ls6oc1_exec"]),
        "--ls6oc1-consumption-lock", str(files["ls6oc1_lock"]),
        "--credential-env", str(files["credential_env"]),
        "--wordpress-current-draft-status-output", str(files["wp_result"]),
        "--manual-publish-final-preflight-output", str(files["preflight_result"]),
        "--manual-publish-final-preflight-lock-output", str(files["preflight_lock"]),
        "--output", str(files["output"]),
        "--report", str(files["report"]),
    ]
    if verify:
        args.append("--verify-current-draft")
    if record:
        args.append("--record-final-preflight")
    monkeypatch.setattr(module.request, "urlopen", urlopen_impl)
    monkeypatch.setattr(sys, "argv", args)
    return module.main()


def test_01_missing_verify_flag_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(monkeypatch, files, verify=False, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"


def test_02_missing_record_flag_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(monkeypatch, files, verify=True, record=False, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY_MISSING_RECORD_FLAG"


def test_03_ls6r_ready_missing_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    files["ls6r_ready"].unlink()
    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_04_ls6r_ready_status_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6r_ready"])
    payload["status"] = "WRONG"
    write_json(files["ls6r_ready"], payload)
    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_05_ls6r_approval_label_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6r_ready"])
    payload["approval_label"] = "WRONG"
    write_json(files["ls6r_ready"], payload)
    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_06_ls6r_approval_label_consumed_true_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6r_ready"])
    payload["approval_label_consumed"] = True
    write_json(files["ls6r_ready"], payload)
    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_07_ls6r_manual_publish_executed_true_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6r_ready"])
    payload["manual_publish_executed"] = True
    write_json(files["ls6r_ready"], payload)
    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_08_ls6q_decision_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6q_ready"])
    payload["human_decision"] = "HOLD_AS_DRAFT"
    write_json(files["ls6q_ready"], payload)
    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_09_ls6p_validation_status_mismatch_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    payload = read_json(files["ls6p_validation"])
    payload["status"] = "WRONG"
    write_json(files["ls6p_validation"], payload)
    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_10_ls6oc1_consumption_rerun_allowed_true_not_ready(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    write_json(files["ls6oc1_lock"], {"rerun_allowed": True})
    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=lambda req, timeout=30: None)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_NOT_READY"


def test_11_credential_key_missing_failed_before_get(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    files["credential_env"].write_text("WORDPRESS_BASE_URL=https://example.com\nWORDPRESS_USERNAME=wpuser\n", encoding="utf-8")
    called = {"n": 0}

    def fake(req, timeout=30):
        called["n"] += 1
        raise AssertionError("must not call GET")

    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=fake)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"
    assert called["n"] == 0


def test_12_wordpress_get_http_500_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    module = load_module(Path("scripts/run_start_ls6s_manual_publish_final_preflight.py"))

    def fake(req, timeout=30):
        raise module.HTTPError(req.full_url, 500, "err", None, None)

    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=fake)
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_13_wordpress_get_id_mismatch_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(
        monkeypatch,
        files,
        verify=True,
        record=True,
        urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 999, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}),
    )
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_14_wordpress_get_status_not_draft_failed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(
        monkeypatch,
        files,
        verify=True,
        record=True,
        urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "publish", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}),
    )
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"


def test_15_valid_mocked_wordpress_get_passed(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(
        monkeypatch,
        files,
        verify=True,
        record=True,
        urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}),
    )
    assert read_json(files["output"])["status"] == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"


def test_16_post_put_patch_delete_not_called(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    methods = []

    def fake(req, timeout=30):
        methods.append(req.get_method())
        return DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}})

    run_main(monkeypatch, files, verify=True, record=True, urlopen_impl=fake)
    assert methods == ["GET"]


def test_17_publish_schedule_delete_update_not_called(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(
        monkeypatch,
        files,
        verify=True,
        record=True,
        urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}),
    )
    out = read_json(files["output"])
    assert out["wordpress_write_executed_by_this_phase"] is False
    assert out["wordpress_publish_executed"] is False
    assert out["publish_executed"] is False
    assert out["future_schedule_executed"] is False
    assert out["delete_executed"] is False
    assert out["post119_update_executed"] is False


def test_18_credential_values_not_exposed_in_result(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    files["credential_env"].write_text(
        "WORDPRESS_BASE_URL=https://example.com\nWORDPRESS_USERNAME=wpuser\nWORDPRESS_APP_PASSWORD=super-secret-pass\n",
        encoding="utf-8",
    )
    run_main(
        monkeypatch,
        files,
        verify=True,
        record=True,
        urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}),
    )
    out_text = files["output"].read_text(encoding="utf-8")
    assert "WORDPRESS_APP_PASSWORD" not in out_text
    assert "super-secret-pass" not in out_text
    assert "Authorization" not in out_text


def test_19_final_preflight_lock_generated(tmp_path: Path, monkeypatch) -> None:
    files = make_files(tmp_path)
    run_main(
        monkeypatch,
        files,
        verify=True,
        record=True,
        urlopen_impl=lambda req, timeout=30: DummyResponse(200, {"id": 183, "status": "draft", "link": "https://hoshido.jp/?p=183", "title": {"rendered": "2.5次元の誘惑"}}),
    )
    assert files["preflight_lock"].exists()
