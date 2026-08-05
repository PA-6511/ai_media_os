import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "core"))

from run_exchange_connection_dry_run import aggregate_status, run_dry_run


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def write_json(payload: dict) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    try:
        json.dump(payload, f, ensure_ascii=False)
        f.close()
        return Path(f.name)
    except Exception:
        f.close()
        os.unlink(f.name)
        raise


def cleanup(*paths: Path) -> None:
    for p in paths:
        if p.exists():
            os.unlink(p)


def base_decision_package() -> dict:
    return {
        "package_type": "decision_package",
        "source": "local_self_builder",
        "target": "ebook_affiliate_block",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "requested_action": "propose_article_template_update",
        "risk_level": "LOW",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "summary": "safe dry-run package",
    }


def base_patch_proposal() -> dict:
    return {
        "package_type": "patch_proposal",
        "source": "local_self_builder",
        "target": "ebook_affiliate_block",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "risk_level": "LOW",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "proposal_id": "dry-run-test-001",
        "title": "dry-run test proposal",
        "description": "safe proposal for testing",
    }


def base_test_report(all_pass: bool = True) -> dict:
    tests = {
        "schema_check": "PASS",
        "link_check": "PASS" if all_pass else "WARN",
        "wp_post": "PASS" if all_pass else "NOT_EXECUTED",
        "secret_access_check": "PASS",
        "dangerous_operation_check": "PASS",
    }
    return {
        "package_type": "test_report",
        "source": "local_self_builder",
        "target": "ebook_affiliate_block",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "risk_level": "LOW",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "tests": tests,
    }


# ---------------------------------------------------------------------------
# aggregate_status 単体テスト
# ---------------------------------------------------------------------------


def test_aggregate_status_abort_wins():
    results = [{"status": "PASS"}, {"status": "WARN"}, {"status": "ABORT"}]
    assert aggregate_status(results) == "ABORT"


def test_aggregate_status_fail_beats_warn():
    results = [{"status": "WARN"}, {"status": "FAIL"}]
    assert aggregate_status(results) == "FAIL"


def test_aggregate_status_warn_beats_pass():
    results = [{"status": "PASS"}, {"status": "WARN"}]
    assert aggregate_status(results) == "WARN"


def test_aggregate_status_all_pass():
    results = [{"status": "PASS"}, {"status": "PASS"}]
    assert aggregate_status(results) == "PASS"


# ---------------------------------------------------------------------------
# run_dry_run: 正常系（PASS または WARN）
# ---------------------------------------------------------------------------


def test_run_dry_run_normal_returns_pass_or_warn():
    p1, p2, p3 = write_json(base_decision_package()), write_json(base_patch_proposal()), write_json(base_test_report(all_pass=True))
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "validation_result.json"
        try:
            result = run_dry_run(
                package_files={"decision_package": p1, "patch_proposal": p2, "test_report": p3},
                output_path=out,
            )
            assert result["overall_status"] in {"PASS", "WARN"}
            assert result["execution"] == "DRY_RUN"
            assert result["auto_post"] is False
        finally:
            cleanup(p1, p2, p3)


def test_run_dry_run_warn_report_gives_warn():
    p1, p2, p3 = write_json(base_decision_package()), write_json(base_patch_proposal()), write_json(base_test_report(all_pass=False))
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "validation_result.json"
        try:
            result = run_dry_run(
                package_files={"decision_package": p1, "patch_proposal": p2, "test_report": p3},
                output_path=out,
            )
            assert result["overall_status"] == "WARN"
        finally:
            cleanup(p1, p2, p3)


# ---------------------------------------------------------------------------
# run_dry_run: validation_result.json の保存内容
# ---------------------------------------------------------------------------


