from typing import Any, Dict, List


class SaleSorter:
    """Sort sale data by discount and remove duplicate title/store pairs."""

    def rank(self, sales: List[Dict[str, Any]], top_k: int = 20) -> List[Dict[str, Any]]:
        seen = set()
        unique: List[Dict[str, Any]] = []

        for item in sales:
            title = str(item.get("title", "")).strip()
            store = str(item.get("store", "")).strip().lower()
            if not title or not store:
                continue
            key = (title, store)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        unique.sort(key=lambda x: int(x.get("discount", 0)), reverse=True)
        return unique[:top_k]
