"""
exchange_validator.py

Phase 4-2: 受信バリデータ
電子書籍アフィリエイトブロックAI × ローカル自動構築プログラムAI 限定接続インターフェース

役割:
  exchange/incoming/ 以下の decision_package / patch_proposal / test_report を読み込み、
  安全フラグ・必須フィールド・危険操作を検査して PASS / WARN / FAIL / ABORT を返す。
  結果を exchange/logs/validation_result.json に保存する。

固定条件:
  MODE=CONNECTION_TEST
  EXECUTION=DRY_RUN
  HUMAN_APPROVAL_REQUIRED=true
  AUTO_POST=false / AUTO_UPDATE=false / AUTO_DELETE=false / AUTO_EXPORT=false
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
EXCHANGE_DIR = REPO_ROOT / "exchange"
INCOMING_DIR = EXCHANGE_DIR / "incoming"
LOGS_DIR = EXCHANGE_DIR / "logs"

# 検査対象ファイル名（.example.json は除外し、実ファイルを優先）
TARGET_FILES = {
    "decision_package": "decision_package.json",
    "patch_proposal": "patch_proposal.json",
    "test_report": "test_report.json",
}

REQUIRED_SAFE_FLAGS = {
    "auto_post": False,
    "auto_update": False,
    "auto_delete": False,
    "auto_export": False,
    "human_approval_required": True,
}

FORBIDDEN_EXECUTION_VALUES = {"LIVE", "PRODUCTION", "PROD"}
ALLOWED_SELF_BUILDER_TYPES = {"LOCAL_SELF_BUILDER", "VPS_SELF_BUILDER"}
ALLOWED_SELF_BUILDER_LOCATIONS = {"local", "vps"}

# フィールド「値」に含まれてはならないキーワード（フィールド名は対象外）
# auto_post/update/delete/export は _check_safe_flags で別途検査するため除外
FORBIDDEN_KEYWORDS_IN_REQUEST = {
    "wp_post_live",
    "mass_replace",
}

# requested_action / description / summary / changes など「操作内容」フィールドの
# 値に含まれてはならないキーワード（.env / secrets 等への実アクセス要求を検出）
FORBIDDEN_KEYWORDS_IN_ACTION_FIELDS = {
    ".env",
    "secrets",
    "credentials",
}

# 「操作内容」として検査するフィールドキー
ACTION_FIELD_KEYS = {
    "requested_action",
    "description",
    "summary",
    "title",
    "operation",
    "file",
}

REQUIRED_FIELDS_BY_TYPE = {
    "decision_package": [
        "package_type",
        "source",
        "target",
        "mode",
        "execution",
        "human_approval_required",
        "risk_level",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
    ],
    "patch_proposal": [
        "package_type",
        "source",
        "target",
        "mode",
        "execution",
        "human_approval_required",
        "risk_level",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
    ],
    "test_report": [
        "package_type",
        "source",
        "target",
        "mode",
        "execution",
        "human_approval_required",
        "tests",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
    ],
}

# ---------------------------------------------------------------------------
# 判定ステータス
# ---------------------------------------------------------------------------

STATUS_PASS = "PASS"
STATUS_WARN = "WARN"
STATUS_FAIL = "FAIL"
STATUS_ABORT = "ABORT"


# ---------------------------------------------------------------------------
# バリデーション関数
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> tuple[dict | None, str | None]:
    """JSON ファイルを読み込む。失敗時は (None, error_message) を返す。"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except json.JSONDecodeError as e:
        return None, f"JSON parse error in {path}: {e}"


def _check_required_fields(data: dict, package_type: str) -> list[str]:
    """必須フィールドの欠落を返す。"""
    required = REQUIRED_FIELDS_BY_TYPE.get(package_type, [])
    return [f for f in required if f not in data]


def _check_safe_flags(data: dict) -> list[str]:
    """危険フラグ（safe フラグ違反）を返す。"""
    violations = []
    for key, expected in REQUIRED_SAFE_FLAGS.items():
        if key in data and data[key] != expected:
            violations.append(f"{key}={data[key]!r} (expected {expected!r})")
    return violations


def _check_execution(data: dict) -> str | None:
    """LIVE 実行を検出したら違反内容を返す。"""
    value = str(data.get("execution", "")).upper()
    if value in FORBIDDEN_EXECUTION_VALUES:
        return f"execution={value!r} is forbidden"
    return None


