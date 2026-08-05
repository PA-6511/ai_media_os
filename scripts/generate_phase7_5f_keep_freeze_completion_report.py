#!/usr/bin/env python3
"""Phase 7-5F KEEP_FREEZE確定レポート生成"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "exchange/logs"

PHASE7_5F_RESULT = LOGS / "phase7_5f_manual_go_redecision_result.json"
PHASE7_5E_REPORT = LOGS / "phase7_5e_freeze_completion_report.json"
PHASE7_5C_RESULT = LOGS / "phase7_5c_single_draft_create_live_result.json"

OUTPUT_JSON = LOGS / "phase7_5f_keep_freeze_completion_report.json"
OUTPUT_MD = LOGS / "phase7_5f_keep_freeze_completion_report.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _abort(reason: str) -> dict[str, Any]:
    result = {
        "package_type": "phase7_5f_keep_freeze_completion_report",
        "phase": "Phase 7-5F",
        "status": "ABORT",
        "reason": reason,
        "phase7_5f_decision": None,
        "keep_freeze_confirmed": False,
        "live_execution_allowed": False,
        "phase7_5c_execution_unlocked_for_operator": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "manual_recheck_required",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(OUTPUT_JSON, result)
    return result


def build_report(
    phase7_5f_path: Path = PHASE7_5F_RESULT,
    phase7_5e_path: Path = PHASE7_5E_REPORT,
    phase7_5c_path: Path = PHASE7_5C_RESULT,
) -> dict[str, Any]:
    if not phase7_5f_path.exists():
        return _abort(f"missing prerequisite: {phase7_5f_path}")
    if not phase7_5e_path.exists():
        return _abort(f"missing prerequisite: {phase7_5e_path}")
    if not phase7_5c_path.exists():
        return _abort(f"missing prerequisite: {phase7_5c_path}")

    p75f = _load_json(phase7_5f_path)
    p75e = _load_json(phase7_5e_path)
    p75c = _load_json(phase7_5c_path)

    if p75f.get("status") != "PASS":
        return _abort("phase7_5f status must be PASS")
    if p75f.get("decision") != "KEEP_FREEZE":
        return _abort("phase7_5f decision must be KEEP_FREEZE")
    if p75f.get("phase7_5c_execution_unlocked_for_operator") is not False:
        return _abort("phase7_5c_execution_unlocked_for_operator must be false")

    if p75e.get("status") != "PASS":
        return _abort("phase7_5e freeze report status must be PASS")
    if p75e.get("current_decision") != "FREEZE":
        return _abort("phase7_5e current_decision must be FREEZE")

    if p75c.get("wordpress_write_executed") is not False:
        return _abort("phase7_5c wordpress_write_executed must be false")

    result = {
        "package_type": "phase7_5f_keep_freeze_completion_report",
        "phase": "Phase 7-5F",
        "status": "PASS",
        "reason": "KEEP_FREEZE decision confirmed and live execution remains locked",
        "phase7_5f_decision": "KEEP_FREEZE",
        "keep_freeze_confirmed": True,
        "live_execution_allowed": False,
        "phase7_5c_execution_unlocked_for_operator": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "phase_checks": [
            {
                "phase": "7-5C",
                "check": "wordpress_write_executed=false",
                "passed": True,
            },
            {
                "phase": "7-5E",
                "check": "status=PASS and current_decision=FREEZE",
                "passed": True,
            },
            {
                "phase": "7-5F",
                "check": "status=PASS and decision=KEEP_FREEZE and unlocked=false",
                "passed": True,
            },
        ],
        "next_step": "maintain_freeze_or_manual_go_redecision",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(OUTPUT_JSON, result)
    return result


def build_md(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-5F KEEP_FREEZE確定レポート",
        "",
        f"生成日時: {report.get('generated_at', '')}",
        "",
        "## 判定サマリー",
        "",
        "| 項目 | 値 |",
        "|------|----|",
        f"| status | {report.get('status')} |",
        f"| phase7_5f_decision | {report.get('phase7_5f_decision')} |",
        f"| keep_freeze_confirmed | {report.get('keep_freeze_confirmed')} |",
        f"| live_execution_allowed | {report.get('live_execution_allowed')} |",
        f"| phase7_5c_execution_unlocked_for_operator | {report.get('phase7_5c_execution_unlocked_for_operator')} |",
        f"| production_status | {report.get('production_status')} |",
        f"| wordpress_draft_creation | {report.get('wordpress_draft_creation')} |",
        f"| wordpress_write_executed | {report.get('wordpress_write_executed')} |",
        f"| next_step | {report.get('next_step')} |",
        "",
        "## フェーズ確認",
        "",
        "| フェーズ | チェック | 結果 |",
        "|---------|---------|------|",
    ]
    for item in report.get("phase_checks", []):
        lines.append(
            f"| {item.get('phase')} | {item.get('check')} | {'PASS' if item.get('passed') else 'FAIL'} |"
        )

    lines += [
        "",
        "## NO_GO 維持フラグ",
        "",
        f"- wordpress_post_enabled: {report.get('wordpress_post_enabled')}",
        f"- real_write_enabled: {report.get('real_write_enabled')}",
        f"- auto_post: {report.get('auto_post')}",
        f"- auto_update: {report.get('auto_update')}",
        f"- auto_delete: {report.get('auto_delete')}",
        f"- auto_export: {report.get('auto_export')}",
    ]

    return "\n".join(lines) + "\n"


def run_generate() -> dict[str, Any]:
    report = build_report()
    _write_md(OUTPUT_MD, build_md(report))
    return report


def main() -> int:
    result = run_generate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
