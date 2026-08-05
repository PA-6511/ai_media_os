#!/usr/bin/env python3
"""Phase 7-5E FREEZE確定レポート生成

目的:
- Phase 7-5E の判断が FREEZE であることを最終証跡化する
- 本スクリプトは WordPress REST API POST を実行しない
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "exchange/logs"

PHASE7_5E_RESULT = LOGS / "phase7_5e_manual_go_freeze_decision_result.json"
PHASE7_5D_RESULT = LOGS / "phase7_5d_single_draft_live_manual_runbook_generation_result.json"
PHASE7_5C_RESULT = LOGS / "phase7_5c_single_draft_create_live_result.json"

OUTPUT_JSON = LOGS / "phase7_5e_freeze_completion_report.json"
OUTPUT_MD = LOGS / "phase7_5e_freeze_completion_report.md"


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
        "package_type": "phase7_5e_freeze_completion_report",
        "phase": "Phase 7-5E",
        "status": "ABORT",
        "reason": reason,
        "freeze_confirmed": False,
        "current_decision": None,
        "live_execution_allowed": False,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
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
    phase7_5e_path: Path = PHASE7_5E_RESULT,
    phase7_5d_path: Path = PHASE7_5D_RESULT,
    phase7_5c_path: Path = PHASE7_5C_RESULT,
) -> dict[str, Any]:
    if not phase7_5e_path.exists():
        return _abort(f"missing prerequisite: {phase7_5e_path}")
    if not phase7_5d_path.exists():
        return _abort(f"missing prerequisite: {phase7_5d_path}")
    if not phase7_5c_path.exists():
        return _abort(f"missing prerequisite: {phase7_5c_path}")

    p75e = _load_json(phase7_5e_path)
    p75d = _load_json(phase7_5d_path)
    p75c = _load_json(phase7_5c_path)

    if p75e.get("status") != "PASS":
        return _abort("phase7_5e status must be PASS")
    if p75e.get("decision") != "FREEZE":
        return _abort("phase7_5e decision must be FREEZE")
    if p75d.get("status") != "PASS":
        return _abort("phase7_5d status must be PASS")
    if p75c.get("wordpress_write_executed") is not False:
        return _abort("phase7_5c wordpress_write_executed must be false for FREEZE report")

    result = {
        "package_type": "phase7_5e_freeze_completion_report",
        "phase": "Phase 7-5E",
        "status": "PASS",
        "reason": "FREEZE decision confirmed and no live write executed",
        "freeze_confirmed": True,
        "current_decision": "FREEZE",
        "decision_recorded": True,
        "reviewer_is_human": p75e.get("reviewer_is_human", False),
        "manual_decision_recorded": p75e.get("manual_decision_recorded", False),
        "live_execution_allowed": False,
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "phase_checks": [
            {"phase": "7-5C", "check": "wordpress_write_executed=false", "passed": True},
            {"phase": "7-5D", "check": "status=PASS", "passed": True},
            {"phase": "7-5E", "check": "status=PASS and decision=FREEZE", "passed": True},
        ],
        "next_step": "freeze_maintain_or_manual_go_redecision",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(OUTPUT_JSON, result)
    return result


def build_md(report: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-5E FREEZE確定レポート",
        "",
        f"生成日時: {report.get('generated_at', '')}",
        "",
        "## 判定サマリー",
        "",
        f"| 項目 | 値 |",
        f"|------|-----|",
        f"| status | {report.get('status')} |",
        f"| freeze_confirmed | {report.get('freeze_confirmed')} |",
        f"| current_decision | {report.get('current_decision')} |",
        f"| live_execution_allowed | {report.get('live_execution_allowed')} |",
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
        mark = "PASS" if item.get("passed") else "FAIL"
        lines.append(f"| {item.get('phase')} | {item.get('check')} | {mark} |")

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
    report = run_generate()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
