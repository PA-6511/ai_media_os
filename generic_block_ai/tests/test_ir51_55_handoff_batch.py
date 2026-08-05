import json
from pathlib import Path

from generic_block_ai.app.core_ir51_55_handoff_batch import (
    run_ir51_55_batch_dryrun,
    run_ir53_release_packet_verifier,
    run_ir54_final_no_external_submit_gate,
    write_ir51_55_completion_bundle,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_reference_files(base: Path) -> list[str]:
    refs = [
        "generic_block_ai/reports/ir48_destination_submission_handoff_manifest_ir50_live_trial/compliance_archive_human_review_result.json",
        "generic_block_ai/reports/ir48_destination_submission_handoff_manifest_ir50_live_trial/internal_review_board_human_review_result.json",
        "generic_block_ai/reports/ir48_destination_submission_handoff_manifest_ir50_live_trial/regulatory_audit_human_review_result.json",
    ]
    for ref in refs:
        abs_path = base.parent / ref
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text("{}\n", encoding="utf-8")
    return refs


def _base_ir50_payload(base: Path) -> dict:
    refs = _prepare_reference_files(base)
    return {
        "schema_version": "ir50_destination_submission_handoff_manifest_v1",
        "phase": "IR50",
        "generated_at": "2026-05-24T03:43:18.808942+00:00",
        "source_task_id": "ir50_fixture",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "overall_submission_gate_decision": "READY_FOR_REVIEW",
        "overall_review_queue_approval_decision": "READY_FOR_HUMAN_REVIEW",
        "overall_human_review_result": "APPROVE",
        "overall_submission_readiness_decision": "READY_DRY_RUN_ONLY",
        "overall_submission_handoff_decision": "READY_DRY_RUN_HANDOFF",
        "validation_result": "PASS",
        "validation_failed_checks": [],
        "validation_warnings": [],
        "summary": {
            "destination_count": 3,
            "include_in_dry_run_handoff_count": 3,
            "hold_count": 0,
            "reject_count": 0,
            "abort_count": 0,
            "handoff_target_count": 3,
        },
        "handoff_manifest": {
            "target_destinations": [
                "compliance_archive",
                "internal_review_board",
                "regulatory_audit",
            ],
            "reference_record_paths": refs,
            "submission_execution_blocked": True,
            "network_transmission_blocked": True,
            "production_release_blocked": True,
        },
        "destination_submission_handoff_manifest": [
            {
                "destination": "compliance_archive",
                "handoff_manifest_decision": "INCLUDE_IN_DRY_RUN_HANDOFF",
            },
            {
                "destination": "internal_review_board",
                "handoff_manifest_decision": "INCLUDE_IN_DRY_RUN_HANDOFF",
            },
            {
                "destination": "regulatory_audit",
                "handoff_manifest_decision": "INCLUDE_IN_DRY_RUN_HANDOFF",
            },
        ],
        "artifacts": {
            "destination_submission_handoff_manifest": "generic_block_ai/reports/ir50_destination_submission_handoff_manifest_fixture/destination_submission_handoff_manifest.json",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "submission_execution_blocked": True,
            "execution_policy_execute": False,
            "external_write_executed": False,
            "network_transmission_executed": False,
            "production_release": False,
        },
    }


def _prepare_ir50(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir50_destination_submission_handoff_manifest_report_fixture.json"
    _write(target, payload or _base_ir50_payload(base))
    return target


def test_ir51_pass_for_valid_ir50_manifest(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir50_path = _prepare_ir50(base)

    out = run_ir51_55_batch_dryrun(
        base_path=base,
        source_task_id="ir51_55_pass",
        ir50_handoff_report_path=ir50_path,
    )

    ir51 = out["ir51_result"]
    assert ir51["validation_result"] == "PASS"
    assert ir51["ir51_integrity_decision"] == "PASS"


def test_ir51_fail_when_target_destinations_duplicated(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir50_payload(base)
    payload["handoff_manifest"]["target_destinations"] = [
        "compliance_archive",
        "internal_review_board",
        "internal_review_board",
    ]
    ir50_path = _prepare_ir50(base, payload)

    out = run_ir51_55_batch_dryrun(
        base_path=base,
        source_task_id="ir51_55_dup",
        ir50_handoff_report_path=ir50_path,
    )

    ir51 = out["ir51_result"]
    assert ir51["validation_result"] == "FAIL"
    assert any("duplicates" in msg for msg in ir51["validation_failed_checks"])


def test_ir52_builds_release_packet_in_dry_run(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir50_path = _prepare_ir50(base)

    out = run_ir51_55_batch_dryrun(
        base_path=base,
        source_task_id="ir51_55_packet",
        ir50_handoff_report_path=ir50_path,
    )

    ir52 = out["ir52_result"]
    assert ir52["validation_result"] == "PASS"
    assert ir52["release_packet_id"].startswith("rp_ir51_55_packet")
    assert ir52["safety_gate_snapshot"]["execution_policy_execute"] is False


def test_ir53_detects_release_packet_hash_tamper(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir50_path = _prepare_ir50(base)

    out = run_ir51_55_batch_dryrun(
        base_path=base,
        source_task_id="ir51_55_tamper",
        ir50_handoff_report_path=ir50_path,
    )

    tampered = dict(out["ir52_result"])
    tampered["packet_hash"] = "0" * 64

    # Re-run verifier path via normal batch by replacing generated file payload.
    ir52_path = base / "reports" / "ir51_55" / "ir52_release_packet.json"
    _write(ir52_path, tampered)

    ir53 = run_ir53_release_packet_verifier(
        ir52_release_packet=tampered,
        ir51_handoff_integrity_report=out["ir51_result"],
        source_task_id="ir51_55_tamper",
    )
    assert ir53["validation_result"] == "FAIL"
    assert ir53["tamper_detection_summary"] == "TAMPER_DETECTED"


def test_ir54_abort_when_external_flags_true(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir50_path = _prepare_ir50(base)

    out = run_ir51_55_batch_dryrun(
        base_path=base,
        source_task_id="ir51_55_abort",
        ir50_handoff_report_path=ir50_path,
    )

    ir52 = dict(out["ir52_result"])
    ir52["safety_gate_snapshot"] = dict(ir52["safety_gate_snapshot"])
    ir52["safety_gate_snapshot"]["external_write_executed"] = True

    ir54 = run_ir54_final_no_external_submit_gate(
        ir53_release_packet_verification=out["ir53_result"],
        ir52_release_packet=ir52,
        source_task_id="ir51_55_abort",
    )
    assert ir54["final_no_external_submit_gate_decision"] == "ABORT"


def test_ir55_builds_completion_bundle(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir50_path = _prepare_ir50(base)

    out = run_ir51_55_batch_dryrun(
        base_path=base,
        source_task_id="ir51_55_complete",
        ir50_handoff_report_path=ir50_path,
    )

    completion = write_ir51_55_completion_bundle(
        base_path=base,
        ir51_55_output=out,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 356, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "IR55"
    assert loaded["final_decision"] == "READY_FOR_DRY_RUN_HANDOFF_ONLY"
    assert (base / "reports" / "ir51_55" / "ir51_55_live_status.md").exists()
    assert (base / "reports" / "ir51_55" / "ir51_55_completion_table.md").exists()