def test_run_dry_run_writes_validation_result():
    p1, p2, p3 = write_json(base_decision_package()), write_json(base_patch_proposal()), write_json(base_test_report())
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "validation_result.json"
        try:
            run_dry_run(
                package_files={"decision_package": p1, "patch_proposal": p2, "test_report": p3},
                output_path=out,
            )
            assert out.exists(), "validation_result.json が生成されていない"
            saved = json.loads(out.read_text(encoding="utf-8"))

            assert saved["execution"] == "DRY_RUN"
            assert saved["auto_post"] is False
            assert saved["auto_update"] is False
            assert saved["auto_delete"] is False
            assert saved["auto_export"] is False
            assert saved["wordpress_write_executed"] is False
            assert saved["slack_notification_executed"] is False
            assert saved["github_actions_triggered"] is False
            assert saved["human_approval_required"] is True
            assert saved["source_builder"]["type"] == "LOCAL_SELF_BUILDER"
            assert saved["source_builder"]["execution_allowed"] is False
        finally:
            cleanup(p1, p2, p3)


def test_run_dry_run_human_review_required_when_warn():
    p1, p2, p3 = write_json(base_decision_package()), write_json(base_patch_proposal()), write_json(base_test_report(all_pass=False))
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "validation_result.json"
        try:
            result = run_dry_run(
                package_files={"decision_package": p1, "patch_proposal": p2, "test_report": p3},
                output_path=out,
            )
            assert result["human_review_required"] is True
        finally:
            cleanup(p1, p2, p3)


# ---------------------------------------------------------------------------
# run_dry_run: ABORT が1件でも混ざると全体 ABORT
# ---------------------------------------------------------------------------


def test_run_dry_run_aborts_when_one_dangerous_package():
    dangerous = {**base_decision_package(), "auto_post": True}
    p1, p2, p3 = write_json(dangerous), write_json(base_patch_proposal()), write_json(base_test_report())
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "validation_result.json"
        try:
            result = run_dry_run(
                package_files={"decision_package": p1, "patch_proposal": p2, "test_report": p3},
                output_path=out,
            )
            assert result["overall_status"] == "ABORT"
            assert result["human_review_required"] is True
            assert result["wordpress_write_executed"] is False
        finally:
            cleanup(p1, p2, p3)


def test_run_dry_run_aborts_on_execution_live():
    dangerous = {**base_decision_package(), "execution": "LIVE"}
    p1, p2, p3 = write_json(dangerous), write_json(base_patch_proposal()), write_json(base_test_report())
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "validation_result.json"
        try:
            result = run_dry_run(
                package_files={"decision_package": p1, "patch_proposal": p2, "test_report": p3},
                output_path=out,
            )
            assert result["overall_status"] == "ABORT"
        finally:
            cleanup(p1, p2, p3)


# ---------------------------------------------------------------------------
# run_dry_run: FAIL が1件でも混ざると全体 FAIL（ABORT なし）
# ---------------------------------------------------------------------------


def test_run_dry_run_fails_when_missing_field():
    broken = base_decision_package()
    del broken["risk_level"]
    p1, p2, p3 = write_json(broken), write_json(base_patch_proposal()), write_json(base_test_report())
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "validation_result.json"
        try:
            result = run_dry_run(
                package_files={"decision_package": p1, "patch_proposal": p2, "test_report": p3},
                output_path=out,
            )
            assert result["overall_status"] == "FAIL"
        finally:
            cleanup(p1, p2, p3)


# ---------------------------------------------------------------------------
# 本番系処理が呼ばれないことを確認
# ---------------------------------------------------------------------------


def test_run_dry_run_never_executes_production_operations():
    p1, p2, p3 = write_json(base_decision_package()), write_json(base_patch_proposal()), write_json(base_test_report())
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "validation_result.json"
        try:
            result = run_dry_run(
                package_files={"decision_package": p1, "patch_proposal": p2, "test_report": p3},
                output_path=out,
            )
            assert result["wordpress_write_executed"] is False
            assert result["slack_notification_executed"] is False
            assert result["github_actions_triggered"] is False
        finally:
            cleanup(p1, p2, p3)
