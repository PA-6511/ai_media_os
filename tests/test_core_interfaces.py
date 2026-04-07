from core.interfaces import normalize_block_result, normalize_core_decision


def test_normalize_block_result_fills_minimum_fields() -> None:
    normalized = normalize_block_result({"title": "demo"}, block_name="DemoBlock", event_id="e1")
    assert normalized is not None
    assert normalized["block_name"] == "DemoBlock"
    assert normalized["item_id"] == "demo"
    assert normalized["target"] == "demo"
    assert normalized["event_id"] == "e1"
    assert 0.0 <= float(normalized["priority"]) <= 1.0


def test_normalize_block_result_returns_none_for_non_dict() -> None:
    assert normalize_block_result("bad", block_name="DemoBlock", event_id="e1") is None


def test_normalize_core_decision_invalid_type_freezes() -> None:
    decision = normalize_core_decision("bad", event_id="e1")
    assert decision["decision"] == "freeze"
    assert decision["next_action"] == "freeze"
    assert decision["requires_human_review"] is True


def test_normalize_core_decision_unknown_is_safe_side() -> None:
    decision = normalize_core_decision({"decision": "mystery"}, event_id="e1")
    assert decision["next_action"] != "run_pipeline"
    assert decision["requires_human_review"] is True
