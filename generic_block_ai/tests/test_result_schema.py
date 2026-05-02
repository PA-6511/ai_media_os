import pytest

from generic_block_ai.app.result_schema import build_block_result


def test_build_block_result_success() -> None:
    result = build_block_result(
        status="success",
        decision="human_review",
        summary="ok",
        risk_level="low",
        needs_approval=True,
        mode="dry_run",
        actual_execution=False,
        actions=[],
        warnings=[],
        errors=[],
        block_id="generic_block",
        version="0.1.0",
    )
    assert result["status"] == "success"
    assert result["decision"] == "human_review"
    assert result["actual_execution"] is False


def test_build_block_result_rejects_non_dry_run() -> None:
    with pytest.raises(ValueError):
        build_block_result(
            status="success",
            decision="decision",
            summary="bad",
            risk_level="low",
            needs_approval=False,
            mode="real_run",
            actual_execution=False,
            actions=[],
            warnings=[],
            errors=[],
            block_id="generic_block",
            version="0.1.0",
        )
