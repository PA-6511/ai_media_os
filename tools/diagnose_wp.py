"""WordPress 接続診断ツール

実投稿は一切行わず、REST API の認証・権限・投稿タイプを確認します。

使い方:
    python3 tools/diagnose_wp.py
"""
import sys
import os
from pathlib import Path

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
print("OK: .env 読み込み")


def check_env() -> tuple[str, str, str]:
    base_url = os.environ.get("WP_BASE_URL", "").rstrip("/")
    username = os.environ.get("WP_USER", "") or os.environ.get("WP_USERNAME", "")
    app_password = os.environ.get("WP_APP_PASSWORD", "")

    missing = []
    if not base_url:
        missing.append("WP_BASE_URL")
    if not username:
        missing.append("WP_USER (or legacy WP_USERNAME)")
    if not app_password:
        missing.append("WP_APP_PASSWORD")

    if missing:
        print(f"エラー: 環境変数が未設定です: {', '.join(missing)}")
        print("  .env に設定してから再実行してください。")
        sys.exit(1)

    print(f"OK: 環境変数確認 (WP_BASE_URL={base_url}, WP_USER={username})")
    return base_url, username, app_password


def check_auth(base_url: str, username: str, app_password: str) -> dict:
    url = f"{base_url}/wp-json/wp/v2/users/me"
    try:
        resp = requests.get(
            url,
            auth=(username, app_password),
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
    except requests.ConnectionError as e:
        print(f"エラー: WordPress に接続できません: {e}")
        sys.exit(1)
    except requests.Timeout:
        print(f"エラー: WordPress への接続がタイムアウトしました (15秒)")
        sys.exit(1)

    if resp.status_code == 401:
        print(f"エラー: WordPress 認証エラー (401) — WP_USER (or WP_USERNAME) / WP_APP_PASSWORD を確認してください")
        sys.exit(1)
    if resp.status_code == 403:
        print(f"エラー: WordPress 権限エラー (403) — ユーザーの権限を確認してください")
        sys.exit(1)
    if resp.status_code >= 400:
        print(f"エラー: WordPress REST API エラー status={resp.status_code} body={resp.text[:200]}")
        sys.exit(1)

    data = resp.json()
    print(f"OK: REST API 認証成功 (ユーザーID={data.get('id')}, 表示名={data.get('name')}, roles={data.get('roles')})")
    return data


def check_post_type(base_url: str, username: str, app_password: str) -> None:
    url = f"{base_url}/wp-json/wp/v2/types/post"
    try:
        resp = requests.get(
            url,
            auth=(username, app_password),
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        print(f"エラー: 投稿タイプ確認中に例外が発生しました: {e}")
        sys.exit(1)

    if resp.status_code >= 400:
        print(f"エラー: 投稿タイプ 'post' の取得に失敗しました status={resp.status_code}")
        sys.exit(1)

    data = resp.json()
    rest_base = data.get("rest_base", "")
    print(f"OK: 投稿タイプ 'post' 確認 (rest_base={rest_base})")


def check_draft_permission(base_url: str, username: str, app_password: str) -> None:
    """draft ステータスで投稿一覧が取得できるか（投稿作成はしない）"""
    url = f"{base_url}/wp-json/wp/v2/posts"
    params = {"status": "draft", "per_page": 1}
    try:
        resp = requests.get(
            url,
            auth=(username, app_password),
            params=params,
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        print(f"エラー: draft 一覧取得中に例外が発生しました: {e}")
        sys.exit(1)

    if resp.status_code == 401:
        print(f"エラー: draft 取得時に認証エラー (401)")
        sys.exit(1)
    if resp.status_code == 403:
        print(f"エラー: draft 取得時に権限エラー (403) — ユーザーに投稿権限がありません")
        sys.exit(1)
    if resp.status_code >= 400:
        print(f"エラー: draft ステータス確認に失敗 status={resp.status_code} body={resp.text[:200]}")
        sys.exit(1)

    count = len(resp.json()) if isinstance(resp.json(), list) else 0
    total = resp.headers.get("X-WP-Total", "不明")
    print(f"OK: draft status 確認 (既存draft件数={total}件, 今回取得={count}件) ※投稿は作成していません")


def check_namespaces(base_url: str) -> None:
    url = f"{base_url}/wp-json/"
    try:
        resp = requests.get(url, timeout=10)
    except Exception as e:
        print(f"警告: REST API ルート確認中に例外: {e}")
        return

    if resp.status_code >= 400:
        print(f"警告: REST API ルート取得失敗 status={resp.status_code}")
        return

    data = resp.json()
    namespaces = data.get("namespaces", [])
    wp_v2_ok = "wp/v2" in namespaces
    print(f"OK: REST API ルート確認 (wp/v2={'あり' if wp_v2_ok else 'なし'}, namespaces={namespaces[:5]})")


def main() -> None:
    print("=" * 50)
    print("WordPress 接続診断")
    print("※ 実投稿は一切行いません")
    print("=" * 50)

    base_url, username, app_password = check_env()
    check_namespaces(base_url)
    user_data = check_auth(base_url, username, app_password)
    check_post_type(base_url, username, app_password)
    check_draft_permission(base_url, username, app_password)

    print()
    print("=" * 50)
    print("診断結果: 全チェック通過")
    print(f"  WP_BASE_URL : {base_url}")
    print(f"  WP_USER     : {username}")
    print(f"  ユーザーID  : {user_data.get('id')}")
    print(f"  表示名      : {user_data.get('name')}")
    print(f"  roles       : {user_data.get('roles')}")
    print()
    print("次のステップ: 1件だけ実draft確認は WP_DRY_RUN=0 bash scripts/run_ai_post_queue.sh --max-items 1 を実行")
    print("=" * 50)


if __name__ == "__main__":
    main()
