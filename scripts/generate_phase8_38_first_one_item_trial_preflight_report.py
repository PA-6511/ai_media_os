#!/usr/bin/env python3
"""Phase 8-38: preflight レポート生成。"""
import json
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_phase8_38_first_one_item_trial_preflight import validate

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "exchange/logs/phase8_38_first_one_item_trial_preflight_result.json"
REPORT_JSON = ROOT / "exchange/logs/phase8_38_first_one_item_trial_preflight_report.json"
REPORT_MD = ROOT / "exchange/logs/phase8_38_first_one_item_trial_preflight_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_markdown(r: dict) -> str:
    lines = [
        "# Phase 8-38: First One-Item Trial Preflight Report",
        "",
        "## Status",
        f"- status: {r.get('status')}",
        f"- production_status: {r.get('production_status')}",
        f"- execution: {r.get('execution')}",
        f"- phase8_36_status: {r.get('phase8_36_status')}",
        f"- phase8_37_status: {r.get('phase8_37_status')}",
        "",
        "## Preflight Flags",
        f"- target_item_selected: {r.get('target_item_selected')}",
        f"- affiliate_disclosure_present: {r.get('affiliate_disclosure_present')}",
        f"- pr_label_present: {r.get('pr_label_present')}",
        f"- cta_policy_checked: {r.get('cta_policy_checked')}",
        f"- one_shot_lock_exists_simulated: {r.get('one_shot_lock_exists_simulated')}",
        f"- human_approval_present: {r.get('human_approval_present')}",
        "",
        "## Safety",
        f"- wordpress_write_executed: {r.get('wordpress_write_executed')}",
        f"- executed_external_changes: {r.get('executed_external_changes')}",
        f"- secret_output_safe: {r.get('secret_output_safe')}",
        "",
        "## Blocked Reasons",
    ]
    br = r.get("blocked_reasons", [])
    lines += [f"- {b}" for b in br] if br else ["- none"]
    return "\n".join(lines) + "\n"


def generate_report(
    result_path: Path = RESULT_PATH,
    report_json_path: Path = REPORT_JSON,
    report_md_path: Path = REPORT_MD,
) -> dict:
    if result_path.exists():
        r = json.loads(result_path.read_text(encoding="utf-8"))
    else:
        r = validate(output_path=result_path)

    report = {**r, "report_generated_at": _now_iso()}
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md_path.write_text(build_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    result = generate_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
