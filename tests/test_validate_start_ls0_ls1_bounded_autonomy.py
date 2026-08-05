import json
import subprocess
from pathlib import Path


import json
import subprocess
from pathlib import Path


def test_start_ls_policy_and_charter_json_are_valid():
    json.loads(Path("config/start_ls_route_policy.json").read_text(encoding="utf-8"))
    json.loads(Path("core_ai/config/bounded_autonomy_charter.json").read_text(encoding="utf-8"))


def test_start_ls_policy_preserves_no_go_and_dry_run():
    policy = json.loads(Path("config/start_ls_route_policy.json").read_text(encoding="utf-8"))
    assert policy["route_id"] == "START-LS/SR"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["production_status"] == "NO_GO"
    assert policy["baseline"]["source_status"] == "PHASE8_50B_HARDENING_PASS_DRY_RUN_ONLY"
    assert policy["baseline"]["next_phase_lock"] == "NOT_STARTED_LOCKED"

    flags = policy["safety_flags"]
    assert flags["amazon_api_call_allowed"] is False
    assert flags["wordpress_write_allowed"] is False
    assert flags["x_api_call_allowed"] is False
    assert flags["x_post_allowed"] is False
    assert flags["publish_allowed"] is False
    assert flags["approval_token_consumed"] is False
    assert flags["phase_forward_execution_allowed"] is False


def test_bounded_autonomy_charter_roles_are_fixed():
    charter = json.loads(Path("core_ai/config/bounded_autonomy_charter.json").read_text(encoding="utf-8"))

    assert charter["core_ai_role"]["primary_role"] == "manager_administrator"
    assert charter["core_ai_role"]["not_role"] == "ruler_governor"
    assert "dominate_block_ai_domain_execution" in charter["core_ai_role"]["prohibited_behaviors"]

    assert charter["block_ai_role"]["primary_role"] == "domain_autonomous_operator"
    assert "as freely as possible" in charter["block_ai_role"]["autonomy_principle"]

    assert charter["audit_block_ai_role"]["primary_role"] == "read_only_balance_observer"
    assert charter["audit_block_ai_role"]["improvement_application_requires_human_approval"] is True


def test_validator_passes_and_writes_outputs(tmp_path):
    output = tmp_path / "result.json"
    report = tmp_path / "report.md"

    completed = subprocess.run(
        [
            "python3",
            "scripts/validate_start_ls0_ls1_bounded_autonomy.py",
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "PASS_DESIGN_ONLY_NO_EXECUTION"
    assert result["execution_mode"] == "DRY_RUN_ONLY"
    assert result["production_status"] == "NO_GO"
    assert result["checks"]["core_ai_role"] == "manager_administrator_not_ruler_governor"
    assert result["checks"]["block_ai_autonomy"] == "preserved_within_approved_boundaries"
    assert result["checks"]["audit_block_ai"] == "read_only_balance_observer"
    assert result["checks"]["human_approval_required_for_audit_improvements"] is True
    assert report.exists()
    assert "Core AI is fixed as a manager/administrator" in report.read_text(encoding="utf-8")
    assert "PASS_DESIGN_ONLY_NO_EXECUTION" in completed.stdout
    json.loads(Path("core_ai/config/bounded_autonomy_charter.json").read_text(encoding="utf-8"))
