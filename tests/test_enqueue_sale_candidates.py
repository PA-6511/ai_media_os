from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

_spec = importlib.util.spec_from_file_location(
    "enqueue_sale_candidates",
    PROJECT_DIR / "tools" / "enqueue_sale_candidates.py",
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]


class TestEnqueueSaleCandidates(unittest.TestCase):
    def _candidate(
        self,
        *,
        cid: str,
        review_status: str,
        sale_end_date: str,
        title: str = "test title",
    ) -> dict:
        return {
            "candidate_id": cid,
            "source_store": "rakuten_kobo",
            "work_title": title,
            "campaign_name": "test campaign",
            "sale_start_date": sale_end_date,
            "sale_end_date": sale_end_date,
            "entry_required": "required",
            "discount_text": "30%OFF",
            "point_text": "10%",
            "official_url": "https://example.com/of",
            "rakuten_url": "https://example.com/rk",
            "dmm_url": "",
            "amazon_url": "",
            "cta_store_priority": "rakuten,official",
            "review_status": review_status,
        }

    def test_select_target_picks_nearest_approved(self) -> None:
        today = datetime.now(timezone.utc).date()
        near = (today + timedelta(days=1)).isoformat()
        far = (today + timedelta(days=7)).isoformat()

        stats, results = _mod._collect_valid_candidates(
            [
                self._candidate(cid="c2", review_status="approved", sale_end_date=far, title="far"),
                self._candidate(cid="c1", review_status="approved", sale_end_date=near, title="near"),
                self._candidate(cid="c3", review_status="pending", sale_end_date=near, title="pending"),
            ]
        )

        self.assertEqual(stats["valid"], 3)
        target = _mod._select_target(results)
        self.assertIsNotNone(target)
        self.assertEqual(target["candidate_id"], "c1")

    def test_enqueue_dry_run_no_approved_returns_zero(self) -> None:
        future = (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat()
        payload = [self._candidate(cid="p1", review_status="pending", sale_end_date=future)]

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "candidates.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            rc = _mod.enqueue(p, dry_run=True)

        self.assertEqual(rc, 0)

    def test_enqueue_cancelled_returns_zero(self) -> None:
        future = (datetime.now(timezone.utc).date() + timedelta(days=3)).isoformat()
        payload = [self._candidate(cid="a1", review_status="approved", sale_end_date=future)]

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "candidates.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            with patch("builtins.input", return_value="NO"):
                rc = _mod.enqueue(p, dry_run=False)

        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()