from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts/pr_warn_backfill_phase1f_live_route_runner.py"
    spec = importlib.util.spec_from_file_location("phase1f_live_route_runner", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load phase1f live-route runner module")
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


def _base_phase0_target(diff_preview=None, **overrides):
    if diff_preview is None:
        diff_preview = [
            "--- original",
            "+++ backfill_candidate",
            "@@ -1,4 +1,4 @@",
            "-<h1>呪術廻戦は何巻まで出てる？最新巻・関連情報まとめ</h1>",
            "+<h1>呪術廻戦は何巻まで出てる？最新巻・関連情報まとめ</h1><p class=\"pr-notice\">※本記事にはアフィリエイト広告（PR）が含まれます。</p>",
            " <h2>結論</h2><p>本文</p>",
        ]
    data = {
        "post_id": 101,
        "title": "呪術廻戦は何巻まで出てる？最新巻・関連情報まとめ",
        "dry_run_strategy": "insert_after_h1",
        "diff_preview": diff_preview,
    }
    data.update(overrides)
    return data


def _base_phase0(targets=None):
    if targets is None:
        targets = [_base_phase0_target()]
    return {"targets": targets}


def _base_phase1d_dry(**overrides):
    data = {
        "status": "PASS_DRY_RUN_ONLY",
        "target_post_id": 101,
        "wordpress_write_executed": False,
        "proposed_changed_fields": ["content"],
    }
    data.update(overrides)
    return data


def _base_phase1f_abort(**overrides):
    data = {
        "status": "ABORT_LIVE_ROUTE_NOT_AVAILABLE",
        "target_post_id": 101,
        "wordpress_write_executed": False,
    }
    data.update(overrides)
    return data


def _run(
    tmp_path: Path,
    *,
    post_id=101,
    mode="DRY_RUN",
    approval=None,
    phase0=None,
    phase1d_dry=None,
    phase1f_abort=None,
):
    module = _load_module()

    approval_path = tmp_path / "approval.json"
    phase0_path = tmp_path / "phase0.json"
    phase1d_dry_path = tmp_path / "phase1d_dry.json"
    phase1f_abort_path = tmp_path / "phase1f_abort.json"
    output_path = tmp_path / "out.json"

    _write_json(approval_path, approval or _base_approval())
    _write_json(phase0_path, phase0 or _base_phase0())
    _write_json(phase1d_dry_path, phase1d_dry or _base_phase1d_dry())
    _write_json(phase1f_abort_path, phase1f_abort or _base_phase1f_abort())

    return module.run(
        post_id=post_id,
        mode=mode,
        approval_path=approval_path,
        phase0_path=phase0_path,
        phase1d_dry_run_path=phase1d_dry_path,
        phase1f_abort_path=phase1f_abort_path,
        output_path=output_path,
    )


def test_pass_dry_run_first_only(tmp_path: Path):
    result = _run(tmp_path)
    assert result["status"] == "PASS_DRY_RUN_FIRST_ONLY"
    assert result["wordpress_write_executed"] is False
    assert result["update_count"] == 0
    assert result["live_mode_enabled"] is False
    assert result["proposed_changed_fields"] == ["content"]


def test_abort_when_post_id_not_101(tmp_path: Path):
    result = _run(tmp_path, post_id=999)
    assert result["status"] == "ABORT_INVALID_TARGET_POST_ID"


def test_abort_when_approved_false(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(approved=False))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_wordpress_write_allowed_false(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(wordpress_write_allowed=False))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_target_post_id_not_101(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(target_post_id=102))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_max_live_updates_not_1(tmp_path: Path):
    result = _run(tmp_path, approval=_base_approval(max_live_updates=2))
    assert result["status"] == "ABORT_APPROVAL_VALIDATION_FAILED"


def test_abort_when_phase0_target_missing(tmp_path: Path):
    result = _run(tmp_path, phase0={"targets": []})
    assert result["status"] == "ABORT_PHASE0_TARGET_NOT_FOUND"


def test_abort_when_phase0_diff_invalid(tmp_path: Path):
    bad_diff = [
        "--- original",
        "+++ backfill_candidate",
        "@@ -1,4 +1,4 @@",
        "-<h1>old</h1>",
        "+<h1>new</h1><p class=\"pr-notice\">※本記事にはアフィリエイト広告（PR）が含まれます。</p>",
        "-<p>a</p>",
        "+<p>b</p>",
    ]
    target = _base_phase0_target(diff_preview=bad_diff)
    result = _run(tmp_path, phase0=_base_phase0([target]))
    assert result["status"] == "ABORT_PHASE0_DIFF_SCOPE_VIOLATION"


def test_abort_when_phase1d_dry_run_invalid(tmp_path: Path):
    result = _run(tmp_path, phase1d_dry=_base_phase1d_dry(proposed_changed_fields=["content", "title"]))
    assert result["status"] == "ABORT_PHASE1D_DRY_RUN_VALIDATION_FAILED"


def test_abort_when_live_mode_requested(tmp_path: Path):
    result = _run(tmp_path, mode="LIVE")
    assert result["status"] == "ABORT_LIVE_NOT_ENABLED_IN_LIVE_ROUTE_PHASE"
    assert result["wordpress_write_executed"] is False
    assert result["update_count"] == 0
