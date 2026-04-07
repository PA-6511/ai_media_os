import json
import logging
import os
from typing import Any, Dict, List

from sale_ranking_ai.sale_collector import SaleCollector
from sale_ranking_ai.sale_sorter import SaleSorter
from sale_ranking_ai.wp_publisher import WPPublisher


class SaleRankingAI:
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collector = SaleCollector()
        self.sorter = SaleSorter()

    def collect_sales(self) -> List[Dict[str, Any]]:
        return self.collector.collect()

    def rank_sales(self, sales: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.sorter.rank(sales, top_k=20)

    def generate_page(self, ranked_sales: List[Dict[str, Any]]) -> Dict[str, Any]:
        title = "【最新】Kindle漫画セールランキング"
        lines = [
            "# 【最新】Kindle漫画セールランキング",
            "",
            "セール中の漫画・電子書籍を割引率順でまとめました。",
            "",
            "## ランキング一覧",
            "",
        ]

        for idx, item in enumerate(ranked_sales, start=1):
            work_title = item.get("title", "不明作品")
            discount = int(item.get("discount", 0))
            store = item.get("store", "store")
            url = item.get("url", "")
            lines.append(f"### {idx}位 {work_title}（{discount}%OFF / {store}）")
            if url:
                lines.append(f"- 購入リンク: [{work_title}]({url})")
            lines.append("")

        lines.append("## 購入前チェック")
        lines.append("- セール期限と対象巻数を必ず確認してください。")
        lines.append("- ポイント還元キャンペーンもあわせて確認するとお得です。")

        return {
            "title": title,
            "content": "\n".join(lines).strip(),
        }

    def run(self, dry_run: bool = True) -> Dict[str, Any]:
        sales = self.collect_sales()
        ranked = self.rank_sales(sales)
        page = self.generate_page(ranked)

        publisher = WPPublisher(
            base_url=os.getenv("WP_BASE_URL", "https://example.com"),
            username=os.getenv("WP_USERNAME", "demo_user"),
            app_password=os.getenv("WP_APP_PASSWORD", "demo_app_password"),
        )
        publish_result = publisher.publish(page, dry_run=dry_run)

        output = {
            "article": page,
            "ranked_count": len(ranked),
            "publish_result": publish_result,
        }
        self.logger.info("sale ranking pipeline completed ranked_count=%d", len(ranked))
        return output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    dry_run = os.getenv("WP_DRY_RUN", "1") == "1"
    ai = SaleRankingAI()
    result = ai.run(dry_run=dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
