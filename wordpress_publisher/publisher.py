import json
import logging
import os
from typing import Any, Dict

from wordpress_publisher.formatter import ArticleFormatter
from wordpress_publisher.term_resolver import TermResolver
from wordpress_publisher.wp_client import WordPressClient


class WordPressPublisher:
    def __init__(
        self,
        base_url: str,
        username: str,
        application_password: str,
        default_status: str = "draft",
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.default_status = default_status
        self.formatter = ArticleFormatter()
        self.client = WordPressClient(
            base_url=base_url,
            username=username,
            application_password=application_password,
        )
        self.term_resolver = TermResolver(self.client)

    def format_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        return self.formatter.to_wp_payload(article=article, status=self.default_status)

    def resolve_terms(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """category_names / tag_names を term ID 配列へ変換する。"""
        return self.term_resolver.enrich_payload_with_term_ids(payload)

    def publish(self, article: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        payload = self.format_article(article)
        resolved_payload = self.resolve_terms(payload)
        self.logger.info("prepared wordpress payload title=%s", resolved_payload.get("title"))

        if dry_run:
            self.logger.info("dry_run enabled. Skipping WordPress API call.")
            return {
                "dry_run": True,
                "request_payload": resolved_payload,
            }

        result = self.client.create_post(resolved_payload)
        return {
            "dry_run": False,
            "post_id": result.get("id"),
            "status": result.get("status"),
            "link": result.get("link"),
            "raw": result,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    sample_article = {
        "title": "今売れている漫画ランキングTOP20",
        "content": (
            "# 今売れている漫画ランキングTOP20\n\n"
            "## 導入\n"
            "話題の漫画をランキング形式で紹介します。\n\n"
            "## 作品紹介\n"
            "- [異世界料理道](https://example.com/ebook/1)\n"
            "- [恋するアルケミスト](https://example.com/ebook/2)\n\n"
            "## 購入リンク\n"
            "気になる作品は上記リンクから確認してください。"
        ),
    }

    base_url = os.getenv("WP_BASE_URL", "https://example.com")
    username = os.getenv("WP_USERNAME", "demo_user")
    app_password = os.getenv("WP_APP_PASSWORD", "demo_app_password")
    dry_run = os.getenv("WP_DRY_RUN", "1") == "1"

    publisher = WordPressPublisher(
        base_url=base_url,
        username=username,
        application_password=app_password,
        default_status="draft",
    )

    output = publisher.publish(sample_article, dry_run=dry_run)
    print(json.dumps(output, ensure_ascii=False, indent=2))
