import json
from pathlib import Path

from generic_block_ai.app.core_ir56_60_release_archive_batch import (
    run_ir56_60_batch_dryrun,
    run_ir59_archive_integrity_gate,
    write_ir56_60_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _base_ir55_payload() -> dict:
    return {
        "schema_version": "ir55_phase_51_55_completion_bundle_v1",
        "phase": "IR55",
        "generated_at": "2026-05-24T04:00:00+00:00",
        "source_task_id": "ir55_fixture",
        "final_decision": "READY_FOR_DRY_RUN_HANDOFF_ONLY",
        "completion_table": [
            {"phase": "IR51", "content": "Handoff Integrity Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR52", "content": "Release Packet Builder", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR53", "content": "Release Packet Verifier", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR54", "content": "Final No-External-Submit Gate", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
            {"phase": "IR55", "content": "Phase 51-55 Completion Bundle", "focused": "PASS", "adjacent": "PASS", "scoped": "PASS", "live": "PASS", "judgement": "完了"},
        ],
        "live_summary": {"ir51": "PASS", "ir52": "PASS", "ir53": "PASS", "ir54": "PASS", "ir55": "PASS"},
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
            "ir55_completion_bundle": "generic_block_ai/reports/ir51_55/ir55_completion_bundle.json",
        },
    }


def _prepare_ir55(base: Path, payload: dict | None = None) -> Path:
    target = base / "reports" / "ir51_55" / "ir55_completion_bundle.json"
    _write(target, payload or _base_ir55_payload())
    return target


def test_ir56_pass_for_valid_ir55_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir55_path = _prepare_ir55(base)

    out = run_ir56_60_batch_dryrun(
        base_path=base,
        source_task_id="ir56_60_pass",
        ir55_completion_bundle_path=ir55_path,
    )

    ir56 = out["ir56_result"]
    assert ir56["validation_result"] == "PASS"
    assert "audit_trail_id" in ir56["audit_trail_entry"]


def test_ir57_pass_when_all_phases_complete(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir55_path = _prepare_ir55(base)

    out = run_ir56_60_batch_dryrun(
        base_path=base,
        source_task_id="ir57_pass",
        ir55_completion_bundle_path=ir55_path,
    )

    ir57 = out["ir57_result"]
    assert ir57["validation_result"] == "PASS"
    assert ir57["finalization_decision"] == "FINALIZED_DRY_RUN_COMPLETE"


def test_ir58_builds_archive_manifest_in_dry_run(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir55_path = _prepare_ir55(base)

    out = run_ir56_60_batch_dryrun(
        base_path=base,
        source_task_id="ir58_archive",
        ir55_completion_bundle_path=ir55_path,
    )

    ir58 = out["ir58_result"]
    assert ir58["validation_result"] == "PASS"
    assert ir58["archive_manifest"]["archive_execution_blocked"] is True
    assert ir58["archive_manifest"]["network_write_blocked"] is True


def test_ir59_detects_archive_hash_tamper(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir55_path = _prepare_ir55(base)

    out = run_ir56_60_batch_dryrun(
        base_path=base,
        source_task_id="ir59_tamper",
        ir55_completion_bundle_path=ir55_path,
    )

    tampered_ir58 = dict(out["ir58_result"])
    tampered_ir58["archive_hash"] = "0" * 64

    ir59 = run_ir59_archive_integrity_gate(
        ir58_release_archive=tampered_ir58,
        ir57_dry_run_finalization=out["ir57_result"],
        source_task_id="ir59_tamper",
    )
    assert ir59["validation_result"] == "FAIL"
    assert ir59["tamper_detection_summary"] == "TAMPER_DETECTED"
    assert ir59["archive_integrity_gate_decision"] == "REJECT"


def test_ir59_abort_when_external_flags_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir55_path = _prepare_ir55(base)

    out = run_ir56_60_batch_dryrun(
        base_path=base,
        source_task_id="ir59_abort",
        ir55_completion_bundle_path=ir55_path,
    )

    ir58_with_risk = dict(out["ir58_result"])
    ir58_with_risk["safety_gate_snapshot"] = dict(ir58_with_risk["safety_gate_snapshot"])
    ir58_with_risk["safety_gate_snapshot"]["execution_policy_execute"] = True

    ir59 = run_ir59_archive_integrity_gate(
        ir58_release_archive=ir58_with_risk,
        ir57_dry_run_finalization=out["ir57_result"],
        source_task_id="ir59_abort",
    )
    assert ir59["archive_integrity_gate_decision"] == "ABORT"


def test_ir60_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir55_path = _prepare_ir55(base)

    out = run_ir56_60_batch_dryrun(
        base_path=base,
        source_task_id="ir60_complete",
        ir55_completion_bundle_path=ir55_path,
    )

    completion = write_ir56_60_completion_bundle(
        base_path=base,
        ir56_60_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 368, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "IR60"
    assert loaded["final_decision"] == "READY_FOR_DRY_RUN_HANDOFF_ONLY"
    assert (base / "reports" / "ir56_60" / "ir56_60_live_status.md").exists()
    assert (base / "reports" / "ir56_60" / "ir56_60_completion_table.md").exists()
