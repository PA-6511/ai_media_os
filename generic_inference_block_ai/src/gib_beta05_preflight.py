from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
CONFIG_PATH = _ROOT / "config" / "gib_beta05_local_ollama_preflight.json"


@dataclass
class EndpointCheck:
    endpoint: str
    host_allowed: bool
    port_allowed: bool
    valid_scheme: bool

    @property
    def valid(self) -> bool:
        return self.host_allowed and self.port_allowed and self.valid_scheme


@dataclass
class PreflightResult:
    config_valid: bool
    config_issues: list[str]
    ollama_binary_found: bool
    ollama_binary_path: str | None
    endpoint_checks: list[EndpointCheck]
    all_endpoints_valid: bool
    model_allowed: bool
    forbidden_host_rejected: bool
    generate_api_called: bool
    chat_api_called: bool
    ready_for_connecting_stage: bool


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def validate_preflight_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.beta05.local_ollama_preflight.v0.1":
        issues.append("schema_version must be gib.beta05.local_ollama_preflight.v0.1")
    if config.get("beta_version") != "beta0.5":
        issues.append("beta_version must be beta0.5")
    if config.get("status") != "DRY_RUN_PREFLIGHT_ONLY":
        issues.append("status must be DRY_RUN_PREFLIGHT_ONLY")
    if config.get("production_status") != "NO_GO":
        issues.append("production_status must be NO_GO")
    if config.get("runtime_target") != "ollama":
        issues.append("runtime_target must be ollama")

    for flag in ["real_llm_call_allowed", "execution_allowed", "generate_call_allowed", "chat_call_allowed"]:
        if config.get(flag) is not False:
            issues.append(f"{flag} must be false")

    policy = config.get("network_policy", {})
    if policy.get("scope") != "localhost_only":
        issues.append("network_policy.scope must be localhost_only")
    if not isinstance(policy.get("allowed_hosts"), list):
        issues.append("network_policy.allowed_hosts must be a list")
    if not isinstance(policy.get("allowed_ports"), list):
        issues.append("network_policy.allowed_ports must be a list")
    if not isinstance(policy.get("forbidden_hosts"), list):
        issues.append("network_policy.forbidden_hosts must be a list")

    if not isinstance(config.get("endpoint_candidates"), list) or not config["endpoint_candidates"]:
        issues.append("endpoint_candidates must be a non-empty list")
    if not isinstance(config.get("model_allowlist"), list) or not config["model_allowlist"]:
        issues.append("model_allowlist must be a non-empty list")

    artifact = config.get("artifact_policy", {})
    if artifact.get("report_write_scope") != ["generic_inference_block_ai/reports"]:
        issues.append("artifact_policy.report_write_scope must be generic_inference_block_ai/reports")
    if artifact.get("reports_only") is not True:
        issues.append("artifact_policy.reports_only must be true")

    return issues


def check_endpoint(endpoint: str, allowed_hosts: list[str], allowed_ports: list[int]) -> EndpointCheck:
    parsed = urlparse(endpoint)
    host = parsed.hostname or ""
    port = parsed.port or (80 if parsed.scheme == "http" else 443)
    return EndpointCheck(
        endpoint=endpoint,
        host_allowed=host in allowed_hosts,
        port_allowed=port in allowed_ports,
        valid_scheme=parsed.scheme == "http",
    )


def run_preflight(config: dict[str, Any]) -> PreflightResult:
    issues = validate_preflight_config(config)

    policy = config["network_policy"]
    allowed_hosts = policy["allowed_hosts"]
    allowed_ports = policy["allowed_ports"]

    endpoint_checks = [
        check_endpoint(ep, allowed_hosts, allowed_ports)
        for ep in config["endpoint_candidates"]
    ]
    all_endpoints_valid = all(item.valid for item in endpoint_checks)

    target_model = str(config["target_model"])
    allowlist = [str(item) for item in config["model_allowlist"]]
    model_allowed = any(pattern in target_model for pattern in allowlist)

    forbidden_hosts = set(policy["forbidden_hosts"])
    forbidden_host_rejected = all((urlparse(ep).hostname or "") not in forbidden_hosts for ep in config["endpoint_candidates"])

    ollama_path = shutil.which("ollama")
    ollama_found = ollama_path is not None

    generate_api_called = False
    chat_api_called = False

    ready_for_connecting_stage = (
        len(issues) == 0
        and all_endpoints_valid
        and model_allowed
        and forbidden_host_rejected
        and ollama_found
        and (generate_api_called is False)
        and (chat_api_called is False)
        and config["real_llm_call_allowed"] is False
    )

    return PreflightResult(
        config_valid=(len(issues) == 0),
        config_issues=issues,
        ollama_binary_found=ollama_found,
        ollama_binary_path=ollama_path,
        endpoint_checks=endpoint_checks,
        all_endpoints_valid=all_endpoints_valid,
        model_allowed=model_allowed,
        forbidden_host_rejected=forbidden_host_rejected,
        generate_api_called=generate_api_called,
        chat_api_called=chat_api_called,
        ready_for_connecting_stage=ready_for_connecting_stage,
    )


def load_and_run(path: Path | None = None) -> tuple[dict[str, Any], PreflightResult]:
    config = load_json(path or CONFIG_PATH)
    result = run_preflight(config)
    if result.config_issues:
        raise RuntimeError("GIB beta0.5 preflight config validation failed: " + "; ".join(result.config_issues))
    return config, result
