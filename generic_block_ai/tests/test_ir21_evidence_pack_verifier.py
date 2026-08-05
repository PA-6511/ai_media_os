import json
from pathlib import Path

from generic_block_ai.app.core_cross_phase_evidence_bundler import (
    run_ir20_cross_phase_evidence_bundler_dryrun,
    write_ir20_completion_report,
)
from generic_block_ai.app.core_evidence_pack_verifier import (
    run_ir21_evidence_pack_verifier_dryrun,
    write_ir21_completion_report,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_ir20_pack(tmp_path: Path) -> tuple[Path, Path, dict]:
    root = tmp_path
    base = root / "generic_block_ai"

    required = [
        "generic_block_ai/reports/implementation_restart_phase12_completion_report.json",
        "generic_block_ai/reports/implementation_restart_phase13_completion_report.json",
    ]
    _write(root / required[0], '{"phase":"12"}\n')
    _write(root / required[1], '{"phase":"13"}\n')

    ir20 = run_ir20_cross_phase_evidence_bundler_dryrun(
        base_path=base,
        source_task_id="ir20_pack_for_ir21",
        required_artifacts=required,
        optional_globs=[],
    )
    write_ir20_completion_report(
        base_path=base,
        ir20_output=ir20,
        focused_tests={"passed": 1, "failed": 0},
        full_regression={"passed": 1, "failed": 0},
    )

    bundle_path = Path(ir20["path"])
    completion_path = base / "reports" / "implementation_restart_phase20_completion_report.json"
    return base, completion_path, ir20


def test_ir21_verifier_pass(tmp_path: Path) -> None:
    base, completion_path, ir20 = _prepare_ir20_pack(tmp_path)
    out = run_ir21_evidence_pack_verifier_dryrun(
        base_path=base,
        source_task_id="ir21_pass",
        bundle_report_path=Path(ir20["path"]),
        completion_report_path=completion_path,
    )
    report = out["verifier_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["tampered_files"] == 0


def test_ir21_detects_missing_file(tmp_path: Path) -> None:
    base, completion_path, ir20 = _prepare_ir20_pack(tmp_path)

    manifest = json.loads(Path(ir20["manifest_path"]).read_text(encoding="utf-8"))
    target_rel = manifest["included_artifacts"][0]
    target_abs = base.parent / target_rel
    target_abs.unlink()

    out = run_ir21_evidence_pack_verifier_dryrun(
        base_path=base,
        source_task_id="ir21_missing",
        bundle_report_path=Path(ir20["path"]),
        completion_report_path=completion_path,
    )
    report = out["verifier_report"]
    assert report["validation_result"] == "FAIL"
    assert any("missing" in item.lower() for item in report["validation_failed_checks"])


def test_ir21_detects_tampered_file(tmp_path: Path) -> None:
    base, completion_path, ir20 = _prepare_ir20_pack(tmp_path)

    manifest = json.loads(Path(ir20["manifest_path"]).read_text(encoding="utf-8"))
    target_rel = manifest["included_artifacts"][0]
    target_abs = base.parent / target_rel
    target_abs.write_text('{"phase":"tampered"}\n', encoding="utf-8")

    out = run_ir21_evidence_pack_verifier_dryrun(
        base_path=base,
        source_task_id="ir21_tampered",
        bundle_report_path=Path(ir20["path"]),
        completion_report_path=completion_path,
    )
    report = out["verifier_report"]
    assert report["validation_result"] == "FAIL"
    assert any("sha256 mismatch" in item.lower() for item in report["validation_failed_checks"])


def test_ir21_detects_completion_mismatch(tmp_path: Path) -> None:
    base, completion_path, ir20 = _prepare_ir20_pack(tmp_path)

    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["artifacts"]["manifest"] = "wrong/path.json"
    completion_path.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = run_ir21_evidence_pack_verifier_dryrun(
        base_path=base,
        source_task_id="ir21_completion_mismatch",
        bundle_report_path=Path(ir20["path"]),
        completion_report_path=completion_path,
    )
    report = out["verifier_report"]
    assert report["validation_result"] == "FAIL"
    assert any("completion report manifest path mismatch" in item for item in report["validation_failed_checks"])


def test_write_ir21_completion_report(tmp_path: Path) -> None:
    base, completion_path, ir20 = _prepare_ir20_pack(tmp_path)

    ir21 = run_ir21_evidence_pack_verifier_dryrun(
        base_path=base,
        source_task_id="ir21_complete",
        bundle_report_path=Path(ir20["path"]),
        completion_report_path=completion_path,
    )
    out = write_ir21_completion_report(
        base_path=base,
        ir21_output=ir21,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 185, "failed": 0},
    )

    loaded = json.loads(Path(out["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 21"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
