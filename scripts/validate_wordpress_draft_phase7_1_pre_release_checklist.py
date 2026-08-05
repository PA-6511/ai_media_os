#!/usr/bin/env python3
"""Phase 7-1 手動解放前チェックリスト設計 バリデータ"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/wordpress_draft_phase7_1_pre_release_checklist.json"
OUTPUT = ROOT / "exchange/logs/phase7_1_pre_release_checklist_validation_result.json"

REQUIRED_FALSE_FLAGS = [
    "wordpress_post_enabled",
    "real_write_enabled",
    "wordpress_write_executed",
]

REQUIRED_NO_GO_FLAGS = [
    "production_status",
    "wordpress_draft_creation",
]

REQUIRED_CHECKLIST_SECTIONS = [
    "prerequisite_phase_checks",
    "environment_checks",
    "content_quality_checks",
    "safety_checks",
    "forbidden_actions_on_checklist_pass",
    "checklist_pass_condition",
]

MIN_PREREQUISITE_CHECKS = 4
MIN_ENVIRONMENT_CHECKS = 4
MIN_CONTENT_QUALITY_CHECKS = 5
MIN_SAFETY_CHECKS = 8
MIN_FORBIDDEN_ACTIONS = 12


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_1_pre_release_checklist_validation_result",
        "phase": "Phase 7-1",
        "status": "ABORT",
        "reason": reason,
        "checklist_ready": False,
        "wordpress_post_enabled": None,
        "real_write_enabled": None,
        "production_status": None,
        "wordpress_draft_creation": None,
        "wordpress_write_executed": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(config_path: Path = CONFIG, output_path: Path = OUTPUT) -> dict:
    if not config_path.exists():
        return _abort(f"config not found: {config_path}")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON: {e}")

    # design_status 確認
    if data.get("design_status") != "DESIGN_ONLY":
        return _abort("design_status must be DESIGN_ONLY")

    # 本番系 false フラグ確認
    for flag in REQUIRED_FALSE_FLAGS:
        if data.get(flag) is not False:
            return _abort(f"{flag} must be false")

    # NO_GO フラグ確認
    for flag in REQUIRED_NO_GO_FLAGS:
        if data.get(flag) != "NO_GO":
            return _abort(f"{flag} must be NO_GO")

    # 必須セクション存在確認
    for section in REQUIRED_CHECKLIST_SECTIONS:
        if section not in data:
            return _abort(f"missing required section: {section}")

    # 各セクション件数確認
    pre = data.get("prerequisite_phase_checks", [])
    if not isinstance(pre, list) or len(pre) < MIN_PREREQUISITE_CHECKS:
        return _abort(
            f"prerequisite_phase_checks must have at least {MIN_PREREQUISITE_CHECKS} items"
        )

    env = data.get("environment_checks", [])
    if not isinstance(env, list) or len(env) < MIN_ENVIRONMENT_CHECKS:
        return _abort(
            f"environment_checks must have at least {MIN_ENVIRONMENT_CHECKS} items"
        )

    cq = data.get("content_quality_checks", [])
    if not isinstance(cq, list) or len(cq) < MIN_CONTENT_QUALITY_CHECKS:
        return _abort(
            f"content_quality_checks must have at least {MIN_CONTENT_QUALITY_CHECKS} items"
        )

    sf = data.get("safety_checks", [])
    if not isinstance(sf, list) or len(sf) < MIN_SAFETY_CHECKS:
        return _abort(
            f"safety_checks must have at least {MIN_SAFETY_CHECKS} items"
        )

    fa = data.get("forbidden_actions_on_checklist_pass", [])
    if not isinstance(fa, list) or len(fa) < MIN_FORBIDDEN_ACTIONS:
        return _abort(
            f"forbidden_actions_on_checklist_pass must have at least {MIN_FORBIDDEN_ACTIONS} items"
        )

    # 全 mandatory 項目の id 存在確認
    all_items = pre + env + cq + sf
    mandatory_items = [item for item in all_items if item.get("mandatory") is True]
    if len(mandatory_items) == 0:
        return _abort("no mandatory items found in checklist")

    # checklist_pass_condition の current_result 確認
    cpc = data.get("checklist_pass_condition", {})
    current_result = cpc.get("current_result")
    if current_result not in ("CHECKLIST_INCOMPLETE", "CHECKLIST_BLOCKED"):
        return _abort(
            "checklist_pass_condition.current_result must be CHECKLIST_INCOMPLETE or CHECKLIST_BLOCKED in design phase"
        )

    # wordpress_post_enabled が true なら即 ABORT（安全二重チェック）
    if data.get("wordpress_post_enabled") is True:
        return _abort("wordpress_post_enabled must not be true")

    result = {
        "package_type": "phase7_1_pre_release_checklist_validation_result",
        "phase": "Phase 7-1",
        "status": "PASS",
        "reason": "pre-release checklist design is valid and keeps wordpress_post_enabled false",
        "checklist_ready": True,
        "design_status": data.get("design_status"),
        "current_result": current_result,
        "mandatory_item_count": len(mandatory_items),
        "total_checklist_items": len(all_items),
        "forbidden_action_count": len(fa),
        "wordpress_post_enabled": data.get("wordpress_post_enabled"),
        "real_write_enabled": data.get("real_write_enabled"),
        "production_status": data.get("production_status"),
        "wordpress_draft_creation": data.get("wordpress_draft_creation"),
        "wordpress_write_executed": data.get("wordpress_write_executed", False),
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": data.get("next_step"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
