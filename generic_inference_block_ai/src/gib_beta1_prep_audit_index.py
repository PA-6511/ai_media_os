from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
REPORTS_DIR = _ROOT / "reports"

_REQUIRED_REFERENCE_REPORTS = (
    "gib_beta099_freeze_report.json",
    "gib_beta1_prep_validation_report.json",
)


@dataclass
class GuardrailContinuity:
    all_real_llm_call_allowed_false: bool
    all_execution_allowed_false: bool
    all_can_execute_now_false: bool
    violations: list[str]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def _as_bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _extract_index_item(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    safety = report.get("safety_summary", {})
    phase = report.get("phase")
    if not isinstance(phase, str):
        if report.get("report_type") == "BETA099_FINAL_FREEZE_REPORT":
            phase = "freeze_alpha0_beta099"
        else:
            phase = "unknown"

    final_status = report.get("final_status")
    if not isinstance(final_status, str):
        final_status = str(report.get("report_type", "UNKNOWN"))

    status = report.get("status")
    if not isinstance(status, str):
        status = "N/A"

    production_status = report.get("production_status")
    if not isinstance(production_status, str):
        from_safety = safety.get("production_status")
        production_status = from_safety if isinstance(from_safety, str) else "UNKNOWN"

    can_execute_now = _as_bool_or_none(report.get("can_execute_now"))
    if can_execute_now is None:
        can_execute_now = _as_bool_or_none(safety.get("can_execute_now"))

    real_llm_call_allowed = _as_bool_or_none(report.get("real_llm_call_allowed"))
    if real_llm_call_allowed is None:
        real_llm_call_allowed = _as_bool_or_none(safety.get("real_llm_call_allowed"))

    execution_allowed = _as_bool_or_none(report.get("execution_allowed"))
    if execution_allowed is None:
        execution_allowed = _as_bool_or_none(safety.get("execution_allowed"))

    return {
        "report_file": path.name,
        "phase": phase,
        "final_status": final_status,
        "status": status,
        "production_status": production_status,
        "can_execute_now": can_execute_now,
        "real_llm_call_allowed": real_llm_call_allowed,
        "execution_allowed": execution_allowed,
    }


def _evaluate_guardrail_continuity(index_items: list[dict[str, Any]]) -> GuardrailContinuity:
    violations: list[str] = []

    for item in index_items:
        file_name = item["report_file"]

        real_flag = item.get("real_llm_call_allowed")
        if real_flag is True:
            violations.append(f"{file_name}: real_llm_call_allowed=true")

        exec_flag = item.get("execution_allowed")
        if exec_flag is True:
            violations.append(f"{file_name}: execution_allowed=true")

        run_flag = item.get("can_execute_now")
        if run_flag is True:
            violations.append(f"{file_name}: can_execute_now=true")

    return GuardrailContinuity(
        all_real_llm_call_allowed_false=all(item.get("real_llm_call_allowed") is not True for item in index_items),
        all_execution_allowed_false=all(item.get("execution_allowed") is not True for item in index_items),
        all_can_execute_now_false=all(item.get("can_execute_now") is not True for item in index_items),
        violations=violations,
    )


def build_beta1_prep_audit_index(reports_dir: Path | None = None) -> dict[str, Any]:
    base_dir = reports_dir or REPORTS_DIR
    files = sorted(base_dir.glob("gib_*.json"))

    items: list[dict[str, Any]] = []
    for path in files:
        data = _read_json(path)
        items.append(_extract_index_item(path, data))

    continuity = _evaluate_guardrail_continuity(items)

    existing = {path.name for path in files}
    missing_refs = [name for name in _REQUIRED_REFERENCE_REPORTS if name not in existing]

    return {
        "schema_version": "gib.beta1.prep.audit_index.v0.1",
        "block_id": "GIB",
        "phase": "beta1_prep_a",
        "report_type": "BETA1_PREP_AUDIT_INDEX_REPORTS_ONLY",
        "production_status": "NO_GO",
        "write_scope": "generic_inference_block_ai/reports",
        "report_count": len(items),
        "index": items,
        "required_reference_reports": list(_REQUIRED_REFERENCE_REPORTS),
        "missing_reference_reports": missing_refs,
        "reference_reports_ready": len(missing_refs) == 0,
        "pre_beta1_final_reference": {
            "freeze_report": "gib_beta099_freeze_report.json",
            "prep_report": "gib_beta1_prep_validation_report.json",
        },
        "guardrail_continuity": {
            "all_real_llm_call_allowed_false": continuity.all_real_llm_call_allowed_false,
            "all_execution_allowed_false": continuity.all_execution_allowed_false,
            "all_can_execute_now_false": continuity.all_can_execute_now_false,
            "violations": continuity.violations,
        },
        "final_status": (
            "PASS_REPORTS_ONLY_BETA1_PREP_AUDIT_INDEX_FIXED"
            if len(missing_refs) == 0
            and continuity.all_real_llm_call_allowed_false
            and continuity.all_execution_allowed_false
            and continuity.all_can_execute_now_false
            else "FAIL_BETA1_PREP_AUDIT_INDEX"
        ),
    }


def write_beta1_prep_audit_index(reports_dir: Path | None = None) -> Path:
    base_dir = reports_dir or REPORTS_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    report = build_beta1_prep_audit_index(base_dir)
    output_path = base_dir / "gib_beta1_prep_audit_index_report.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path
