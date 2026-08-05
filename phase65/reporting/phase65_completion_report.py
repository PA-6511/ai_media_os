from __future__ import annotations

import json
from pathlib import Path


REQUIRED_KEYS = [
    "completion_status",
    "phase_range",
    "phases_passed_count",
    "total_phases_in_scope",
    "pass_evidence_summary",
    "safety_boundaries",
    "unreleased_items",
    "next_stage_go_no_go_conditions",
    "recommended_next_step",
]


REQUIRED_SAFETY_FLAGS = {
    "dry_run_fixed": True,
    "human_approval_required": True,
    "can_execute": False,
    "execute_allowed": False,
    "max_files_to_execute": 1,
    "sandbox_scope_required": True,
    "single_file_scope_required": True,
    "does_not_execute_guards": True,
}


def write_phase65_completion_report(payload: dict, output_path: str) -> dict:
    missing = [k for k in REQUIRED_KEYS if k not in payload]
    if missing:
        return {"status": "FAIL", "reason": f"missing keys: {missing}"}

    safety = payload.get("safety_boundaries")
    if not isinstance(safety, dict):
        return {"status": "FAIL", "reason": "safety_boundaries must be a dict"}

    invalid_flags: list[str] = []
    for key, expected in REQUIRED_SAFETY_FLAGS.items():
        if safety.get(key) != expected:
            invalid_flags.append(f"safety_boundaries.{key} must be {expected}")

    if invalid_flags:
        return {"status": "FAIL", "reason": "; ".join(invalid_flags)}

    report = {
        "phase": "65",
        "report_type": "manual_dry_run_pre_execution_design_completion_report",
        "scope": "phase15_to_phase64",
        **payload,
    }

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "PASS", "output_path": str(path)}
