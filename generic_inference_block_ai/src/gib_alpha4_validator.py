from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha4_gate import (
    evaluate_runtime_gate,
    get_alpha_policy_flags,
    load_and_validate_gate_config,
)

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"


def validate_alpha4_contract() -> dict[str, Any]:
    gate_config = load_and_validate_gate_config()
    flags = get_alpha_policy_flags()

    scenarios = [
        {"requested_runtime": "stub", "expected_allowed": True},
        {"requested_runtime": "ollama", "expected_allowed": False},
        {"requested_runtime": "llama_cpp", "expected_allowed": False},
        {"requested_runtime": "unknown_runtime", "expected_allowed": False},
    ]

    results = []
    for index, scenario in enumerate(scenarios):
        decision = evaluate_runtime_gate(
            requested_runtime=scenario["requested_runtime"],
            policy_flags=flags,
            gate_config=gate_config,
        )
        matches_expected = decision.allowed is scenario["expected_allowed"]
        results.append(
            {
                "index": index,
                "requested_runtime": decision.requested_runtime,
                "active_runtime": decision.active_runtime,
                "allowed": decision.allowed,
                "expected_allowed": scenario["expected_allowed"],
                "matches_expected": matches_expected,
                "blocked_reason": decision.blocked_reason,
                "required_flags": decision.required_flags,
                "missing_flags": decision.missing_flags,
            }
        )

    all_expected = all(item["matches_expected"] for item in results)
    hard_block_ok = all(
        item["allowed"] is False
        for item in results
        if item["requested_runtime"] in ["ollama", "llama_cpp"]
    )

    final_status = (
        "PASS_DESIGN_ONLY_ALPHA4_RUNTIME_GATE_FIXED"
        if all_expected and hard_block_ok
        else "FAIL_ALPHA4_RUNTIME_GATE"
    )

    return {
        "schema_version": "gib.alpha4.validation_report.v0.1",
        "block_id": "GIB",
        "alpha_version": "alpha4",
        "final_status": final_status,
        "production_status": gate_config["production_status"],
        "execution_mode": gate_config["execution_mode"],
        "active_runtime_lock": gate_config["active_runtime_lock"],
        "policy_flags": flags,
        "all_scenarios_match_expected": all_expected,
        "hard_block_for_non_stub_runtime": hard_block_ok,
        "scenario_count": len(results),
        "scenario_results": results,
        "beta0_promotion_requirements": gate_config["beta0_promotion_requirements"],
    }


def write_alpha4_validation_report() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = validate_alpha4_contract()
    output_path = REPORTS_DIR / "gib_alpha4_validation_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
