import json
from pathlib import Path

from generic_block_ai.app.core_release_candidate_submission_dryrun import (
    run_ir29_release_candidate_submission_dryrun,
    write_ir29_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir28(base: Path) -> Path:
    reports = base / "reports"

    trace_dir = reports / "ir28_release_candidate_trace_bundle_ir28_live_trial"
    _write(
        trace_dir / "trace_manifest.json",
        json.dumps(
            {
                "schema_version": "ir28_release_candidate_trace_bundle_v1",
                "phase": "IR28",
                "release_candidate_id": "rc_fixture",
                "counts": {"included": 22, "missing_required": 0},
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
    )
    _write(trace_dir / "trace_sha256_manifest.json", '{"a":"b"}\n')
    _write(trace_dir / "README.md", "# ir28\n")

    ir28 = {
        "schema_version": "ir28_release_candidate_trace_bundle_v1",
        "phase": "IR28",
        "validation_result": "PASS",
        "release_candidate_id": "rc_fixture",
        "artifacts": {
            "trace_bundle_dir": "generic_block_ai/reports/ir28_release_candidate_trace_bundle_ir28_live_trial",
            "trace_manifest": "generic_block_ai/reports/ir28_release_candidate_trace_bundle_ir28_live_trial/trace_manifest.json",
            "trace_sha256_manifest": "generic_block_ai/reports/ir28_release_candidate_trace_bundle_ir28_live_trial/trace_sha256_manifest.json",
            "readme": "generic_block_ai/reports/ir28_release_candidate_trace_bundle_ir28_live_trial/README.md",
        },
    }
    ir28_path = reports / "ir28_release_candidate_trace_bundle_report_ir28_live_trial.json"
    _write(ir28_path, json.dumps(ir28, ensure_ascii=False, indent=2) + "\n")
    return ir28_path


def test_ir29_build_submission_package_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir28_path = _prepare_ir28(base)

    out = run_ir29_release_candidate_submission_dryrun(
        base_path=base,
        source_task_id="ir29_pass",
        ir28_trace_report_path=ir28_path,
    )

    report = out["submission_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["send_allowed"] is False
    assert report["summary"]["send_executed"] is False


def test_ir29_fail_when_ir28_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir29_release_candidate_submission_dryrun(
        base_path=base,
        source_task_id="ir29_missing",
        ir28_trace_report_path=tmp_path / "not_found.json",
    )

    report = out["submission_report"]
    assert report["validation_result"] == "FAIL"


def test_ir29_fail_when_ir28_not_pass(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir28_path = _prepare_ir28(base)

    ir28 = json.loads(ir28_path.read_text(encoding="utf-8"))
    ir28["validation_result"] = "FAIL"
    ir28_path.write_text(json.dumps(ir28, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir29_release_candidate_submission_dryrun(
        base_path=base,
        source_task_id="ir29_ir28_fail",
        ir28_trace_report_path=ir28_path,
    )

    report = out["submission_report"]
    assert report["validation_result"] == "FAIL"


def test_ir29_fail_when_trace_manifest_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir28_path = _prepare_ir28(base)

    manifest_path = base / "reports" / "ir28_release_candidate_trace_bundle_ir28_live_trial" / "trace_manifest.json"
    manifest_path.unlink()

    out = run_ir29_release_candidate_submission_dryrun(
        base_path=base,
        source_task_id="ir29_manifest_missing",
        ir28_trace_report_path=ir28_path,
    )

    report = out["submission_report"]
    assert report["validation_result"] == "FAIL"


def test_ir29_fail_when_release_candidate_id_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir28_path = _prepare_ir28(base)

    manifest_path = base / "reports" / "ir28_release_candidate_trace_bundle_ir28_live_trial" / "trace_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["release_candidate_id"] = "rc_other"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir29_release_candidate_submission_dryrun(
        base_path=base,
        source_task_id="ir29_rc_mismatch",
        ir28_trace_report_path=ir28_path,
    )

    report = out["submission_report"]
    assert report["validation_result"] == "FAIL"


def test_write_ir29_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir28_path = _prepare_ir28(base)

    ir29 = run_ir29_release_candidate_submission_dryrun(
        base_path=base,
        source_task_id="ir29_complete",
        ir28_trace_report_path=ir28_path,
    )

    completion = write_ir29_completion_report(
        base_path=base,
        ir29_output=ir29,
        focused_tests={"passed": 6, "failed": 0},
        full_regression={"passed": 229, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 29"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
