from __future__ import annotations

from generic_block_ai.soc_node_profile.runtime.soc_task_runner import run_soc_dry_run_task


def test_soc_runner_never_executes_production_actions() -> None:
    blocked_result = run_soc_dry_run_task({"task_type": "wordpress_publish", "input_lines": ["x"]})
    assert blocked_result["status"] == "ABORT"
    assert blocked_result["freeze_executed"] is False
    assert blocked_result["isolation_executed"] is False
    assert blocked_result["state_change_executed"] is False
    assert blocked_result["wordpress_write_executed"] is False
    assert blocked_result["publish_allowed"] is False
