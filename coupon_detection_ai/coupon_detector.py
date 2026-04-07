import json
import logging
from typing import Any, Dict, List

from coupon_detection_ai.coupon_collector import CouponCollector
from coupon_detection_ai.proposal_generator import CouponProposalGenerator


class CouponDetectionAI:
    """Detect high-value coupons and generate article ideas."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collector = CouponCollector()
        self.proposal_generator = CouponProposalGenerator()

    def collect_coupons(self) -> List[Dict[str, Any]]:
        return self.collector.collect()

    def detect_coupon(self, coupon_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for row in coupon_data:
            coupon_type = str(row.get("coupon_type", "percentage")).lower()
            discount = float(row.get("discount", 0))
            target_count = int(row.get("target_count", 0))

            is_high_percentage = coupon_type == "percentage" and discount >= 30
            is_high_yen = coupon_type == "yen" and discount >= 300
            has_large_target = target_count >= 50

            # Trigger when coupon value is high and campaign scope is meaningful.
            if (is_high_percentage or is_high_yen) and has_large_target:
                events.append(row)

        self.logger.info("coupon events detected count=%d", len(events))
        return events

    def generate_proposal(self, coupon_event: Dict[str, Any]) -> Dict[str, Any]:
        return self.proposal_generator.generate(coupon_event)

    def run(self) -> List[Dict[str, Any]]:
        data = self.collect_coupons()
        events = self.detect_coupon(data)
        proposals = [self.generate_proposal(e) for e in events]
        self.logger.info("coupon proposals generated count=%d", len(proposals))
        return proposals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    ai = CouponDetectionAI()
    proposals = ai.run()
    print(json.dumps(proposals, ensure_ascii=False, indent=2))