def _extract_action_values(data: dict) -> list[str]:
    """dict を再帰的に走査し、ACTION_FIELD_KEYS に一致するキーの値（文字列）を収集する。"""
    found: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ACTION_FIELD_KEYS and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_extract_action_values(value))
    elif isinstance(data, list):
        for item in data:
            found.extend(_extract_action_values(item))
    return found


def _check_forbidden_keywords(data: dict) -> list[str]:
    """
    禁止キーワードを検査する。
    - FORBIDDEN_KEYWORDS_IN_REQUEST: JSON 全体の文字列表現を対象
    - FORBIDDEN_KEYWORDS_IN_ACTION_FIELDS: 操作内容フィールドの値のみを対象
    """
    violations: list[str] = []

    # 全体検査（wp_post_live, mass_replace など）
    raw = json.dumps(data, ensure_ascii=False).lower()
    for kw in FORBIDDEN_KEYWORDS_IN_REQUEST:
        if kw.lower() in raw:
            violations.append(f"Forbidden keyword in package: {kw!r}")

    # 操作内容フィールドのみ検査（.env / secrets / credentials）
    action_values = " ".join(_extract_action_values(data)).lower()
    for kw in FORBIDDEN_KEYWORDS_IN_ACTION_FIELDS:
        if kw.lower() in action_values:
            violations.append(f"Forbidden keyword in action field: {kw!r}")

    return violations


def _check_test_results(data: dict) -> list[str]:
    """test_report の各テスト結果で WARN に相当するものを返す。"""
    warns = []
    tests = data.get("tests", {})
    for name, result in tests.items():
        if result in ("WARN", "NOT_EXECUTED"):
            warns.append(f"tests.{name}={result!r}")
    return warns


def _check_decision_warnings(data: dict) -> list[str]:
    """decision.status が WARN の場合に warning を返す。"""
    warnings = []
    decision = data.get("decision")
    if isinstance(decision, dict) and decision.get("status") == "WARN":
        reason = decision.get("reason", "")
        if reason:
            warnings.append(f"decision.status='WARN' ({reason})")
        else:
            warnings.append("decision.status='WARN'")
    return warnings


def _check_self_builder_origin(data: dict) -> list[str]:
    """
    decision_package の self_builder_origin を検査する。

    Phase 5-1 では後方互換のため optional 扱いだが、存在する場合は厳格に検査する。
    """
    origin = data.get("self_builder_origin")
    if origin is None:
        return []

    issues: list[str] = []
    if not isinstance(origin, dict):
        return ["self_builder_origin must be an object"]

    origin_type = origin.get("type")
    location = origin.get("location")
    execution_allowed = origin.get("execution_allowed")
    vps_migration_ready = origin.get("vps_migration_ready")

    if origin_type not in ALLOWED_SELF_BUILDER_TYPES:
        issues.append(f"unknown self_builder_origin.type: {origin_type!r}")

    if location not in ALLOWED_SELF_BUILDER_LOCATIONS:
        issues.append(f"unknown self_builder_origin.location: {location!r}")

    if execution_allowed is True:
        issues.append("self_builder_origin.execution_allowed=true is forbidden")

    # VPS の受信は設計上許可するが、Phase 5-1 では実行不可の条件を厳格化する
    if origin_type == "VPS_SELF_BUILDER":
        if vps_migration_ready is not True:
            issues.append(
                "VPS_SELF_BUILDER requires self_builder_origin.vps_migration_ready=true"
            )

        execution = str(data.get("execution", "")).upper()
        if execution != "DRY_RUN":
            issues.append("VPS_SELF_BUILDER is allowed only with execution=DRY_RUN")

        if data.get("human_approval_required") is not True:
            issues.append(
                "VPS_SELF_BUILDER requires human_approval_required=true"
            )

    return issues


# ---------------------------------------------------------------------------
# メインバリデーション
# ---------------------------------------------------------------------------


