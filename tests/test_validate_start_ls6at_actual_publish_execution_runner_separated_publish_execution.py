from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6at_actual_publish_execution_runner_separated_publish_execution import (
    STATUS_NOT_VALIDATED,
    STATUS_VALIDATED,
    main,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def mutate(path: Path, keys: tuple[str, ...], value) -> None:
    data = read_json(path)
    cur = data
    for key in keys[:-1]:
        cur = cur[key]
    cur[keys[-1]] = value
    write_json(path, data)


def make_files(tmp_path: Path) -> dict[str, Path]:
    files = {
        "policy": tmp_path / "config/policy.json",
        "execution_result": tmp_path / "exchange/runtime/result.json",
        "execution_lock": tmp_path / "exchange/locks/lock.json",
        "run_result": tmp_path / "exchange/logs/result.json",
        "ls6as_ready": tmp_path / "exchange/logs/ls6as_ready.json",
        "ls6as_final": tmp_path / "exchange/human_review/ls6as_final.json",
        "ls6ar_preflight": tmp_path / "exchange/runtime/ls6ar_preflight.json",
        "ls6ar_validation": tmp_path / "exchange/logs/ls6ar_validation.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }

    write_json(files["policy"], {"phase": "LS-6AT", "target_post": {"post_id": 183}})

    result = {
        "status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED",
        "execution_mode": "SEPARATED_ACTUAL_PUBLISH_EXECUTION",
        "production_status": "PUBLISHED",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "pre_publish_returned_post_status": "draft",
        "post_publish_returned_post_status": "publish",
        "returned_post_status": "publish",
        "ls6as_final_command_validated": True,
        "ls6ar_credential_preflight_validated": True,
        "publish_executed": True,
        "wordpress_api_call_executed": True,
        "wordpress_get_executed": True,
        "wordpress_post_executed": True,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "post119_update_executed": False,
        "delete_executed": False,
        "future_schedule_executed": False,
        "content_update_executed": False,
        "title_update_executed": False,
        "meta_update_executed": False,
        "new_post_created": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "manual_publish_executed": False,
        "rerun_allowed": False,
        "requires_post_publish_verification": True,
        "next_phase": {"phase": "LS-6AU"},
    }
    write_json(files["execution_result"], result)
    write_json(files["run_result"], dict(result))

    write_json(
        files["execution_lock"],
        {
            "locked": True,
            "status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_LOCKED_PUBLISHED",
        },
    )
    write_json(
        files["ls6as_ready"],
        {"status": "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_READY_NO_PUBLISH"},
    )
    write_json(
        files["ls6as_final"],
        {"command_status": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_RECORDED_NO_PUBLISH_EXECUTION"},
    )
    write_json(
        files["ls6ar_preflight"],
        {"actual_publish_execution_runner_credential_preflight_ready": True},
    )
    write_json(
        files["ls6ar_validation"],
        {"status": "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_VALIDATED_NO_PUBLISH"},
    )

    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--publish-execution-result",
        str(files["execution_result"]),
        "--publish-execution-lock",
        str(files["execution_lock"]),
        "--run-result",
        str(files["run_result"]),
        "--ls6as-ready-result",
        str(files["ls6as_ready"]),
        "--ls6as-final-command-result",
        str(files["ls6as_final"]),
        "--ls6ar-credential-preflight-result",
        str(files["ls6ar_preflight"]),
        "--ls6ar-validation-result",
        str(files["ls6ar_validation"]),
        "--output",
        str(files["output"]),
        "--report",
        str(files["report"]),
    ]


def run_validate(monkeypatch, files: dict[str, Path]) -> dict:
    monkeypatch.setattr("sys.argv", build_argv(files))
    rc = main()
    assert rc == 0
    return read_json(files["output"])


def test_61_validation_valid(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


def test_62_validation_missing_execution_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["execution_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_63_validation_missing_lock(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["execution_lock"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_64_validation_missing_run_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["run_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


@pytest.mark.parametrize(
    "path_key,keys,value",
    [
        ("execution_result", ("status",), "WRONG"),
        ("execution_result", ("production_status",), "NO_PUBLISH"),
        ("execution_result", ("post_id",), 999),
        ("execution_result", ("pre_publish_returned_post_status",), "publish"),
        ("execution_result", ("post_publish_returned_post_status",), "draft"),
        ("execution_result", ("publish_executed",), False),
        ("execution_result", ("wordpress_api_call_executed",), False),
        ("execution_result", ("wordpress_get_executed",), False),
        ("execution_result", ("wordpress_post_executed",), False),
        ("execution_result", ("wordpress_put_executed",), True),
        ("execution_result", ("wordpress_patch_executed",), True),
        ("execution_result", ("wordpress_delete_executed",), True),
        ("execution_result", ("post119_update_executed",), True),
        ("execution_result", ("delete_executed",), True),
        ("execution_result", ("future_schedule_executed",), True),
        ("execution_result", ("content_update_executed",), True),
        ("execution_result", ("title_update_executed",), True),
        ("execution_result", ("meta_update_executed",), True),
        ("execution_result", ("new_post_created",), True),
        ("execution_result", ("credential_value_output",), True),
        ("execution_result", ("credential_value_persisted",), True),
        ("execution_result", ("secret_length_output",), True),
        ("execution_result", ("secret_hash_output",), True),
        ("execution_result", ("manual_publish_executed",), True),
        ("execution_result", ("rerun_allowed",), True),
        ("execution_result", ("next_phase", "phase"), "LS-XXX"),
        ("execution_result", ("requires_post_publish_verification",), False),
    ],
)
def test_65_to_91_validation_field_checks(monkeypatch, tmp_path: Path, path_key: str, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    mutate(files[path_key], keys, value)
    if path_key == "execution_result":
        write_json(files["run_result"], read_json(files["execution_result"]))
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_92_source_no_requests_put() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/run_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
    ).read_text(encoding="utf-8")
    assert "requests.put" not in src


def test_93_source_no_requests_patch() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/run_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
    ).read_text(encoding="utf-8")
    assert "requests.patch" not in src


def test_94_source_no_requests_delete() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/run_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
    ).read_text(encoding="utf-8")
    assert "requests.delete" not in src


def test_95_source_no_base64() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/run_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
        ).read_text(encoding="utf-8")
        + Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
        ).read_text(encoding="utf-8")
    )
    assert "base64" not in merged
    assert "b64encode" not in merged


def test_96_source_no_authorization_output() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/run_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
        ).read_text(encoding="utf-8")
        + Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
        ).read_text(encoding="utf-8")
    )
    assert "Authorization:" not in merged


def test_97_source_no_basic_output() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/run_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
        ).read_text(encoding="utf-8")
        + Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls6at_actual_publish_execution_runner_separated_publish_execution.py"
        ).read_text(encoding="utf-8")
    )
    assert "Basic " not in merged
