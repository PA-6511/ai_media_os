#!/usr/bin/env python3
"""Phase 7-2  1件限定 実下書き作成 実行ドライラン
WordPress REST API POST は一切行わない。
Phase 7-1 チェックリスト全項目 PASS 想定で payload を組み立て、
dry-run 証跡と outgoing payload ファイルのみ生成する。
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blocks.ebook_affiliate.draft_payload_builder import build_draft_payload

LOGS = ROOT / "exchange/logs"
OUTGOING = ROOT / "exchange/outgoing"

PHASE7_1_RESULT = LOGS / "phase7_1_pre_release_checklist_validation_result.json"
CANDIDATE = ROOT / "exchange/outgoing/wordpress_draft_candidate.example.json"

OUTPUT_LOG = LOGS / "phase7_2_single_draft_create_execution_dry_run_result.json"
OUTPUT_PAYLOAD = OUTGOING / "wordpress_draft_create_payload.dry_run.json"

# 安全定数 ─ 変更禁止
_WORDPRESS_POST_ENABLED = False
_REAL_WRITE_ENABLED = False
_WORDPRESS_WRITE_EXECUTED = False


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_2_single_draft_create_execution_dry_run_result",
        "phase": "Phase 7-2",
        "status": "ABORT",
        "reason": reason,
        "dry_run_completed": False,
        "wordpress_post_enabled": _WORDPRESS_POST_ENABLED,
        "real_write_enabled": _REAL_WRITE_ENABLED,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": _WORDPRESS_WRITE_EXECUTED,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_payload(candidate: dict) -> dict:
    """WordPress REST API /wp/v2/posts 向け payload を組み立てる（POST はしない）"""
    return build_draft_payload(candidate)


def run_dry_run(
    phase7_1_result_path: Path = PHASE7_1_RESULT,
    candidate_path: Path = CANDIDATE,
    output_log: Path = OUTPUT_LOG,
    output_payload: Path = OUTPUT_PAYLOAD,
) -> dict:

    # Phase 7-1 チェックリスト検証結果の確認
    if not phase7_1_result_path.exists():
        return _abort(f"Phase 7-1 result not found: {phase7_1_result_path}")

    try:
        p71 = json.loads(phase7_1_result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in Phase 7-1 result: {e}")

    if p71.get("status") != "PASS":
        return _abort("Phase 7-1 validation status is not PASS")

    if p71.get("wordpress_post_enabled") is not False:
        return _abort("Phase 7-1 result: wordpress_post_enabled must be false")

    if p71.get("real_write_enabled") is not False:
        return _abort("Phase 7-1 result: real_write_enabled must be false")

    # 下書き候補ファイルの読み込み
    if not candidate_path.exists():
        return _abort(f"draft candidate not found: {candidate_path}")

    try:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return _abort(f"invalid JSON in candidate: {e}")

    if candidate.get("wordpress_write_executed") is not False:
        return _abort("candidate: wordpress_write_executed must be false")

    # payload 組み立て（POSTは行わない）
    payload = _build_payload(candidate)

    # dry-run 実行ステップログ
    execution_steps = [
        {"step": 1, "action": "Phase 7-1 checklist result 確認", "result": "PASS"},
        {"step": 2, "action": "draft candidate 読み込み", "result": "PASS"},
        {"step": 3, "action": "payload 組み立て（title / content / categories / tags）", "result": "PASS"},
        {"step": 4, "action": "WordPress REST API POST ─ 実行禁止を確認", "result": "SKIPPED_DRY_RUN_ONLY"},
        {"step": 5, "action": "payload ファイルを exchange/outgoing へ保存", "result": "PASS"},
        {"step": 6, "action": "dry-run 証跡を exchange/logs へ保存", "result": "PASS"},
    ]

    result = {
        "package_type": "phase7_2_single_draft_create_execution_dry_run_result",
        "phase": "Phase 7-2",
        "status": "PASS",
        "reason": "dry-run completed. WordPress POST was not executed.",
        "dry_run_completed": True,
        "wordpress_post_enabled": _WORDPRESS_POST_ENABLED,
        "real_write_enabled": _REAL_WRITE_ENABLED,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": _WORDPRESS_WRITE_EXECUTED,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "execution_steps": execution_steps,
        "payload_title": payload.get("title", ""),
        "payload_status_field": payload.get("status", ""),
        "payload_categories_hint": payload.get("categories_hint", []),
        "payload_tags_hint": payload.get("tags_hint", []),
        "payload_output": str(output_payload),
        "next_step": "phase7_3_single_draft_create_human_final_approval",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # ファイル出力
    output_log.parent.mkdir(parents=True, exist_ok=True)
    output_payload.parent.mkdir(parents=True, exist_ok=True)
    output_log.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_payload.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return result


def main() -> int:
    result = run_dry_run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
