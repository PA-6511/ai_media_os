#!/usr/bin/env python3
"""Phase 8-40: Phase 8-36〜8-40 試験稼働ルート総合レポート生成。

Phase 8-29~8-31, 8-35, 8-36, 8-37, 8-38, 8-39, N-1~N-5, N-6~N-10 の
evidence を集約し、試験稼働ルートの総合状態を判定する。
WordPress / 外部 API 呼び出しなし。Secret 出力なし。
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EVIDENCE_PATHS: dict[str, Path] = {
    "phase8_29_to_8_31": ROOT / "exchange/logs/phase8_29_to_8_31_pre_execution_approval_pack_overall_report.json",
    "phase8_35": ROOT / "exchange/logs/phase8_35_final_ready_blocked_rerun_decision.json",
    "phase8_36": ROOT / "exchange/logs/phase8_36_one_shot_draft_creation_dry_run_handoff_result.json",
    "phase8_37": ROOT / "exchange/logs/phase8_37_first_trial_operation_runbook_result.json",
    "phase8_38": ROOT / "exchange/logs/phase8_38_first_one_item_trial_preflight_result.json",
    "phase8_39": ROOT / "exchange/logs/phase8_39_abort_rollback_freeze_simulation_result.json",
    "n1_n5": ROOT / "exchange/logs/n_series_overall_report.json",
    "n6_n10": ROOT / "exchange/logs/n6_n10_series_overall_report.json",
}

OUTPUT_JSON = ROOT / "exchange/logs/phase8_36_to_8_40_trial_route_overall_report.json"
OUTPUT_MD = ROOT / "exchange/logs/phase8_36_to_8_40_trial_route_overall_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> "dict | None":
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _get_status(d: "dict | None") -> "str | None":
    if d is None:
        return None
    return str(d.get("status") or d.get("overall_status") or d.get("pack_status") or "")


def _credentials_ready(phase8_35_data: "dict | None") -> bool:
    """phase8_35 evidence から credential 準備状態を判定。"""
    if phase8_35_data is None:
        return False
    s = _get_status(phase8_35_data) or ""
    if "CREDENTIALS_MISSING" in s or "BLOCKED" in s:
        return False
    if "READY" in s:
        return True
    return False


def _build_markdown(r: dict, evidence_summary: dict) -> str:
    lines = [
        "# Phase 8-36〜8-40: 試験稼働ルート総合レポート",
        "",
        "## Overall Status",
        f"- overall_status: {r.get('overall_status')}",
        f"- production_status: {r.get('production_status')}",
        f"- execution: {r.get('execution')}",
        f"- ready_for_first_trial_execution: {r.get('ready_for_first_trial_execution')}",
        f"- executed_external_changes: {r.get('executed_external_changes')}",
        "",
        "## Evidence Summary",
    ]
    for key, info in evidence_summary.items():
        lines.append(f"- {key}: exists={info['exists']} status={info['status']}")
    lines += [
        "",
        "## Safety Flags",
        f"- wordpress_write_executed: {r.get('wordpress_write_executed')}",
        f"- secret_values_output: {r.get('secret_values_output')}",
        f"- rollback_executed: {r.get('rollback_executed')}",
        f"- freeze_executed: {r.get('freeze_executed')}",
        "",
        "## Next Step",
        f"- next_step: {r.get('next_step')}",
    ]
    return "\n".join(lines) + "\n"


def generate_report(
    evidence_paths: "dict[str, Path] | None" = None,
    output_json: Path = OUTPUT_JSON,
    output_md: Path = OUTPUT_MD,
) -> dict:
    if evidence_paths is None:
        evidence_paths = EVIDENCE_PATHS

    base: dict = {
        "phase": "8-40",
        "phase_name": "Trial Route Overall Report (Phase 8-36 to 8-40)",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "ready_for_first_trial_execution": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "executed_external_changes": 0,
        "rollback_executed": False,
        "freeze_executed": False,
        "slack_message_sent": False,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_masks_output": False,
        "secret_hashes_output": False,
        "checked_at": _now_iso(),
    }

    evidence_summary: dict[str, dict] = {}
    missing_keys: list[str] = []

    for key, path in evidence_paths.items():
        data = _load_json(path)
        status = _get_status(data)
        evidence_summary[key] = {"exists": path.exists(), "status": status, "path": str(path)}
        if data is None:
            missing_keys.append(key)

    phase8_35_data = _load_json(evidence_paths["phase8_35"]) if "phase8_35" in evidence_paths else None
    creds_ready = _credentials_ready(phase8_35_data)

    # overall_status 判定
    if not creds_ready:
        if "phase8_35" in missing_keys:
            overall_status = "PHASE8_36_TO_8_40_TRIAL_ROUTE_BLOCKED_MISSING_EVIDENCE_NO_EXECUTION"
        else:
            overall_status = "PHASE8_36_TO_8_40_TRIAL_ROUTE_BLOCKED_CREDENTIALS_NOT_READY_NO_EXECUTION"
        next_step = "NEXT_STEP_COMPLETE_CREDENTIAL_READY_ROUTE_AND_RERUN_PHASE8_29_TO_8_40"
    elif missing_keys:
        overall_status = "PHASE8_36_TO_8_40_TRIAL_ROUTE_BLOCKED_MISSING_EVIDENCE_NO_EXECUTION"
        next_step = "NEXT_STEP_COMPLETE_MISSING_PHASES_THEN_RERUN_OVERALL_REPORT"
    else:
        # check each phase passes
        # PASS/READY/FINALIZED を含む → 成功。それ以外 → 失敗。
        # ただし BLOCKED/FAIL が末尾や単語境界にある場合も失敗とする。
        import re
        _FAIL_RE = re.compile(r'(?<![A-Z_])(FAIL|BLOCKED)(?![A-Z_])|_FAIL_|_BLOCKED_|FAIL$|BLOCKED$')

        def _is_phase_pass(s: str) -> bool:
            if not s:
                return False
            if _FAIL_RE.search(s):
                return False
            return bool(re.search(r'PASS|READY|FINALIZED', s))

        all_pass = True
        for key, info in evidence_summary.items():
            s = info["status"] or ""
            if not _is_phase_pass(s):
                all_pass = False
                break

        if all_pass:
            overall_status = "PHASE8_36_TO_8_40_TRIAL_ROUTE_READY_FOR_FIRST_ONE_ITEM_TRIAL_NO_EXECUTION"
            next_step = "NEXT_STEP_HUMAN_APPROVAL_THEN_EXECUTE_FIRST_ONE_ITEM_TRIAL"
        else:
            overall_status = "PHASE8_36_TO_8_40_TRIAL_ROUTE_BLOCKED_PHASE_FAILURE_NO_EXECUTION"
            next_step = "NEXT_STEP_RESOLVE_PHASE_FAILURES_AND_RERUN"

    result = {
        **base,
        "overall_status": overall_status,
        "credentials_ready": creds_ready,
        "next_step": next_step,
        "missing_evidence_keys": missing_keys,
        "evidence_summary": evidence_summary,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(_build_markdown(result, evidence_summary), encoding="utf-8")
    return result


def main() -> int:
    result = generate_report()
    display = {k: v for k, v in result.items() if k != "evidence_summary"}
    print(json.dumps(display, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
