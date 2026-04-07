import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from release_calendar_ai.release_collector import ReleaseCollector
from release_calendar_ai.release_parser import ReleaseParser
from release_calendar_ai.wp_publisher import WPPublisher


class ReleaseCalendarAI:
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collector = ReleaseCollector()
        self.parser = ReleaseParser()

    def collect_releases(self) -> List[Dict[str, Any]]:
        return self.collector.collect()

    def generate_calendar(self, release_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        monthly = self.parser.parse(release_data)
        pages: List[Dict[str, Any]] = []

        for ym, payload in sorted(monthly.items()):
            year, month = ym.split("-")
            title = f"【{int(year)}年{int(month)}月】漫画新刊発売日カレンダー"

            lines = [
                f"# {title}",
                "",
                f"{int(month)}月発売予定の漫画・ライトノベル・書籍を日付順にまとめました。",
                "",
            ]

            days = payload.get("days", {})
            for day, works in days.items():
                dt = datetime.strptime(day, "%Y-%m-%d")
                lines.append(f"## {dt.month}月{dt.day}日")
                for work in works:
                    work_title = work.get("title", "不明作品")
                    publisher = work.get("publisher", "出版社不明")
                    link = work.get("affiliate_url", "")
                    lines.append(f"- {work_title}（{publisher}）")
                    if link:
                        lines.append(f"  - 購入リンク: [{work_title}]({link})")
                lines.append("")

            pages.append(
                {
                    "year_month": ym,
                    "title": title,
                    "content": "\n".join(lines).strip(),
                }
            )

        self.logger.info("calendar pages generated count=%d", len(pages))
        return pages

    def publish_calendar(self, calendar_page: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        publisher = WPPublisher(
            base_url=os.getenv("WP_BASE_URL", "https://example.com"),
            username=os.getenv("WP_USERNAME", "demo_user"),
            app_password=os.getenv("WP_APP_PASSWORD", "demo_app_password"),
        )
        return publisher.publish(calendar_page, dry_run=dry_run)

    def run(self, dry_run: bool = True) -> Dict[str, Any]:
        release_data = self.collect_releases()
        pages = self.generate_calendar(release_data)

        publish_results = []
        for page in pages:
            result = self.publish_calendar(page, dry_run=dry_run)
            publish_results.append({"year_month": page["year_month"], "result": result})

        output = {
            "pages": pages,
            "publish_results": publish_results,
        }
        self.logger.info("release calendar pipeline completed pages=%d", len(pages))
        return output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    dry_run = os.getenv("WP_DRY_RUN", "1") == "1"

    ai = ReleaseCalendarAI()
    result = ai.run(dry_run=dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
