"""Integration tests for TemplateValidatedAdapter."""
import pytest
from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha2_adapter import TemplateValidatedAdapter


@pytest.fixture(scope="module")
def adapter() -> TemplateValidatedAdapter:
    return TemplateValidatedAdapter()


def test_valid_request_fully_valid(adapter: TemplateValidatedAdapter) -> None:
    result = adapter.generate_alpha2(
        GIBAlphaRequest(
            task_type="phase_log_summary",
            input={"phase_name": "P47", "status": "NO_GO", "log_excerpt": "dry-run ok"},
        )
    )
    assert result.fully_valid is True
    assert result.template_rendered is True
    assert result.schema_valid is True
    assert result.template_render_error is None
    assert result.rendered_user_prompt is not None
    assert "P47" in result.rendered_user_prompt


def test_system_prompt_is_returned(adapter: TemplateValidatedAdapter) -> None:
    result = adapter.generate_alpha2(
        GIBAlphaRequest(
            task_type="compliance_classify",
            input={"content_excerpt": "50% off", "context": "promo"},
        )
    )
    assert result.system_prompt is not None
    assert len(result.system_prompt) > 0


def test_schema_violation_skips_template_render(adapter: TemplateValidatedAdapter) -> None:
    result = adapter.generate_alpha2(
        GIBAlphaRequest(
            task_type="phase_log_summary",
            input={"phase_name": "P"},  # missing required fields
        )
    )
    assert result.response.status == "INPUT_SCHEMA_VIOLATION"
    assert result.template_rendered is False
    assert result.rendered_user_prompt is None
    assert result.fully_valid is False


def test_execution_effect_always_none(adapter: TemplateValidatedAdapter) -> None:
    result = adapter.generate_alpha2(
        GIBAlphaRequest(
            task_type="product_summary",
            input={"title": "T", "publisher": "P", "genre": "G"},
        )
    )
    assert result.response.execution_effect == "none"


def test_model_runtime_is_stub(adapter: TemplateValidatedAdapter) -> None:
    result = adapter.generate_alpha2(
        GIBAlphaRequest(
            task_type="security_log_explain",
            input={"log_excerpt": "WARNING login", "detector_result": "rec"},
        )
    )
    assert result.response.model_runtime == "stub_no_model_loaded"


def test_all_sample_requests_fully_valid(adapter: TemplateValidatedAdapter) -> None:
    import json
    from pathlib import Path
    samples_path = Path(__file__).parent.parent / "samples" / "gib_alpha_sample_requests.json"
    samples = json.loads(samples_path.read_text(encoding="utf-8"))

    for raw in samples["requests"]:
        result = adapter.generate_alpha2(
            GIBAlphaRequest(task_type=raw["task_type"], input=raw.get("input", {}))
        )
        assert result.fully_valid is True, (
            f"Not fully valid for {raw['task_type']}: "
            f"schema_valid={result.schema_valid} "
            f"template_rendered={result.template_rendered} "
            f"render_error={result.template_render_error}"
        )


def test_rendered_prompt_within_length_limit(adapter: TemplateValidatedAdapter) -> None:
    from generic_inference_block_ai.src.gib_alpha2_templates import load_template_config
    config = load_template_config()
    result = adapter.generate_alpha2(
        GIBAlphaRequest(
            task_type="social_post_draft",
            input={"topic": "T", "source_summary": "S", "target_audience": "A"},
        )
    )
    assert result.rendered_user_prompt is not None
    max_len = config["task_templates"]["social_post_draft"]["max_rendered_length"]
    assert len(result.rendered_user_prompt) <= max_len
