from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts/pr_warn_backfill_phase1n_pre_live_resnapshot.py"
    spec = importlib.util.spec_from_file_location("phase1n_pre_live_resnapshot", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load phase1n pre-live resnapshot module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _env_ready():
    return {
        "WORDPRESS_BASE_URL": "https://example.com",
        "WORDPRESS_USERNAME": "user",
        "WORDPRESS_APP_PASSWORD": "pass",
    }


def _base_policy(**overrides):
    data = {
        "status": "PASS_FINAL_APPROVAL_AND_RESNAPSHOT_POLICY_REPORTS_ONLY",
        "mode": "REPORTS_ONLY",
        "target_post_id": 101,
    }
    data.update(overrides)
    return data


def _base_template(**overrides):
    data = {
        "template_only": True,
        "approved": False,
        "wordpress_live_write_allowed": False,
        "target_post_id": 101,
        "max_live_updates": 1,
        "allowed_changed_fields": ["content"],
    }
    data.update(overrides)
    return data


def _base_rollback_snapshot(**overrides):
    data = {
        "fetched_post_id": 101,
        "status_from_wp": "draft",
        "modified": "2026-05-01T14:14:24",
        "content_hash": "hash-same",
    }
    data.update(overrides)
    return data


def _base_rollback_snapshot_result(**overrides):
    data = {"status": "PASS_READONLY_SNAPSHOT"}
    data.update(overrides)
    return data


def _base_phase1l_payload(**overrides):
    data = {
        "payload_changed_fields": ["content"],
        "wordpress_write_executed": False,
        "live_execution_executed": False,
    }
    data.update(overrides)
    return data


def _make_get(id_val=101, status="draft", modified="2026-05-01T14:14:24", content="same-content"):
    class Resp:
        status_code = 200

        def json(self):
            return {
                "id": id_val,
                "title": {"rendered": "title"},
                "content": {"raw": content},
                "status": status,
                "link": "https://example.com/?p=101",
                "slug": "slug-101",
                "modified_gmt": modified,
                "categories": [1],
                "tags": [2],
                "featured_media": 3,
            }

    return lambda **kwargs: Resp()


def _run(
    tmp_path: Path,
    *,
    post_id=101,
    mode="READ_ONLY_GET",
    policy=None,
    template=None,
    rollback_snapshot=None,
    rollback_snapshot_result=None,
    phase1l_payload=None,
    get_func=None,
    env=None,
    remove_rollback_snapshot=False,
):
    module = _load_module()

    policy_path = tmp_path / "policy.json"
    template_path = tmp_path / "template.json"
    rollback_snapshot_path = tmp_path / "rollback_snapshot.json"
    rollback_snapshot_result_path = tmp_path / "rollback_snapshot_result.json"
    phase1l_payload_path = tmp_path / "phase1l_payload.json"
    snapshot_output = tmp_path / "snapshot_output.json"
    result_output = tmp_path / "result_output.json"

    rb = rollback_snapshot or _base_rollback_snapshot(content_hash=module._sha256_text("same-content"))

    _write_json(policy_path, policy or _base_policy())
    _write_json(template_path, template or _base_template())
    _write_json(rollback_snapshot_path, rb)
    _write_json(rollback_snapshot_result_path, rollback_snapshot_result or _base_rollback_snapshot_result())
    _write_json(phase1l_payload_path, phase1l_payload or _base_phase1l_payload())

    if remove_rollback_snapshot:
        rollback_snapshot_path.unlink()

    return module.run(
        post_id=post_id,
        mode=mode,
        policy_log_path=policy_path,
        template_path=template_path,
        rollback_snapshot_path=rollback_snapshot_path,
        rollback_snapshot_result_path=rollback_snapshot_result_path,
        phase1l_payload_log_path=phase1l_payload_path,
        snapshot_output=snapshot_output,
        result_output=result_output,
        env=env or _env_ready(),
        get_func=get_func or _make_get(),
    )


def test_pass_pre_live_resnapshot(tmp_path: Path):
    result = _run(tmp_path)
    assert result["status"] == "PASS_PRE_LIVE_RESNAPSHOT"
    assert result["wordpress_read_executed"] is True
    assert result["wordpress_write_executed"] is False
    assert result["live_execution_executed"] is False
    assert result["update_count"] == 0

    snapshot = json.loads(Path(result["snapshot_output"]).read_text(encoding="utf-8"))
    assert snapshot["fetched_post_id"] == 101
    assert snapshot["status_from_wp"] == "draft"
    assert snapshot["modified_matches_rollback_snapshot"] is True
    assert snapshot["content_hash_matches_rollback_snapshot"] is True


def test_abort_post_id_mismatch(tmp_path: Path):
    result = _run(tmp_path, post_id=999)
    assert result["status"] == "ABORT_INVALID_TARGET_POST_ID"


def test_abort_mode_mismatch(tmp_path: Path):
    result = _run(tmp_path, mode="DRY_RUN")
    assert result["status"] == "ABORT_UNSUPPORTED_MODE"


def test_abort_template_approved_true(tmp_path: Path):
    result = _run(tmp_path, template=_base_template(approved=True))
    assert result["status"] == "ABORT_TEMPLATE_VALIDATION_FAILED"


def test_abort_template_write_allowed_true(tmp_path: Path):
    result = _run(tmp_path, template=_base_template(wordpress_live_write_allowed=True))
    assert result["status"] == "ABORT_TEMPLATE_VALIDATION_FAILED"


def test_abort_rollback_snapshot_missing(tmp_path: Path):
    result = _run(tmp_path, remove_rollback_snapshot=True)
    assert result["status"] == "ABORT_MISSING_ROLLBACK_SNAPSHOT"


def test_abort_phase1l_payload_scope_invalid(tmp_path: Path):
    result = _run(tmp_path, phase1l_payload=_base_phase1l_payload(payload_changed_fields=["content", "title"]))
    assert result["status"] == "ABORT_PHASE1L_PAYLOAD_SCOPE_INVALID"


def test_abort_fetched_post_id_mismatch(tmp_path: Path):
    result = _run(tmp_path, get_func=_make_get(id_val=999))
    assert result["status"] == "ABORT_FETCHED_POST_ID_MISMATCH"


def test_abort_status_not_draft(tmp_path: Path):
    result = _run(tmp_path, get_func=_make_get(status="publish"))
    assert result["status"] == "ABORT_FETCHED_STATUS_NOT_DRAFT"


def test_abort_modified_diff(tmp_path: Path):
    result = _run(tmp_path, get_func=_make_get(modified="2026-05-01T14:14:25"))
    assert result["status"] == "ABORT_PRE_LIVE_RESNAPSHOT_MODIFIED_DIFF"


def test_abort_content_hash_diff(tmp_path: Path):
    result = _run(tmp_path, get_func=_make_get(content="different-content"))
    assert result["status"] == "ABORT_PRE_LIVE_RESNAPSHOT_CONTENT_HASH_DIFF"


def test_abort_wordpress_get_failed(tmp_path: Path):
    class Resp:
        status_code = 500

        def json(self):
            return {}

    result = _run(tmp_path, get_func=lambda **kwargs: Resp())
    assert result["status"] == "ABORT_WORDPRESS_GET_FAILED"


def test_no_write_methods_in_source():
    root = Path(__file__).resolve().parents[1]
    src = (root / "scripts/pr_warn_backfill_phase1n_pre_live_resnapshot.py").read_text(encoding="utf-8")
    assert "requests.post" not in src
    assert "requests.put" not in src
    assert "requests.patch" not in src
    assert "requests.delete" not in src
