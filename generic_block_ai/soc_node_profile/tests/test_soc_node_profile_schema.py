from __future__ import annotations

import json
from pathlib import Path


BASE = Path("generic_block_ai/soc_node_profile/config")


def test_soc_node_profile_examples_have_required_fields() -> None:
    schema = json.loads((BASE / "soc_node_profile.schema.json").read_text(encoding="utf-8"))
    required_fields = set(schema["required"])

    for example_name in [
        "example_android_soc_node.json",
        "example_snapdragon_node.json",
        "example_apple_silicon_mobile_node.json",
    ]:
        payload = json.loads((BASE / example_name).read_text(encoding="utf-8"))
        missing = [field for field in required_fields if field not in payload]
        assert not missing, f"{example_name} missing required fields: {missing}"
        assert payload["device_class"] in {"SMARTPHONE_SOC", "MOBILE_SOC_BOARD", "TABLET_SOC"}
