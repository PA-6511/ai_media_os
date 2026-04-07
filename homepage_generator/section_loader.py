from typing import Dict, List


class SectionLoader:
    """Manage section order and labels for mall-style homepage."""

    def load(self) -> List[Dict[str, str]]:
        return [
            {"key": "hero_banner", "title": "注目トピック"},
            {"key": "sale_ranking", "title": "セールランキング"},
            {"key": "today_price_drop", "title": "今日の値下げ作品"},
            {"key": "new_releases", "title": "新刊発売"},
            {"key": "popular_manga", "title": "人気漫画ランキング"},
            {"key": "completed_manga", "title": "完結漫画まとめ"},
            {"key": "genre_ranking", "title": "ジャンルランキング"},
            {"key": "keyword_tags", "title": "キーワードタグ"},
        ]
