import json
import logging
from typing import Any, Dict, List

from price_drop_ai.price_collector import PriceCollector
from price_drop_ai.price_history import PriceHistoryStore
from price_drop_ai.proposal_generator import PriceDropProposalGenerator


class PriceDropAI:
    """Detect price drops and generate article proposals."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collector = PriceCollector()
        self.history = PriceHistoryStore()
        self.proposal_generator = PriceDropProposalGenerator()

    def collect_prices(self) -> List[Dict[str, Any]]:
        return self.collector.collect()

    def detect_price_drop(self, price_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        for current in price_data:
            work_id = str(current.get("work_id", "")).strip()
            store = str(current.get("store", "")).strip()
            if not work_id or not store:
                continue

            prev = self.history.get_latest(work_id=work_id, store=store)
            self.history.save(current)

            if not prev:
                continue

            previous_price = float(prev.get("price", 0.0))
            current_price = float(current.get("price", 0.0))
            if previous_price <= 0 or current_price >= previous_price:
                continue

            drop_amount = previous_price - current_price
            discount_rate = (drop_amount / previous_price) * 100.0
            is_sale = bool(current.get("is_sale", False))

            # Detect when any one of the required conditions is satisfied.
            is_drop_event = (
                discount_rate >= 10.0
                or drop_amount >= 50.0
                or is_sale
            )
            if not is_drop_event:
                continue

            events.append(
                {
                    "work_id": work_id,
                    "title": current.get("title"),
                    "store": store,
                    "previous_price": int(previous_price),
                    "current_price": int(current_price),
                    "price_drop": int(drop_amount),
                    "discount_rate": round(discount_rate, 2),
                    "is_sale": is_sale,
                }
            )

        self.logger.info("price drop events detected count=%d", len(events))
        return events

    def generate_proposal(self, drop_event: Dict[str, Any]) -> Dict[str, Any]:
        return self.proposal_generator.generate(drop_event)

    def run(self) -> List[Dict[str, Any]]:
        price_data = self.collect_prices()
        events = self.detect_price_drop(price_data)
        proposals = [self.generate_proposal(event) for event in events]
        self.logger.info("price drop proposals generated count=%d", len(proposals))
        return proposals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    ai = PriceDropAI()
    proposals = ai.run()
    print(json.dumps(proposals, ensure_ascii=False, indent=2))
