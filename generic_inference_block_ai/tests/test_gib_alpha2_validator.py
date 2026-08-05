"""Integration test for alpha2 full validation report."""
from generic_inference_block_ai.src.gib_alpha2_validator import validate_alpha2_contract


def test_alpha2_contract_passes() -> None:
    report = validate_alpha2_contract()

    assert report["final_status"] == "PASS_DESIGN_ONLY_ALPHA2_TEMPLATE_RENDERED"
    assert report["production_status"] == "NO_GO"
    assert report["execution_allowed"] is False
    assert report["external_network_allowed"] is False
    assert report["credential_access_allowed"] is False
    assert report["wordpress_write_allowed"] is False
    assert report["systemd_operation_allowed"] is False
    assert report["real_llm_call_allowed"] is False
    assert report["template_config_valid"] is True
    assert report["template_config_issues"] == []
    assert report["all_samples_fully_valid"] is True
    assert report["sample_request_count"] == 7
    assert report["task_template_count"] == 7


def test_alpha2_all_samples_fully_valid() -> None:
    report = validate_alpha2_contract()
    for result in report["sample_results"]:
        assert result["fully_valid"] is True, (
            f"Sample {result['index']} ({result['task_type']}) not fully valid: "
            f"schema_valid={result['schema_valid']} "
            f"template_rendered={result['template_rendered']} "
            f"error={result['template_render_error']}"
        )
        assert result["rendered_prompt_len"] > 0
        assert result["execution_effect"] == "none"
        assert result["model_runtime"] == "stub_no_model_loaded"
