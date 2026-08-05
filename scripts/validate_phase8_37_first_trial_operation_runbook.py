#!/usr/bin/env python3
"""Phase 8-37: 試験稼働 Runbook 最終版バリデータ。

Runbook ファイルが存在し、必須章が全て含まれているかを確認する。
WordPress API 呼び出し・外部状態変更は行わない。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/phase8_37_first_trial_operation_runbook_policy.json"
RUNBOOK = ROOT / "docs/runbooks/phase8_37_first_trial_operation_runbook_final.md"
OUTPUT_RESULT = ROOT / "exchange/logs/phase8_37_first_trial_operation_runbook_result.json"
OUTPUT_REPORT_JSON = ROOT / "exchange/logs/phase8_37_first_trial_operation_runbook_report.json"
OUTPUT_REPORT_MD = ROOT / "exchange/logs/phase8_37_first_trial_operation_runbook_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_required_sections(runbook_text: str, required_sections: list) -> tuple[list, list]:
    present = []
    missing = []
    for section in required_sections:
        if section in runbook_text:
            present.append(section)
        else:
            missing.append(section)
    return present, missing


def validate(
    policy_path: Path = POLICY,
    runbook_path: Path = RUNBOOK,
    output_result_path: Path = OUTPUT_RESULT,
    output_report_json_path: Path = OUTPUT_REPORT_JSON,
    output_report_md_path: Path = OUTPUT_REPORT_MD,
) -> dict:
    base: dict = {
        "phase": "8-37",
        "phase_name": "First Trial Operation Runbook Final",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "one_shot_target_count": 1,
        "rollback_executed": False,
        "freeze_executed": False,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_masks_output": False,
        "secret_hashes_output": False,
        "executed_external_changes": 0,
        "checked_at": _now_iso(),
    }

    try:
        policy = _load_json(policy_path)
    except Exception as exc:
        result = {
            **base,
            "status": "ABORT_RUNBOOK_REQUIRED_SECTION_MISSING_NO_EXECUTION",
            "fail_list": [f"policy_load_error: {exc}"],
            "runbook_exists": False,
        }
        for p in (output_result_path, output_report_json_path):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    required_sections = policy.get("required_runbook_sections", [])

    runbook_exists = runbook_path.exists()
    if not runbook_exists:
        result = {
            **base,
            "status": "ABORT_RUNBOOK_REQUIRED_SECTION_MISSING_NO_EXECUTION",
            "runbook_exists": False,
            "fail_list": ["runbook_file_missing"],
        }
        for p in (output_result_path, output_report_json_path):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    runbook_text = runbook_path.read_text(encoding="utf-8")
    present, missing = _check_required_sections(runbook_text, required_sections)

    fail_list = [f"missing_section: {s}" for s in missing]
    status = (
        "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION"
        if not missing
        else "ABORT_RUNBOOK_REQUIRED_SECTION_MISSING_NO_EXECUTION"
    )

    result = {
        **base,
        "status": status,
        "runbook_exists": True,
        "runbook_path": str(runbook_path),
        "required_section_count": len(required_sections),
        "present_section_count": len(present),
        "missing_section_count": len(missing),
        "missing_sections": missing,
        "fail_list": fail_list,
        "warn_list": [],
    }

    md_lines = [
        "# Phase 8-37: Trial Operation Runbook Validation Report",
        "",
        f"- status: {status}",
        f"- production_status: NO_GO",
        f"- runbook_exists: {runbook_exists}",
        f"- required_sections: {len(required_sections)}",
        f"- present: {len(present)}",
        f"- missing: {len(missing)}",
        "",
        "## Missing Sections",
    ]
    md_lines += [f"- {s}" for s in missing] if missing else ["- none"]

    for p, content in [
        (output_result_path, json.dumps(result, ensure_ascii=False, indent=2)),
        (output_report_json_path, json.dumps(result, ensure_ascii=False, indent=2)),
        (output_report_md_path, "\n".join(md_lines) + "\n"),
    ]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    return result


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
