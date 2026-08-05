"""Integration test for alpha1 full validation report."""
from generic_inference_block_ai.src.gib_alpha1_validator import validate_alpha1_contract


def test_alpha1_contract_passes() -> None:
    report = validate_alpha1_contract()

    assert report["final_status"] == "PASS_DESIGN_ONLY_ALPHA1_SCHEMA_STRICT"
    assert report["production_status"] == "NO_GO"
    assert report["execution_allowed"] is False
    assert report["external_network_allowed"] is False
    assert report["credential_access_allowed"] is False
    assert report["wordpress_write_allowed"] is False
    assert report["systemd_operation_allowed"] is False
    assert report["real_llm_call_allowed"] is False
    assert report["all_samples_schema_valid"] is True
    assert report["sample_request_count"] == 7


def test_alpha1_schema_coverage_complete() -> None:
    report = validate_alpha1_contract()
    cov = report["schema_coverage"]

    assert cov["coverage_complete"] is True
    assert cov["missing_input"]  == []
    assert cov["missing_output"] == []
    assert cov["input_schemas"]  == 7
    assert cov["output_schemas"] == 7
