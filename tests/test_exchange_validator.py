import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from exchange_validator import validate_package


def write_temp_json(payload):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    try:
        json.dump(payload, f, ensure_ascii=False)
        f.close()
        return Path(f.name)
    except Exception:
        f.close()
        os.unlink(f.name)
        raise


def validate_temp(package_type, payload):
    path = write_temp_json(payload)
    try:
        return validate_package(package_type, path)
    finally:
        os.unlink(path)


def base_decision_package():
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
        "summary": "safe test package",
    }


def base_test_report():
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
        "tests": {
            "schema_check": "PASS",
            "link_check": "PASS",
            "wp_post": "PASS",
            "secret_access_check": "PASS",
            "dangerous_operation_check": "PASS",
        },
    }


def assert_status(result, expected):
    assert result["status"] == expected, f"Expected {expected}, got {result}"


# ---------------------------------------------------------------------------
# 正常系
# ---------------------------------------------------------------------------


def test_safe_decision_package_does_not_abort():
    """正常な decision_package は ABORT しない"""
    result = validate_temp("decision_package", base_decision_package())
    assert result["status"] in {"PASS", "WARN"}, result


def test_safe_test_report_all_pass_returns_pass():
    """全テスト PASS の test_report は PASS を返す"""
    assert_status(validate_temp("test_report", base_test_report()), "PASS")


# ---------------------------------------------------------------------------
# 危険フラグ true 系 → ABORT
# ---------------------------------------------------------------------------


def test_auto_post_true_aborts():
    payload = {**base_decision_package(), "auto_post": True}
    assert_status(validate_temp("decision_package", payload), "ABORT")


def test_auto_update_true_aborts():
    payload = {**base_decision_package(), "auto_update": True}
    assert_status(validate_temp("decision_package", payload), "ABORT")


def test_auto_delete_true_aborts():
    payload = {**base_decision_package(), "auto_delete": True}
    assert_status(validate_temp("decision_package", payload), "ABORT")


def test_auto_export_true_aborts():
    payload = {**base_decision_package(), "auto_export": True}
    assert_status(validate_temp("decision_package", payload), "ABORT")


def test_human_approval_false_aborts():
    payload = {**base_decision_package(), "human_approval_required": False}
    assert_status(validate_temp("decision_package", payload), "ABORT")


# ---------------------------------------------------------------------------
# LIVE 実行 → ABORT
# ---------------------------------------------------------------------------


def test_execution_live_aborts():
    payload = {**base_decision_package(), "execution": "LIVE"}
    assert_status(validate_temp("decision_package", payload), "ABORT")


def test_execution_production_aborts():
    payload = {**base_decision_package(), "execution": "PRODUCTION"}
    assert_status(validate_temp("decision_package", payload), "ABORT")


# ---------------------------------------------------------------------------
# 必須フィールド欠落 → FAIL
# ---------------------------------------------------------------------------


def test_missing_required_field_fails():
    payload = base_decision_package()
    del payload["risk_level"]
    assert_status(validate_temp("decision_package", payload), "FAIL")


def test_missing_source_field_fails():
    payload = base_decision_package()
    del payload["source"]
    assert_status(validate_temp("decision_package", payload), "FAIL")


# ---------------------------------------------------------------------------
# 禁止キーワード（操作フィールド値） → ABORT
# ---------------------------------------------------------------------------


def test_requested_action_env_aborts():
    payload = {**base_decision_package(), "requested_action": "read .env file"}
    assert_status(validate_temp("decision_package", payload), "ABORT")


def test_description_secrets_aborts():
    payload = {**base_decision_package(), "description": "access secrets for update"}
    assert_status(validate_temp("decision_package", payload), "ABORT")


def test_summary_credentials_aborts():
    payload = {**base_decision_package(), "summary": "load credentials from vault"}
    assert_status(validate_temp("decision_package", payload), "ABORT")


# ---------------------------------------------------------------------------
# 回帰テスト: フィールド名に auto_delete が存在するだけでは ABORT しない
# ---------------------------------------------------------------------------


def test_auto_delete_false_field_name_does_not_abort():
    """auto_delete=false というフィールドが存在するだけでは ABORT しない（回帰）"""
    payload = base_decision_package()
    assert payload["auto_delete"] is False
    result = validate_temp("decision_package", payload)
    assert result["status"] != "ABORT", (
        f"REGRESSION: auto_delete=false should not trigger ABORT, got {result}"
    )


def test_auto_update_false_field_name_does_not_abort():
    """auto_update=false は ABORT しない（回帰）"""
    payload = base_decision_package()
    assert payload["auto_update"] is False
    result = validate_temp("decision_package", payload)
    assert result["status"] != "ABORT", result


# ---------------------------------------------------------------------------
# test_report の WARN / NOT_EXECUTED
# ---------------------------------------------------------------------------


def test_test_report_not_executed_warns():
    payload = {**base_test_report(), "tests": {**base_test_report()["tests"], "wp_post": "NOT_EXECUTED"}}
    assert_status(validate_temp("test_report", payload), "WARN")


def test_test_report_link_check_warn_warns():
    payload = {**base_test_report(), "tests": {**base_test_report()["tests"], "link_check": "WARN"}}
    assert_status(validate_temp("test_report", payload), "WARN")
