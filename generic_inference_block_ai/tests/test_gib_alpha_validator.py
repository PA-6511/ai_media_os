from generic_inference_block_ai.src.gib_alpha_validator import validate_alpha_contract
from generic_inference_block_ai.src.gib_alpha_demo import run_demo_no_execution


def test_alpha_contract_passes_validation() -> None:
    report = validate_alpha_contract()

    assert report["final_status"] == "PASS_DESIGN_ONLY_ALPHA_TEMPLATE"
    assert report["production_status"] == "NO_GO"
    assert report["execution_allowed"] is False
    assert report["external_network_allowed"] is False
    assert report["credential_access_allowed"] is False
    assert report["wordpress_write_allowed"] is False
    assert report["systemd_operation_allowed"] is False
    assert report["real_llm_call_allowed"] is False
    assert report["task_count"] == 7
    assert report["sample_request_count"] == 7


def test_demo_is_dry_run_only() -> None:
    report = run_demo_no_execution()

    assert report["final_status"] == "PASS_DRY_RUN_STUB_DEMO_ONLY"
    assert report["production_status"] == "NO_GO"
    assert report["execution_allowed"] is False
    assert report["real_llm_call_allowed"] is False
    assert report["credential_access_allowed"] is False
    assert report["wordpress_write_allowed"] is False
    assert len(report["responses"]) == 7
