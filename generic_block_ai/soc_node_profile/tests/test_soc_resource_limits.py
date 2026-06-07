from __future__ import annotations

import json
from pathlib import Path


def test_soc_resource_limits_stay_small_and_capped() -> None:
    policy_path = Path("generic_block_ai/soc_node_profile/policy/soc_node_resource_limits.json")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    assert policy["recommended_task_size"] == "SMALL"
    assert policy["max_cpu_usage_percent"] <= 70
    assert policy["max_memory_mb"] <= 2048
    assert policy["abort_on_battery_below_percent"] >= 15
