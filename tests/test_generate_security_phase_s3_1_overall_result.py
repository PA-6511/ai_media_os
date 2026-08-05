from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_security_phase_s3_1_overall_result import (  # noqa: E402
    generate_security_phase_s3_1_overall_result,
)
from scripts.replay_security_observability_events_phase_s3_1 import (  # noqa: E402
    replay_security_observability_events_phase_s3_1,
)


CONFIG_PATH = ROOT / "config" / "security_observability_event_replay_phase_s3_1.json"
BATCH_PATH = ROOT / "exchange" / "examples" / "security_observability_phase_s3_event_batch.example.json"


def test_overall_result_pass_dry_run_only(tmp_path: Path) -> None:
    replay_security_observability_events_phase_s3_1(
        config_path=CONFIG_PATH,
        batch_path=BATCH_PATH,
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    result = generate_security_phase_s3_1_overall_result(
        config_path=CONFIG_PATH,
        replay_result_path=tmp_path / "replay.json",
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "PASS_DRY_RUN_ONLY"
    assert result["event_replay_completed"] is True
    assert result["event_count"] == 5
    assert result["matched_expected_count"] == 5
    assert result["mismatched_expected_count"] == 0
    assert result["freeze_recommendation_detected"] is True
    assert result["human_review_recommendation_detected"] is True
    assert result["freeze_executed"] is False
    assert result["revoke_executed"] is False
    assert result["isolation_executed"] is False
    assert result["process_kill_executed"] is False
    assert result["scheduler_stop_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
    assert result["next_step"] == "prepare_cross_phase_security_audit_view"


def test_overall_mismatch_requires_review(tmp_path: Path) -> None:
    replay_security_observability_events_phase_s3_1(
        config_path=CONFIG_PATH,
        batch_path=BATCH_PATH,
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    payload = json.loads((tmp_path / "replay.json").read_text(encoding="utf-8"))
    payload["mismatched_expected_count"] = 1
    (tmp_path / "replay.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result = generate_security_phase_s3_1_overall_result(
        config_path=CONFIG_PATH,
        replay_result_path=tmp_path / "replay.json",
        output_json_path=tmp_path / "overall.json",
        output_md_path=tmp_path / "overall.md",
    )
    assert result["final_status"] == "OBSERVABILITY_REVIEW_REQUIRED"
