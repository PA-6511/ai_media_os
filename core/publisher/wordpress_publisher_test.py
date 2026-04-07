from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectionError, RequestException, Timeout

WP_URL = os.getenv("WP_URL", "").strip()
WP_USERNAME = os.getenv("WP_USERNAME", "").strip()
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "").strip()


class WordPressPublisher:
    """WordPress REST API へ下書き投稿する最小確認クラス。"""

    def __init__(self, wp_url: str, username: str, app_password: str, timeout_sec: int = 15) -> None:
        self.wp_url = wp_url.rstrip("/")
        self.username = username
        self.app_password = app_password
        self.timeout_sec = timeout_sec

    def build_post_payload(self, title: str, content: str) -> dict[str, str]:
        """投稿用の最小ペイロードを作る。"""
        return {
            "title": title,
            "content": content,
            "status": "draft",
        }

    def publish_draft(self, title: str, content: str) -> requests.Response | None:
        """WordPress REST API に draft 投稿を作成する。"""
        endpoint = f"{self.wp_url}/wp-json/wp/v2/posts"
        payload = self.build_post_payload(title=title, content=content)

        try:
            response = requests.post(
                endpoint,
                json=payload,
                auth=HTTPBasicAuth(self.username, self.app_password),
                timeout=self.timeout_sec,
            )
            return response
        except Timeout:
            print("接続失敗: タイムアウトが発生しました。")
            return None
        except ConnectionError:
            print("接続失敗: WordPressに接続できません。")
            return None
        except RequestException as exc:
            print(f"リクエスト失敗: {exc}")
            return None

    def print_response_summary(self, response: requests.Response | None) -> None:
        """レスポンスの要約を表示する。"""
        if response is None:
            print("レスポンスなし（接続エラー）")
            return

        print(f"status_code: {response.status_code}")

        if response.status_code in (401, 403):
            print("認証失敗: WP_USERNAME / WP_APP_PASSWORD を確認してください。")
            print("response.text:")
            print(response.text)
            return

        if response.ok:
            try:
                data: dict[str, Any] = response.json()
            except ValueError:
                print("成功しましたがJSON解析に失敗しました。")
                print(response.text)
                return

            print("投稿成功（draft作成）")
            print(f"post_id: {data.get('id')}")
            print(f"status: {data.get('status')}")
            print(f"title: {data.get('title', {}).get('rendered')}")
            return

        print("投稿失敗")
        print("response.text:")
        print(response.text)


def run_test() -> None:
    """テスト投稿を1本作成して結果を表示する。"""
    title = "テスト投稿"
    content = "これはAI Media OSのテスト投稿です。"

    if not (WP_URL and WP_USERNAME and WP_APP_PASSWORD):
        print("設定不足: 環境変数 WP_URL / WP_USERNAME / WP_APP_PASSWORD を設定してください。")
        return

    publisher = WordPressPublisher(wp_url=WP_URL, username=WP_USERNAME, app_password=WP_APP_PASSWORD)
    response = publisher.publish_draft(title=title, content=content)
    publisher.print_response_summary(response)


if __name__ == "__main__":
    run_test()
