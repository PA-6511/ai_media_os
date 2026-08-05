import json
from pathlib import Path

from generic_block_ai.app.core_ir61_65_long_term_retention_batch import (
    run_ir61_65_batch_dryrun,
    run_ir64_handoff_package_release_gate,
    write_ir61_65_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir60_payload() -> dict:
    return {
        "schema_version": "ir60_phase_56_60_completion_bundle_v1",
        "phase": "IR60",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir60_fixture",
        "final_decision": "READY_FOR_DRY_RUN_HANDOFF_ONLY",
        "completion_table": [
            {"phase": "IR56", "content": "Post-Bundle Audit Trail Recorder", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR57", "content": "Dry-Run Finalization Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR58", "content": "Pre-Release Archive Builder", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR59", "content": "Archive Integrity Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR60", "content": "Phase 56-60 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
        ],
        "live_summary": {"ir56": "PASS", "ir57": "PASS", "ir58": "PASS", "ir59": "PASS", "ir60": "PASS"},
        "safety_gate_summary": {
            "dry_run": "maintained",
            "OBSERVE": "maintained",
            "submission_execution_blocked": True,
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
            "GitHub_push": "未実行",
        },
        "artifacts": {
            "ir60_completion_bundle": "generic_block_ai/reports/ir56_60/ir60_completion_bundle.json",
        },
    }


def _prepare_ir60(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir56_60" / "ir60_completion_bundle.json"
    _write(target, payload or _base_ir60_payload())
    return target


def test_ir61_pass_for_valid_ir60_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir60_path = _prepare_ir60(base)

    out = run_ir61_65_batch_dryrun(
        base_path=base,
        source_task_id="ir61_65_pass",
        ir60_completion_bundle_path=ir60_path,
    )

    ir61 = out["ir61_result"]
    assert ir61["validation_result"] == "PASS"
    assert "confirmation_id" in ir61["confirmation_entry"]
    assert ir61["confirmation_entry"]["long_term_retention_blocked_until_live"] is True


def test_ir62_pass_when_all_phases_complete(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir60_path = _prepare_ir60(base)

    out = run_ir61_65_batch_dryrun(
        base_path=base,
        source_task_id="ir62_pass",
        ir60_completion_bundle_path=ir60_path,
    )

    ir62 = out["ir62_result"]
    assert ir62["validation_result"] == "PASS"
    assert ir62["re_verification_result"] == "CYCLE_VERIFIED"
    assert ir62["hash_re_verification"]["hash_match"] is True


def test_ir63_assembles_handoff_package_in_dry_run(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir60_path = _prepare_ir60(base)

    out = run_ir61_65_batch_dryrun(
        base_path=base,
        source_task_id="ir63_assemble",
        ir60_completion_bundle_path=ir60_path,
    )

    ir63 = out["ir63_result"]
    assert ir63["validation_result"] == "PASS"
    assert ir63["handoff_package"]["assembly_execution_blocked"] is True
    assert ir63["handoff_package"]["external_distribution_blocked"] is True
    assert ir63["handoff_package"]["retention_scope"] == "dry_run_only"


def test_ir64_detects_handoff_package_hash_tamper(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir60_path = _prepare_ir60(base)

    out = run_ir61_65_batch_dryrun(
        base_path=base,
        source_task_id="ir64_tamper",
        ir60_completion_bundle_path=ir60_path,
    )

    tampered_ir63 = dict(out["ir63_result"])
    tampered_ir63["handoff_package_hash"] = "0" * 64

    ir64 = run_ir64_handoff_package_release_gate(
        ir63_handoff_package=tampered_ir63,
        ir62_re_verification=out["ir62_result"],
        source_task_id="ir64_tamper",
    )
    assert ir64["validation_result"] == "FAIL"
    assert ir64["tamper_detection_summary"] == "TAMPER_DETECTED"
    assert ir64["handoff_release_gate_decision"] == "REJECT"


def test_ir64_abort_when_external_flags_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir60_path = _prepare_ir60(base)

    out = run_ir61_65_batch_dryrun(
        base_path=base,
        source_task_id="ir64_abort",
        ir60_completion_bundle_path=ir60_path,
    )

    ir63_with_risk = dict(out["ir63_result"])
    ir63_with_risk["safety_gate_snapshot"] = dict(ir63_with_risk["safety_gate_snapshot"])
    ir63_with_risk["safety_gate_snapshot"]["execution_policy_execute"] = True

    ir64 = run_ir64_handoff_package_release_gate(
        ir63_handoff_package=ir63_with_risk,
        ir62_re_verification=out["ir62_result"],
        source_task_id="ir64_abort",
    )
    assert ir64["handoff_release_gate_decision"] == "ABORT"


def test_ir65_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir60_path = _prepare_ir60(base)

    out = run_ir61_65_batch_dryrun(
        base_path=base,
        source_task_id="ir65_complete",
        ir60_completion_bundle_path=ir60_path,
    )

    result = write_ir61_65_completion_bundle(
        base_path=base,
        ir61_65_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 12, "failed": 0},
        scoped_regression={"passed": 374, "failed": 0},
    )

    report = result["completion_report"]
    assert report["schema_version"] == "ir65_phase_61_65_completion_bundle_v1"
    assert report["final_decision"] == "READY_FOR_DRY_RUN_HANDOFF_ONLY"
    assert report["safety_gate_summary"]["dry_run"] == "maintained"
    assert report["safety_gate_summary"]["execution_policy_execute"] is False
    assert all(row["judgement"] == "完了" for row in report["completion_table"])
    bundle_file = base / "reports" / "ir61_65" / "ir65_completion_bundle.json"
    assert bundle_file.exists()
