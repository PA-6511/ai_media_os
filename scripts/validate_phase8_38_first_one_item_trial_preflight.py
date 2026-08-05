#!/usr/bin/env python3
"""Phase 8-38: 初回1件試験稼働 preflight validator。

WordPress API 呼び出し・外部状態変更は行わない。
Phase 8-36 / 8-37 の evidence を参照し、preflight 状態を確認する。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/phase8_38_first_one_item_trial_preflight_policy.json"
REQUEST = ROOT / "exchange/examples/phase8_38_first_one_item_trial_preflight_request.example.json"
OUTPUT = ROOT / "exchange/logs/phase8_38_first_one_item_trial_preflight_result.json"

PHASE8_36_LOG = ROOT / "exchange/logs/phase8_36_one_shot_draft_creation_dry_run_handoff_result.json"
PHASE8_37_LOG = ROOT / "exchange/logs/phase8_37_first_trial_operation_runbook_result.json"


_READY_STATUS_36 = "PHASE8_36_DRY_RUN_HANDOFF_READY_NO_EXECUTION"
_READY_STATUS_37 = "PHASE8_37_TRIAL_OPERATION_RUNBOOK_FINALIZED_NO_EXECUTION"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _phase_status(path: Path) -> "str | None":
    if not path.exists():
        return None
    try:
        d = _load_json(path)
        return str(d.get("status") or d.get("overall_status") or "")
    except Exception:
        return None


def validate(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
    phase8_36_path: Path = PHASE8_36_LOG,
    phase8_37_path: Path = PHASE8_37_LOG,
) -> dict:
    base: dict = {
        "phase": "8-38",
        "phase_name": "First One-Item Trial Preflight",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "actual_go_decision_issued": False,
        "human_approval_required": True,
        "human_approval_present": False,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "one_shot_target_count": 1,
        "one_shot_lock_required": True,
        "one_shot_lock_exists_simulated": False,
        "secret_output_safe": True,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_masks_output": False,
        "secret_hashes_output": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "executed_external_changes": 0,
        "blocked_reasons": [],
        "warn_list": [],
        "fail_list": [],
        "checked_at": _now_iso(),
    }

    try:
        policy = _load_json(policy_path)
        req = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "ABORT_UNSAFE_PREFLIGHT_FLAG_DETECTED_NO_EXECUTION",
            "fail_list": [f"input_load_error: {exc}"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    # evidence 確認
    phase8_36_status = _phase_status(phase8_36_path)
    phase8_37_status = _phase_status(phase8_37_path)

    blocked: list[str] = []
    if phase8_36_status is None:
        blocked.append("missing_phase8_36_evidence")
    elif _READY_STATUS_36 not in phase8_36_status:
        if "CREDENTIALS_NOT_READY" in phase8_36_status or "BLOCKED" in phase8_36_status:
            blocked.append("phase8_36_blocked_credentials_not_ready")
        else:
            blocked.append(f"phase8_36_not_ready: {phase8_36_status}")

    if phase8_37_status is None:
        blocked.append("missing_phase8_37_runbook_evidence")
    elif _READY_STATUS_37 not in phase8_37_status:
        blocked.append(f"phase8_37_runbook_not_finalized: {phase8_37_status}")

    # request から追加フラグ読み取り
    target_selected = bool(req.get("target_item_selected", False))
    target_schema_valid = bool(req.get("target_item_schema_valid", False))
    duplicate_passed = bool(req.get("target_item_duplicate_check_passed", False))
    affiliate = bool(req.get("affiliate_disclosure_present", False))
    pr_label = bool(req.get("pr_label_present", False))
    cta = bool(req.get("cta_policy_checked", False))
    cat_tag = bool(req.get("category_tag_policy_checked", False))
    lock_sim = bool(req.get("one_shot_lock_exists_simulated", False))
    human_approval = bool(req.get("human_approval_present", False))

    if not target_selected:
        blocked.append("target_item_not_selected")

    # 危険フラグ検出
    if req.get("execution_allowed") or req.get("wordpress_write_allowed"):
        result = {
            **base,
            "status": "ABORT_UNSAFE_PREFLIGHT_FLAG_DETECTED_NO_EXECUTION",
            "fail_list": ["dangerous_execution_flag_in_request"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    # secret 出力検出
    if req.get("secret_values_output") or req.get("secret_lengths_output"):
        result = {
            **base,
            "status": "ABORT_SECRET_OUTPUT_DETECTED_NO_EXECUTION",
            "fail_list": ["secret_output_flag_in_request"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    # status 判定
    if "missing_phase8_36_evidence" in blocked or "phase8_36_blocked_credentials_not_ready" in blocked:
        if "missing_phase8_36_evidence" in blocked:
            status = "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_MISSING_PHASE8_36_NO_EXECUTION"
        else:
            status = "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
    elif "missing_phase8_37_runbook_evidence" in blocked or any("phase8_37" in b for b in blocked):
        status = "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_MISSING_RUNBOOK_NO_EXECUTION"
    elif "target_item_not_selected" in blocked:
        status = "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_TARGET_ITEM_NOT_SELECTED_NO_EXECUTION"
    elif blocked:
        status = "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
    else:
        status = "PHASE8_38_FIRST_ONE_ITEM_TRIAL_PREFLIGHT_READY_NO_EXECUTION"

    result = {
        **base,
        "status": status,
        "phase8_36_status": phase8_36_status,
        "phase8_37_status": phase8_37_status,
        "phase8_36_evidence_exists": phase8_36_path.exists(),
        "phase8_37_evidence_exists": phase8_37_path.exists(),
        "target_item_selected": target_selected,
        "target_item_schema_valid": target_schema_valid,
        "target_item_duplicate_check_passed": duplicate_passed,
        "affiliate_disclosure_present": affiliate,
        "pr_label_present": pr_label,
        "cta_policy_checked": cta,
        "category_tag_policy_checked": cat_tag,
        "one_shot_lock_exists_simulated": lock_sim,
        "human_approval_present": human_approval,
        "blocked_reasons": blocked,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
