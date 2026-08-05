from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ALLOWED_RUNTIMES = ["stub", "ollama", "llama_cpp"]
_REQUIRED_FALSE_FLAGS = [
    "execution_allowed",
    "external_network_allowed",
    "credential_access_allowed",
    "wordpress_write_allowed",
    "systemd_operation_allowed",
    "model_runtime_enabled",
    "real_llm_call_allowed",
]

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
RUNTIME_DESIGN_PATH = _ROOT / "config" / "gib_alpha3_runtime_design.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_runtime_design(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.alpha3.runtime_design.v0.1":
        issues.append("schema_version must be gib.alpha3.runtime_design.v0.1")
    if config.get("design_status") != "DESIGN_ONLY":
        issues.append("design_status must be DESIGN_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("execution_mode") != "DRY_RUN_ONLY":
        issues.append("execution_mode must be DRY_RUN_ONLY")

    for flag in _REQUIRED_FALSE_FLAGS:
        if config.get(flag) is not False:
            issues.append(f"{flag} must be false")

    selection = config.get("runtime_selection")
    if not isinstance(selection, dict):
        issues.append("runtime_selection must be an object")
    else:
        active = selection.get("active_runtime_locked")
        default = selection.get("default_runtime")
        fallback = selection.get("fallback_order")

        if active != "stub":
            issues.append("active_runtime_locked must be stub")
        if default != "stub":
            issues.append("default_runtime must be stub")
        if fallback != ["stub", "ollama", "llama_cpp"]:
            issues.append("fallback_order must be [stub, ollama, llama_cpp]")

    runtimes = config.get("runtime_designs")
    if not isinstance(runtimes, dict):
        issues.append("runtime_designs must be an object")
    else:
        for runtime in ["ollama", "llama_cpp"]:
            if runtime not in runtimes:
                issues.append(f"runtime_designs missing {runtime}")
                continue
            definition = runtimes[runtime]
            if not isinstance(definition, dict):
                issues.append(f"{runtime}: definition must be an object")
                continue
            if definition.get("enabled") is not False:
                issues.append(f"{runtime}: enabled must be false")
            if definition.get("call_allowed") is not False:
                issues.append(f"{runtime}: call_allowed must be false")
            if definition.get("transport") != "http_local_only_design":
                issues.append(f"{runtime}: transport must be http_local_only_design")
            if not isinstance(definition.get("base_url"), str):
                issues.append(f"{runtime}: base_url must be a string")
            if not isinstance(definition.get("timeout_ms"), int):
                issues.append(f"{runtime}: timeout_ms must be an integer")

    prohibited = config.get("prohibited_actions")
    if not isinstance(prohibited, list):
        issues.append("prohibited_actions must be a list")
    else:
        required = {
            "network_http_call",
            "subprocess_runtime_call",
            "credential_read",
            "wordpress_write",
            "systemd_operation",
            "go_nogo_decision",
        }
        missing = sorted(required - set(prohibited))
        if missing:
            issues.append(f"missing prohibited_actions: {missing}")

    return issues


def load_and_validate_runtime_design(path: Path | None = None) -> dict[str, Any]:
    config = load_json(path or RUNTIME_DESIGN_PATH)
    issues = validate_runtime_design(config)
    if issues:
        raise RuntimeError("GIB alpha3 runtime design validation failed: " + "; ".join(issues))
    return config
