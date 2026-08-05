from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = ROOT / "config/x_post_wording_feedback_schema.json"
EXAMPLE_INPUT_PATH = (
    ROOT / "exchange/examples/x_post_wording_feedback_record.example.json"
)
NORMALIZED_PATH = (
    ROOT / "exchange/examples/x_post_wording_feedback_normalized.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/x_fb_0_result.json"
REPORT_PATH = ROOT / "reports/x_fb_0_minimum_feedback_record_report.md"
SCRIPT_PATH = ROOT / "scripts/build_x_fb_0.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_builder(
    input_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--input",
            str(input_path),
            "--check-only",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def write_case(
    path: Path,
    record: dict,
) -> None:
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_schema_identity() -> None:
    schema = load_json(SCHEMA_PATH)

    assert schema["phase_id"] == "X-FB-0"
    assert schema["schema_id"] == "X_POST_WORDING_FEEDBACK_SCHEMA_V1"


def test_schema_has_required_label_groups() -> None:
    schema = load_json(SCHEMA_PATH)
    groups = schema["wording_label_groups"]

    assert "TITLE_FIRST" in groups["structure"]
    assert "INFORMATIONAL_TONE" in groups["tone"]
    assert "NO_EMOJI" in groups["decoration"]
    assert "UNNATURAL_JAPANESE" in schema["edit_reason_labels"]


def test_schema_blocks_live_operations_and_rule_updates() -> None:
    schema = load_json(SCHEMA_PATH)
    boundary = schema["execution_boundary"]

    assert boundary["x_api_call_allowed"] is False
    assert boundary["x_post_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["external_api_call_allowed"] is False
    assert boundary["automatic_rule_update_allowed"] is False
    assert boundary["algorithm_research_handoff_allowed"] is False
    assert boundary["production_status"] == "NO_GO"
    assert boundary["safety_state"] == "DRY_RUN_ONLY"


def test_three_text_snapshots_are_preserved() -> None:
    source = load_json(EXAMPLE_INPUT_PATH)
    normalized = load_json(NORMALIZED_PATH)
    snapshots = normalized["text_snapshots"]

    assert snapshots["generated_text"] == source["generated_text"]
    assert (
        snapshots["human_edited_text"]
        == source["human_edited_text"]
    )
    assert (
        snapshots["actually_posted_text"]
        == source["actually_posted_text"]
    )


def test_normalized_record_has_digest_and_derived_flags() -> None:
    normalized = load_json(NORMALIZED_PATH)

    assert len(normalized["record_digest_sha256"]) == 64
    assert (
        normalized["derived_flags"]["human_edit_detected"]
        is True
    )
    assert (
        normalized["derived_flags"]["posting_adjustment_detected"]
        is False
    )
    assert (
        normalized["derived_flags"][
            "ready_for_future_learning_dataset"
        ]
        is True
    )


def test_builder_check_only_passes_without_live_execution() -> None:
    completed = run_builder(EXAMPLE_INPUT_PATH)

    assert completed.returncode == 0

    result = json.loads(completed.stdout)

    assert result["status"] == "PASS_DESIGN_ONLY_NO_EXECUTION"
    assert result["source_text_snapshots_preserved"] is True
    assert result["x_api_call_allowed"] is False
    assert result["x_post_allowed"] is False
    assert result["automatic_rule_update_allowed"] is False
    assert result["ready_for_manual_feedback_recording"] is True
    assert result["ready_for_x_fb_1"] is True


def test_edited_record_without_reason_is_rejected(
    tmp_path: Path,
) -> None:
    record = load_json(EXAMPLE_INPUT_PATH)
    record["edit_reason_labels"] = []

    path = tmp_path / "missing-edit-reason.json"
    write_case(path, record)

    completed = run_builder(path)

    assert completed.returncode == 1
    assert (
        "edited record requires at least one edit_reason_label"
        in completed.stderr
    )


def test_false_was_edited_with_different_text_is_rejected(
    tmp_path: Path,
) -> None:
    record = load_json(EXAMPLE_INPUT_PATH)
    record["was_edited"] = False
    record["edit_reason_labels"] = []

    path = tmp_path / "false-edit-flag.json"
    write_case(path, record)

    completed = run_builder(path)

    assert completed.returncode == 1
    assert (
        "was_edited does not match generated/reviewed text difference"
        in completed.stderr
    )


def test_posting_difference_requires_adjustment_label(
    tmp_path: Path,
) -> None:
    record = load_json(EXAMPLE_INPUT_PATH)
    record["actually_posted_text"] += " 詳細はこちら。"
    record["posting_adjustment_labels"] = []

    path = tmp_path / "missing-post-adjustment.json"
    write_case(path, record)

    completed = run_builder(path)

    assert completed.returncode == 1
    assert (
        "posted text difference requires "
        "posting_adjustment_labels"
        in completed.stderr
    )


def test_negative_metric_is_rejected(
    tmp_path: Path,
) -> None:
    record = load_json(EXAMPLE_INPUT_PATH)
    record["metrics"]["likes"] = -1

    path = tmp_path / "negative-metric.json"
    write_case(path, record)

    completed = run_builder(path)

    assert completed.returncode == 1
    assert "metrics.likes must not be negative" in completed.stderr


def test_unedited_reviewed_record_is_accepted(
    tmp_path: Path,
) -> None:
    record = load_json(EXAMPLE_INPUT_PATH)

    record["record_stage"] = "HUMAN_REVIEWED"
    record["human_edited_text"] = record["generated_text"]
    record["actually_posted_text"] = None
    record["was_edited"] = False
    record["edit_reason_labels"] = []
    record["posting_adjustment_labels"] = []
    record["posted_at"] = None
    record["review_status"] = "HUMAN_REVIEWED"

    path = tmp_path / "unedited-reviewed.json"
    write_case(path, record)

    completed = run_builder(path)

    assert completed.returncode == 0

    result = json.loads(completed.stdout)

    assert result["human_edit_detected"] is False
    assert result["actually_posted_text_preserved"] is False


def test_generated_evidence_is_safe_and_complete() -> None:
    assert RESULT_PATH.exists()
    assert REPORT_PATH.exists()

    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert result["status"] == "PASS_DESIGN_ONLY_NO_EXECUTION"
    assert result["production_status"] == "NO_GO"
    assert result["safety_state"] == "DRY_RUN_ONLY"
    assert result["next_phase_execution_allowed"] is False
    assert "X API call allowed: `false`" in report
    assert "Automatic wording-rule update allowed: `false`" in report
