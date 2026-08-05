from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts/pr_warn_backfill_phase1j_live_write_runner.py"
    spec = importlib.util.spec_from_file_location("phase1j_live_write_runner", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load phase1j live write runner module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_approval(**overrides):
    data = {
        "approved": True,
        "wordpress_write_allowed": True,
        "target_post_id": 101,
        "max_live_updates": 1,
    }
    data.update(overrides)
    return data


def _base_final_live_approval_example(**overrides):
    data = {
        "phase": "PR_WARN_BACKFILL_PHASE1I_FINAL_LIVE_APPROVAL",
        "approved": False,
        "wordpress_live_write_allowed": False,
        "target_post_id": 101,
        "max_live_updates": 1,
        "allowed_changed_fields": ["content"],
    }
    data.update(overrides)
    return data


def _base_snapshot(**overrides):
    data = {
        "target_post_id": 101,
        "fetched_post_id": 101,
        "title": "target title",
        "status_from_wp": "draft",
        "modified": "2026-05-01T14:14:24",
        "content_hash": "abc123",
        "content_length": 123,
    }
    data.update(overrides)
    return data


def _base_snapshot_result(**overrides):
    data = {"status": "PASS_READONLY_SNAPSHOT"}
    data.update(overrides)
    return data


def _base_phase1f_dry_run(**overrides):
    data = {
        "status": "PASS_DRY_RUN_FIRST_ONLY",
        "target_post_id": 101,
        "wordpress_write_executed": False,
        "update_count": 0,
        "proposed_changed_fields": ["content"],
    }
    data.update(overrides)
    return data


def _run(
    tmp_path: Path,
    *,
    post_id=101,
    mode="DRY_RUN",
    approval=None,
    final_live_approval_example=None,
    snapshot=None,
    snapshot_result=None,
    phase1f_dry_run=None,
    remove_approval=False,
    remove_snapshot=False,
):
    module = _load_module()

    approval_path = tmp_path / "approval.json"
    final_live_approval_path = tmp_path / "final_live_approval.example.json"
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_result_path = tmp_path / "snapshot_result.json"
    phase1f_dry_run_path = tmp_path / "phase1f_dry_run.json"
    output_path = tmp_path / "out.json"

    _write_json(approval_path, approval or _base_approval())
    _write_json(final_live_approval_path, final_live_approval_example or _base_final_live_approval_example())
    _write_json(snapshot_path, snapshot or _base_snapshot())
    _write_json(snapshot_result_path, snapshot_result or _base_snapshot_result())
    _write_json(phase1f_dry_run_path, phase1f_dry_run or _base_phase1f_dry_run())

    if remove_approval:
        approval_path.unlink()
    if remove_snapshot:
        snapshot_path.unlink()

    return module.run(
        post_id=post_id,
        mode=mode,
        approval_path=approval_path,
        final_live_approval_path=final_live_approval_path,
        snapshot_path=snapshot_path,
        snapshot_result_path=snapshot_result_path,
        phase1f_dry_run_path=phase1f_dry_run_path,
        result_output_path=output_path,
    )


def test_pass_dry_run_only(tmp_path: Path):
    result = _run(tmp_path)
    assert result["status"] == "PASS_LIVE_WRITE_RUNNER_DRY_RUN_ONLY"
    assert result["mode"] == "DRY_RUN"
    assert result["target_post_id"] == 101
    assert result["dedicated_live_write_runner_created"] is True
    assert result["existing_runners_modified"] is False
    assert result["final_live_approval_example_only"] is True
    assert result["final_live_approval_approved"] is False
    assert result["final_live_write_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["live_execution_executed"] is False
    assert result["update_count"] == 0


def test_abort_when_post_id_not_101(tmp_path: Path):
    result = _run(tmp_path, post_id=999)
    assert result["status"] == "ABORT_INVALID_TARGET_POST_ID"


def test_abort_when_mode_not_dry_run(tmp_path: Path):
    result = _run(tmp_path, mode="LIVE")
    assert result["status"] == "ABORT_MODE_NOT_ALLOWED"


def test_abort_when_approval_missing(tmp_path: Path):
    result = _run(tmp_path, remove_approval=True)
    assert result["status"] == "ABORT_MISSING_APPROVAL_FILE"


def test_abort_when_approval_approved_false(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(approved=False))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_approval_write_not_allowed(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(wordpress_write_allowed=False))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_approval_target_mismatch(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(target_post_id=102))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_approval_max_live_updates_not_one(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(max_live_updates=2))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_final_live_approval_example_has_approved_true(tmp_path: Path):
    result = _run(tmp_path, final_live_approval_example=_base_final_live_approval_example(approved=True))
    assert result["status"] == "ABORT_FINAL_LIVE_APPROVAL_EXAMPLE_INVALID"


def test_abort_when_final_live_approval_example_has_write_allowed_true(tmp_path: Path):
    result = _run(
        tmp_path,
        final_live_approval_example=_base_final_live_approval_example(wordpress_live_write_allowed=True),
    )
    assert result["status"] == "ABORT_FINAL_LIVE_APPROVAL_EXAMPLE_INVALID"


def test_abort_when_snapshot_missing(tmp_path: Path):
    result = _run(tmp_path, remove_snapshot=True)
    assert result["status"] == "ABORT_MISSING_SNAPSHOT_FILE"


def test_abort_when_snapshot_fetched_post_id_mismatch(tmp_path: Path):
    result = _run(tmp_path, snapshot=_base_snapshot(fetched_post_id=102))
    assert result["status"] == "ABORT_SNAPSHOT_VALIDATION_FAILED"


def test_abort_when_snapshot_result_not_pass(tmp_path: Path):
    result = _run(tmp_path, snapshot_result=_base_snapshot_result(status="NOT_PASS"))
    assert result["status"] == "ABORT_SNAPSHOT_RESULT_VALIDATION_FAILED"


def test_abort_when_phase1f_content_scope_invalid(tmp_path: Path):
    result = _run(tmp_path, phase1f_dry_run=_base_phase1f_dry_run(proposed_changed_fields=["content", "title"]))
    assert result["status"] == "ABORT_PHASE1F_DRY_RUN_VALIDATION_FAILED"


def test_source_has_no_requests_write_calls():
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts/pr_warn_backfill_phase1j_live_write_runner.py").read_text(encoding="utf-8")
    forbidden = ["requests.post", "requests.put", "requests.patch", "requests.delete", "wp-json/wp/v2/posts"]
    for token in forbidden:
        assert token not in source
