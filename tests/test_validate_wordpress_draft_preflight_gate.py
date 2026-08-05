import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_preflight_gate import validate_preflight_gate, run_validation


def _write(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_gate(tmp_root: Path) -> dict:
    return {
        "phase": "Phase 6-2",
        "gate_name": "wordpress_draft_preflight_gate_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "gate_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "required_inputs": {
            "phase5_overall_report": "a/phase5.json",
            "phase6_1_design_validation": "a/phase6_1.json",
            "draft_candidate_quality_validation": "a/quality.json",
            "draft_candidate_review_result": "a/review.json"
        },
        "preflight_rules": {
            "allowed_phase5_completion_status": ["PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY_WITH_WARN"],
            "require_phase6_1_policy_status": "DESIGN_ONLY",
            "require_phase6_1_production_status": "NO_GO",
            "allowed_quality_status": ["PASS", "WARN"],
            "allow_warn_only_when_human_review_required": True,
            "post_count_limit": 1,
            "post_status": "draft",
            "publish_forbidden": True,
            "update_forbidden": True,
            "delete_forbidden": True,
            "export_forbidden": True,
            "env_secret_auto_edit_forbidden": True,
            "wordpress_rest_execute_must_be_false": True,
            "github_actions_trigger_must_be_false": True,
            "slack_production_notification_must_be_false": True,
            "vps_self_builder_execution_must_be_false": True
        },
        "decision_extension": {
            "current_allowed": ["APPROVE_DRY_RUN_ONLY"],
            "reserved_future": {
                "token": "APPROVE_DRAFT_CREATE_ONLY",
                "allowed": False,
                "note": "reserved"
            }
        },
        "forbidden_actions": [
            "wordpress_rest_post",
            "wordpress_rest_put_patch",
            "publish_post",
            "update_existing_post",
            "delete_post",
            "bulk_posting",
            "external_export",
            "github_actions_trigger",
            "slack_production_notification",
            "cron_automation",
            "env_secret_auto_edit",
            "vps_self_builder_execution"
        ]
    }


def base_sources() -> dict:
    return {
        "phase5_overall_report": {
            "completion_status": "PASS_DRY_RUN_ONLY_WITH_WARN",
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_write_executed": False,
            "slack_notification_executed": False,
            "github_actions_triggered": False,
        },
        "phase6_1_design_validation": {
            "policy_status": "DESIGN_ONLY",
            "production_status": "NO_GO",
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_write_executed": False,
            "slack_notification_executed": False,
            "github_actions_triggered": False,
        },
        "draft_candidate_quality_validation": {
            "status": "WARN",
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_write_executed": False,
            "slack_notification_executed": False,
            "github_actions_triggered": False,
        },
        "draft_candidate_review_result": {
            "decision": "APPROVE_DRY_RUN_ONLY",
            "status": "PASS",
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_write_executed": False,
            "slack_notification_executed": False,
            "github_actions_triggered": False,
        },
    }


def test_validate_preflight_gate_passes():
    gate = base_gate(Path("."))
    result = validate_preflight_gate(gate, base_sources())
    assert result["status"] == "PASS"
    assert result["production_status"] == "NO_GO"


def test_reserved_future_allowed_true_aborts():
    gate = base_gate(Path("."))
    gate["decision_extension"]["reserved_future"]["allowed"] = True
    result = validate_preflight_gate(gate, base_sources())
    assert result["status"] == "ABORT"


def test_quality_fail_aborts():
    gate = base_gate(Path("."))
    src = base_sources()
    src["draft_candidate_quality_validation"]["status"] = "FAIL"
    result = validate_preflight_gate(gate, src)
    assert result["status"] == "ABORT"


def test_post_count_limit_not_one_aborts():
    gate = base_gate(Path("."))
    gate["preflight_rules"]["post_count_limit"] = 2
    result = validate_preflight_gate(gate, base_sources())
    assert result["status"] == "ABORT"


def test_production_flag_true_aborts():
    gate = base_gate(Path("."))
    src = base_sources()
    src["phase5_overall_report"]["auto_post"] = True
    result = validate_preflight_gate(gate, src)
    assert result["status"] == "ABORT"


def test_run_validation_writes_result_file():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        a = root / "a"
        a.mkdir(parents=True, exist_ok=True)

        gate = base_gate(root)
        sources = base_sources()

        # required_inputsをtemp配下に合わせる
        gate["required_inputs"] = {
            "phase5_overall_report": "a/phase5.json",
            "phase6_1_design_validation": "a/phase6_1.json",
            "draft_candidate_quality_validation": "a/quality.json",
            "draft_candidate_review_result": "a/review.json",
        }

        _write(a / "phase5.json", sources["phase5_overall_report"])
        _write(a / "phase6_1.json", sources["phase6_1_design_validation"])
        _write(a / "quality.json", sources["draft_candidate_quality_validation"])
        _write(a / "review.json", sources["draft_candidate_review_result"])

        gate_path = root / "gate.json"
        result_path = root / "result.json"
        _write(gate_path, gate)

        # 一時ディレクトリをROOTとして使えないため、run_validationは
        # 既定ROOT相対を使う実装。ここでは validate_preflight_gate の
        # 実行結果検証と、run_validationのファイル出力確認を分ける。
        result = validate_preflight_gate(gate, sources)
        assert result["status"] == "PASS"

        # run_validation は既定ROOTを参照するため、ここでは存在しない gate 指定で ABORT になり得る。
        # ただし出力ファイルは生成されることを検証する。
        out = run_validation(gate_path=Path("/not/exist/gate.json"), output_path=result_path)
        assert result_path.exists()
        saved = json.loads(result_path.read_text(encoding="utf-8"))
        assert saved["package_type"] == "phase6_2_preflight_gate_validation_result"
        assert out["status"] in {"PASS", "ABORT"}
