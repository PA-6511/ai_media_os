#!/usr/bin/env python3
"""SFB-12: Real-Data CSV運用固定 readiness チェック。

運用ルール文書とチェックリストの必須要素を検証し、
NO_GO維持のまま次工程へ進める準備状態を判定する。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/real_data_csv_operating_policy.json"
RUNBOOK_PATH = ROOT / "docs/runbooks/real_data_csv_import_runbook.md"
CHECKLIST_PATH = ROOT / "docs/runbooks/sfb_v1_trial_operation_checklist.md"
OUTPUT_PATH = ROOT / "logs/real_data_csv_operating_readiness.json"

READY_STATUS = "SFB12_REAL_DATA_CSV_OPERATING_RULES_LOCKED_READY"
BLOCKED_STATUS = "SFB12_REAL_DATA_CSV_OPERATING_RULES_LOCKED_BLOCKED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_all(text: str, required_tokens: list[str]) -> tuple[list[str], list[str]]:
    present: list[str] = []
    missing: list[str] = []
    for token in required_tokens:
        if token in text:
            present.append(token)
        else:
            missing.append(token)
    return present, missing


def evaluate(policy_path: Path = POLICY_PATH) -> dict:
    base = {
        "phase": "SFB-12",
        "phase_name": "Real-Data CSV Operating Runbook Lock",
        "checked_at": _now_iso(),
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "sfb_hold_fixed": True,
        "execution_allowed": False,
        "wordpress_write_executed": False,
        "approval_token_consumed": False,
    }

    fail_list: list[str] = []

    try:
        policy = _load_json(policy_path)
    except Exception as exc:
        return {
            **base,
            "status": BLOCKED_STATUS,
            "fail_list": [f"policy_load_error: {exc}"],
            "runbook_exists": False,
            "checklist_exists": False,
            "next_action": "STOP_AND_FIX",
        }

    runbook_exists = RUNBOOK_PATH.exists()
    checklist_exists = CHECKLIST_PATH.exists()

    runbook_text = RUNBOOK_PATH.read_text(encoding="utf-8") if runbook_exists else ""
    checklist_text = CHECKLIST_PATH.read_text(encoding="utf-8") if checklist_exists else ""

    required_sections = policy.get("required_runbook_sections", [])
    required_checklist_items = policy.get("required_checklist_items", [])

    present_sections, missing_sections = _contains_all(runbook_text, required_sections)
    present_checklist_items, missing_checklist_items = _contains_all(checklist_text, required_checklist_items)

    if not runbook_exists:
        fail_list.append("runbook_missing")
    if not checklist_exists:
        fail_list.append("checklist_missing")

    fail_list.extend([f"missing_runbook_section: {s}" for s in missing_sections])
    fail_list.extend([f"missing_checklist_item: {i}" for i in missing_checklist_items])

    no_go_safe = (
        base["production_status"] == "NO_GO"
        and base["execution_allowed"] is False
        and base["wordpress_write_executed"] is False
        and base["approval_token_consumed"] is False
    )

    if not no_go_safe:
        fail_list.append("no_go_invariant_violated")

    status = READY_STATUS if not fail_list else BLOCKED_STATUS

    result = {
        **base,
        "status": status,
        "runbook_exists": runbook_exists,
        "checklist_exists": checklist_exists,
        "required_runbook_section_count": len(required_sections),
        "present_runbook_section_count": len(present_sections),
        "missing_runbook_section_count": len(missing_sections),
        "missing_runbook_sections": missing_sections,
        "required_checklist_item_count": len(required_checklist_items),
        "present_checklist_item_count": len(present_checklist_items),
        "missing_checklist_item_count": len(missing_checklist_items),
        "missing_checklist_items": missing_checklist_items,
        "no_go_invariant_ok": no_go_safe,
        "next_action": "PROCEED_RULES_LOCK" if status == READY_STATUS else "STOP_AND_FIX",
        "fail_list": fail_list,
        "warn_list": [],
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="互換用フラグ（判定は常にDRY_RUN）")
    args = parser.parse_args()
    _ = args

    result = evaluate()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
