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

    def check_featured_image_warning(self, result_payload: Dict[str, Any], article: Dict[str, Any]) -> None:
        """投稿後にアイキャッチ有無を確認し、未設定なら warning のみ出す。"""
        post_id = result_payload.get("id")
        post_id_text = str(post_id).strip() if post_id is not None else ""
        if not post_id_text:
            return

        row_id = str(article.get("row_id", "")).strip()
        work_id = str(article.get("work_id", "")).strip()
        slug = str(article.get("slug", "")).strip()
        title = str(article.get("title", "")).strip()
        draft_url = str(result_payload.get("link", "")).strip()

        try:
            post_data = self.client.get_post(post_id_text)
            if not isinstance(post_data, dict):
                self.logger.warning(
                    "featured image check skipped row_id=%s work_id=%s slug=%s wp_post_id=%s reason=post_not_found",
                    row_id,
                    work_id,
                    slug,
                    post_id_text,
                )
                return

            featured_media = post_data.get("featured_media")
            missing_featured = featured_media in (None, "", 0, "0")
            if missing_featured:
                self.logger.warning(
                    "featured image missing row_id=%s work_id=%s slug=%s wp_post_id=%s wp_draft_url=%s title=%s",
                    row_id,
                    work_id,
                    slug,
                    post_id_text,
                    draft_url,
                    title,
                )
        except Exception as exc:
            self.logger.warning(
                "featured image check failed row_id=%s work_id=%s slug=%s wp_post_id=%s error=%s",
                row_id,
                work_id,
                slug,
                post_id_text,
                exc,
            )

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
        self.check_featured_image_warning(result, article)
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
    username = os.getenv("WP_USER", "").strip() or os.getenv("WP_USERNAME", "demo_user")
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
