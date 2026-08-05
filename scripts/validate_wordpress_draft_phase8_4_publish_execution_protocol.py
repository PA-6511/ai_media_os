#!/usr/bin/env python3
"""Phase 8-4 公開実行プロトコル設計バリデータ（設計のみ）"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/wordpress_draft_phase8_4_publish_execution_protocol.json"
OUTPUT = ROOT / "exchange/logs/phase8_4_publish_execution_protocol_validation_result.json"
PHASE8_3 = ROOT / "exchange/logs/phase8_3_publish_gate_design_validation_result.json"
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

MIN_PROTOCOL_STEPS = 10
MIN_ABORT_CONDITIONS = 7
MIN_FORBIDDEN_ACTIONS = 10


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase8_4_publish_execution_protocol_validation_result",
        "phase": "Phase 8-4",
        "status": "ABORT",
        "reason": reason,
        "protocol_design_ready": False,
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
    elif not PHASE8_3.exists() or not PHASE8_2.exists() or not PHASE7_6.exists():
        result = _abort("required upstream logs not found")
    else:
        try:
            data = _load_json(config_path)
            p83 = _load_json(PHASE8_3)
            p82 = _load_json(PHASE8_2)
            p76 = _load_json(PHASE7_6)
        except json.JSONDecodeError as e:
            result = _abort(f"invalid JSON: {e}")
        else:
            if data.get("design_status") != "DESIGN_ONLY":
                result = _abort("design_status must be DESIGN_ONLY")
            elif p83.get("status") != "PASS":
                result = _abort("phase8_3 status must be PASS")
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
                            steps = data.get("protocol_steps", [])
                            aborts = data.get("abort_conditions", [])
                            forbidden = data.get("forbidden_actions_in_phase8_4", [])
                            token = data.get("approval_token_rules", {})
                            constraints = data.get("safety_constraints", {})
                            current = data.get("protocol_result", {}).get("current_result")

                            if not isinstance(steps, list) or len(steps) < MIN_PROTOCOL_STEPS:
                                result = _abort(f"protocol_steps must have at least {MIN_PROTOCOL_STEPS} items")
                            elif not isinstance(aborts, list) or len(aborts) < MIN_ABORT_CONDITIONS:
                                result = _abort(f"abort_conditions must have at least {MIN_ABORT_CONDITIONS} items")
                            elif not isinstance(forbidden, list) or len(forbidden) < MIN_FORBIDDEN_ACTIONS:
                                result = _abort(f"forbidden_actions_in_phase8_4 must have at least {MIN_FORBIDDEN_ACTIONS} items")
                            elif token.get("token_name") != "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY":
                                result = _abort("approval_token_rules.token_name must be APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY")
                            elif token.get("token_value_required") != "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY":
                                result = _abort("approval_token_rules.token_value_required mismatch")
                            elif token.get("one_time_only") is not True:
                                result = _abort("approval_token_rules.one_time_only must be true")
                            elif token.get("expires_minutes") != 30:
                                result = _abort("approval_token_rules.expires_minutes must be 30")
                            elif token.get("human_reviewer_required") is not True:
                                result = _abort("approval_token_rules.human_reviewer_required must be true")
                            elif token.get("publish_count_limit") != 1:
                                result = _abort("approval_token_rules.publish_count_limit must be 1")
                            elif token.get("allowed_status_transition") != "draft_to_publish_only":
                                result = _abort("approval_token_rules.allowed_status_transition must be draft_to_publish_only")
                            elif constraints.get("allow_publish_only") is not True:
                                result = _abort("safety_constraints.allow_publish_only must be true")
                            elif constraints.get("allow_update") is not False:
                                result = _abort("safety_constraints.allow_update must be false")
                            elif constraints.get("allow_delete") is not False:
                                result = _abort("safety_constraints.allow_delete must be false")
                            elif constraints.get("allow_export") is not False:
                                result = _abort("safety_constraints.allow_export must be false")
                            elif constraints.get("allow_bulk_operations") is not False:
                                result = _abort("safety_constraints.allow_bulk_operations must be false")
                            elif constraints.get("allow_cron_automation") is not False:
                                result = _abort("safety_constraints.allow_cron_automation must be false")
                            elif current not in {
                                "PUBLISH_PROTOCOL_DESIGN_READY",
                                "PUBLISH_PROTOCOL_NEEDS_FIX",
                                "PUBLISH_PROTOCOL_BLOCKED",
                            }:
                                result = _abort("invalid protocol_result.current_result")
                            else:
                                mandatory = [x for x in steps if x.get("mandatory") is True]
                                if len(mandatory) < MIN_PROTOCOL_STEPS:
                                    result = _abort("all protocol steps must be mandatory in phase8_4 design")
                                else:
                                    result = {
                                        "package_type": "phase8_4_publish_execution_protocol_validation_result",
                                        "phase": "Phase 8-4",
                                        "status": "PASS",
                                        "reason": "publish execution protocol design is valid and keeps publish execution locked",
                                        "protocol_design_ready": True,
                                        "design_status": data.get("design_status"),
                                        "target_draft_id": target_id,
                                        "target_draft_status": target.get("expected_status"),
                                        "phase8_2_decision": p82.get("decision"),
                                        "phase8_3_gate_status": p83.get("status"),
                                        "current_result": current,
                                        "protocol_step_count": len(steps),
                                        "mandatory_step_count": len(mandatory),
                                        "abort_condition_count": len(aborts),
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
