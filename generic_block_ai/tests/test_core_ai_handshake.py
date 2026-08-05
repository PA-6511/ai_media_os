import json
from pathlib import Path

import pytest

from generic_block_ai.app.connection_dryrun_validator import validate_connection_dryrun
from generic_block_ai.app.core_ai_handshake_package import (
    build_core_ai_handshake_package,
    write_core_ai_handshake_package,
)


def _minimal_block_result(recommended: str = "RECOMMEND_APPROVE_DRY_RUN_ONLY") -> dict:
    return {
        "status": "success",
        "decision": "human_review",
        "summary": "planned=2, allowed=1, blocked=0, needs_review=1, candidates=2, filtered=1, rejected=1",
        "meta": {"block_id": "generic_block", "version": "0.1.0"},
        "review_decision": {
            "recommended_decision": recommended,
            "reason": "review_readiness=ready",
        },
        "quality_metrics": {
            "quality_score": 72,
            "risk_balance": 61,
            "review_readiness": "ready",
        },
        "policy_versioning": {
            "version": "v1.0.0",
            "environment": "dev",
            "policy_hash": "a" * 64,
        },
        "signoff_audit": {
            "record": {"signoff": {"actor": "generic_block_ai"}},
        },
    }


# --- build_core_ai_handshake_package ---

def test_build_handshake_package_has_required_fields() -> None:
    package = build_core_ai_handshake_package(
        _minimal_block_result(),
        source_task_id="IR4-T1-001",
    )
    assert package["_meta"]["schema_version"] == "handshake_v1"
    assert package["handshake_contract"]["execution"] == "dry_run"
    assert package["handshake_contract"]["operation_mode"] == "OBSERVE"
    assert package["safeguards"]["external_write_executed"] is False
    assert package["safeguards"]["actual_auto_execute"] is False


def test_build_handshake_maps_connection_status() -> None:
    cases = {
        "RECOMMEND_APPROVE_DRY_RUN_ONLY": "HANDSHAKE_READY_DRY_RUN",
        "RECOMMEND_REJECT": "HANDSHAKE_REJECTED",
        "BLOCKED_BY_POLICY": "HANDSHAKE_BLOCKED",
        "REQUIRE_HUMAN_REVIEW": "HANDSHAKE_PENDING_REVIEW",
    }
    for recommended, expected_status in cases.items():
        result = _minimal_block_result(recommended)
        pkg = build_core_ai_handshake_package(result, source_task_id="IR4-T1-002")
        assert pkg["connection_status"] == expected_status, (
            f"Expected {expected_status} for {recommended}"
        )


def test_write_handshake_package_creates_local_json(tmp_path: Path) -> None:
    output = write_core_ai_handshake_package(
        base_path=tmp_path,
        block_result=_minimal_block_result(),
        source_task_id="IR4-T1-003",
    )
    path = Path(output["path"])
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["handshake_contract"]["transport"] == "none"
    assert output["external_write_executed"] is False


# --- validate_connection_dryrun ---

def test_connection_validator_passes_valid_package() -> None:
    package = build_core_ai_handshake_package(
        _minimal_block_result(),
        source_task_id="IR4-T3-001",
    )
    result = validate_connection_dryrun(package)
    assert result.result == "PASS"


def test_connection_validator_fails_wrong_schema_version() -> None:
    package = build_core_ai_handshake_package(
        _minimal_block_result(),
        source_task_id="IR4-T3-002",
    )
    package["_meta"]["schema_version"] = "wrong_v99"
    result = validate_connection_dryrun(package)
    assert result.result == "FAIL"
    assert any("schema_version" in c for c in result.failed_checks)


def test_connection_validator_fails_if_auto_execute_true() -> None:
    package = build_core_ai_handshake_package(
        _minimal_block_result(),
        source_task_id="IR4-T3-003",
    )
    package["safeguards"]["actual_auto_execute"] = True
    result = validate_connection_dryrun(package)
    assert result.result == "FAIL"
    assert any("actual_auto_execute" in c for c in result.failed_checks)


def test_connection_validator_warns_missing_policy_hash() -> None:
    block_result = _minimal_block_result()
    block_result["policy_versioning"]["policy_hash"] = None
    package = build_core_ai_handshake_package(block_result, source_task_id="IR4-T3-004")
    result = validate_connection_dryrun(package)
    assert result.result in {"PASS", "WARN"}
    if result.result == "WARN":
        assert any("policy_hash" in w for w in result.warnings)
