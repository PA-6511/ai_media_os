#!/usr/bin/env python3
"""
run_exchange_connection_dry_run.py

Phase 4-4: 接続フロー全体 DRY_RUN スクリプト
電子書籍アフィリエイトブロックAI × ローカル自動構築プログラムAI 限定接続インターフェース

役割:
  exchange/incoming/*.example.json を読み込み、exchange_validator で検証し、
  結果を exchange/logs/validation_result.json に保存する。
  WordPress / Slack / GitHub Actions は一切実行しない。

固定条件:
  MODE=CONNECTION_TEST / EXECUTION=DRY_RUN / HUMAN_APPROVAL_REQUIRED=true
  AUTO_POST=false / AUTO_UPDATE=false / AUTO_DELETE=false / AUTO_EXPORT=false
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from exchange_validator import validate_package

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

PACKAGE_FILES = {
    "decision_package": ROOT / "exchange/incoming/decision_package.example.json",
    "patch_proposal":   ROOT / "exchange/incoming/patch_proposal.example.json",
    "test_report":      ROOT / "exchange/incoming/test_report.example.json",
}

OUTPUT_PATH = ROOT / "exchange/logs/validation_result.json"

STATUS_PRIORITY = {
    "PASS":  0,
    "WARN":  1,
    "FAIL":  2,
    "ABORT": 3,
}

# ---------------------------------------------------------------------------
# 集計
# ---------------------------------------------------------------------------


def aggregate_status(results: list[dict]) -> str:
    overall = "PASS"
    for result in results:
        status = result.get("status", "FAIL")
        if STATUS_PRIORITY.get(status, 2) > STATUS_PRIORITY[overall]:
            overall = status
    return overall


def _load_json_safely(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _extract_source_builder(package_files: dict) -> dict:
    """decision_package から self_builder_origin 情報を抽出する。"""
    decision_path = package_files.get("decision_package")
    if not decision_path:
        return {
            "type": "UNKNOWN",
            "location": "unknown",
            "execution_allowed": False,
            "vps_migration_ready": False,
            "source_file": None,
        }

    data = _load_json_safely(Path(decision_path))
    origin = data.get("self_builder_origin", {}) if isinstance(data, dict) else {}

    return {
        "type": origin.get("type", "LOCAL_SELF_BUILDER"),
        "location": origin.get("location", "local"),
        "execution_allowed": bool(origin.get("execution_allowed", False)),
        "vps_migration_ready": bool(origin.get("vps_migration_ready", False)),
        "source_file": str(decision_path),
    }


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------


def run_dry_run(
    package_files: dict | None = None,
    output_path: Path | None = None,
) -> dict:
    """
    接続フロー全体を DRY_RUN で実行し、結果を保存して返す。

    Args:
        package_files: {package_type: Path} の dict。省略時はデフォルトの example ファイルを使用。
        output_path:   validation_result.json の保存先。省略時はデフォルトパスを使用。

    Returns:
        検証結果の dict。
    """
    package_files = package_files or PACKAGE_FILES
    output_path = output_path or OUTPUT_PATH
    source_builder = _extract_source_builder(package_files)

    results = []
    for package_type, path in package_files.items():
        result = validate_package(package_type, Path(path))
        result["package_type"] = package_type
        result["path"] = str(path)
        results.append(result)

    overall_status = aggregate_status(results)
    human_review_required = overall_status in {"WARN", "FAIL", "ABORT"}

    output = {
        "package_type": "exchange_connection_dry_run_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "source_builder": source_builder,
        "human_review_required": human_review_required,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
        "overall_status": overall_status,
        "results": results,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "next_step": (
            "ABORT_STOP"    if overall_status == "ABORT"
            else "fix_required"  if overall_status == "FAIL"
            else "human_review"  if overall_status == "WARN"
            else "record_pass_evidence"
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def main() -> int:
    result = run_dry_run()

    print("\n=== exchange_connection_dry_run ===")
    print(f"overall_status         : {result['overall_status']}")
    print(f"human_review_required  : {result['human_review_required']}")
    print(f"execution              : {result['execution']}")
    print(f"next_step              : {result['next_step']}")
    print(f"created_at             : {result['created_at']}")
    print()
    for r in result["results"]:
        status = r["status"]
        ptype = r["package_type"]
        print(f"  [{status:5s}] {ptype}")
        for issue in r.get("issues", []):
            print(f"          ISSUE  : {issue}")
        for warn in r.get("warnings", []):
            print(f"          WARN   : {warn}")

    print(f"\nResult saved: {OUTPUT_PATH}")

    if result["overall_status"] == "ABORT":
        print("\nABORT: dangerous operation detected. Stop immediately.")
        return 2
    if result["overall_status"] == "FAIL":
        print("\nFAIL: fix required before next step.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
