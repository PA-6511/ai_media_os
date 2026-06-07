from __future__ import annotations

from generic_block_ai.soc_node_profile.runtime.task_acceptance_gate import evaluate_task_acceptance


def test_soc_task_acceptance_gate_passes_allowed_task() -> None:
    decision = evaluate_task_acceptance({"task_type": "log_summary"})
    assert decision["decision"] == "PASS"


def test_soc_task_acceptance_gate_aborts_blocked_task() -> None:
    decision = evaluate_task_acceptance({"task_type": "wordpress_publish"})
    assert decision["decision"] == "ABORT"
    assert "blocked_task_type" in decision["reason"]
