import logging
from typing import Any, Dict


class ProposalGenerator:
    """Generate article proposals from adaptation detection events."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, event: Dict[str, Any]) -> Dict[str, Any]:
        work_title = str(event.get("work_title", "不明作品"))
        adaptation_type = str(event.get("adaptation_type", "other"))

        title = self._build_title(work_title, adaptation_type)
        proposal = {
            "source": "media_adaptation_ai",
            "action": "generate_media_news_article",
            "work_title": work_title,
            "adaptation_type": adaptation_type,
            "title": title,
            "priority": self._priority(event),
            "reason": str(event.get("reason", "メディア化情報を検出")),
            "metadata": {
                "news_source": event.get("source", ""),
                "date": event.get("date", ""),
                "keyword": event.get("keyword", ""),
            },
        }
        self.logger.info("media proposal generated title=%s", title)
        return proposal

    @staticmethod
    def _build_title(work_title: str, adaptation_type: str) -> str:
        if adaptation_type == "anime":
            return f"{work_title}アニメ続編決定！原作漫画も人気"
        if adaptation_type == "drama":
            return f"{work_title}ドラマ化決定！原作を先取りチェック"
        if adaptation_type == "movie":
            return f"{work_title}映画化決定！原作の見どころまとめ"
        if adaptation_type == "stage":
            return f"{work_title}舞台化決定！原作ファン向けガイド"
        return f"{work_title}メディア化最新ニュース"

    @staticmethod
    def _priority(event: Dict[str, Any]) -> float:
        base = 0.82
        adaptation_type = str(event.get("adaptation_type", "other"))
        source = str(event.get("source", ""))

        if adaptation_type == "anime":
            base += 0.12
        elif adaptation_type == "movie":
            base += 0.1
        elif adaptation_type == "drama":
            base += 0.08
        elif adaptation_type == "stage":
            base += 0.06

        if source in {"anime_news", "publisher", "official_sns"}:
            base += 0.03

        return round(min(base, 0.99), 2)
