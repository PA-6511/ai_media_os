from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

REQUIRED_FOR_DRY_RUN = [
    "SPREADSHEET_ID",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "OPENAI_API_KEY",
]

RECOMMENDED_FOR_DRY_RUN = [
    "SLACK_WEBHOOK_URL",
]

OPTIONAL_FOR_DRY_RUN = [
    "WP_BASE_URL",
    "WP_USER",
    "WP_USERNAME",
    "WP_APP_PASSWORD",
]

RUNTIME_FLAGS = [
    "DRY_RUN",
    "WP_DRY_RUN",
    "MAX_ROWS_PER_RUN",
]

PLACEHOLDER_MARKERS = (
    "changeme",
    "your_",
    "dummy",
    "example",
    "placeholder",
    "todo",
    "xxxx",
    "test",
    "仮",
)


def _normalize(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'")


def _is_placeholder(value: str) -> bool:
    text = value.lower()
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def _status(key: str) -> tuple[str, str]:
    value = _normalize(os.getenv(key))
    if not value:
        return "missing", "未設定"
    if _is_placeholder(value):
        return "placeholder", "仮値"
    return "configured", "設定済み"


def _print_group(name: str, keys: list[str]) -> list[str]:
    print(f"[{name}]")
    issues: list[str] = []
    for key in keys:
        code, label = _status(key)
        print(f"- {key}: {label}")
        if code in {"missing", "placeholder"}:
            issues.append(key)
    return issues


def main() -> int:
    load_dotenv(ENV_PATH)

    print("check_env: .env 診断 (値は表示しません)")
    print(f"env_file: {ENV_PATH}")

    missing_required = _print_group("必須(DRY_RUN)", REQUIRED_FOR_DRY_RUN)
    print()
    _print_group("推奨(DRY_RUN)", RECOMMENDED_FOR_DRY_RUN)
    print()
    _print_group("後でも可(DRY_RUN)", OPTIONAL_FOR_DRY_RUN)
    print()
    _print_group("実行フラグ", RUNTIME_FLAGS)

    print()
    wp_user = _normalize(os.getenv("WP_USER"))
    wp_username = _normalize(os.getenv("WP_USERNAME"))
    if wp_user:
        print("INFO: WP_USER が設定されています")
    elif wp_username:
        print("INFO: 旧キー WP_USERNAME が設定されています (互換モード)")

    sa_path = _normalize(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
    if sa_path.startswith("/"):
        exists = Path(sa_path).exists()
        print(f"INFO: service account file exists: {'yes' if exists else 'no'}")
        if not exists and "GOOGLE_SERVICE_ACCOUNT_JSON" not in missing_required:
            missing_required.append("GOOGLE_SERVICE_ACCOUNT_JSON")

    if missing_required:
        print()
        print("NG: DRY_RUN 1行検証の必須項目が不足しています")
        print("不足:", ", ".join(sorted(set(missing_required))))
        return 1

    print()
    print("OK: DRY_RUN 1行検証の必須項目は満たしています")
    return 0


if __name__ == "__main__":
    sys.exit(main())