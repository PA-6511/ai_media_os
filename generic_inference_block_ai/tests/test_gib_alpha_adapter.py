import pytest

from generic_inference_block_ai.src.gib_alpha_adapter import (
    GIBAlphaRequest,
    StubInferenceAdapter,
    contains_secret_like_text,
)


def test_stub_adapter_generates_dry_run_output() -> None:
    adapter = StubInferenceAdapter()
    response = adapter.generate(
        GIBAlphaRequest(
            task_type="phase_log_summary",
            input={
                "phase_name": "Phase X",
                "status": "NO_GO",
                "log_excerpt": "dry-run sample",
            },
        )
    )

    assert response.status == "DRY_RUN_STUB_OUTPUT"
    assert response.model_runtime == "stub_no_model_loaded"
    assert response.execution_effect == "none"
    assert response.blocked is False


def test_stub_adapter_rejects_unknown_task_type() -> None:
    adapter = StubInferenceAdapter()

    with pytest.raises(ValueError):
        adapter.generate(
            GIBAlphaRequest(
                task_type="unknown_task",
                input={"text": "sample"},
            )
        )


def test_secret_like_input_is_blocked() -> None:
    adapter = StubInferenceAdapter()
    response = adapter.generate(
        GIBAlphaRequest(
            task_type="validator_result_explain",
            input={
                "validator_name": "sample",
                "result": "sample",
                "issues": ["WORDPRESS_APP_PASSWORD=do-not-print"],
            },
        )
    )

    assert response.status == "BLOCKED_SECRET_LIKE_INPUT_DETECTED"
    assert response.blocked is True
    assert response.block_reason == "secret_like_input_detected"


def test_secret_like_detector() -> None:
    assert contains_secret_like_text({"x": "credential.env"}) is True
    assert contains_secret_like_text({"x": "access_token=abc"}) is True
    assert contains_secret_like_text({"x": "normal dry-run text"}) is False
