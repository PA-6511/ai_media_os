import json
from pathlib import Path

from generic_block_ai.app.core_destination_evidence_bundle_verifier import (
    run_ir43_destination_evidence_bundle_verifier_dryrun,
    write_ir43_completion_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_digest(payload: dict) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    import hashlib

    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _bundle_hash(destination: str, evidence_digest: str, review_status: str) -> str:
    import hashlib

    return hashlib.sha256(f"{destination}|{evidence_digest}|{review_status}".encode("utf-8")).hexdigest()


def _bundle_record(destination: str, review_status: str = "PASS") -> dict:
    return {
        "destination": destination,
        "review_status": review_status,
        "selected_event": "APPROVE",
        "lock_state": "EVIDENCE_LOCKED_APPROVED",
        "actor_id": "HUMAN_APPROVER_REQUIRED",
        "bundle_hash": "placeholder",
        "evidence_digest": "placeholder_digest",
        "chain_hash": {
            "regulatory_audit": "881a2d751cb9d3b45841b1f671e4984b6ca97e0bacceb57bdd4704c0747b7821",
            "internal_review_board": "072ad9c550d8e7ff74ab1a6e662a1b0344e5d7f696e52ec0ccbf9478d061e8e8",
            "compliance_archive": "fbf166942a72e7496df4c6db872d2402cf9434f92ef335d788e6b1998f1e9a55",
        }[destination],
        "source_refs": {
            "ir39": "generic_block_ai/reports/ir39_human_approval_event_simulator_for_destinations_report_ir39_live_trial.json",
            "ir40": "generic_block_ai/reports/ir40_human_event_audit_replay_for_destinations_report_ir40_live_trial.json",
            "ir41": "generic_block_ai/reports/ir41_destination_human_event_chain_integrity_report_ir41_live_trial.json",
        },
        "integrity_checks": {
            "sequence_ok": True,
            "event_ok": True,
            "state_ok": True,
            "actor_ok": True,
            "hash_ok": True,
            "evidence_lock_ok": True,
        },
        "failed_reasons": [],
        "hash_manifest_path": "",
        "review_summary_path": "",
    }


def _base_ir42_payload(base: Path) -> dict:
    bundle_root = base / "reports" / "ir42_destination_human_event_chain_evidence_bundle_ir42_live_trial"
    entries = []
    for destination in ["regulatory_audit", "internal_review_board", "compliance_archive"]:
        record = _bundle_record(destination)
        bundle_dir = base / "reports" / f"ir42_destination_human_event_chain_evidence_bundle_{destination}_ir42_live_trial"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        hash_manifest_path = bundle_dir / "destination_human_event_chain_hash_manifest.json"
        review_summary_path = bundle_dir / "destination_human_event_chain_review_summary.md"
        record["hash_manifest_path"] = str(hash_manifest_path.relative_to(base.parent))
        record["review_summary_path"] = str(review_summary_path.relative_to(base.parent))
        evidence_digest = _json_digest(
            {
                "destination": record["destination"],
                "release_candidate_id": "rc_20260523T155148Z_ir26_live_trial_b940393b490b",
                "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
                "overall_approval_decision": "APPROVE_DRY_RUN",
                "selected_event": record["selected_event"],
                "lock_state": record["lock_state"],
                "actor_id": record["actor_id"],
                "chain_hash": record["chain_hash"],
                "source_refs": record["source_refs"],
            }
        )
        bundle_hash = _bundle_hash(record["destination"], evidence_digest, record["review_status"])
        record["evidence_digest"] = evidence_digest
        record["bundle_hash"] = bundle_hash
        entries.append(record)
        _write(hash_manifest_path, {
            "destination": destination,
            "bundle_hash": bundle_hash,
            "evidence_digest": evidence_digest,
            "chain_hash": record["chain_hash"],
            "review_status": "PASS",
            "source_refs": record["source_refs"],
            "generated_at": "2026-05-24T00:00:00+00:00",
        })
        review_summary_path.write_text(
            "\n".join([
                "# Destination Human Event Chain Evidence Bundle",
                "",
                f"- Destination: {destination}",
                "- Review Status: PASS",
                "- Selected Event: APPROVE",
                "- Lock State: EVIDENCE_LOCKED_APPROVED",
                "- Actor ID: HUMAN_APPROVER_REQUIRED",
                f"- Bundle Hash: {bundle_hash}",
                f"- Evidence Digest: {evidence_digest}",
                "",
                "## Integrity Checks",
                "- sequence_ok: True",
                "- event_ok: True",
                "- state_ok: True",
                "- actor_ok: True",
                "- hash_ok: True",
                "- evidence_lock_ok: True",
            ])
            + "\n",
            encoding="utf-8",
        )
    return {
        "schema_version": "ir42_destination_human_event_chain_evidence_bundle_v1",
        "phase": "IR42",
        "release_candidate_id": "rc_fixture",
        "final_submission_decision": "READY_FOR_SUBMISSION_SUMMARY",
        "overall_approval_decision": "APPROVE_DRY_RUN",
        "destination_human_event_chain_evidence_bundle": entries,
        "artifacts": {"bundle_root": str(bundle_root.relative_to(base.parent))},
    }


def _prepare_ir42(base: Path, payload: dict | None = None) -> Path:
    reports = base / "reports"
    target = reports / "ir42_destination_human_event_chain_evidence_bundle_report_fixture.json"
    _write(target, payload or _base_ir42_payload(base))
    return target


def test_ir43_pass_verifier(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir42_path = _prepare_ir42(base)

    out = run_ir43_destination_evidence_bundle_verifier_dryrun(
        base_path=base,
        source_task_id="ir43_pass",
        ir42_bundle_report_path=ir42_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["destination_count"] == 3


def test_ir43_fail_when_hash_manifest_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir42_payload(base)
    entry = payload["destination_human_event_chain_evidence_bundle"][0]
    missing_path = base / "reports" / "missing_hash_manifest.json"
    entry["hash_manifest_path"] = str(missing_path.relative_to(base.parent))
    ir42_path = _prepare_ir42(base, payload)

    out = run_ir43_destination_evidence_bundle_verifier_dryrun(
        base_path=base,
        source_task_id="ir43_missing_hash",
        ir42_bundle_report_path=ir42_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"


def test_ir43_fail_when_summary_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir42_payload(base)
    entry = payload["destination_human_event_chain_evidence_bundle"][1]
    summary_path = base.parent / entry["review_summary_path"]
    summary_path.unlink()
    ir42_path = _prepare_ir42(base, payload)

    out = run_ir43_destination_evidence_bundle_verifier_dryrun(
        base_path=base,
        source_task_id="ir43_missing_summary",
        ir42_bundle_report_path=ir42_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"


def test_ir43_fail_on_completeness_flag(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir42_payload(base)
    payload["destination_human_event_chain_evidence_bundle"][2]["review_status"] = "FAIL"
    ir42_path = _prepare_ir42(base, payload)

    out = run_ir43_destination_evidence_bundle_verifier_dryrun(
        base_path=base,
        source_task_id="ir43_incomplete",
        ir42_bundle_report_path=ir42_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    row = [r for r in report["destination_evidence_bundle_verification"] if r["destination"] == "compliance_archive"][0]
    assert row["verification_checks"]["completeness_ok"] is False


def test_ir43_fail_on_manifest_tamper(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    payload = _base_ir42_payload(base)
    ir42_path = _prepare_ir42(base, payload)
    entry = payload["destination_human_event_chain_evidence_bundle"][1]
    manifest_path = base.parent / entry["hash_manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["bundle_hash"] = "tampered"
    _write(manifest_path, manifest)

    out = run_ir43_destination_evidence_bundle_verifier_dryrun(
        base_path=base,
        source_task_id="ir43_manifest_tamper",
        ir42_bundle_report_path=ir42_path,
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"


def test_ir43_fail_when_input_missing(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"

    out = run_ir43_destination_evidence_bundle_verifier_dryrun(
        base_path=base,
        source_task_id="ir43_missing",
        ir42_bundle_report_path=tmp_path / "missing_ir42.json",
    )

    report = out["runbook_report"]
    assert report["validation_result"] == "FAIL"
    assert len(report["validation_failed_checks"]) >= 1


def test_write_ir43_completion_report(tmp_path: Path) -> None:
    base = tmp_path / "generic_block_ai"
    ir42_path = _prepare_ir42(base)
    ir43 = run_ir43_destination_evidence_bundle_verifier_dryrun(
        base_path=base,
        source_task_id="ir43_completion",
        ir42_bundle_report_path=ir42_path,
    )

    completion = write_ir43_completion_report(
        base_path=base,
        ir43_output=ir43,
        focused_tests={"passed": 6, "failed": 0},
        adjacent_tests={"passed": 18, "failed": 0},
        scoped_regression={"passed": 313, "failed": 0},
    )

    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 43"
    assert loaded["status"] == "COMPLETED"
    assert loaded["overall_approval_decision"] == "APPROVE_DRY_RUN"