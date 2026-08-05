from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha3_runtime_design import load_and_validate_runtime_design

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
GATE_CONFIG_PATH = _ROOT / "config" / "gib_alpha4_runtime_gate.json"


@dataclass
class RuntimeGateDecision:
    requested_runtime: str
    active_runtime: str
    allowed: bool
    blocked_reason: str | None
    required_flags: list[str]
    missing_flags: list[str]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_gate_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.alpha4.runtime_gate.v0.1":
        issues.append("schema_version must be gib.alpha4.runtime_gate.v0.1")
    if config.get("design_status") != "DESIGN_ONLY":
        issues.append("design_status must be DESIGN_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("execution_mode") != "DRY_RUN_ONLY":
        issues.append("execution_mode must be DRY_RUN_ONLY")
    if config.get("active_runtime_lock") != "stub":
        issues.append("active_runtime_lock must be stub")

    allowed_runtimes = config.get("allowed_runtimes")
    if allowed_runtimes != ["stub", "ollama", "llama_cpp"]:
        issues.append("allowed_runtimes must be [stub, ollama, llama_cpp]")

    switch_conditions = config.get("runtime_switch_conditions")
    if not isinstance(switch_conditions, dict):
        issues.append("runtime_switch_conditions must be an object")
    else:
        for runtime in ["stub", "ollama", "llama_cpp"]:
            if runtime not in switch_conditions:
                issues.append(f"runtime_switch_conditions missing {runtime}")

    beta_requirements = config.get("beta0_promotion_requirements")
    if not isinstance(beta_requirements, list) or not beta_requirements:
        issues.append("beta0_promotion_requirements must be a non-empty list")

    hard_blocks = config.get("hard_blocks")
    if not isinstance(hard_blocks, list) or not hard_blocks:
        issues.append("hard_blocks must be a non-empty list")

    return issues


def load_and_validate_gate_config(path: Path | None = None) -> dict[str, Any]:
    config = load_json(path or GATE_CONFIG_PATH)
    issues = validate_gate_config(config)
    if issues:
        raise RuntimeError("GIB alpha4 gate config validation failed: " + "; ".join(issues))
    return config


def evaluate_runtime_gate(
    requested_runtime: str,
    policy_flags: dict[str, bool],
    gate_config: dict[str, Any],
) -> RuntimeGateDecision:
    allowed_runtimes = gate_config["allowed_runtimes"]
    if requested_runtime not in allowed_runtimes:
        return RuntimeGateDecision(
            requested_runtime=requested_runtime,
            active_runtime="stub",
            allowed=False,
            blocked_reason="unsupported_runtime",
            required_flags=[],
            missing_flags=[],
        )

    # In alpha stage, stub is always permitted.
    if requested_runtime == "stub":
        return RuntimeGateDecision(
            requested_runtime=requested_runtime,
            active_runtime="stub",
            allowed=True,
            blocked_reason=None,
            required_flags=[],
            missing_flags=[],
        )

    required_flags = gate_config["runtime_switch_conditions"][requested_runtime]["requires_flags"]
    missing_flags = [flag for flag in required_flags if policy_flags.get(flag) is not True]

    if missing_flags:
        return RuntimeGateDecision(
            requested_runtime=requested_runtime,
            active_runtime="stub",
            allowed=False,
            blocked_reason="runtime_call_not_allowed_by_policy_flags",
            required_flags=required_flags,
            missing_flags=missing_flags,
        )

    # Even if all flags are true in future phases, alpha lock keeps active runtime as stub.
    active_runtime = gate_config["active_runtime_lock"]
    allowed = active_runtime == requested_runtime
    return RuntimeGateDecision(
        requested_runtime=requested_runtime,
        active_runtime=active_runtime,
        allowed=allowed,
        blocked_reason=None if allowed else "runtime_locked_to_stub_in_alpha",
        required_flags=required_flags,
        missing_flags=[] if allowed else [],
    )


def get_alpha_policy_flags() -> dict[str, bool]:
    runtime_design = load_and_validate_runtime_design()
    return {
        "model_runtime_enabled": bool(runtime_design["model_runtime_enabled"]),
        "real_llm_call_allowed": bool(runtime_design["real_llm_call_allowed"]),
        "execution_allowed": bool(runtime_design["execution_allowed"]),
    }
