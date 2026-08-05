import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_manual_review_checklist import build_checklist, load_json
from scripts.csv_to_manual_affiliate_items import convert_csv_to_data


def test_review_checklist_generated(tmp_path):
    data = convert_csv_to_data(ROOT / "manual_affiliate_builder" / "manual_items.csv.example")
    policy = load_json(ROOT / "manual_affiliate_builder" / "review_policy.json")

    text = build_checklist(data, policy)
    out = tmp_path / "checklist.md"
    out.write_text(text, encoding="utf-8")

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "WordPress write allowed: false" in content
    assert "Amazon API call allowed: false" in content
    assert "APPROVED_FOR_PREVIEW_ONLY" in content
