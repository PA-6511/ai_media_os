import logging
import re
from typing import Any, Dict, List


class NewsParser:
    """Parse news text and extract candidate work titles."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse(self, news_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed: List[Dict[str, Any]] = []
        for row in news_rows:
            title = str(row.get("title", "")).strip()
            content = str(row.get("content", "")).strip()
            work_title = self._extract_work_title(title)
            parsed.append(
                {
                    **row,
                    "title": title,
                    "content": content,
                    "work_title": work_title,
                    "text": f"{title}\n{content}",
                }
            )
        self.logger.info("news parsed count=%d", len(parsed))
        return parsed

    def _extract_work_title(self, title: str) -> str:
        # Extract leading phrase before adaptation keywords.
        separators = [" アニメ", " 実写", " 映画", " ドラマ", " 舞台"]
        for sep in separators:
            if sep in title:
                return title.split(sep)[0].strip()

        # Fallback: keep Japanese/alnum phrase from title head.
        m = re.match(r"([一-龠ぁ-んァ-ヴーA-Za-z0-9・ー\s]{2,30})", title)
        return m.group(1).strip() if m else title
