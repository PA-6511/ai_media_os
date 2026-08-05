from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_beta06_validator import validate_beta06_contract

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CONFIG_PATH = _ROOT / "config" / "gib_beta07_ready_simulation.json"


@dataclass
class Beta07SimulationResult:
    config_valid: bool
    config_issues: list[str]
    base_ready_conditions_ok: bool
    simulated_ready_conditions_ok: bool
    simulated_state: dict[str, Any]
    auto_connect_triggered: bool


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_beta07_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta07.ready_simulation.v0.1":
        issues.append("schema_version must be gib.beta07.ready_simulation.v0.1")
    if config.get("beta_version") != "beta0.7":
        issues.append("beta_version must be beta0.7")
    if config.get("status") != "DRY_RUN_READY_SIMULATION_ONLY":
        issues.append("status must be DRY_RUN_READY_SIMULATION_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")

    for flag in ["real_llm_call_allowed", "execution_allowed", "generate_call_allowed", "chat_call_allowed"]:
        if config.get(flag) is not False:
            issues.append(f"{flag} must be false")

    if config.get("auto_connect_on_ready") is not False:
        issues.append("auto_connect_on_ready must be false")

    true_conditions = config.get("required_true_conditions_for_ready")
    false_conditions = config.get("required_false_conditions_for_ready")
    if not isinstance(true_conditions, list) or not true_conditions:
        issues.append("required_true_conditions_for_ready must be non-empty list")
    if not isinstance(false_conditions, list) or not false_conditions:
        issues.append("required_false_conditions_for_ready must be non-empty list")

    overrides = config.get("simulation_overrides")
    if not isinstance(overrides, dict):
        issues.append("simulation_overrides must be an object")

    artifact = config.get("artifact_policy", {})
    if artifact.get("report_write_scope") != ["generic_inference_block_ai/reports"]:
        issues.append("artifact_policy.report_write_scope must be generic_inference_block_ai/reports")
    if artifact.get("reports_only") is not True:
        issues.append("artifact_policy.reports_only must be true")

    return issues


def _conditions_ok(state: dict[str, Any], required_true: list[str], required_false: list[str]) -> bool:
    true_ok = all(state.get(key) is True for key in required_true)
    false_ok = all(state.get(key) is False for key in required_false)
    return true_ok and false_ok


def run_ready_simulation(config: dict[str, Any], beta06_report: dict[str, Any]) -> Beta07SimulationResult:
    issues = validate_beta07_config(config)

    base_state = dict(beta06_report["beta05_snapshot"])
    base_ready = _conditions_ok(
        base_state,
        config["required_true_conditions_for_ready"],
        config["required_false_conditions_for_ready"],
    )

    simulated_state = dict(base_state)
    simulated_state.update(config["simulation_overrides"])

    simulated_ready = _conditions_ok(
        simulated_state,
        config["required_true_conditions_for_ready"],
        config["required_false_conditions_for_ready"],
    )

    auto_connect_triggered = (
        simulated_ready
        and config["auto_connect_on_ready"] is True
        and config["real_llm_call_allowed"] is True
        and config["execution_allowed"] is True
    )

    return Beta07SimulationResult(
        config_valid=(len(issues) == 0),
        config_issues=issues,
        base_ready_conditions_ok=base_ready,
        simulated_ready_conditions_ok=simulated_ready,
        simulated_state=simulated_state,
        auto_connect_triggered=auto_connect_triggered,
    )


def load_and_run(path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Beta07SimulationResult]:
    config = load_json(path or CONFIG_PATH)
    beta06_report = validate_beta06_contract()
    result = run_ready_simulation(config, beta06_report)
    if result.config_issues:
        raise RuntimeError("GIB beta0.7 config validation failed: " + "; ".join(result.config_issues))
    return config, beta06_report, result
