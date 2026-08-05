from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha3_adapter_blueprint import RuntimeDesignOnlyAdapter
from generic_inference_block_ai.src.gib_alpha4_gate import (
    evaluate_runtime_gate,
    get_alpha_policy_flags,
    load_and_validate_gate_config,
)


def test_alpha4_gate_matches_alpha3_stub_lock() -> None:
    adapter = RuntimeDesignOnlyAdapter()
    gate_config = load_and_validate_gate_config()
    flags = get_alpha_policy_flags()

    request = GIBAlphaRequest(
        task_type="product_summary",
        input={"title": "T", "publisher": "P", "genre": "G"},
    )
    alpha3_result = adapter.generate_alpha3(request)

    decision = evaluate_runtime_gate("ollama", flags, gate_config)
    assert alpha3_result.runtime_plan.runtime == "stub"
    assert alpha3_result.runtime_plan.would_call is False
    assert decision.allowed is False
    assert decision.active_runtime == "stub"


def test_alpha4_stub_path_remains_valid() -> None:
    gate_config = load_and_validate_gate_config()
    flags = get_alpha_policy_flags()

    decision = evaluate_runtime_gate("stub", flags, gate_config)
    assert decision.allowed is True
    assert decision.active_runtime == "stub"
    assert decision.missing_flags == []
