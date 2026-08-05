#!/usr/bin/env python3
"""Phase 8-36: レポート生成。validate の出力を読み MD + JSON に整形する。"""
import json
from datetime import datetime, timezone
from pathlib import Path

from validate_phase8_36_one_shot_draft_creation_dry_run_handoff import validate

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "exchange/logs/phase8_36_one_shot_draft_creation_dry_run_handoff_result.json"
REPORT_JSON = ROOT / "exchange/logs/phase8_36_one_shot_draft_creation_dry_run_handoff_report.json"
REPORT_MD = ROOT / "exchange/logs/phase8_36_one_shot_draft_creation_dry_run_handoff_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_markdown(r: dict) -> str:
    lines = [
        "# Phase 8-36: One-shot Draft Creation Dry-Run Handoff Report",
        "",
        "## Status",
        f"- status: {r.get('status')}",
        f"- production_status: {r.get('production_status')}",
        f"- execution: {r.get('execution')}",
        f"- credentials_ready: {r.get('credentials_ready')}",
        f"- handoff_status: {r.get('handoff_status')}",
        f"- handoff_allowed: {r.get('handoff_allowed')}",
        "",
        "## Safety",
        f"- wordpress_api_call_attempted: {r.get('wordpress_api_call_attempted')}",
        f"- wordpress_write_executed: {r.get('wordpress_write_executed')}",
        f"- wordpress_draft_created: {r.get('wordpress_draft_created')}",
        f"- actual_go_decision_issued: {r.get('actual_go_decision_issued')}",
        f"- executed_external_changes: {r.get('executed_external_changes')}",
        f"- secret_values_output: {r.get('secret_values_output')}",
        "",
        "## Blocked Reasons",
    ]
    br = r.get("blocked_reasons", [])
    lines += [f"- {b}" for b in br] if br else ["- none"]
    lines += ["", "## Next Step", f"- {r.get('next_step')}"]
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
    print(json.dumps({k: v for k, v in result.items() if k not in ("schedule",)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
