"""
test_block_template.py — IR5-T4

BlockTemplateSpec / Builder / Validator / Affiliate dry-run のユニットテスト。
"""
import json
from pathlib import Path

import pytest

from generic_block_ai.app.block_template_spec import (
    AFFILIATE_BLOCK_SPEC,
    ALLOWED_CATEGORIES,
    ALLOWED_RISK_LEVELS,
    BlockTemplateSpec,
    _BASE_FORBIDDEN_ACTIONS,
)
from generic_block_ai.app.block_template_builder import (
    BUILDER_SCHEMA_VERSION,
    build_block_skeleton,
    write_block_skeleton_dryrun,
)
from generic_block_ai.app.block_skeleton_validator import (
    REQUIRED_FILE_PATHS,
    validate_block_skeleton,
)


# ─── IR5-T1: BlockTemplateSpec ─────────────────────────────────────────────────

def test_affiliate_spec_validate_no_errors() -> None:
    errors = AFFILIATE_BLOCK_SPEC.validate()
    assert errors == []


def test_affiliate_spec_forbidden_actions_include_base() -> None:
    for action in _BASE_FORBIDDEN_ACTIONS:
        assert action in AFFILIATE_BLOCK_SPEC.forbidden_actions


def test_affiliate_spec_extra_forbidden_merged() -> None:
    for action in AFFILIATE_BLOCK_SPEC.extra_forbidden_actions:
        assert action in AFFILIATE_BLOCK_SPEC.forbidden_actions


def test_spec_validation_rejects_bad_category() -> None:
    bad = BlockTemplateSpec(
        block_id="x",
        display_name="X",
        version="0.1.0",
        category="unknown_cat",
        risk_level="low",
        capabilities={"analyze": True},
    )
    errors = bad.validate()
    assert any("category" in e for e in errors)


def test_spec_validation_rejects_bad_risk_level() -> None:
    bad = BlockTemplateSpec(
        block_id="x",
        display_name="X",
        version="0.1.0",
        category="affiliate",
        risk_level="ultra_high",
        capabilities={"analyze": True},
    )
    errors = bad.validate()
    assert any("risk_level" in e for e in errors)


# ─── IR5-T2: build_block_skeleton ──────────────────────────────────────────────

def test_build_skeleton_meta_ok() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    assert skeleton["_meta"]["status"] == "OK"
    assert skeleton["_meta"]["schema_version"] == BUILDER_SCHEMA_VERSION
    assert skeleton["_meta"]["block_id"] == "affiliate_block"


def test_build_skeleton_has_required_files() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    paths = {f["path"] for f in skeleton["files"]}
    for req in REQUIRED_FILE_PATHS:
        assert req in paths, f"Missing required file: {req}"


def test_build_skeleton_safeguards_are_safe() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    sg = skeleton["safeguards"]
    assert sg["external_write_executed"] is False
    assert sg["actual_auto_execute"] is False
    assert sg["mode"] == "dry_run"
    assert sg["operation_mode"] == "OBSERVE"


def test_build_skeleton_manifest_json_parseable() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    manifest_file = next(f for f in skeleton["files"] if f["path"] == "block_manifest.json")
    data = json.loads(manifest_file["content"])
    assert data["block_id"] == "affiliate_block"
    assert data["mode"] == "dry_run"
    assert data["approval_policy"]["requires_human_approval"] is True
    assert data["affiliate_safety"]["require_disclosure"] is True
    assert data["affiliate_safety"]["allow_external_checkout"] is False


def test_build_skeleton_includes_runner_and_runner_tests() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    paths = {f["path"] for f in skeleton["files"]}
    assert "app/schemas.py" in paths
    assert "app/runner.py" in paths
    assert "tests/test_schemas.py" in paths
    assert "tests/test_runner.py" in paths


def test_build_skeleton_policy_has_affiliate_guardrails() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    policy_file = next(f for f in skeleton["files"] if f["path"] == "config/policy.json")
    policy = json.loads(policy_file["content"])
    guardrails = policy["affiliate_guardrails"]
    assert guardrails["allow_external_checkout"] is False
    assert guardrails["allow_pii_storage"] is False
    assert guardrails["allow_direct_purchase"] is False
    assert guardrails["require_manual_review_before_publish"] is True


def test_build_skeleton_error_on_invalid_spec() -> None:
    bad = BlockTemplateSpec(
        block_id="",
        display_name="",
        version="0.1.0",
        category="affiliate",
        risk_level="low",
        capabilities={},
    )
    skeleton = build_block_skeleton(bad)
    assert skeleton["_meta"]["status"] == "ERROR"
    assert len(skeleton["_meta"]["errors"]) > 0
    assert skeleton["files"] == []


# ─── IR5-T3: validate_block_skeleton ───────────────────────────────────────────

def test_validate_skeleton_passes_for_affiliate() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    result = validate_block_skeleton(skeleton)
    assert result.result == "PASS", f"FAIL checks: {result.failed_checks}"


