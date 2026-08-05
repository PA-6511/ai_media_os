from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CONTRACT_PATH = ROOT / "config/post185_standard_template_contract.json"
POLICY_PATH = ROOT / "config/new_release_batch_operation_policy.json"
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_0_result.json"
REPORT_PATH = ROOT / "reports/ls_new_batch_0_standard_template_contract_report.md"
SCRIPT_PATH = ROOT / "scripts/build_ls_new_batch_0.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_contract_identifies_post_185() -> None:
    contract = load_json(CONTRACT_PATH)

    assert contract["contract_id"] == "POST185_STANDARD_TEMPLATE_V1_FIXED"
    assert contract["template_id"] == "POST185_STANDARD_TEMPLATE_V1"
    assert contract["source_post"]["post_id"] == 185
    assert contract["source_post"]["title"] == "月曜日のたわわ 第15巻"
    assert contract["source_post"]["standardization_completed"] is True


def test_required_store_button_order_is_fixed() -> None:
    contract = load_json(CONTRACT_PATH)

    assert contract["required_components"]["store_button_order"] == [
        "amazon",
        "rakuten_kobo",
        "dmm",
    ]


def test_required_visual_components_are_fixed() -> None:
    contract = load_json(CONTRACT_PATH)
    components = contract["required_components"]

    assert components["rakuten_cover_image"] is True
    assert components["price_card"] is True
    assert components["pr_disclosure"] is True
    assert components["uncategorized_hidden"] is True


def test_contract_blocks_live_execution() -> None:
    contract = load_json(CONTRACT_PATH)
    boundary = contract["execution_boundary"]

    assert boundary["design_only"] is True
    assert boundary["dry_run_only"] is True
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["wordpress_publish_allowed"] is False
    assert boundary["x_post_allowed"] is False
    assert boundary["external_api_call_allowed"] is False


def test_initial_batch_policy_is_three_to_five_drafts() -> None:
    policy = load_json(POLICY_PATH)
    operation = policy["initial_operation"]

    assert operation["minimum_items"] == 3
    assert operation["maximum_items"] == 5
    assert operation["wordpress_default_status"] == "draft"
    assert operation["human_review_required"] is True
    assert operation["individual_publish_required"] is True


def test_batch_policy_blocks_production_execution() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert boundary["batch_execution_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["wordpress_publish_allowed"] is False
    assert boundary["production_status"] == "NO_GO"
    assert boundary["safety_state"] == "DRY_RUN_ONLY"


def test_builder_check_only_passes_without_live_execution() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check-only"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)

    assert result["status"] == "PASS_DESIGN_ONLY_NO_EXECUTION"
    assert result["source_post_id"] == 185
    assert result["wordpress_write_allowed"] is False
    assert result["batch_execution_allowed"] is False
    assert result["ready_for_ls_new_batch_1"] is True


def test_generated_evidence_is_safe_and_complete() -> None:
    assert RESULT_PATH.exists()
    assert REPORT_PATH.exists()

    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert result["status"] == "PASS_DESIGN_ONLY_NO_EXECUTION"
    assert result["template_fixed"] is True
    assert result["production_status"] == "NO_GO"
    assert result["safety_state"] == "DRY_RUN_ONLY"
    assert "POST185_STANDARD_TEMPLATE_V1_FIXED" in report
    assert "WordPress write allowed: `false`" in report
