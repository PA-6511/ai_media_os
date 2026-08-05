from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha3_adapter_blueprint import RuntimeDesignOnlyAdapter


def test_alpha3_adapter_returns_no_runtime_call_plan() -> None:
    adapter = RuntimeDesignOnlyAdapter()

    result = adapter.generate_alpha3(
        GIBAlphaRequest(
            task_type="phase_log_summary",
            input={"phase_name": "P47", "status": "NO_GO", "log_excerpt": "dry-run"},
        )
    )

    assert result.runtime_plan.runtime == "stub"
    assert result.runtime_plan.would_call is False
    assert result.runtime_plan.endpoint is not None
    assert result.runtime_plan.model_placeholder == "gemma-4-qat-design-placeholder"
    assert result.response.execution_effect == "none"
    assert result.response.model_runtime == "stub_no_model_loaded"
    assert result.fully_valid is True


def test_alpha3_adapter_preserves_alpha2_blocking_behavior() -> None:
    adapter = RuntimeDesignOnlyAdapter()

    result = adapter.generate_alpha3(
        GIBAlphaRequest(
            task_type="validator_result_explain",
            input={
                "validator_name": "x",
                "result": "y",
                "issues": ["password=do-not-print"],
            },
        )
    )

    assert result.response.blocked is True
    assert result.response.status == "BLOCKED_SECRET_LIKE_INPUT_DETECTED"
    assert result.runtime_plan.would_call is False


def test_alpha3_adapter_all_sample_task_types() -> None:
    adapter = RuntimeDesignOnlyAdapter()

    samples = [
        ("phase_log_summary", {"phase_name": "P", "status": "ok", "log_excerpt": "ok"}),
        ("validator_result_explain", {"validator_name": "v", "result": "PASS", "issues": []}),
        ("product_summary", {"title": "t", "publisher": "p", "genre": "g"}),
        ("social_post_draft", {"topic": "t", "source_summary": "s", "target_audience": "a"}),
        ("article_outline", {"topic": "t", "target_reader": "r", "key_points": ["k"]}),
        ("compliance_classify", {"content_excerpt": "c", "context": "ctx"}),
        ("security_log_explain", {"log_excerpt": "log", "detector_result": "rec"}),
    ]

    for task_type, payload in samples:
        result = adapter.generate_alpha3(GIBAlphaRequest(task_type=task_type, input=payload))
        assert result.runtime_plan.would_call is False
        assert result.response.execution_effect == "none"
        assert result.response.model_runtime == "stub_no_model_loaded"
