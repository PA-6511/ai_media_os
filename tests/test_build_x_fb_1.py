from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = ROOT / "config/x_fb_manual_operation_policy.json"
SCHEMA_PATH = ROOT / "config/x_post_wording_feedback_schema.json"
MANAGER_PATH = ROOT / "scripts/manage_x_feedback_record.py"
VALIDATOR_PATH = ROOT / "scripts/build_x_fb_0.py"

RESULT_PATH = ROOT / "exchange/logs/x_fb_1_result.json"
REPORT_PATH = ROOT / "reports/x_fb_1_manual_operation_report.md"

EXAMPLE_PATHS = {
    "INITIALIZE": (
        ROOT
        / "exchange/examples/"
        "x_fb_1_initialize_request.example.json"
    ),
    "REVIEW": (
        ROOT
        / "exchange/examples/"
        "x_fb_1_review_request.example.json"
    ),
    "POST": (
        ROOT
        / "exchange/examples/"
        "x_fb_1_post_request.example.json"
    ),
    "METRICS": (
        ROOT
        / "exchange/examples/"
        "x_fb_1_metrics_request.example.json"
    ),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_policy_identity_and_safety_boundary() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "X-FB-1"
    assert policy["policy_id"] == "X_FB_MANUAL_OPERATION_POLICY_V1"
    assert boundary["x_api_call_allowed"] is False
    assert boundary["x_post_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["external_api_call_allowed"] is False
    assert boundary["automatic_rule_update_allowed"] is False
    assert boundary["production_status"] == "NO_GO"


def test_in_memory_transition_sequence() -> None:
    manager = load_module(MANAGER_PATH, "manager_sequence_test")
    validator = load_module(VALIDATOR_PATH, "validator_sequence_test")
    schema = load_json(SCHEMA_PATH)

    current = None
    stages = []
    versions = []

    for action in ["INITIALIZE", "REVIEW", "POST", "METRICS"]:
        current = manager.apply_request(
            current=current,
            request=load_json(EXAMPLE_PATHS[action]),
            schema=schema,
            validator=validator,
        )
        stages.append(current["record_stage"])
        versions.append(current["record_version"])

    assert stages == [
        "DRAFT_GENERATED",
        "HUMAN_REVIEWED",
        "POSTED",
        "METRICS_RECORDED",
    ]
    assert versions == [1, 2, 3, 4]


def test_review_without_edit_reason_is_rejected() -> None:
    manager = load_module(MANAGER_PATH, "manager_reason_test")
    validator = load_module(VALIDATOR_PATH, "validator_reason_test")
    schema = load_json(SCHEMA_PATH)

    current = manager.apply_request(
        current=None,
        request=load_json(EXAMPLE_PATHS["INITIALIZE"]),
        schema=schema,
        validator=validator,
    )

    request = load_json(EXAMPLE_PATHS["REVIEW"])
    request["edit_reason_labels"] = []

    try:
        manager.apply_request(
            current=current,
            request=request,
            schema=schema,
            validator=validator,
        )
    except validator.ValidationError as exc:
        assert "edit_reason_label" in str(exc)
    else:
        raise AssertionError("missing edit reason was accepted")


def test_post_before_review_is_rejected() -> None:
    manager = load_module(MANAGER_PATH, "manager_stage_test")
    validator = load_module(VALIDATOR_PATH, "validator_stage_test")
    schema = load_json(SCHEMA_PATH)

    current = manager.apply_request(
        current=None,
        request=load_json(EXAMPLE_PATHS["INITIALIZE"]),
        schema=schema,
        validator=validator,
    )

    try:
        manager.apply_request(
            current=current,
            request=load_json(EXAMPLE_PATHS["POST"]),
            schema=schema,
            validator=validator,
        )
    except manager.OperationError as exc:
        assert "HUMAN_REVIEWED" in str(exc)
    else:
        raise AssertionError("POST before REVIEW was accepted")


def prepare_temp_root(tmp_path: Path) -> Path:
    temp_root = tmp_path / "ai_media_os"

    (temp_root / "config").mkdir(parents=True)
    (temp_root / "scripts").mkdir(parents=True)
    (temp_root / "exchange/examples").mkdir(parents=True)

    shutil.copy2(SCHEMA_PATH, temp_root / "config")
    shutil.copy2(POLICY_PATH, temp_root / "config")
    shutil.copy2(VALIDATOR_PATH, temp_root / "scripts")

    for path in EXAMPLE_PATHS.values():
        shutil.copy2(path, temp_root / "exchange/examples")

    return temp_root


def run_manager(
    temp_root: Path,
    request_path: Path,
    *,
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(MANAGER_PATH),
        "--request",
        str(request_path),
    ]

    if dry_run:
        command.append("--dry-run")

    env = dict(os.environ)
    env["AI_MEDIA_OS_ROOT"] = str(temp_root)

    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dry_run_does_not_write_current_record(
    tmp_path: Path,
) -> None:
    temp_root = prepare_temp_root(tmp_path)

    request_path = (
        temp_root
        / "exchange/examples/"
        "x_fb_1_initialize_request.example.json"
    )

    completed = run_manager(
        temp_root,
        request_path,
        dry_run=True,
    )

    assert completed.returncode == 0

    result = json.loads(completed.stdout)

    assert result["status"] == "PASS_DRY_RUN_NO_WRITE"
    assert result["current_record_written"] is False
    assert not (
        temp_root
        / "exchange/input/x_post_feedback/"
        "x-fb-example-20260717-101/current.json"
    ).exists()


def test_versioned_write_and_archive_flow(
    tmp_path: Path,
) -> None:
    temp_root = prepare_temp_root(tmp_path)

    for action in ["INITIALIZE", "REVIEW", "POST", "METRICS"]:
        request_path = (
            temp_root
            / "exchange/examples"
            / EXAMPLE_PATHS[action].name
        )

        completed = run_manager(temp_root, request_path)

        assert completed.returncode == 0, completed.stderr

    feedback_id = "x-fb-example-20260717-101"

    current_path = (
        temp_root
        / "exchange/input/x_post_feedback"
        / feedback_id
        / "current.json"
    )

    current = load_json(current_path)

    assert current["record_version"] == 4
    assert current["record_stage"] == "METRICS_RECORDED"

    for version in [1, 2, 3]:
        archived_path = (
            temp_root
            / "exchange/archive/x_post_feedback"
            / feedback_id
            / f"v{version:03d}.json"
        )
        assert archived_path.exists()

    assert (
        temp_root
        / "exchange/logs"
        / f"x_fb_1_{feedback_id}_v004_result.json"
    ).exists()


def test_duplicate_initialize_is_rejected(
    tmp_path: Path,
) -> None:
    temp_root = prepare_temp_root(tmp_path)

    request_path = (
        temp_root
        / "exchange/examples/"
        "x_fb_1_initialize_request.example.json"
    )

    first = run_manager(temp_root, request_path)
    second = run_manager(temp_root, request_path)

    assert first.returncode == 0
    assert second.returncode == 1
    assert "current record exists" in second.stderr


def test_baseline_evidence_is_complete() -> None:
    assert RESULT_PATH.exists()
    assert REPORT_PATH.exists()

    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_MANUAL_OPERATION_BASELINE_NO_LIVE_POST"
    )
    assert result["verified_version_sequence"] == [1, 2, 3, 4]
    assert result["x_post_allowed"] is False
    assert result["wordpress_write_allowed"] is False
    assert result["ready_for_real_manual_feedback_records"] is True
    assert "Silent overwrite allowed: `false`" in report
