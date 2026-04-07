import logging
from typing import Dict, List


class LinkRecommender:
    """Recommends next pages and internal links based on stage and current article."""

    def __init__(self, base_url: str = "https://example.com") -> None:
        self.base_url = base_url.rstrip("/")
        self.logger = logging.getLogger(self.__class__.__name__)

    def recommend(self, keyword: str, article_type: str, stage: str, current_article: str) -> Dict[str, List[str]]:
        work_slug = self._to_slug(keyword)
        work_title = self._extract_work_title(keyword)

        stage_routes = self._stage_routes(work_title, work_slug)
        next_articles = stage_routes.get(stage, stage_routes["information_gathering"])[:3]

        internal_links = [
            self._to_url(path)
            for path in self._internal_link_paths(work_slug=work_slug, stage=stage, article_type=article_type)
        ]

        self.logger.info(
            "links recommended keyword=%s article_type=%s stage=%s next=%d links=%d",
            keyword,
            article_type,
            stage,
            len(next_articles),
            len(internal_links),
        )
        return {
            "next_articles": next_articles,
            "internal_links": internal_links,
        }

    def _stage_routes(self, work_title: str, work_slug: str) -> Dict[str, List[str]]:
        return {
            "information_gathering": [
                f"{work_title} review and highlights",
                f"{work_title} latest volume and order guide",
                f"{work_title} beginner reading roadmap",
            ],
            "comparison": [
                f"{work_title} vs similar titles comparison",
                f"{work_title} ranking position and audience fit",
                f"{work_title} completed set value check",
            ],
            "purchase_ready": [
                f"{work_title} sale and coupon tracker",
                f"{work_title} best price by store",
                f"{work_title} all-volume bundle buying guide",
            ],
        }

    def _internal_link_paths(self, work_slug: str, stage: str, article_type: str) -> List[str]:
        common = [
            f"/work/{work_slug}",
            f"/volume/{work_slug}",
            f"/sale/{work_slug}",
        ]

        if stage == "information_gathering":
            return common + [f"/ranking/{work_slug}-related", f"/genre/{work_slug}-genre"]

        if stage == "comparison":
            return common + [f"/ranking/top-{work_slug}", f"/work/{work_slug}-alternatives"]

        if article_type == "sale_article":
            return common + [f"/coupon/{work_slug}", f"/buy/{work_slug}"]

        return common + [f"/buy/{work_slug}", f"/coupon/{work_slug}"]

    def _to_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _to_slug(self, keyword: str) -> str:
        title = self._extract_work_title(keyword)
        slug = (
            title.lower()
            .replace(" ", "-")
            .replace("/", "-")
            .replace("_", "-")
        )
        return "-".join(part for part in slug.split("-") if part) or "untitled"

    def _extract_work_title(self, keyword: str) -> str:
        cleaned = (keyword or "").strip()
        split_tokens = [
            "何巻",
            "どこまで",
            "読む順",
            "評価",
            "レビュー",
            "セール",
            "クーポン",
            "おすすめ",
            "ランキング",
            "最新刊",
            "発売日",
        ]
        for token in split_tokens:
            if token in cleaned:
                cleaned = cleaned.split(token)[0].strip()
                break

        return cleaned or "target work"
