from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List


class ReleaseParser:
    """Parse and group release records by year/month and date."""

    def parse(self, rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        # Key: YYYY-MM, Value: grouped calendar payload
        monthly: Dict[str, Dict[str, Any]] = {}

        grouped = defaultdict(list)
        for row in rows:
            date_str = str(row.get("release_date", "")).strip()
            if not date_str:
                continue
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            ym = dt.strftime("%Y-%m")
            grouped[ym].append({**row, "_dt": dt})

        for ym, items in grouped.items():
            items.sort(key=lambda x: x["_dt"])
            by_day = defaultdict(list)
            for item in items:
                day = item["_dt"].strftime("%Y-%m-%d")
                clean = {k: v for k, v in item.items() if k != "_dt"}
                by_day[day].append(clean)

            monthly[ym] = {
                "year_month": ym,
                "days": dict(sorted(by_day.items())),
            }

        return monthly
