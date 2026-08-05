import json
from pathlib import Path

from generic_block_ai.app.block_runner import GenericBlockRunner
from generic_block_ai.app.review_artifacts_validator import validate_review_artifacts_from_result


def _runner_on_tmp_manifest(tmp_path: Path) -> GenericBlockRunner:
    source_manifest = Path("generic_block_ai/block_manifest.json")
    local_manifest = tmp_path / "block_manifest.json"
    local_manifest.write_text(source_manifest.read_text(encoding="utf-8"), encoding="utf-8")
    return GenericBlockRunner(local_manifest, Path("generic_block_ai/config/policy.json"))


def test_review_artifacts_validation_passes_for_human_review_result(tmp_path: Path) -> None:
    runner = _runner_on_tmp_manifest(tmp_path)
    result = runner.run(
        requested_actions=[
            {"type": "collect_data", "target": "source_a"},
            {"type": "propose_deployment_plan", "target": "ops"},
        ],
        source_task_id="IR1-T5-001",
        persist_human_review_artifacts=True,
    )

    assert result["decision"] == "human_review"
    assert result["review_artifacts_validation"]["overall_result"] == "PASS"
    assert Path(result["review_artifacts_summary"]["summary_json_path"]).exists()
    assert Path(result["review_artifacts_summary"]["summary_md_path"]).exists()


def test_review_artifacts_validation_fails_when_paths_missing() -> None:
    result = {
        "decision": "human_review",
        "review_artifacts": {
            "review_queue_path": "/tmp/not_found_queue.json",
            "evidence_path": "/tmp/not_found_evidence.json",
            "external_write_executed": False,
        },
    }

    report = validate_review_artifacts_from_result(result)
    assert report["overall_result"] == "FAIL"
    assert any("does not exist" in item for item in report["failed_checks"])


def test_review_artifacts_summary_json_contains_meta_and_overall_result(tmp_path: Path) -> None:
    runner = _runner_on_tmp_manifest(tmp_path)
    result = runner.run(
        requested_actions=[{"type": "delete_block", "target": "generic_block"}],
        source_task_id="IR1-T5-002",
        persist_human_review_artifacts=True,
    )

    summary_json_path = Path(result["review_artifacts_summary"]["summary_json_path"])
    payload = json.loads(summary_json_path.read_text(encoding="utf-8"))

    assert payload["_meta"]["purpose"] == "human_review_artifacts_summary"
    assert payload["_meta"]["mode"] == "dry_run"
    assert payload["overall_result"] == "PASS"