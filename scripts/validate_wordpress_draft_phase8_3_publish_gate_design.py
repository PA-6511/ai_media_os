#!/usr/bin/env python3
"""Phase 8-3 公開ゲート設計バリデータ（設計のみ）"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/wordpress_draft_phase8_3_publish_gate_design.json"
OUTPUT = ROOT / "exchange/logs/phase8_3_publish_gate_design_validation_result.json"
PHASE8_1 = ROOT / "exchange/logs/phase8_1_pre_publish_review_design_validation_result.json"
PHASE8_2 = ROOT / "exchange/logs/phase8_2_manual_pre_publish_review_result.json"
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

MIN_GATE_REQUIREMENTS = 8
MIN_FORBIDDEN_ACTIONS = 10


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase8_3_publish_gate_design_validation_result",
        "phase": "Phase 8-3",
        "status": "ABORT",
        "reason": reason,
        "gate_design_ready": False,
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
    elif not PHASE8_1.exists() or not PHASE8_2.exists() or not PHASE7_6.exists():
        result = _abort("required upstream logs not found")
    else:
        try:
            data = _load_json(config_path)
            p81 = _load_json(PHASE8_1)
            p82 = _load_json(PHASE8_2)
            p76 = _load_json(PHASE7_6)
        except json.JSONDecodeError as e:
            result = _abort(f"invalid JSON: {e}")
        else:
            if data.get("design_status") != "DESIGN_ONLY":
                result = _abort("design_status must be DESIGN_ONLY")
            elif p81.get("status") != "PASS":
                result = _abort("phase8_1 status must be PASS")
            elif p82.get("status") != "PASS":
                result = _abort("phase8_2 status must be PASS")
            elif p82.get("decision") != "APPROVE":
                result = _abort("phase8_2 decision must be APPROVE")
            elif p76.get("status") != "PASS":
                result = _abort("phase7_6 status must be PASS")
            else:
                target = data.get("target_draft", {})
                target_id = target.get("wordpress_draft_id")
                if target_id != p76.get("wordpress_draft_id") or target_id != p82.get("wordpress_draft_id"):
                    result = _abort("target_draft.wordpress_draft_id must match phase7_6 and phase8_2")
                elif target.get("expected_status") != "draft":
                    result = _abort("target_draft.expected_status must be draft")
                elif p76.get("created_post_status") != "draft" or p82.get("target_draft_status") != "draft":
                    result = _abort("upstream draft status must be draft")
                else:
                    bad_flag = next((f for f in REQUIRED_FALSE_FLAGS if data.get(f) is not False), None)
                    if bad_flag:
                        result = _abort(f"{bad_flag} must be false")
                    else:
                        bad_no_go = next((f for f in REQUIRED_NO_GO_FLAGS if data.get(f) != "NO_GO"), None)
                        if bad_no_go:
                            result = _abort(f"{bad_no_go} must be NO_GO")
                        else:
                            reqs = data.get("gate_requirements", [])
                            forbidden = data.get("forbidden_actions_in_phase8_3", [])
                            token = data.get("publish_token_rules", {})
                            current = data.get("gate_result", {}).get("current_result")

                            if not isinstance(reqs, list) or len(reqs) < MIN_GATE_REQUIREMENTS:
                                result = _abort(f"gate_requirements must have at least {MIN_GATE_REQUIREMENTS} items")
                            elif not isinstance(forbidden, list) or len(forbidden) < MIN_FORBIDDEN_ACTIONS:
                                result = _abort(f"forbidden_actions_in_phase8_3 must have at least {MIN_FORBIDDEN_ACTIONS} items")
                            elif token.get("one_time_only") is not True:
                                result = _abort("publish_token_rules.one_time_only must be true")
                            elif token.get("expires_minutes") != 30:
                                result = _abort("publish_token_rules.expires_minutes must be 30")
                            elif token.get("human_reviewer_required") is not True:
                                result = _abort("publish_token_rules.human_reviewer_required must be true")
                            elif token.get("publish_count_limit") != 1:
                                result = _abort("publish_token_rules.publish_count_limit must be 1")
                            elif current not in {
                                "PUBLISH_GATE_DESIGN_READY",
                                "PUBLISH_GATE_NEEDS_FIX",
                                "PUBLISH_GATE_BLOCKED",
                            }:
                                result = _abort("invalid gate_result.current_result")
                            else:
                                mandatory = [x for x in reqs if x.get("mandatory") is True]
                                if len(mandatory) < MIN_GATE_REQUIREMENTS:
                                    result = _abort("all gate requirements must be mandatory in phase8_3 design")
                                else:
                                    result = {
                                        "package_type": "phase8_3_publish_gate_design_validation_result",
                                        "phase": "Phase 8-3",
                                        "status": "PASS",
                                        "reason": "publish gate design is valid and keeps publish execution locked",
                                        "gate_design_ready": True,
                                        "design_status": data.get("design_status"),
                                        "target_draft_id": target_id,
                                        "target_draft_status": target.get("expected_status"),
                                        "phase8_2_decision": p82.get("decision"),
                                        "current_result": current,
                                        "gate_requirement_count": len(reqs),
                                        "mandatory_requirement_count": len(mandatory),
                                        "forbidden_action_count": len(forbidden),
                                        "token_name": token.get("token_name"),
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
