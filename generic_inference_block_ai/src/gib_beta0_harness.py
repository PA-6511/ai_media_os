from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
HARNESS_CONFIG_PATH = _ROOT / "config" / "gib_beta0_local_ollama_harness.json"


@dataclass
class Beta0ProbePlan:
    runtime_target: str
    endpoint: str
    would_call: bool
    blocked_reason: str | None
    fallback_runtime: str


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_beta0_harness_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta0.local_ollama_harness.v0.1":
        issues.append("schema_version must be gib.beta0.local_ollama_harness.v0.1")
    if config.get("beta_version") != "beta0":
        issues.append("beta_version must be beta0")
    if config.get("status") != "DRY_RUN_HARNESS_ONLY":
        issues.append("status must be DRY_RUN_HARNESS_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("execution_mode") != "DRY_RUN_ONLY":
        issues.append("execution_mode must be DRY_RUN_ONLY")
    if config.get("runtime_target") != "ollama":
        issues.append("runtime_target must be ollama")
    if config.get("fallback_runtime") != "stub":
        issues.append("fallback_runtime must be stub")

    network_policy = config.get("network_policy", {})
    if network_policy.get("external_network_allowed") is not True:
        issues.append("network_policy.external_network_allowed must be true")
    if network_policy.get("external_network_scope") != "localhost_only":
        issues.append("network_policy.external_network_scope must be localhost_only")

    safety_flags = config.get("safety_flags", {})
    if safety_flags.get("execution_allowed") is not False:
        issues.append("safety_flags.execution_allowed must be false")
    if safety_flags.get("credential_access_allowed") is not False:
        issues.append("safety_flags.credential_access_allowed must be false")
    if safety_flags.get("wordpress_write_allowed") is not False:
        issues.append("safety_flags.wordpress_write_allowed must be false")
    if safety_flags.get("systemd_operation_allowed") is not False:
        issues.append("safety_flags.systemd_operation_allowed must be false")
    if safety_flags.get("real_llm_call_allowed") is not False:
        issues.append("safety_flags.real_llm_call_allowed must be false")
    if safety_flags.get("model_runtime_enabled") is not True:
        issues.append("safety_flags.model_runtime_enabled must be true")

    artifact_policy = config.get("artifact_policy", {})
    if artifact_policy.get("report_write_scope") != ["generic_inference_block_ai/reports"]:
        issues.append("artifact_policy.report_write_scope must be generic_inference_block_ai/reports")

    ollama_design = config.get("ollama_design", {})
    if not str(ollama_design.get("base_url", "")).startswith("http://127.0.0.1:"):
        issues.append("ollama_design.base_url must use 127.0.0.1")

    return issues


def load_and_validate_beta0_config(path: Path | None = None) -> dict[str, Any]:
    config = load_json(path or HARNESS_CONFIG_PATH)
    issues = validate_beta0_harness_config(config)
    if issues:
        raise RuntimeError("GIB beta0 harness config validation failed: " + "; ".join(issues))
    return config


def build_probe_plan(config: dict[str, Any]) -> Beta0ProbePlan:
    design = config["ollama_design"]
    endpoint = str(design["base_url"]) + str(design["health_path"])
    safety_flags = config["safety_flags"]

    if safety_flags["real_llm_call_allowed"] is not True:
        return Beta0ProbePlan(
            runtime_target=config["runtime_target"],
            endpoint=endpoint,
            would_call=False,
            blocked_reason="real_llm_call_allowed_false",
            fallback_runtime=config["fallback_runtime"],
        )

    return Beta0ProbePlan(
        runtime_target=config["runtime_target"],
        endpoint=endpoint,
        would_call=False,
        blocked_reason="beta0_harness_dry_run_only",
        fallback_runtime=config["fallback_runtime"],
    )
