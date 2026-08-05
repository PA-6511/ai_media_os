from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts/pr_warn_backfill_phase1g_readonly_snapshot.py"
    spec = importlib.util.spec_from_file_location("phase1g_readonly_snapshot", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load phase1g readonly snapshot module")
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


def _env_ready():
    return {
        "WORDPRESS_BASE_URL": "https://example.com",
        "WORDPRESS_USERNAME": "user",
        "WORDPRESS_APP_PASSWORD": "pass",
    }


def _ok_get(**kwargs):
    class Resp:
        status_code = 200

        def json(self):
            return {
                "id": 101,
                "title": {"rendered": "title"},
                "content": {"raw": "<h1>x</h1>body"},
                "status": "draft",
                "link": "https://example.com/?p=101",
                "slug": "slug-101",
                "modified_gmt": "2026-06-20T00:00:00",
                "categories": [1],
                "tags": [2],
                "featured_media": 3,
            }

    return Resp()


def _run(
    tmp_path: Path,
    *,
    post_id=101,
    mode="READ_ONLY_GET",
    approval=None,
    env=None,
    get_func=None,
):
    module = _load_module()
    approval_path = tmp_path / "approval.json"
    snapshot_output = tmp_path / "snapshot.json"
    result_output = tmp_path / "result.json"

    _write_json(approval_path, approval or _base_approval())

    return module.run(
        post_id=post_id,
        mode=mode,
        approval_path=approval_path,
        snapshot_output=snapshot_output,
        result_output=result_output,
        env=env or _env_ready(),
        get_func=get_func or _ok_get,
    )


def test_pass_readonly_snapshot(tmp_path: Path):
    result = _run(tmp_path)
    assert result["status"] == "PASS_READONLY_SNAPSHOT"
    assert result["wordpress_read_executed"] is True
    assert result["wordpress_write_executed"] is False
    assert result["update_count"] == 0
    snapshot = json.loads(Path(result["snapshot_output"]).read_text(encoding="utf-8"))
    assert snapshot["fetched_post_id"] == 101
    assert snapshot["content_length"] > 0
    assert snapshot["content_hash"]


def test_abort_when_post_id_not_101(tmp_path: Path):
    result = _run(tmp_path, post_id=102)
    assert result["status"] == "ABORT_INVALID_TARGET_POST_ID"


def test_abort_when_mode_invalid(tmp_path: Path):
    result = _run(tmp_path, mode="DRY_RUN")
    assert result["status"] == "ABORT_UNSUPPORTED_MODE"


def test_abort_when_approved_false(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(approved=False))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_write_allowed_false(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(wordpress_write_allowed=False))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_target_post_id_mismatch(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(target_post_id=999))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_max_live_updates_not_1(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(max_live_updates=2))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_env_missing(tmp_path: Path):
    result = _run(tmp_path, env={"WORDPRESS_BASE_URL": "x"})
    assert result["status"] == "ABORT_MISSING_WORDPRESS_ENV"


def test_abort_when_get_fails_status_code(tmp_path: Path):
    def bad_get(**kwargs):
        class Resp:
            status_code = 401

            def json(self):
                return {}

        return Resp()

    result = _run(tmp_path, get_func=bad_get)
    assert result["status"] == "ABORT_WORDPRESS_GET_FAILED"


def test_abort_when_fetched_post_id_mismatch(tmp_path: Path):
    def wrong_id_get(**kwargs):
        class Resp:
            status_code = 200

            def json(self):
                return {"id": 102}

        return Resp()

    result = _run(tmp_path, get_func=wrong_id_get)
    assert result["status"] == "ABORT_FETCHED_POST_ID_MISMATCH"


def test_no_write_methods_in_source(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    src = (root / "scripts/pr_warn_backfill_phase1g_readonly_snapshot.py").read_text(encoding="utf-8")
    assert "requests.post" not in src
    assert "requests.put" not in src
    assert "requests.patch" not in src
    assert "requests.delete" not in src
