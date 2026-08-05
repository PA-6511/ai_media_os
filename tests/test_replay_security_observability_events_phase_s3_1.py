from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.replay_security_observability_events_phase_s3_1 import (  # noqa: E402
    replay_security_observability_events_phase_s3_1,
)


CONFIG_PATH = ROOT / "config" / "security_observability_event_replay_phase_s3_1.json"
BATCH_PATH = ROOT / "exchange" / "examples" / "security_observability_phase_s3_event_batch.example.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_event_batch_normal_replay(tmp_path: Path) -> None:
    result = replay_security_observability_events_phase_s3_1(
        config_path=CONFIG_PATH,
        batch_path=BATCH_PATH,
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    assert result["event_count"] == 5
    assert result["matched_expected_count"] == 5
    assert result["mismatched_expected_count"] == 0
    assert result["freeze_recommendation_detected"] is True
    assert result["human_review_recommendation_detected"] is True
    assert result["freeze_executed"] is False
    assert result["state_change_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["external_api_call_executed"] is False
    actuals = {item["event_id"]: item["actual_result"] for item in result["event_results"]}
    assert actuals["scheduler_retry_loop_sample"] == "WARN"
    assert actuals["wordpress_publish_intent_sample"] == "FAIL"
    assert actuals["unknown_external_api_intent_sample"] == "WARN"
    assert actuals["env_secret_echo_intent_sample"] == "FAIL"
    assert actuals["process_duplicate_runner_sample"] == "FAIL"


def test_replay_wordpress_write_executed_abort(tmp_path: Path) -> None:
    batch = load_json(BATCH_PATH)
    batch["events"] = [
        {
            "event_id": "wp_abort",
            "event_type": "wordpress_write_intent",
            "intent": "publish_intent",
            "wordpress_write_executed": True,
            "expected_result": "ABORT",
        }
    ]
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    result = replay_security_observability_events_phase_s3_1(
        config_path=CONFIG_PATH,
        batch_path=batch_path,
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    assert result["replay_result"] == "ABORT"


def test_replay_external_api_call_executed_abort(tmp_path: Path) -> None:
    batch = load_json(BATCH_PATH)
    batch["events"] = [
        {
            "event_id": "api_abort",
            "event_type": "external_api_intent",
            "intent": "unknown_api_call",
            "external_api_call_executed": True,
            "expected_result": "ABORT",
        }
    ]
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    result = replay_security_observability_events_phase_s3_1(
        config_path=CONFIG_PATH,
        batch_path=batch_path,
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    assert result["replay_result"] == "ABORT"


def test_replay_secret_output_allowed_abort(tmp_path: Path) -> None:
    batch = load_json(BATCH_PATH)
    batch["events"] = [
        {
            "event_id": "env_abort",
            "event_type": "env_access_intent",
            "intent": "secret_value_echo",
            "secret_value_output_allowed": True,
            "expected_result": "ABORT",
        }
    ]
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    result = replay_security_observability_events_phase_s3_1(
        config_path=CONFIG_PATH,
        batch_path=batch_path,
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    assert result["replay_result"] == "ABORT"


def test_replay_process_kill_executed_abort(tmp_path: Path) -> None:
    batch = load_json(BATCH_PATH)
    batch["events"] = [
        {
            "event_id": "process_abort",
            "event_type": "process_anomaly",
            "intent": "duplicated_runner",
            "process_kill_executed": True,
            "expected_result": "ABORT",
        }
    ]
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    result = replay_security_observability_events_phase_s3_1(
        config_path=CONFIG_PATH,
        batch_path=batch_path,
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    assert result["replay_result"] == "ABORT"


def test_replay_scheduler_abort_threshold_abort(tmp_path: Path) -> None:
    batch = load_json(BATCH_PATH)
    batch["events"] = [
        {
            "event_id": "scheduler_abort",
            "event_type": "scheduler_anomaly",
            "retry_count": 10,
            "queue_depth": 0,
            "cron_runs_per_hour": 0,
            "duplicate_runs": 0,
            "expected_result": "ABORT",
        }
    ]
    batch_path = tmp_path / "batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    result = replay_security_observability_events_phase_s3_1(
        config_path=CONFIG_PATH,
        batch_path=batch_path,
        output_json_path=tmp_path / "replay.json",
        output_md_path=tmp_path / "replay.md",
    )
    assert result["replay_result"] == "ABORT"
