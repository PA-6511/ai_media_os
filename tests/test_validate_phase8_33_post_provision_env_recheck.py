"""Tests for validate_phase8_33_post_provision_env_recheck."""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_33_post_provision_env_recheck import (  # noqa: E402
    validate_post_provision_env_recheck,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-33",
        "name": "post_provision_env_recheck_policy",
        "policy_status": "ENV_RECHECK_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "recheck_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_env": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "required_evidence": ["exchange/logs/phase8_32_provisioned_declaration_overlay_result.json"],
        "ready_overlay_status": "OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        "not_ready_overlay_status": "OVERLAY_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT",
        "secret_output_policy": {
            "print_values": False,
            "write_values_to_logs": False,
            "print_lengths": False,
            "print_prefix_suffix": False,
            "hash_values": False,
            "mask_values": False,
            "allowed_output": "exists_boolean_only",
        },
        "allowed_next_step": "Phase 8-34 one-time manual rerun token / lock package",
    }


def run_case(
    tmp_path: Path,
    monkeypatch,
    policy: dict | None = None,
    overlay_status: str = "OVERLAY_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT",
    include_evidence: bool = True,
    set_all_env: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()

    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    pol = cfg / "policy.json"
    pol.write_text(json.dumps(p), encoding="utf-8")

    for name in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
        monkeypatch.delenv(name, raising=False)
    if set_all_env:
        monkeypatch.setenv("WORDPRESS_BASE_URL", "x")
        monkeypatch.setenv("WORDPRESS_USERNAME", "x")
        monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "x")

    if include_evidence:
        logs = tmp_path / "exchange" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "phase8_32_provisioned_declaration_overlay_result.json").write_text(
            json.dumps({"status": overlay_status, "secret_values_written": False}), encoding="utf-8"
        )

    return validate_post_provision_env_recheck(
        policy_path=pol,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_overlay_provisioned_with_env_ready(monkeypatch, tmp_path):
    result = run_case(
        tmp_path,
        monkeypatch,
        overlay_status="OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        set_all_env=True,
    )
    assert result["status"] == "POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT"


def test_overlay_provisioned_with_env_missing(monkeypatch, tmp_path):
    result = run_case(
        tmp_path,
        monkeypatch,
        overlay_status="OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        set_all_env=False,
    )
    assert result["status"] == "POST_PROVISION_ENV_MISSING_NO_SECRET_OUTPUT"


def test_overlay_not_ready(monkeypatch, tmp_path):
    result = run_case(tmp_path, monkeypatch)
    assert result["status"] == "POST_PROVISION_ENV_NOT_READY_BY_DECLARATION"


def test_evidence_missing_abort(monkeypatch, tmp_path):
    result = run_case(tmp_path, monkeypatch, include_evidence=False)
    assert result["status"] == "ABORT"


def test_evidence_abort_abort(monkeypatch, tmp_path):
    result = run_case(tmp_path, monkeypatch, overlay_status="ABORT")
    assert result["status"] == "ABORT"


def test_no_values_in_json(monkeypatch, tmp_path):
    result = run_case(
        tmp_path,
        monkeypatch,
        overlay_status="OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        set_all_env=True,
    )
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    serialized = json.dumps(out)
    assert '"length"' not in serialized
    assert '"prefix"' not in serialized
    assert '"suffix"' not in serialized
    assert '"hash"' not in serialized
    assert '"mask"' not in serialized
    assert result["credentials"]["WORDPRESS_APP_PASSWORD"] == {"exists": True}


def test_no_lengths_in_json(monkeypatch, tmp_path):
    result = run_case(tmp_path, monkeypatch)
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert "length" not in json.dumps(out)
    assert result["status"] == "POST_PROVISION_ENV_NOT_READY_BY_DECLARATION"


def test_secret_output_print_values_true_abort(monkeypatch, tmp_path):
    p = base_policy()
    p["secret_output_policy"]["print_values"] = True
    result = run_case(tmp_path, monkeypatch, policy=p)
    assert result["status"] == "ABORT"


def test_secret_output_mask_values_true_abort(monkeypatch, tmp_path):
    p = base_policy()
    p["secret_output_policy"]["mask_values"] = True
    result = run_case(tmp_path, monkeypatch, policy=p)
    assert result["status"] == "ABORT"


def test_wordpress_api_call_allowed_true_abort(monkeypatch, tmp_path):
    p = base_policy()
    p["wordpress_api_call_allowed"] = True
    result = run_case(tmp_path, monkeypatch, policy=p)
    assert result["status"] == "ABORT"


def test_commands_executed_true_abort(monkeypatch, tmp_path):
    p = base_policy()
    p["commands_executed_in_this_phase"] = True
    result = run_case(tmp_path, monkeypatch, policy=p)
    assert result["status"] == "ABORT"


def test_phase8_6_to_8_10_executed_true_abort(monkeypatch, tmp_path):
    p = base_policy()
    p["phase8_6_to_8_10_executed"] = True
    result = run_case(tmp_path, monkeypatch, policy=p)
    assert result["status"] == "ABORT"


def test_publish_allowed_true_abort(monkeypatch, tmp_path):
    p = base_policy()
    p["publish_allowed"] = True
    result = run_case(tmp_path, monkeypatch, policy=p)
    assert result["status"] == "ABORT"
