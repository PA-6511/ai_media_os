from __future__ import annotations

from typing import Any


def select_model_for_soc_task(task_type: str, profile: dict[str, Any]) -> str:
    thermal_status = str(profile.get("thermal_status", "NORMAL")).upper()
    ram_gb = float(profile.get("ram_gb", 0))

    if thermal_status in {"HOT", "CRITICAL"}:
        return "abort"

    if task_type in {"summarize", "classify", "log_summary"} and ram_gb >= 6:
        return "soc-small-instruct"

    return "soc-minimal-rules"
