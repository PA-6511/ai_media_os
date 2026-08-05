#!/usr/bin/env python3
"""Phase 7-4  1件限定 実下書き作成 最終実行ゲート
WordPress REST API POST は一切行わない。
Phase 7-2 payload と Phase 7-3 human approval result を突き合わせ、
LIVE実行可能条件が全て揃っているかを判定して証跡だけ保存する。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "exchange/logs"

PHASE7_2_RESULT = LOGS / "phase7_2_single_draft_create_execution_dry_run_result.json"
PHASE7_3_RESULT = LOGS / "phase7_3_single_draft_create_final_approval_result.json"
PAYLOAD_FILE = ROOT / "exchange/outgoing/wordpress_draft_create_payload.dry_run.json"
OUTPUT = LOGS / "phase7_4_single_draft_create_execution_gate_result.json"

# 安全定数 ─ 変更禁止
_WORDPRESS_POST_ENABLED = False
_REAL_WRITE_ENABLED = False
_WORDPRESS_WRITE_EXECUTED = False


def _abort(reason: str, gate_checks: list | None = None) -> dict:
    return {
        "package_type": "phase7_4_single_draft_create_execution_gate_result",
        "phase": "Phase 7-4",
        "status": "ABORT",
        "reason": reason,
        "gate_passed": False,
        "gate_checks": gate_checks or [],
        "wordpress_post_enabled": _WORDPRESS_POST_ENABLED,
        "real_write_enabled": _REAL_WRITE_ENABLED,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": _WORDPRESS_WRITE_EXECUTED,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_gate(
    phase7_2_result_path: Path = PHASE7_2_RESULT,
    phase7_3_result_path: Path = PHASE7_3_RESULT,
    payload_path: Path = PAYLOAD_FILE,
    output_path: Path = OUTPUT,
) -> dict:

    gate_checks = []

    def check(name: str, passed: bool, detail: str = "") -> bool:
        gate_checks.append({"check": name, "passed": passed, "detail": detail})
        return passed

    # ── Phase 7-2 ロード ──────────────────────────────────────────────────
    if not phase7_2_result_path.exists():
        return _abort(f"Phase 7-2 result not found: {phase7_2_result_path}")
    try:
        p72 = json.loads(phase7_2_result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in Phase 7-2 result: {e}")

    check("phase7_2_status_pass", p72.get("status") == "PASS", p72.get("status", ""))
    check("phase7_2_dry_run_completed", p72.get("dry_run_completed") is True)
    check("phase7_2_wordpress_post_enabled_false", p72.get("wordpress_post_enabled") is False)
    check("phase7_2_real_write_enabled_false", p72.get("real_write_enabled") is False)
    check("phase7_2_wordpress_write_executed_false", p72.get("wordpress_write_executed") is False)

    # ── payload ロード ────────────────────────────────────────────────────
    if not payload_path.exists():
        return _abort(f"dry-run payload not found: {payload_path}", gate_checks)
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in payload: {e}", gate_checks)

    check("payload_dry_run_true", payload.get("dry_run") is True)
    check("payload_post_must_not_be_called", payload.get("wordpress_post_must_not_be_called") is True)
    check("payload_status_is_draft", payload.get("status") == "draft", payload.get("status", ""))

    # ── Phase 7-3 ロード ──────────────────────────────────────────────────
    if not phase7_3_result_path.exists():
        return _abort(f"Phase 7-3 result not found: {phase7_3_result_path}", gate_checks)
    try:
        p73 = json.loads(phase7_3_result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in Phase 7-3 result: {e}", gate_checks)

    check("phase7_3_status_pass", p73.get("status") == "PASS", p73.get("status", ""))
    check(
        "phase7_3_decision_dry_run_only",
        p73.get("decision") == "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY",
        p73.get("decision", ""),
    )
    check("phase7_3_checklist_all_confirmed", p73.get("checklist_all_confirmed") is True)
    check("phase7_3_reviewer_is_human", p73.get("reviewer_is_human") is True)
    check("phase7_3_wordpress_post_enabled_false", p73.get("wordpress_post_enabled") is False)
    check("phase7_3_real_write_enabled_false", p73.get("real_write_enabled") is False)
    check("phase7_3_wordpress_write_executed_false", p73.get("wordpress_write_executed") is False)

    # ── 全チェック評価 ────────────────────────────────────────────────────
    failed = [c for c in gate_checks if not c["passed"]]
    if failed:
        return _abort(
            f"gate failed: {[c['check'] for c in failed]}",
            gate_checks,
        )

    result = {
        "package_type": "phase7_4_single_draft_create_execution_gate_result",
        "phase": "Phase 7-4",
        "status": "PASS",
        "reason": "all gate checks passed. WordPress POST is still not executed.",
        "gate_passed": True,
        "gate_check_count": len(gate_checks),
        "gate_checks": gate_checks,
        "wordpress_post_enabled": _WORDPRESS_POST_ENABLED,
        "real_write_enabled": _REAL_WRITE_ENABLED,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": _WORDPRESS_WRITE_EXECUTED,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "phase7_5_single_draft_create_live_execution_or_freeze",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
