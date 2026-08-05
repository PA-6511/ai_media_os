import json
from pathlib import Path

from generic_block_ai.app.core_policy_drift_detector import (
    run_ir19_policy_drift_detector_dryrun,
    write_ir19_completion_report,
)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in entries) + "\n", encoding="utf-8")


def _audit_entry(at: str, prev_hash: str | None, new_hash: str, change_type: str) -> dict:
    return {
        "event": "role_policy_version_recorded",
        "at": at,
        "source_task_id": "ir17_test",
        "role_policy_schema_version": "ir17_role_policy_v1",
        "previous_role_policy_hash": prev_hash,
        "new_role_policy_hash": new_hash,
        "change_type": change_type,
        "external_write_executed": False,
        "production_release": False,
    }


def _ir15_report(path: Path, generated_at: str, policy_hash: str) -> None:
    data = {
        "schema_version": "ir15_manual_event_role_guard_v1",
        "phase": "IR15",
        "generated_at": generated_at,
        "source_task_id": path.stem,
        "manual_event": "APPROVE",
        "actor": "reviewer",
        "actor_role": "approver",
        "allowed_roles": ["approver", "admin"],
        "role_policy_hash": policy_hash,
        "queue_state": "APPROVED_DRY_RUN_PENDING_RELEASE",
        "quality_gate_judgment": "PASS",
        "role_guard_result": "PASS",
        "role_guard_failed_checks": [],
        "role_guard_warnings": [],
        "execution_policy": {
            "execute": False,
            "reason": "ir15_role_guard_dryrun_only",
        },
        "safeguards": {
            "mode": "dry_run",
            "operation_mode": "OBSERVE",
            "external_write_executed": False,
            "actual_auto_execute": False,
            "production_release": False,
        },
    }
    _write_json(path, data)


def test_ir19_pass(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    audit_path = reports / "ir17_role_policy_change_audit.log"
    h1 = "1111" * 16
    h2 = "2222" * 16

    _write_jsonl(
        audit_path,
        [
            _audit_entry("2026-01-01T00:00:00+00:00", None, h1, "initial"),
            _audit_entry("2026-01-02T00:00:00+00:00", h1, h2, "updated"),
        ],
    )

    p1 = reports / "ir15_a.json"
    p2 = reports / "ir15_b.json"
    _ir15_report(p1, "2026-01-01T12:00:00+00:00", h1)
    _ir15_report(p2, "2026-01-02T12:00:00+00:00", h2)

    out = run_ir19_policy_drift_detector_dryrun(
        base_path=tmp_path,
        source_task_id="ir19_pass",
        ir17_change_audit_path=audit_path,
        ir15_report_paths=[str(p1), str(p2)],
    )
    report = out["drift_report"]
    assert report["validation_result"] == "PASS"
    assert report["summary"]["unrecorded_policy_use_count"] == 0


def test_ir19_detects_unrecorded_policy_use(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    audit_path = reports / "ir17_role_policy_change_audit.log"
    h1 = "1111" * 16
    h3 = "3333" * 16

    _write_jsonl(audit_path, [_audit_entry("2026-01-01T00:00:00+00:00", None, h1, "initial")])

    p1 = reports / "ir15_unknown.json"
    _ir15_report(p1, "2026-01-01T01:00:00+00:00", h3)

    out = run_ir19_policy_drift_detector_dryrun(
        base_path=tmp_path,
        source_task_id="ir19_unrecorded",
        ir17_change_audit_path=audit_path,
        ir15_report_paths=[str(p1)],
    )
    report = out["drift_report"]
    assert report["validation_result"] == "FAIL"
    assert any("unrecorded policy hash" in item for item in report["validation_failed_checks"])


def test_ir19_detects_timeline_hash_mismatch(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    audit_path = reports / "ir17_role_policy_change_audit.log"
    h1 = "1111" * 16
    h2 = "2222" * 16

    _write_jsonl(
        audit_path,
        [
            _audit_entry("2026-01-01T00:00:00+00:00", None, h1, "initial"),
            _audit_entry("2026-01-02T00:00:00+00:00", h1, h2, "updated"),
        ],
    )

    p1 = reports / "ir15_old_hash_after_update.json"
    _ir15_report(p1, "2026-01-03T00:00:00+00:00", h1)

    out = run_ir19_policy_drift_detector_dryrun(
        base_path=tmp_path,
        source_task_id="ir19_timeline",
        ir17_change_audit_path=audit_path,
        ir15_report_paths=[str(p1)],
    )
    report = out["drift_report"]
    assert report["validation_result"] == "FAIL"
    assert any("timeline hash mismatch" in item for item in report["validation_failed_checks"])


def test_ir19_detects_audit_chain_break(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    audit_path = reports / "ir17_role_policy_change_audit.log"
    h1 = "1111" * 16
    h2 = "2222" * 16

    _write_jsonl(
        audit_path,
        [
            _audit_entry("2026-01-01T00:00:00+00:00", None, h1, "initial"),
            _audit_entry("2026-01-02T00:00:00+00:00", "wrong_prev", h2, "updated"),
        ],
    )

    p1 = reports / "ir15_after_chain_break.json"
    _ir15_report(p1, "2026-01-02T12:00:00+00:00", h2)

    out = run_ir19_policy_drift_detector_dryrun(
        base_path=tmp_path,
        source_task_id="ir19_chain_break",
        ir17_change_audit_path=audit_path,
        ir15_report_paths=[str(p1)],
    )
    report = out["drift_report"]
    assert report["validation_result"] == "FAIL"
    assert any("audit chain break" in item for item in report["validation_failed_checks"])


def test_write_ir19_completion_report(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    audit_path = reports / "ir17_role_policy_change_audit.log"
    h1 = "1111" * 16

    _write_jsonl(audit_path, [_audit_entry("2026-01-01T00:00:00+00:00", None, h1, "initial")])

    p1 = reports / "ir15_for_completion.json"
    _ir15_report(p1, "2026-01-01T01:00:00+00:00", h1)

    ir19 = run_ir19_policy_drift_detector_dryrun(
        base_path=tmp_path,
        source_task_id="ir19_complete",
        ir17_change_audit_path=audit_path,
        ir15_report_paths=[str(p1)],
    )
    completion = write_ir19_completion_report(
        base_path=tmp_path,
        ir19_output=ir19,
        focused_tests={"passed": 5, "failed": 0},
        full_regression={"passed": 176, "failed": 0},
    )
    loaded = json.loads(Path(completion["path"]).read_text(encoding="utf-8"))
    assert loaded["phase"] == "Implementation Restart Phase 19"
    assert loaded["status"] == "COMPLETED"
    assert loaded["validation_result"] == "PASS"
