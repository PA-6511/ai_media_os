"""Focused tests for Phase 8-36 through Phase 8-40."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase8_39_manual_rerun_command_bundle import (  # noqa: E402
    generate_manual_rerun_command_bundle,
)
from generate_phase8_40_post_rerun_branch_decision import (  # noqa: E402
    generate_post_rerun_branch_decision,
)
from validate_phase8_36_provisioned_overlay_rerun import (  # noqa: E402
    validate_provisioned_overlay_rerun,
)
from validate_phase8_37_credential_ready_revalidation import (  # noqa: E402
    validate_credential_ready_revalidation,
)
from validate_phase8_38_one_time_rerun_authorization_checkpoint import (  # noqa: E402
    validate_one_time_rerun_authorization_checkpoint,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _temp_root(tmp_path: Path) -> tuple[Path, Path, Path]:
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "exchange" / "logs"
    review_dir = tmp_path / "exchange" / "human_review"
    config_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    return config_dir, logs_dir, review_dir


def test_phase8_36_default_not_ready(
    tmp_path,
    isolated_missing_credential_state,
):
    config_dir, logs_dir, review_dir = _temp_root(tmp_path)
    policy = json.loads(
        (
            ROOT
            / "config/phase8_36_provisioned_overlay_rerun_policy.json"
        ).read_text(encoding="utf-8")
    )
    review = {
        "decision": (
            "OVERLAY_RERUN_DECLARE_CREDENTIALS_STILL_NOT_READY"
        ),
        "target_item_count": 1,
        "secret_values_included": False,
        "approval_scope": policy["approval_scope_required"],
    }
    for acknowledgement in policy["required_acknowledgements"]:
        review[acknowledgement] = True

    _write_json(
        config_dir
        / "phase8_36_provisioned_overlay_rerun_policy.json",
        policy,
    )
    _write_json(
        review_dir
        / "phase8_36_provisioned_overlay_rerun.example.json",
        review,
    )
    _write_json(
        logs_dir
        / "phase8_31_secret_safe_credential_procedure_result.json",
        {
            "status": policy["required_phase8_31_status"],
            "secret_values_written": False,
        },
    )
    _write_json(
        logs_dir
        / "phase8_35_final_ready_blocked_rerun_decision.json",
        {
            "status": "BLOCKED_CREDENTIALS_MISSING",
            "secret_values_written": False,
        },
    )

    result = validate_provisioned_overlay_rerun(
        policy_path=(
            config_dir
            / "phase8_36_provisioned_overlay_rerun_policy.json"
        ),
        review_path=(
            review_dir
            / "phase8_36_provisioned_overlay_rerun.example.json"
        ),
        output_json_path=logs_dir / "out.json",
        output_md_path=logs_dir / "out.md",
    )
    assert result["status"] == "OVERLAY_RERUN_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT"
    assert json.loads((logs_dir / "out.json").read_text(encoding="utf-8"))["status"] == result["status"]
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["commands_executed_in_this_phase"] is False
    assert not isolated_missing_credential_state["path"].exists()
    assert isolated_missing_credential_state[
        "production_access_attempts"
    ] == []


def test_phase8_36_rejects_missing_ack(tmp_path):
    config_dir, logs_dir, review_dir = _temp_root(tmp_path)
    policy = json.loads((ROOT / "config/phase8_36_provisioned_overlay_rerun_policy.json").read_text(encoding="utf-8"))
    review = json.loads((ROOT / "exchange/human_review/phase8_36_provisioned_overlay_rerun.example.json").read_text(encoding="utf-8"))
    review["acknowledged_no_publish"] = False
    _write_json(config_dir / "phase8_36_provisioned_overlay_rerun_policy.json", policy)
    _write_json(review_dir / "phase8_36_provisioned_overlay_rerun.example.json", review)
    _write_json(logs_dir / "phase8_31_secret_safe_credential_procedure_result.json", json.loads((ROOT / "exchange/logs/phase8_31_secret_safe_credential_procedure_result.json").read_text(encoding="utf-8")))
    _write_json(logs_dir / "phase8_35_final_ready_blocked_rerun_decision.json", json.loads((ROOT / "exchange/logs/phase8_35_final_ready_blocked_rerun_decision.json").read_text(encoding="utf-8")))

    result = validate_provisioned_overlay_rerun(
        policy_path=config_dir / "phase8_36_provisioned_overlay_rerun_policy.json",
        review_path=review_dir / "phase8_36_provisioned_overlay_rerun.example.json",
        output_json_path=logs_dir / "phase8_36_provisioned_overlay_rerun_result.json",
        output_md_path=logs_dir / "phase8_36_provisioned_overlay_rerun_result.md",
    )
    assert result["status"] == "ABORT"


def test_phase8_37_ready_revalidation_with_env(tmp_path, monkeypatch):
    config_dir, logs_dir, review_dir = _temp_root(tmp_path)
    policy = json.loads((ROOT / "config/phase8_37_credential_ready_revalidation_policy.json").read_text(encoding="utf-8"))
    policy["required_evidence"] = ["exchange/logs/phase8_36_provisioned_overlay_rerun_result.json"]
    _write_json(config_dir / "phase8_37_credential_ready_revalidation_policy.json", policy)
    _write_json(logs_dir / "phase8_36_provisioned_overlay_rerun_result.json", {
        "phase": "Phase 8-36",
        "status": "OVERLAY_RERUN_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        "secret_values_written": False,
    })
    for name in policy["required_env"]:
        monkeypatch.setenv(name, f"value-for-{name.lower()}")

    result = validate_credential_ready_revalidation(
        policy_path=config_dir / "phase8_37_credential_ready_revalidation_policy.json",
        output_json_path=logs_dir / "phase8_37_credential_ready_revalidation_result.json",
        output_md_path=logs_dir / "phase8_37_credential_ready_revalidation_result.md",
    )
    assert result["status"] == "CREDENTIAL_READY_REVALIDATED_NO_SECRET_OUTPUT"
    assert result["credentials"][policy["required_env"][0]]["exists"] is True


def test_phase8_37_not_ready_by_declaration(tmp_path, monkeypatch):
    config_dir, logs_dir, _ = _temp_root(tmp_path)
    policy = json.loads((ROOT / "config/phase8_37_credential_ready_revalidation_policy.json").read_text(encoding="utf-8"))
    policy["required_evidence"] = ["exchange/logs/phase8_36_provisioned_overlay_rerun_result.json"]
    _write_json(config_dir / "phase8_37_credential_ready_revalidation_policy.json", policy)
    _write_json(logs_dir / "phase8_36_provisioned_overlay_rerun_result.json", {
        "phase": "Phase 8-36",
        "status": "OVERLAY_RERUN_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT",
        "secret_values_written": False,
    })
    for name in policy["required_env"]:
        monkeypatch.delenv(name, raising=False)

    result = validate_credential_ready_revalidation(
        policy_path=config_dir / "phase8_37_credential_ready_revalidation_policy.json",
        output_json_path=logs_dir / "phase8_37_credential_ready_revalidation_result.json",
        output_md_path=logs_dir / "phase8_37_credential_ready_revalidation_result.md",
    )
    assert result["status"] == "CREDENTIAL_READY_REVALIDATION_NOT_READY_BY_DECLARATION"


def test_phase8_38_blocked_credentials_missing(
    tmp_path,
    isolated_missing_credential_state,
):
    config_dir, logs_dir, review_dir = _temp_root(tmp_path)
    revalidation_policy = json.loads(
        (
            ROOT
            / "config/phase8_37_credential_ready_revalidation_policy.json"
        ).read_text(encoding="utf-8")
    )
    revalidation_policy["required_evidence"] = [
        "exchange/logs/phase8_36_provisioned_overlay_rerun_result.json"
    ]
    _write_json(
        config_dir
        / "phase8_37_credential_ready_revalidation_policy.json",
        revalidation_policy,
    )
    _write_json(
        logs_dir
        / "phase8_36_provisioned_overlay_rerun_result.json",
        {
            "phase": "Phase 8-36",
            "status": (
                "OVERLAY_RERUN_CREDENTIALS_DECLARED_PROVISIONED_"
                "NO_SECRET_OUTPUT"
            ),
            "secret_values_written": False,
        },
    )
    revalidation = validate_credential_ready_revalidation(
        policy_path=(
            config_dir
            / "phase8_37_credential_ready_revalidation_policy.json"
        ),
        output_json_path=(
            logs_dir
            / "phase8_37_credential_ready_revalidation_result.json"
        ),
        output_md_path=(
            logs_dir
            / "phase8_37_credential_ready_revalidation_result.md"
        ),
    )
    assert revalidation["status"] == (
        "CREDENTIAL_READY_REVALIDATION_MISSING_NO_SECRET_OUTPUT"
    )
    assert all(
        credential["exists"] is False
        for credential in revalidation["credentials"].values()
    )

    policy = json.loads((ROOT / "config/phase8_38_one_time_rerun_authorization_checkpoint_policy.json").read_text(encoding="utf-8"))
    policy["required_evidence"] = ["exchange/logs/phase8_37_credential_ready_revalidation_result.json"]
    _write_json(config_dir / "phase8_38_one_time_rerun_authorization_checkpoint_policy.json", policy)
    review = {
        "decision": "NO_GO_CREDENTIALS_MISSING",
        "target_item_count": 1,
        "max_manual_rerun_count": 1,
        "secret_values_included": False,
        "approval_scope": policy["approval_scope_required"],
    }
    for acknowledgement in policy["required_acknowledgements"]:
        review[acknowledgement] = True
    _write_json(
        review_dir
        / "phase8_38_one_time_rerun_authorization_checkpoint.example.json",
        review,
    )

    result = validate_one_time_rerun_authorization_checkpoint(
        policy_path=config_dir / "phase8_38_one_time_rerun_authorization_checkpoint_policy.json",
        review_path=(
            review_dir
            / "phase8_38_one_time_rerun_authorization_checkpoint.example.json"
        ),
        output_json_path=logs_dir / "phase8_38_one_time_rerun_authorization_checkpoint_result.json",
        output_md_path=logs_dir / "phase8_38_one_time_rerun_authorization_checkpoint_result.md",
    )
    assert result["status"] == "ONE_TIME_RERUN_AUTH_BLOCKED_CREDENTIALS_MISSING"
    assert result["actual_go_decision_issued"] is False
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["commands_executed_in_this_phase"] is False
    assert not isolated_missing_credential_state["path"].exists()
    assert isolated_missing_credential_state[
        "production_access_attempts"
    ] == []


def test_phase8_39_blocked_command_bundle(tmp_path):
    config_dir, logs_dir, _ = _temp_root(tmp_path)
    policy = json.loads((ROOT / "config/phase8_39_manual_rerun_command_bundle_policy.json").read_text(encoding="utf-8"))
    policy["required_evidence"] = ["exchange/logs/phase8_38_one_time_rerun_authorization_checkpoint_result.json"]
    _write_json(config_dir / "phase8_39_manual_rerun_command_bundle_policy.json", policy)
    _write_json(logs_dir / "phase8_38_one_time_rerun_authorization_checkpoint_result.json", {
        "phase": "Phase 8-38",
        "status": "ONE_TIME_RERUN_AUTH_BLOCKED_CREDENTIALS_MISSING",
        "secret_values_written": False,
    })

    result = generate_manual_rerun_command_bundle(
        policy_path=config_dir / "phase8_39_manual_rerun_command_bundle_policy.json",
        output_json_path=logs_dir / "phase8_39_manual_rerun_command_bundle.json",
        output_md_path=logs_dir / "phase8_39_manual_rerun_command_bundle.md",
    )
    assert result["status"] == "MANUAL_RERUN_COMMAND_BUNDLE_BLOCKED_CREDENTIALS_MISSING"
    assert result["planned_manual_commands"] == []


def test_phase8_40_blocked_branch_decision(tmp_path):
    config_dir, logs_dir, _ = _temp_root(tmp_path)
    policy = json.loads((ROOT / "config/phase8_40_post_rerun_branch_decision_policy.json").read_text(encoding="utf-8"))
    policy["required_evidence"] = ["exchange/logs/phase8_39_manual_rerun_command_bundle.json"]
    _write_json(config_dir / "phase8_40_post_rerun_branch_decision_policy.json", policy)
    _write_json(logs_dir / "phase8_39_manual_rerun_command_bundle.json", {
        "phase": "Phase 8-39",
        "status": "MANUAL_RERUN_COMMAND_BUNDLE_BLOCKED_CREDENTIALS_MISSING",
        "secret_values_written": False,
    })

    result = generate_post_rerun_branch_decision(
        policy_path=config_dir / "phase8_40_post_rerun_branch_decision_policy.json",
        output_json_path=logs_dir / "phase8_40_post_rerun_branch_decision.json",
        output_md_path=logs_dir / "phase8_40_post_rerun_branch_decision.md",
    )
    assert result["status"] == "BRANCH_BLOCKED_CREDENTIALS_MISSING"