def validate_package(package_type: str, path: Path) -> dict:
    """
    単一パッケージを検査して結果 dict を返す。

    Returns:
        {
          "file": str,
          "status": PASS | WARN | FAIL | ABORT,
          "issues": [...],
          "warnings": [...],
        }
    """
    issues: list[str] = []
    warnings: list[str] = []

    data, load_error = _load_json(path)
    if load_error:
        return {
            "file": str(path),
            "status": STATUS_FAIL,
            "issues": [load_error],
            "warnings": [],
        }

    # --- 1. 必須フィールド欠落 ---
    missing = _check_required_fields(data, package_type)
    if missing:
        issues.append(f"Missing required fields: {missing}")

    # --- 2. 危険フラグ違反 → 即 ABORT ---
    flag_violations = _check_safe_flags(data)
    if flag_violations:
        issues.extend(flag_violations)
        return {
            "file": str(path),
            "status": STATUS_ABORT,
            "issues": issues,
            "warnings": warnings,
        }

    # --- 3. LIVE 実行検出 → 即 ABORT ---
    exec_violation = _check_execution(data)
    if exec_violation:
        issues.append(exec_violation)
        return {
            "file": str(path),
            "status": STATUS_ABORT,
            "issues": issues,
            "warnings": warnings,
        }

    # --- 4. 禁止キーワード検出 → 即 ABORT ---
    forbidden = _check_forbidden_keywords(data)
    if forbidden:
        issues.append(f"Forbidden keywords detected: {forbidden}")
        return {
            "file": str(path),
            "status": STATUS_ABORT,
            "issues": issues,
            "warnings": warnings,
        }

    # --- 4.5 self_builder_origin 検証（decision_package のみ） ---
    if package_type == "decision_package":
        origin_issues = _check_self_builder_origin(data)
        if origin_issues:
            issues.extend(origin_issues)
            return {
                "file": str(path),
                "status": STATUS_ABORT,
                "issues": issues,
                "warnings": warnings,
            }

    # --- 5. 必須フィールド欠落がある → FAIL ---
    if issues:
        return {
            "file": str(path),
            "status": STATUS_FAIL,
            "issues": issues,
            "warnings": warnings,
        }

    # --- 6. decision_package の decision.status=WARN を warning として反映 ---
    if package_type == "decision_package":
        decision_warns = _check_decision_warnings(data)
        warnings.extend(decision_warns)

    # --- 7. test_report の WARN / NOT_EXECUTED → WARN ---
    if package_type == "test_report":
        test_warns = _check_test_results(data)
        warnings.extend(test_warns)

    status = STATUS_WARN if warnings else STATUS_PASS
    return {
        "file": str(path),
        "status": status,
        "issues": issues,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# ファイル解決（実ファイル優先 → example フォールバック）
# ---------------------------------------------------------------------------


def _resolve_path(name: str) -> Path:
    """実ファイル → example ファイルの順で解決する。"""
    real = INCOMING_DIR / name
    if real.exists():
        return real
    example = INCOMING_DIR / name.replace(".json", ".example.json")
    return example


# ---------------------------------------------------------------------------
# 結果集計
# ---------------------------------------------------------------------------


def _aggregate_status(results: list[dict]) -> str:
    """各パッケージの結果から全体判定を返す。"""
    statuses = {r["status"] for r in results}
    if STATUS_ABORT in statuses:
        return STATUS_ABORT
    if STATUS_FAIL in statuses:
        return STATUS_FAIL
    if STATUS_WARN in statuses:
        return STATUS_WARN
    return STATUS_PASS


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------


def run_validation(dry_run: bool = True) -> dict:
    """
    全パッケージを検査し、validation_result.json に保存して結果を返す。

    Args:
        dry_run: True の場合、ファイル保存も行うが本番 API は叩かない（常に True）。
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    package_results = []
    for package_type, filename in TARGET_FILES.items():
        path = _resolve_path(filename)
        result = validate_package(package_type, path)
        result["package_type"] = package_type
        package_results.append(result)

    overall = _aggregate_status(package_results)

    output = {
        "validator": "exchange_validator",
        "version": "1.0.0",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "packages": package_results,
        "next_step": (
            "human_review" if overall in (STATUS_PASS, STATUS_WARN)
            else "fix_required" if overall == STATUS_FAIL
            else "ABORT_STOP"
        ),
    }

    result_path = LOGS_DIR / "validation_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output


def main() -> None:
    result = run_validation(dry_run=True)

    print(f"\n=== exchange_validator ===")
    print(f"overall_status : {result['overall_status']}")
    print(f"next_step      : {result['next_step']}")
    print(f"timestamp      : {result['timestamp']}")
    print()

    for pkg in result["packages"]:
        status = pkg["status"]
        ptype = pkg["package_type"]
        print(f"  [{status:5s}] {ptype}")
        for issue in pkg.get("issues", []):
            print(f"          ISSUE  : {issue}")
        for warn in pkg.get("warnings", []):
            print(f"          WARN   : {warn}")

    print(f"\nResult saved: {LOGS_DIR / 'validation_result.json'}")

    if result["overall_status"] == STATUS_ABORT:
        print("\nABORT: dangerous operation detected. Stop immediately.")
        sys.exit(2)
    elif result["overall_status"] == STATUS_FAIL:
        print("\nFAIL: fix required before next step.")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
