import hashlib
import json
from pathlib import Path

from generic_block_ai.app.core_cross_phase_evidence_bundler import (
    run_ir20_cross_phase_evidence_bundler_dryrun,
    write_ir20_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_ir20_bundle_pass_with_required_files(tmp_path: Path) -> None:
    root = tmp_path
    base = root / "generic_block_ai"

    required = [
        "generic_block_ai/reports/implementation_restart_phase12_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase19_completion_report.json",
    ]

    c1 = '{"phase":"12"}\n'
    c2 = '{"phase":"19"}\n'
    _write(root / required[0], c1)
    _write(root / required[1], c2)

    out = run_ir20_cross_phase_evidence_bundler_dryrun(
        base_path=base,
        source_task_id="ir20_test_pass",
        required_artifacts=required,
        optional_globs=[],
    )

    report = out["bundle_report"]
    assert report["validation_result"] == "PASS"
    assert report["missing_required_artifact_count"] == 0

    sha_map = json.loads(Path(out["sha256_manifest_path"]).read_text(encoding="utf-8"))
    assert sha_map[required[0]] == _sha256_text(c1)
    assert sha_map[required[1]] == _sha256_text(c2)


def test_ir20_bundle_fails_on_missing_required(tmp_path: Path) -> None:
    root = tmp_path
    base = root / "generic_block_ai"

    required = [
        "generic_block_ai/reports/implementation_restart_phase12_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase19_completion_report.json",
    ]

    _write(root / required[0], '{"phase":"12"}\n')

    out = run_ir20_cross_phase_evidence_bundler_dryrun(
        base_path=base,
        source_task_id="ir20_test_missing",
        required_artifacts=required,
        optional_globs=[],
    )

    report = out["bundle_report"]
    assert report["validation_result"] == "FAIL"
    manifest = json.loads(Path(out["manifest_path"]).read_text(encoding="utf-8"))
    assert required[1] in manifest["missing_required_artifacts"]


def test_ir20_collects_optional_globs(tmp_path: Path) -> None:
    root = tmp_path
    base = root / "generic_block_ai"

    required = ["generic_block_ai/reports/implementation_restart_phase12_completion_report.json"]
    _write(root / required[0], '{"phase":"12"}\n')
    _write(root / "generic_block_ai/reports/ir15_manual_event_role_guard_x.json", '{"p":"15"}\n')

    out = run_ir20_cross_phase_evidence_bundler_dryrun(
        base_path=base,
        source_task_id="ir20_test_optional",
        required_artifacts=required,
        optional_globs=["ir15_manual_event_role_guard_*.json"],
    )
    manifest = json.loads(Path(out["manifest_path"]).read_text(encoding="utf-8"))
    assert "generic_block_ai/reports/ir15_manual_event_role_guard_x.json" in manifest["included_artifacts"]


def test_write_ir20_completion_report(tmp_path: Path) -> None:
    root = tmp_path
    base = root / "generic_block_ai"

    required = ["generic_block_ai/reports/implementation_restart_phase12_completion_report.json"]
    _write(root / required[0], '{"phase":"12"}\n')

    ir20 = run_ir20_cross_phase_evidence_bundler_dryrun(
        base_path=base,
        source_task_id="ir20_complete",
        required_artifacts=required,
        optional_globs=[],
    )
    completion = write_ir20_completion_report(
        base_path=base,
        ir20_output=ir20,
        focused_tests={"passed": 4, "failed": 0},
        full_regression={"passed": 180, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 20"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
