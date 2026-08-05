#!/usr/bin/env python3
"""Phase 8-1 公開前レビュー設計バリデータ（設計のみ）"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/wordpress_draft_phase8_1_pre_publish_review_design.json"
OUTPUT = ROOT / "exchange/logs/phase8_1_pre_publish_review_design_validation_result.json"
PHASE7_6 = ROOT / "exchange/logs/phase7_6_wordpress_draft_creation_overall_completion_report.json"

REQUIRED_FALSE_FLAGS = [
    "wordpress_post_enabled",
    "real_write_enabled",
    "wordpress_write_executed",
]

REQUIRED_NO_GO_FLAGS = [
    "production_status",
    "wordpress_publish_execution",
]

MIN_REVIEW_ITEMS = 8
MIN_BLOCK_CONDITIONS = 8
MIN_FORBIDDEN_ACTIONS = 10



def _abort(reason: str) -> dict:
    return {
        "package_type": "phase8_1_pre_publish_review_design_validation_result",
        "phase": "Phase 8-1",
        "status": "ABORT",
        "reason": reason,
        "design_ready": False,
        "wordpress_post_enabled": None,
        "real_write_enabled": None,
        "production_status": None,
        "wordpress_publish_execution": None,
        "wordpress_write_executed": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }



def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))



def run_validation(config_path: Path = CONFIG, output_path: Path = OUTPUT) -> dict:
    if not config_path.exists():
        result = _abort(f"config not found: {config_path}")
    elif not PHASE7_6.exists():
        result = _abort(f"phase7_6 log not found: {PHASE7_6}")
    else:
        try:
            data = _load_json(config_path)
            p76 = _load_json(PHASE7_6)
        except json.JSONDecodeError as e:
            result = _abort(f"invalid JSON: {e}")
        else:
            if data.get("design_status") != "DESIGN_ONLY":
                result = _abort("design_status must be DESIGN_ONLY")
            elif p76.get("status") != "PASS":
                result = _abort("phase7_6 status must be PASS")
            elif p76.get("wordpress_draft_id") != data.get("target_draft", {}).get("wordpress_draft_id"):
                result = _abort("target_draft.wordpress_draft_id must match phase7_6 wordpress_draft_id")
            elif p76.get("created_post_status") != "draft":
                result = _abort("phase7_6 created_post_status must be draft")
            else:
                # false flags
                bad_flag = next((f for f in REQUIRED_FALSE_FLAGS if data.get(f) is not False), None)
                if bad_flag:
                    result = _abort(f"{bad_flag} must be false")
                else:
                    bad_no_go = next((f for f in REQUIRED_NO_GO_FLAGS if data.get(f) != "NO_GO"), None)
                    if bad_no_go:
                        result = _abort(f"{bad_no_go} must be NO_GO")
                    else:
                        review = data.get("review_checklist", [])
                        blocks = data.get("publish_block_conditions", [])
                        forbidden = data.get("forbidden_actions_in_phase8_1", [])

                        if not isinstance(review, list) or len(review) < MIN_REVIEW_ITEMS:
                            result = _abort(f"review_checklist must have at least {MIN_REVIEW_ITEMS} items")
                        elif not isinstance(blocks, list) or len(blocks) < MIN_BLOCK_CONDITIONS:
                            result = _abort(f"publish_block_conditions must have at least {MIN_BLOCK_CONDITIONS} items")
                        elif not isinstance(forbidden, list) or len(forbidden) < MIN_FORBIDDEN_ACTIONS:
                            result = _abort(f"forbidden_actions_in_phase8_1 must have at least {MIN_FORBIDDEN_ACTIONS} items")
                        else:
                            mandatory_items = [item for item in review if item.get("mandatory") is True]
                            if len(mandatory_items) < MIN_REVIEW_ITEMS:
                                result = _abort("all review checklist items must be mandatory in phase8_1 design")
                            else:
                                current_result = data.get("pass_condition", {}).get("current_result")
                                if current_result not in {
                                    "PRE_PUBLISH_REVIEW_DESIGN_READY",
                                    "PRE_PUBLISH_REVIEW_NEEDS_FIX",
                                    "PRE_PUBLISH_REVIEW_BLOCKED",
                                }:
                                    result = _abort("invalid pass_condition.current_result")
                                else:
                                    result = {
                                        "package_type": "phase8_1_pre_publish_review_design_validation_result",
                                        "phase": "Phase 8-1",
                                        "status": "PASS",
                                        "reason": "pre-publish review design is valid and keeps publish execution locked",
                                        "design_ready": True,
                                        "design_status": data.get("design_status"),
                                        "target_draft_id": data.get("target_draft", {}).get("wordpress_draft_id"),
                                        "target_draft_status": data.get("target_draft", {}).get("expected_status"),
                                        "current_result": current_result,
                                        "review_item_count": len(review),
                                        "mandatory_item_count": len(mandatory_items),
                                        "publish_block_condition_count": len(blocks),
                                        "forbidden_action_count": len(forbidden),
                                        "phase7_overall_status": p76.get("phase7_overall_status"),
                                        "wordpress_post_enabled": data.get("wordpress_post_enabled"),
                                        "real_write_enabled": data.get("real_write_enabled"),
                                        "production_status": data.get("production_status"),
                                        "wordpress_publish_execution": data.get("wordpress_publish_execution"),
                                        "wordpress_write_executed": data.get("wordpress_write_executed"),
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
