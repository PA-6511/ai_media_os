import json
import logging
from typing import Any, Dict

from work_id_system.work_database import WorkDatabase


class WorkRegistry:
    """Generate and register unique work IDs for manga, light novels, and books."""

    TYPE_PREFIX = {
        "manga": "manga",
        "light_novel": "ln",
        "ln": "ln",
        "book": "book",
    }

    def __init__(self, database: WorkDatabase) -> None:
        self.database = database
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_work_id(self, title: str, type: str) -> str:
        work_type = self._normalize_type(type)
        existing = self.database.get_work_by_title_and_type(title=title, work_type=work_type)
        if existing:
            return str(existing["id"])

        prefix = self.TYPE_PREFIX[work_type]
        seq = self.database.next_sequence(prefix)
        return f"{prefix}_{seq:04d}"

    def register_work(self, work_data: Dict[str, Any]) -> Dict[str, Any]:
        title = str(work_data.get("title", "")).strip()
        if not title:
            raise ValueError("title is required")

        work_type = self._normalize_type(str(work_data.get("type", "")))
        existing = self.database.get_work_by_title_and_type(title=title, work_type=work_type)
        if existing:
            self.logger.info("work already exists id=%s title=%s", existing["id"], title)
            return existing

        work_id = self.generate_work_id(title, work_type)
        payload = {
            "id": work_id,
            "title": title,
            "author": work_data.get("author"),
            "publisher": work_data.get("publisher"),
            "genre": work_data.get("genre"),
            "type": work_type,
            "volumes": int(work_data.get("volumes", 0) or 0),
            "release_date": work_data.get("release_date"),
        }
        self.database.insert_work(payload)
        self.logger.info("work registered id=%s title=%s", work_id, title)
        return payload

    def _normalize_type(self, raw_type: str) -> str:
        value = raw_type.strip().lower()
        mapping = {
            "manga": "manga",
            "light_novel": "light_novel",
            "ln": "light_novel",
            "book": "book",
            "general_book": "book",
        }
        if value not in mapping:
            raise ValueError("type must be one of: manga, light_novel/ln, book")
        return mapping[value]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    db = WorkDatabase()
    registry = WorkRegistry(db)

    sample = {
        "title": "呪術廻戦",
        "author": "芥見下々",
        "publisher": "集英社",
        "genre": "バトル",
        "type": "manga",
        "volumes": 28,
        "release_date": "2026-03-01",
    }
    print(json.dumps(registry.register_work(sample), ensure_ascii=False, indent=2))
