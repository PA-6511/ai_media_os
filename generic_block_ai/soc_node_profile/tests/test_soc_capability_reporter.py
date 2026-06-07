from __future__ import annotations

import json
from pathlib import Path

from generic_block_ai.soc_node_profile.runtime.capability_reporter import build_soc_capability_report
from generic_block_ai.soc_node_profile.runtime.device_probe import probe_device_profile


def test_soc_capability_report_is_dry_run_and_small() -> None:
    manifest_path = Path("generic_block_ai/soc_node_profile/soc_block_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    profile = probe_device_profile({"node_id": "soc_node_001", "thermal_status": "NORMAL"})
    report = build_soc_capability_report("soc_node_001", manifest, profile)

    assert report["schema_version"] == "soc_capability_report_v1"
    assert report["execution_mode"] == "DRY_RUN"
    assert report["recommended_task_size"] == "SMALL"
    assert report["can_call_external_api"] is False
    assert report["can_write_wordpress"] is False
