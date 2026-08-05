import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.csv_to_manual_affiliate_items import convert_csv_to_data
from scripts.snapshot_manual_affiliate_items import build_snapshot


def test_snapshot_generated_fields():
    data = convert_csv_to_data(ROOT / "manual_affiliate_builder" / "manual_items.csv.example")
    snap = build_snapshot(data)

    assert snap["execution_mode"] == "DRY_RUN_ONLY"
    assert snap["production_status"] == "NO_GO"
    assert snap["publish_allowed"] is False
    assert snap["approval_token_consumed"] is False
    assert isinstance(snap["checksum"], str)
    assert len(snap["checksum"]) == 64


def test_snapshot_phase8_51_lock_maintained():
    data = convert_csv_to_data(ROOT / "manual_affiliate_builder" / "manual_items.csv.example")
    snap = build_snapshot(data)

    lock = snap["next_phase_lock_state"]
    assert lock["phase"] == "Phase 8-51-MIGRATION-SKELETON"
    assert lock["execution_state"] == "UNEXECUTED"
    assert lock["lock"] == "NOT_STARTED_LOCKED"
    assert lock["execution_allowed"] is False
