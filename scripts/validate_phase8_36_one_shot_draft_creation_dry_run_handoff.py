#!/usr/bin/env python3
"""Phase 8-36: One-shot Draft Creation Dry-Run Handoff validator.

WordPress API 書き込み・実下書き作成・外部状態変更は行わない。
Phase 8-35 / 8-29〜8-31 の evidence を参照し、
handoff 可否を判定して証跡を出力するのみ。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/phase8_36_one_shot_draft_creation_dry_run_handoff_policy.json"
REQUEST = ROOT / "exchange/examples/phase8_36_one_shot_draft_creation_dry_run_handoff_request.example.json"
OUTPUT = ROOT / "exchange/logs/phase8_36_one_shot_draft_creation_dry_run_handoff_result.json"

# 既存 evidence paths
PHASE8_35_LOG = ROOT / "exchange/logs/phase8_35_final_ready_blocked_rerun_decision.json"
PHASE8_29_31_LOG = ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json"

# status markers that indicate credentials are ready
_READY_MARKERS = {
    "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_READY_NO_EXECUTION",
    "PHASE8_35_FINAL_CONFIRMATION_READY_FOR_DRY_RUN_HANDOFF_NO_EXECUTION",
    "READY",
}
_NOT_READY_MARKERS = {
    "CREDENTIALS_NOT_READY",
    "BLOCKED_CREDENTIALS_MISSING",
    "PHASE8_29_TO_8_31_PRE_EXECUTION_APPROVAL_PACK_PASS_CREDENTIALS_NOT_READY_NO_EXECUTION",
    "PHASE8_35_FINAL_CONFIRMATION_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _credentials_ready_from_evidence(
    phase8_35_path: Path,
    phase8_29_31_path: Path,
    override: "str | None",
) -> tuple[bool, str]:
    """phase8_35 / phase8_29_31 の evidence からCredential状態を判定する。
    値は出力しない。boolean のみ返す。
    """
    if override is not None:
        status_str = str(override)
        # NOT_READY チェックを先に行う（"NOT_READY" は "READY" を含むため）
        if any(m in status_str for m in _NOT_READY_MARKERS):
            return False, status_str
        if any(m in status_str for m in _READY_MARKERS):
            return True, status_str
        return False, status_str

    # Phase 8-35 を優先
    if phase8_35_path.exists():
        try:
            d = _load_json(phase8_35_path)
            s = str(d.get("status") or d.get("overall_status") or "")
            if any(m in s for m in _NOT_READY_MARKERS):
                return False, s
            if any(m in s for m in _READY_MARKERS):
                return True, s
            return False, s
        except Exception:
            pass

    # Phase 8-29〜8-31 fallback
    if phase8_29_31_path.exists():
        try:
            d = _load_json(phase8_29_31_path)
            s = str(d.get("pack_status") or d.get("overall_status") or d.get("status") or "")
            cred_ready = bool(d.get("credentials_ready", False))
            if cred_ready:
                return True, s
            return False, s
        except Exception:
            pass

    return False, "MISSING_EVIDENCE"


def _check_danger_flags(result: dict) -> list[str]:
    danger_keys = [
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_api_call_attempted",
        "execution_allowed",
        "publish_allowed",
        "update_allowed",
        "delete_allowed",
        "bulk_operation_allowed",
        "export_allowed",
        "actual_go_decision_issued",
        "rollback_executed",
        "freeze_executed",
        "secret_values_output",
        "secret_lengths_output",
        "secret_masks_output",
        "secret_hashes_output",
    ]
    return [k for k in danger_keys if result.get(k) is True]


def validate(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_path: Path = OUTPUT,
    phase8_35_path: Path = PHASE8_35_LOG,
    phase8_29_31_path: Path = PHASE8_29_31_LOG,
) -> dict:
    base: dict = {
        "phase": "8-36",
        "phase_name": "One-shot Draft Creation Dry-Run Handoff",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "bulk_operation_allowed": False,
        "export_allowed": False,
        "actual_go_decision_issued": False,
        "human_execution_approval_required": True,
        "human_execution_approval_present": False,
        "one_shot_target_count": 1,
        "one_shot_lock_required": True,
        "one_shot_lock_created": False,
        "one_shot_lock_released": False,
        "rollback_plan_required": True,
        "rollback_executed": False,
        "freeze_plan_required": True,
        "freeze_executed": False,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_masks_output": False,
        "secret_hashes_output": False,
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
            "status": "ABORT_UNKNOWN_STATUS_NO_EXECUTION",
            "fail_list": [f"input_load_error: {exc}"],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    override = req.get("phase8_35_status_override") or req.get("credential_status_override")
    cred_ready, phase8_35_status_observed = _credentials_ready_from_evidence(
        phase8_35_path, phase8_29_31_path, override
    )

    phase8_35_exists = phase8_35_path.exists()
    phase8_29_31_exists = phase8_29_31_path.exists()

    blocked_reasons = []
    if not phase8_35_exists and not phase8_29_31_exists:
        blocked_reasons.append("missing_phase8_35_and_phase8_29_31_evidence")
    if not cred_ready:
        blocked_reasons.append("credentials_not_ready")

    # danger check
    dangerous = _check_danger_flags(base)
    if dangerous:
        result = {
            **base,
            "status": "ABORT_UNSAFE_EXECUTION_FLAG_DETECTED_NO_EXECUTION",
            "fail_list": [f"dangerous_flag_true: {k}" for k in dangerous],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    # status 決定
    # override がある場合は evidence の存在チェックをスキップし、override の内容に基づいて判定する
    if override is None and not phase8_35_exists and not phase8_29_31_exists:
        status = "PHASE8_36_DRY_RUN_HANDOFF_ABORT_MISSING_PHASE8_35_EVIDENCE_NO_EXECUTION"
    elif not cred_ready:
        status = "PHASE8_36_DRY_RUN_HANDOFF_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
    else:
        status = "PHASE8_36_DRY_RUN_HANDOFF_READY_NO_EXECUTION"

    handoff_allowed = cred_ready
    next_step = (
        "NEXT_STEP_REQUEST_EXPLICIT_HUMAN_GO_FOR_FIRST_ONE_ITEM_TRIAL"
        if cred_ready
        else "NEXT_STEP_COMPLETE_CREDENTIAL_READY_ROUTE_AND_RERUN_PHASE8_29_TO_8_40"
    )

    result = {
        **base,
        "status": status,
        "credential_status_source": str(phase8_35_path.name),
        "phase8_29_to_8_31_status": phase8_35_status_observed if not phase8_35_exists else "see_phase8_29_31_evidence",
        "phase8_35_status": phase8_35_status_observed,
        "phase8_35_evidence_exists": phase8_35_exists,
        "phase8_29_31_evidence_exists": phase8_29_31_exists,
        "credentials_ready": cred_ready,
        "handoff_status": "READY" if cred_ready else "BLOCKED",
        "handoff_allowed": handoff_allowed,
        "blocked_reasons": blocked_reasons,
        "next_step": next_step,
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
