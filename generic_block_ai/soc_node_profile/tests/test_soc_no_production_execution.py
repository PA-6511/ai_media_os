from __future__ import annotations

from generic_block_ai.soc_node_profile.runtime.soc_task_runner import run_soc_dry_run_task


def test_soc_runner_never_executes_production_actions() -> None:
    blocked_result = run_soc_dry_run_task(
        {
            "request_id": "req_no_prod_1",
            "node_id": "soc_node_001",
            "task_type": "wordpress_publish",
            "input_lines": ["x"],
            "constraints": {"execution_mode": "DRY_RUN_ONLY"},
        }
    )
    assert blocked_result["schema_version"] == "soc_task_runner_result_v1"
    assert blocked_result["status"] == "ABORT"
    assert blocked_result["acceptance_decision"] == "ABORT"
    assert blocked_result["freeze_executed"] is False
    assert blocked_result["isolation_executed"] is False
    assert blocked_result["state_change_executed"] is False
    assert blocked_result["wordpress_write_executed"] is False
    assert blocked_result["publish_allowed"] is False
    assert blocked_result["safeguards"]["external_api_call"] is False
    assert blocked_result["safeguards"]["wordpress_write"] is False
    assert blocked_result["safeguards"]["shell_execution"] is False
