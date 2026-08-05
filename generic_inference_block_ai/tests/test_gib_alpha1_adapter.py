"""Integration tests for ValidatedInferenceAdapter."""
import pytest
from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha1_adapter import ValidatedInferenceAdapter


@pytest.fixture(scope="module")
def adapter() -> ValidatedInferenceAdapter:
    return ValidatedInferenceAdapter()


def test_valid_request_passes_schema(adapter: ValidatedInferenceAdapter) -> None:
    result = adapter.generate_validated(
        GIBAlphaRequest(
            task_type="phase_log_summary",
            input={"phase_name": "P47", "status": "NO_GO", "log_excerpt": "ok"},
        )
    )
    assert result.schema_valid is True
    assert result.response.status == "DRY_RUN_STUB_OUTPUT"
    assert result.input_schema_issues == []
    assert result.output_schema_issues == []


def test_missing_required_field_triggers_input_schema_violation(adapter: ValidatedInferenceAdapter) -> None:
    result = adapter.generate_validated(
        GIBAlphaRequest(
            task_type="phase_log_summary",
            input={"phase_name": "P47"},  # missing status and log_excerpt
        )
    )
    assert result.response.status == "INPUT_SCHEMA_VIOLATION"
    assert result.response.blocked is True
    assert result.response.block_reason == "input_schema_violation"
    assert result.input_schema_issues  # non-empty
    assert result.schema_valid is False


def test_extra_field_triggers_input_schema_violation(adapter: ValidatedInferenceAdapter) -> None:
    result = adapter.generate_validated(
        GIBAlphaRequest(
            task_type="product_summary",
            input={
                "title": "Manga 1",
                "publisher": "Pub",
                "genre": "Action",
                "forbidden_extra": "should-not-be-here",
            },
        )
    )
    assert result.response.status == "INPUT_SCHEMA_VIOLATION"
    assert result.schema_valid is False


def test_wrong_type_triggers_input_schema_violation(adapter: ValidatedInferenceAdapter) -> None:
    result = adapter.generate_validated(
        GIBAlphaRequest(
            task_type="article_outline",
            input={
                "topic": "t",
                "target_reader": "r",
                "key_points": "should-be-a-list",
            },
        )
    )
    assert result.response.status == "INPUT_SCHEMA_VIOLATION"
    assert result.schema_valid is False


def test_all_sample_task_types_valid(adapter: ValidatedInferenceAdapter) -> None:
    """All 7 sample requests must pass schema validation end-to-end."""
    import json
    from pathlib import Path
    samples_path = Path(__file__).parent.parent / "samples" / "gib_alpha_sample_requests.json"
    samples = json.loads(samples_path.read_text(encoding="utf-8"))

    for raw in samples["requests"]:
        result = adapter.generate_validated(
            GIBAlphaRequest(task_type=raw["task_type"], input=raw.get("input", {}))
        )
        assert result.schema_valid is True, (
            f"Schema validation failed for {raw['task_type']}: "
            f"input_issues={result.input_schema_issues} "
            f"output_issues={result.output_schema_issues}"
        )


def test_unknown_task_type_raises_value_error(adapter: ValidatedInferenceAdapter) -> None:
    with pytest.raises((ValueError, KeyError)):
        adapter.generate_validated(
            GIBAlphaRequest(task_type="nonexistent_task", input={})
        )


def test_execution_effect_is_always_none(adapter: ValidatedInferenceAdapter) -> None:
    result = adapter.generate_validated(
        GIBAlphaRequest(
            task_type="security_log_explain",
            input={"log_excerpt": "WARNING: login", "detector_result": "recommendation_only"},
        )
    )
    assert result.response.execution_effect == "none"


def test_model_runtime_is_stub(adapter: ValidatedInferenceAdapter) -> None:
    result = adapter.generate_validated(
        GIBAlphaRequest(
            task_type="compliance_classify",
            input={"content_excerpt": "50% off", "context": "promo"},
        )
    )
    assert result.response.model_runtime == "stub_no_model_loaded"
