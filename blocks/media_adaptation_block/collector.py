import logging
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup


class MediaSourceCollector:
    """Collect media adaptation signals from news, official, SNS, and anime sites."""

    def __init__(self, timeout_sec: int = 8) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sources = {
            "news_site": "https://example.com/news/media",
            "official_announcement": "https://example.com/official/releases",
            "sns_trend": "https://example.com/sns/trend",
            "anime_info_site": "https://example.com/anime/news",
        }

    def collect(self) -> Dict[str, List[Dict[str, Any]]]:
        data: Dict[str, List[Dict[str, Any]]] = {}
        for source, url in self.sources.items():
            data[source] = self._fetch_source(source, url)
            self.logger.info("media signals collected source=%s count=%d", source, len(data[source]))
        return data

    def _fetch_source(self, source: str, url: str) -> List[Dict[str, Any]]:
        try:
            response = requests.get(url, timeout=self.timeout_sec)
            response.raise_for_status()
            return self._parse_html(source, response.text)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback media data used source=%s reason=%s", source, exc)
            return self._fallback_data(source)

    def _parse_html(self, source: str, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".media-topic")
        items: List[Dict[str, Any]] = []

        for card in cards:
            title = card.get("data-title") or self._text(card, ".title")
            work_title = card.get("data-work-title") or self._text(card, ".work-title")
            adaptation_type = card.get("data-adaptation-type") or self._text(card, ".adaptation-type")
            event_type = card.get("data-event-type") or self._text(card, ".event-type")
            announced_at = card.get("data-announced-at") or self._text(card, ".announced-at")
            trend_score = self._to_int(card.get("data-trend-score") or self._text(card, ".trend-score"))
            popularity_score = self._to_int(
                card.get("data-popularity-score") or self._text(card, ".popularity-score")
            )

            items.append(
                {
                    "source": source,
                    "title": title,
                    "work_title": work_title,
                    "adaptation_type": adaptation_type,
                    "event_type": event_type,
                    "announced_at": announced_at,
                    "trend_score": trend_score,
                    "popularity_score": popularity_score,
                }
            )
        return items

    @staticmethod
    def _text(node, selector: str) -> str:
        el = node.select_one(selector)
        return el.get_text(strip=True) if el else ""

    @staticmethod
    def _to_int(value: str) -> int:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0

    @staticmethod
    def _fallback_data(source: str) -> List[Dict[str, Any]]:
        return [
            {
                "source": source,
                "title": "異世界料理道 アニメ化決定",
                "work_title": "異世界料理道",
                "adaptation_type": "アニメ化",
                "event_type": "新規メディア化発表",
                "announced_at": "2026-03-08",
                "trend_score": 86,
                "popularity_score": 82,
            },
            {
                "source": source,
                "title": "恋するアルケミスト 実写ドラマ キャスト発表",
                "work_title": "恋するアルケミスト",
                "adaptation_type": "実写ドラマ化",
                "event_type": "キャスト発表",
                "announced_at": "2026-03-07",
                "trend_score": 72,
                "popularity_score": 74,
            },
            {
                "source": source,
                "title": "夜明けの魔導院 映画化 PV公開",
                "work_title": "夜明けの魔導院",
                "adaptation_type": "映画化",
                "event_type": "PV公開",
                "announced_at": "2026-03-06",
                "trend_score": 78,
                "popularity_score": 80,
            },
            {
                "source": source,
                "title": "新作バトルクロニクル ゲーム化 放送開始日発表",
                "work_title": "新作バトルクロニクル",
                "adaptation_type": "ゲーム化",
                "event_type": "放送開始日発表",
                "announced_at": "2026-03-05",
                "trend_score": 65,
                "popularity_score": 63,
            },
        ]
