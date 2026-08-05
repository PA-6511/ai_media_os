from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_start_ls6au_post_publish_verification_published_evidence import (
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
        "result": tmp_path / "exchange/runtime/result.json",
        "lock": tmp_path / "exchange/locks/lock.json",
        "run_result": tmp_path / "exchange/logs/result.json",
        "ls6at_result": tmp_path / "exchange/runtime/ls6at_result.json",
        "ls6at_lock": tmp_path / "exchange/locks/ls6at_lock.json",
        "ls6at_validation": tmp_path / "exchange/logs/ls6at_validation.json",
        "output": tmp_path / "exchange/logs/validation.json",
        "report": tmp_path / "reports/validation.md",
    }

    write_json(files["policy"], {"phase": "LS-6AU", "target_post": {"post_id": 183}})

    result = {
        "status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED",
        "execution_mode": "POST_PUBLISH_VERIFICATION_ONLY_NO_WRITE",
        "production_status": "PUBLISHED_VERIFIED",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "rest_returned_post_status": "publish",
        "public_url_reachable": True,
        "post_publish_verified": True,
        "published_evidence_recorded": True,
        "rollback_readiness_recorded": True,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "wordpress_post_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "post119_update_executed": False,
        "credential_value_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "rerun_allowed": False,
        "completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_PUBLISHED_AND_VERIFIED",
        "start_ls_one_shot_publish_chain_closed": True,
        "next_phase": {
            "phase": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED",
            "recommended_next_action": "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
        },
    }
    write_json(files["result"], result)
    write_json(files["run_result"], dict(result))

    write_json(
        files["lock"],
        {
            "status": "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_LOCKED",
            "locked": True,
        },
    )

    write_json(
        files["ls6at_result"],
        {"status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED"},
    )
    write_json(files["ls6at_lock"], {"locked": True})
    write_json(
        files["ls6at_validation"],
        {"status": "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED"},
    )
    return files


def build_argv(files: dict[str, Path]) -> list[str]:
    return [
        "prog",
        "--policy",
        str(files["policy"]),
        "--post-publish-verification-result",
        str(files["result"]),
        "--post-publish-verification-lock",
        str(files["lock"]),
        "--run-result",
        str(files["run_result"]),
        "--ls6at-publish-execution-result",
        str(files["ls6at_result"]),
        "--ls6at-publish-execution-lock",
        str(files["ls6at_lock"]),
        "--ls6at-validation-result",
        str(files["ls6at_validation"]),
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


def test_55_validation_valid(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_VALIDATED


def test_56_validation_missing_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_57_validation_missing_lock(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["lock"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_58_validation_missing_run_result(monkeypatch, tmp_path: Path) -> None:
    files = make_files(tmp_path)
    files["run_result"].unlink()
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


@pytest.mark.parametrize(
    "keys,value",
    [
        (("status",), "WRONG"),
        (("production_status",), "WRONG"),
        (("post_id",), 999),
        (("rest_returned_post_status",), "draft"),
        (("public_url_reachable",), False),
        (("post_publish_verified",), False),
        (("published_evidence_recorded",), False),
        (("rollback_readiness_recorded",), False),
        (("rollback_executed",), True),
        (("unpublish_executed",), True),
        (("draft_revert_executed",), True),
        (("wordpress_post_executed",), True),
        (("wordpress_write_executed_by_this_phase",), True),
        (("publish_executed_by_this_phase",), True),
        (("post119_update_executed",), True),
        (("credential_value_output",), True),
        (("secret_length_output",), True),
        (("secret_hash_output",), True),
        (("rerun_allowed",), True),
        (("completion_status",), "WRONG"),
        (("start_ls_one_shot_publish_chain_closed",), False),
    ],
)
def test_59_to_79_validation_checks(monkeypatch, tmp_path: Path, keys: tuple[str, ...], value) -> None:
    files = make_files(tmp_path)
    mutate(files["result"], keys, value)
    write_json(files["run_result"], read_json(files["result"]))
    out = run_validate(monkeypatch, files)
    assert out["status"] == STATUS_NOT_VALIDATED


def test_80_source_has_no_requests_post() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/run_start_ls6au_post_publish_verification_published_evidence.py"
    ).read_text(encoding="utf-8")
    assert "requests.post" not in src


def test_81_source_has_no_requests_put() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/run_start_ls6au_post_publish_verification_published_evidence.py"
    ).read_text(encoding="utf-8")
    assert "requests.put" not in src


def test_82_source_has_no_requests_patch() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/run_start_ls6au_post_publish_verification_published_evidence.py"
    ).read_text(encoding="utf-8")
    assert "requests.patch" not in src


def test_83_source_has_no_requests_delete() -> None:
    src = Path(
        "/home/deploy/ai_media_os/scripts/run_start_ls6au_post_publish_verification_published_evidence.py"
    ).read_text(encoding="utf-8")
    assert "requests.delete" not in src


def test_84_source_has_no_base64_usage() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/run_start_ls6au_post_publish_verification_published_evidence.py"
        ).read_text(encoding="utf-8")
        + Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls6au_post_publish_verification_published_evidence.py"
        ).read_text(encoding="utf-8")
    )
    assert "base64" not in merged
    assert "b64encode" not in merged


def test_85_source_has_no_authorization_output() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/run_start_ls6au_post_publish_verification_published_evidence.py"
        ).read_text(encoding="utf-8")
        + Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls6au_post_publish_verification_published_evidence.py"
        ).read_text(encoding="utf-8")
    )
    assert "Authorization:" not in merged


def test_86_source_has_no_basic_output() -> None:
    merged = (
        Path(
            "/home/deploy/ai_media_os/scripts/run_start_ls6au_post_publish_verification_published_evidence.py"
        ).read_text(encoding="utf-8")
        + Path(
            "/home/deploy/ai_media_os/scripts/validate_start_ls6au_post_publish_verification_published_evidence.py"
        ).read_text(encoding="utf-8")
    )
    assert "Basic " not in merged
