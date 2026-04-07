import json
import logging
import os
from typing import Any, Dict, List

from homepage_generator.ranking_loader import RankingLoader
from homepage_generator.sale_loader import SaleLoader
from homepage_generator.section_loader import SectionLoader
from homepage_generator.wp_publisher import WPPublisher


class HomepageGenerator:
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.section_loader = SectionLoader()
        self.ranking_loader = RankingLoader()
        self.sale_loader = SaleLoader()

    def load_sections(self) -> Dict[str, Any]:
        sections = self.section_loader.load()
        ranking_data = self.ranking_loader.load()
        sale_data = self.sale_loader.load()
        return {
            "sections": sections,
            **ranking_data,
            **sale_data,
        }

    def generate_homepage(self, data: Dict[str, Any]) -> Dict[str, str]:
        html = self._render_html(data)
        return {
            "title": "電子書籍モールトップ | セール・新刊・ランキング",
            "content": html,
        }

    def publish_homepage(self, page_data: Dict[str, str], dry_run: bool = True) -> Dict[str, Any]:
        publisher = WPPublisher(
            base_url=os.getenv("WP_BASE_URL", "https://example.com"),
            username=os.getenv("WP_USERNAME", "demo_user"),
            app_password=os.getenv("WP_APP_PASSWORD", "demo_app_password"),
        )
        page_id_raw = os.getenv("WP_HOMEPAGE_PAGE_ID", "").strip()
        page_id = int(page_id_raw) if page_id_raw.isdigit() else None
        return publisher.publish(page_data, page_id=page_id, dry_run=dry_run)

    def run(self, dry_run: bool = True) -> Dict[str, Any]:
        data = self.load_sections()
        page_data = self.generate_homepage(data)
        publish_result = self.publish_homepage(page_data, dry_run=dry_run)
        self.logger.info("homepage generation pipeline completed")
        return {"page": page_data, "publish_result": publish_result}

    def _render_html(self, data: Dict[str, Any]) -> str:
        hero = data.get("hero_banner", {})
        sale_ranking = data.get("sale_ranking", [])
        today_drop = data.get("today_price_drop", [])
        new_releases = data.get("new_releases", [])
        popular_manga = data.get("popular_manga", [])
        completed_manga = data.get("completed_manga", [])
        genre_ranking = data.get("genre_ranking", [])
        keyword_tags = data.get("keyword_tags", [])

        sale_rows = "".join(
            f"<li><strong>{x.get('rank')}位</strong> {x.get('title')} - {x.get('discount')}%OFF "
            f"<a href='{x.get('url')}' target='_blank' rel='noopener'>購入</a></li>"
            for x in sale_ranking
        )

        drop_rows = "".join(
            f"<li>{x.get('title')} - {x.get('discount')}%OFF "
            f"<a href='{x.get('url')}' target='_blank' rel='noopener'>確認</a></li>"
            for x in today_drop
        )

        release_rows = "".join(
            f"<li>{x.get('date')} {x.get('title')} "
            f"<a href='{x.get('url')}' target='_blank' rel='noopener'>Amazonリンク</a></li>"
            for x in new_releases
        )

        popular_rows = "".join(
            f"<li>{x.get('rank')}位 {x.get('title')} <a href='{x.get('url')}' target='_blank' rel='noopener'>詳細</a></li>"
            for x in popular_manga
        )

        completed_rows = "".join(
            f"<li>{x.get('title')} <a href='{x.get('url')}' target='_blank' rel='noopener'>まとめ</a></li>"
            for x in completed_manga
        )

        genre_rows = "".join(
            f"<li>{x.get('genre')}ランキング 1位: {x.get('top_title')} "
            f"<a href='{x.get('url')}' target='_blank' rel='noopener'>見る</a></li>"
            for x in genre_ranking
        )

        tag_rows = "".join(
            f"<a href='/tag/{str(tag)}' style='display:inline-block;padding:4px 8px;border:1px solid #ddd;border-radius:999px;margin:4px;text-decoration:none;'>{tag}</a>"
            for tag in keyword_tags
        )

        return f"""
<div class='mall-homepage'>
  <section class='hero' style='padding:20px;border:1px solid #eee;background:#fafafa;margin-bottom:16px;'>
    <h1>{hero.get('title', '電子書籍モール')}</h1>
    <p>{hero.get('subtitle', '今話題の作品をチェック')}</p>
  </section>

  <section><h2>セールランキング</h2><ol>{sale_rows}</ol></section>
  <section><h2>今日の値下げ作品</h2><ul>{drop_rows}</ul></section>
  <section><h2>新刊発売</h2><ul>{release_rows}</ul></section>
  <section><h2>人気漫画ランキング</h2><ol>{popular_rows}</ol></section>
  <section><h2>完結漫画まとめ</h2><ul>{completed_rows}</ul></section>
  <section><h2>ジャンルランキング</h2><ul>{genre_rows}</ul></section>
  <section><h2>キーワードタグ</h2><div>{tag_rows}</div></section>
</div>
""".strip()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    dry_run = os.getenv("WP_DRY_RUN", "1") == "1"

    generator = HomepageGenerator()
    result = generator.run(dry_run=dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
