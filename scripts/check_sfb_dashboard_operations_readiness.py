#!/usr/bin/env python3
"""SFB-15: Dashboard Operations Runbook Lock readiness checker."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/sfb_15_dashboard_operations_runbook_lock_policy.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


def _contains_all(text: str, tokens: list[str]) -> tuple[list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for token in tokens:
        if token in text:
            present.append(token)
        else:
            missing.append(token)
    return present, missing


def _safe_load_json(path: Path) -> tuple[bool, dict[str, Any]]:
    if not path.exists():
        return False, {}
    try:
        return True, _read_json(path)
    except Exception:
        return False, {}


def evaluate(policy_path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    base = {
        "phase": "SFB-15",
        "phase_name": "SFB Dashboard Operations Runbook Lock",
        "checked_at": _now_iso(),
        "mode": "DRY_RUN",
        "production_status": "NO_GO",
        "wordpress_write_executed": False,
        "external_api_called": False,
        "external_network_called": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "human_approval_consumed": False,
    }

    try:
        policy = _read_json(policy_path)
    except Exception as exc:
        return {
            **base,
            "status": "SFB15_DASHBOARD_OPERATIONS_RUNBOOK_LOCK_BLOCKED",
            "fail_list": [f"policy_load_error: {exc}"],
            "warn_list": [],
            "next_action": "STOP_AND_FIX",
        }

    required_files = dict(policy.get("required_files", {}))
    required_runbook_sections = list(policy.get("required_runbook_sections", []))
    required_checklist_tokens = list(policy.get("required_checklist_tokens", []))

    runbook_path = _resolve(required_files.get("runbook", ""))
    checklist_path = _resolve(required_files.get("checklist", ""))
    sfb13_json_path = _resolve(required_files.get("sfb13_json", ""))
    sfb14_json_path = _resolve(required_files.get("sfb14_json", ""))

    output_path = _resolve(policy.get("output", {}).get("readiness_json", "logs/sfb_15_dashboard_operations_readiness.json"))

    fail_list: list[str] = []
    warn_list: list[str] = []

    runbook_exists = runbook_path.exists()
    checklist_exists = checklist_path.exists()

    if not runbook_exists:
        fail_list.append("runbook_missing")
    if not checklist_exists:
        fail_list.append("checklist_missing")

    runbook_text = runbook_path.read_text(encoding="utf-8") if runbook_exists else ""
    checklist_text = checklist_path.read_text(encoding="utf-8") if checklist_exists else ""

    present_sections, missing_sections = _contains_all(runbook_text, required_runbook_sections)
    present_tokens, missing_tokens = _contains_all(checklist_text, required_checklist_tokens)

    fail_list.extend([f"missing_runbook_section: {s}" for s in missing_sections])
    fail_list.extend([f"missing_checklist_token: {t}" for t in missing_tokens])

    sfb13_ok, sfb13_payload = _safe_load_json(sfb13_json_path)
    sfb14_ok, sfb14_payload = _safe_load_json(sfb14_json_path)

    if not sfb13_ok:
        fail_list.append("sfb13_json_missing_or_invalid")
    if not sfb14_ok:
        fail_list.append("sfb14_json_missing_or_invalid")

    sfb14_artifact_missing = int(sfb14_payload.get("artifact_missing", 0)) if sfb14_ok else -1
    if sfb14_ok and sfb14_artifact_missing > 0:
        warn_list.append(f"sfb14_artifact_missing: {sfb14_artifact_missing}")

    if sfb13_ok and sfb13_payload.get("production_status") != "NO_GO":
        fail_list.append("sfb13_no_go_violation")
    if sfb14_ok and sfb14_payload.get("production_status") != "NO_GO":
        fail_list.append("sfb14_no_go_violation")

    if sfb13_ok and sfb13_payload.get("mode") != "DRY_RUN":
        fail_list.append("sfb13_dry_run_violation")
    if sfb14_ok and sfb14_payload.get("mode") != "DRY_RUN":
        fail_list.append("sfb14_dry_run_violation")

    no_go_invariant_ok = (
        base["production_status"] == "NO_GO"
        and base["mode"] == "DRY_RUN"
        and base["external_api_called"] is False
        and base["external_network_called"] is False
        and base["wordpress_write_executed"] is False
        and base["approval_token_consumed"] is False
    )

    if not no_go_invariant_ok:
        fail_list.append("sfb15_no_go_invariant_violation")

    status = "SFB15_DASHBOARD_OPERATIONS_RUNBOOK_LOCK_READY" if not fail_list else "SFB15_DASHBOARD_OPERATIONS_RUNBOOK_LOCK_BLOCKED"

    result = {
        **base,
        "status": status,
        "runbook_exists": runbook_exists,
        "checklist_exists": checklist_exists,
        "required_runbook_section_count": len(required_runbook_sections),
        "present_runbook_section_count": len(present_sections),
        "missing_runbook_section_count": len(missing_sections),
        "missing_runbook_sections": missing_sections,
        "required_checklist_token_count": len(required_checklist_tokens),
        "present_checklist_token_count": len(present_tokens),
        "missing_checklist_token_count": len(missing_tokens),
        "missing_checklist_tokens": missing_tokens,
        "sfb13_json_found": sfb13_ok,
        "sfb14_json_found": sfb14_ok,
        "sfb14_artifact_missing": sfb14_artifact_missing,
        "no_go_invariant_ok": no_go_invariant_ok,
        "fail_list": fail_list,
        "warn_list": warn_list,
        "next_action": "PROCEED_RUNBOOK_LOCK" if status.endswith("READY") else "STOP_AND_FIX",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="policy json path")
    parser.add_argument("--dry-run", action="store_true", help="compat flag")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = ROOT / policy_path

    result = evaluate(policy_path=policy_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "SFB15_DASHBOARD_OPERATIONS_RUNBOOK_LOCK_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