def test_validate_skeleton_fails_on_wrong_mode() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    for f in skeleton["files"]:
        if f["path"] == "block_manifest.json":
            data = json.loads(f["content"])
            data["mode"] = "live"
            f["content"] = json.dumps(data)
            break
    result = validate_block_skeleton(skeleton)
    assert result.result == "FAIL"
    assert any("mode" in c for c in result.failed_checks)


def test_validate_skeleton_fails_if_file_missing() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    skeleton["files"] = [f for f in skeleton["files"] if f["path"] != "config/policy.json"]
    result = validate_block_skeleton(skeleton)
    assert result.result == "FAIL"
    assert any("config/policy.json" in c for c in result.failed_checks)


def test_validate_skeleton_fails_if_safeguard_broken() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    skeleton["safeguards"]["external_write_executed"] = True
    result = validate_block_skeleton(skeleton)
    assert result.result == "FAIL"
    assert any("external_write_executed" in c for c in result.failed_checks)


def test_validate_skeleton_fails_if_affiliate_disclosure_missing() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    for f in skeleton["files"]:
        if f["path"] == "block_manifest.json":
            data = json.loads(f["content"])
            data["affiliate_safety"]["disclosure_text"] = ""
            f["content"] = json.dumps(data)
            break
    result = validate_block_skeleton(skeleton)
    assert result.result == "FAIL"
    assert any("disclosure_text" in c for c in result.failed_checks)


def test_validate_skeleton_fails_if_affiliate_guardrails_missing() -> None:
    skeleton = build_block_skeleton(AFFILIATE_BLOCK_SPEC)
    for f in skeleton["files"]:
        if f["path"] == "config/policy.json":
            data = json.loads(f["content"])
            data.pop("affiliate_guardrails", None)
            f["content"] = json.dumps(data)
            break
    result = validate_block_skeleton(skeleton)
    assert result.result == "FAIL"
    assert any("affiliate_guardrails" in c for c in result.failed_checks)


# ─── IR5-T4: Affiliate Block Skeleton Dry-run (disk write) ──────────────────────

def test_write_affiliate_skeleton_dryrun(tmp_path: Path) -> None:
    skeleton = write_block_skeleton_dryrun(AFFILIATE_BLOCK_SPEC, base_path=tmp_path)
    assert skeleton["_meta"]["status"] == "OK"
    output_dir = tmp_path / "reports" / "generated_skeleton_affiliate_block"
    assert output_dir.exists()
    manifest_path = output_dir / "block_manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["block_id"] == "affiliate_block"


def test_write_affiliate_skeleton_dryrun_creates_summary(tmp_path: Path) -> None:
    skeleton = write_block_skeleton_dryrun(AFFILIATE_BLOCK_SPEC, base_path=tmp_path)
    summary_path = Path(skeleton["summary_path"])
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["safeguards"]["external_write_executed"] is False


def test_write_affiliate_skeleton_validates_as_pass(tmp_path: Path) -> None:
    skeleton = write_block_skeleton_dryrun(AFFILIATE_BLOCK_SPEC, base_path=tmp_path)
    # 再構築した skeleton を validator に渡す（disk を読み直さない）
    result = validate_block_skeleton(skeleton)
    assert result.result == "PASS", f"FAIL checks: {result.failed_checks}"


def test_generated_runner_executes_minimal_dryrun(tmp_path: Path) -> None:
    write_block_skeleton_dryrun(AFFILIATE_BLOCK_SPEC, base_path=tmp_path)
    runner_path = tmp_path / "reports" / "generated_skeleton_affiliate_block" / "app" / "runner.py"
    namespace: dict[str, object] = {}
    exec(runner_path.read_text(encoding="utf-8"), namespace)
    run_fn = namespace["run_affiliate_block_dryrun"]
    result = run_fn(
        {
            "records": [
                {
                    "source": "official_api",
                    "title": "Generated Item A",
                    "asin": "B0RTEST001",
                    "url": "https://example.com/a",
                    "campaign_type": "seasonal",
                    "risk_flags": [],
                },
                {
                    "source": "approved_feed",
                    "title": "Generated Item B",
                    "asin": "B0RTEST002",
                    "url": "https://example.com/b",
                    "campaign_type": "standard",
                    "risk_flags": ["price_volatility"],
                },
            ]
        }
    )
    assert result["status"] == "success"
    assert result["decision"] == "human_review"
    assert result["mode"] == "dry_run"
    assert result["operation_mode"] == "OBSERVE"
    assert result["input_schema"]["version"] == "affiliate_input_v1"
    assert result["output_schema"]["version"] == "affiliate_candidate_v1"
    assert len(result["recommended_candidates"]) == 2
    assert len(result["affiliate_candidates"]) == 2
    assert "article_candidate" in result["affiliate_candidates"][0]
