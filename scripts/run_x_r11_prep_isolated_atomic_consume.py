from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r9_preflight_approval_pack import (
    REQUIRED_APPROVAL_LABEL,
    canonical_digest,
    json_storage_snapshot,
)
from scripts.issue_x_r10_one_shot_approval_token import (
    EXPECTED_LOCK_STATE,
    EXPECTED_LOCK_TYPE,
    EXPECTED_PACK_STATUS,
    NEXT_PHASE,
    TOKEN_STATE,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    find_normal_x_fb_matches,
    prepare_isolated_x_fb_root,
    sha256_file,
)
from scripts.run_x_r8_isolated_x_fb_write import (
    load_json_object,
    run_feedback_manager,
    validate_execution_boundary,
)


ROOT = REPOSITORY_ROOT

CONSUMED_TOKEN_STATE = (
    "CONSUMED_BY_X_R11_PREP_ISOLATED"
)
CONSUMED_LOCK_STATE = (
    "CONSUMED_BY_X_R11_PREP_ISOLATED"
)
TRANSACTION_TYPE = (
    "X_R11_PREP_ISOLATED_ATOMIC_CONSUMPTION"
)

ALLOWED_FAULTS = {
    None,
    "AFTER_X_FB_WRITE",
    "AFTER_TOKEN_REPLACE",
    "AFTER_LOCK_REPLACE",
}


class XR11PrepError(RuntimeError):
    """Raised when X-R11-PREP validation or transaction fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR11PrepError(message)


def atomic_write_bytes(
    path: Path,
    content: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )

    descriptor = os.open(
        temporary,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary, path)

        directory_descriptor = os.open(
            path.parent,
            os.O_RDONLY,
        )

        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    atomic_write_bytes(
        path,
        (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode("utf-8"),
    )


def copy_exact(
    source: Path,
    destination: Path,
) -> None:
    require(
        source.is_file(),
        f"source artifact is missing: {source}",
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    require(
        sha256_file(source)
        == sha256_file(destination),
        (
            "artifact copy digest mismatch: "
            f"{source}"
        ),
    )


def is_within(
    path: Path,
    parent: Path,
) -> bool:
    try:
        path.resolve().relative_to(
            parent.resolve()
        )
    except ValueError:
        return False

    return True


def assert_isolated_run_root(
    run_root: Path,
    normal_x_fb_root: Path,
) -> None:
    forbidden_roots = (
        normal_x_fb_root
        / "exchange/input/x_post_feedback",
        normal_x_fb_root
        / "exchange/archive/x_post_feedback",
        normal_x_fb_root
        / "exchange/logs",
    )

    for forbidden_root in forbidden_roots:
        require(
            not is_within(
                run_root,
                forbidden_root,
            ),
            (
                "run_root must not be inside "
                "normal X-FB storage"
            ),
        )


def validate_pack(
    pack: dict[str, Any],
) -> str:
    require(
        pack.get("status")
        == EXPECTED_PACK_STATUS,
        "approval pack status is invalid",
    )
    require(
        pack.get("required_approval_label")
        == REQUIRED_APPROVAL_LABEL,
        (
            "approval pack required label "
            "is invalid"
        ),
    )
    require(
        pack.get("approval_label_consumed")
        is False,
        (
            "approval pack label must remain "
            "unconsumed"
        ),
    )
    require(
        pack.get("execution_allowed")
        is False,
        (
            "approval pack execution_allowed "
            "must be false"
        ),
    )
    require(
        pack.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "approval pack normal X-FB write "
            "must be false"
        ),
    )

    digest = pack.get(
        "approval_pack_digest_sha256"
    )

    require(
        isinstance(digest, str)
        and len(digest) == 64,
        "approval pack digest is invalid",
    )

    payload = {
        key: value
        for key, value in pack.items()
        if key
        != "approval_pack_digest_sha256"
    }

    require(
        canonical_digest(payload) == digest,
        (
            "approval pack tampering detected: "
            "digest mismatch"
        ),
    )

    return digest


def validate_lock(
    lock: dict[str, Any],
    *,
    pack_digest: str,
    feedback_id: str,
    approval_request_id: str,
) -> None:
    require(
        lock.get("lock_type")
        == EXPECTED_LOCK_TYPE,
        "preflight lock type is invalid",
    )
    require(
        lock.get("lock_state")
        == EXPECTED_LOCK_STATE,
        "preflight lock state is invalid",
    )
    require(
        lock.get("feedback_id")
        == feedback_id,
        (
            "feedback_id mismatch between "
            "pack and lock"
        ),
    )
    require(
        lock.get("approval_request_id")
        == approval_request_id,
        (
            "approval_request_id mismatch "
            "between pack and lock"
        ),
    )
    require(
        lock.get(
            "approval_pack_digest_sha256"
        )
        == pack_digest,
        (
            "preflight lock digest does not "
            "match approval pack"
        ),
    )
    require(
        lock.get("approval_label_consumed")
        is False,
        (
            "preflight lock approval label "
            "must be unconsumed"
        ),
    )
    require(
        lock.get("execution_allowed")
        is False,
        (
            "preflight lock execution_allowed "
            "must be false"
        ),
    )
    require(
        lock.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "preflight lock normal X-FB "
            "write must be false"
        ),
    )


def validate_token(
    token: dict[str, Any],
    *,
    token_path: Path,
    pack_path: Path,
    lock_path: Path,
    pack_digest: str,
    feedback_id: str,
    approval_request_id: str,
) -> str:
    require(
        token.get("token_state")
        == TOKEN_STATE,
        (
            "execution token state must be "
            "ISSUED_NOT_CONSUMED"
        ),
    )
    require(
        token.get("status")
        == "APPROVAL_TOKEN_ISSUED_NO_EXECUTION",
        "execution token status is invalid",
    )
    require(
        token.get("feedback_id")
        == feedback_id,
        (
            "feedback_id mismatch between "
            "pack and token"
        ),
    )
    require(
        token.get("approval_request_id")
        == approval_request_id,
        (
            "approval_request_id mismatch "
            "between pack and token"
        ),
    )
    require(
        token.get(
            "approval_pack_digest_sha256"
        )
        == pack_digest,
        (
            "token pack digest does not "
            "match approval pack"
        ),
    )
    require(
        token.get("approval_label")
        == REQUIRED_APPROVAL_LABEL,
        "execution token approval label is invalid",
    )
    require(
        token.get("approval_label_consumed")
        is True,
        (
            "execution token approval label "
            "must be consumed"
        ),
    )
    require(
        token.get("preflight_lock_consumed")
        is False,
        (
            "preflight lock must be "
            "unconsumed"
        ),
    )
    require(
        token.get("execution_token_consumed")
        is False,
        (
            "execution token must be "
            "unconsumed"
        ),
    )
    require(
        token.get("execution_allowed")
        is False,
        (
            "execution token execution_allowed "
            "must be false"
        ),
    )
    require(
        token.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "execution token normal X-FB "
            "write must be false"
        ),
    )
    require(
        token.get("authorized_next_phase")
        == NEXT_PHASE,
        (
            "execution token is not authorized "
            "for X-R11"
        ),
    )

    token_digest = token.get(
        "execution_token_digest_sha256"
    )

    require(
        isinstance(token_digest, str)
        and len(token_digest) == 64,
        "execution token digest is invalid",
    )

    payload = {
        key: value
        for key, value in token.items()
        if key
        != "execution_token_digest_sha256"
    }

    require(
        canonical_digest(payload)
        == token_digest,
        (
            "execution token tampering "
            "detected: digest mismatch"
        ),
    )

    require(
        token.get("approval_pack_file_sha256")
        == sha256_file(pack_path),
        (
            "approval pack file SHA-256 "
            "does not match token"
        ),
    )
    require(
        token.get("one_shot_lock_file_sha256")
        == sha256_file(lock_path),
        (
            "preflight lock file SHA-256 "
            "does not match token"
        ),
    )

    require(
        token_path.is_file(),
        "execution token is missing",
    )

    return token_digest


def inject_fault(
    fault_injection: str | None,
    checkpoint: str,
) -> None:
    if fault_injection == checkpoint:
        raise XR11PrepError(
            f"FAULT_INJECTION:{checkpoint}"
        )


def build_consumed_token(
    token: dict[str, Any],
    *,
    consumed_at: str,
    transaction_id: str,
    isolated_pack_path: Path,
    isolated_lock_path: Path,
    isolated_request_path: Path,
) -> dict[str, Any]:
    payload = {
        **token,
        "token_state": CONSUMED_TOKEN_STATE,
        "preflight_lock_consumed": True,
        "execution_token_consumed": True,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "consumed_at": consumed_at,
        "consumed_by_phase": "X-R11-PREP",
        "consumption_scope": (
            "ISOLATED_X_FB_ONLY"
        ),
        "transaction_id": transaction_id,
        "isolated_artifacts": {
            "approval_pack_path": str(
                isolated_pack_path
            ),
            "preflight_lock_path": str(
                isolated_lock_path
            ),
            "initialize_request_path": str(
                isolated_request_path
            ),
        },
        "production_status": "NO_GO",
        "safety_state": (
            "ISOLATED_ATOMIC_CONSUMPTION_ONLY"
        ),
    }

    payload.pop(
        "execution_token_digest_sha256",
        None,
    )

    return {
        **payload,
        "consumed_token_digest_sha256": (
            canonical_digest(payload)
        ),
    }


def build_consumed_lock(
    lock: dict[str, Any],
    *,
    consumed_at: str,
    transaction_id: str,
    token_id: str,
) -> dict[str, Any]:
    payload = {
        **lock,
        "lock_state": CONSUMED_LOCK_STATE,
        "approval_label_consumed": True,
        "consumed": True,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "consumed_at": consumed_at,
        "consumed_by_phase": "X-R11-PREP",
        "consumed_by_token_id": token_id,
        "transaction_id": transaction_id,
        "consumption_scope": (
            "ISOLATED_X_FB_ONLY"
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "ISOLATED_ATOMIC_CONSUMPTION_ONLY"
        ),
    }

    return {
        **payload,
        "consumed_lock_digest_sha256": (
            canonical_digest(payload)
        ),
    }


def run_x_r11_prep(
    *,
    approval_pack_path: Path,
    preflight_lock_path: Path,
    approval_token_path: Path,
    initialize_request_path: Path,
    run_root: Path,
    evidence_path: Path,
    normal_x_fb_root: Path = ROOT,
    fault_injection: str | None = None,
) -> dict[str, Any]:
    require(
        fault_injection in ALLOWED_FAULTS,
        "unsupported fault injection value",
    )

    approval_pack_path = (
        approval_pack_path.resolve()
    )
    preflight_lock_path = (
        preflight_lock_path.resolve()
    )
    approval_token_path = (
        approval_token_path.resolve()
    )
    initialize_request_path = (
        initialize_request_path.resolve()
    )
    run_root = run_root.resolve()
    evidence_path = evidence_path.resolve()
    normal_x_fb_root = (
        normal_x_fb_root.resolve()
    )

    if run_root.exists():
        require(
            not any(run_root.iterdir()),
            (
                "run_root must be empty: "
                f"{run_root}"
            ),
        )

    assert_isolated_run_root(
        run_root,
        normal_x_fb_root,
    )

    run_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact_root = run_root / "artifacts"
    transaction_root = (
        run_root / "transaction"
    )
    backup_root = (
        transaction_root / "backup"
    )
    staged_root = (
        transaction_root / "staged"
    )
    isolated_x_fb_root = (
        run_root / "x_fb_root"
    )

    isolated_pack_path = (
        artifact_root / "approval_pack.json"
    )
    isolated_lock_path = (
        artifact_root / "preflight_lock.json"
    )
    isolated_token_path = (
        artifact_root / "approval_token.json"
    )
    isolated_request_path = (
        artifact_root / "initialize_request.json"
    )

    backup_token_path = (
        backup_root / "approval_token.original.json"
    )
    backup_lock_path = (
        backup_root / "preflight_lock.original.json"
    )
    staged_token_path = (
        staged_root / "approval_token.consumed.json"
    )
    staged_lock_path = (
        staged_root / "preflight_lock.consumed.json"
    )
    journal_path = (
        transaction_root / "journal.json"
    )
    rollback_path = (
        transaction_root / "rollback_result.json"
    )

    source_hashes_before = {
        "approval_pack": sha256_file(
            approval_pack_path
        ),
        "preflight_lock": sha256_file(
            preflight_lock_path
        ),
        "approval_token": sha256_file(
            approval_token_path
        ),
        "initialize_request": sha256_file(
            initialize_request_path
        ),
    }

    copy_exact(
        approval_pack_path,
        isolated_pack_path,
    )
    copy_exact(
        preflight_lock_path,
        isolated_lock_path,
    )
    copy_exact(
        approval_token_path,
        isolated_token_path,
    )
    copy_exact(
        initialize_request_path,
        isolated_request_path,
    )

    prepare_isolated_x_fb_root(
        isolated_root=isolated_x_fb_root,
        repository_root=ROOT,
    )

    normal_snapshot_before = (
        json_storage_snapshot(
            normal_x_fb_root
        )
    )

    pack = load_json_object(
        isolated_pack_path
    )
    lock = load_json_object(
        isolated_lock_path
    )
    token = load_json_object(
        isolated_token_path
    )
    load_json_object(
        isolated_request_path
    )

    pack_digest = validate_pack(pack)

    feedback_id = pack.get("feedback_id")
    approval_request_id = pack.get(
        "approval_request_id"
    )

    require(
        isinstance(feedback_id, str)
        and bool(feedback_id.strip()),
        "feedback_id must not be empty",
    )
    require(
        isinstance(approval_request_id, str)
        and bool(approval_request_id.strip()),
        "approval_request_id must not be empty",
    )

    # Validate the execution token first so that a reused
    # consumed token is rejected with the primary one-shot
    # execution error before secondary lock-state checks.
    token_digest = validate_token(
        token,
        token_path=isolated_token_path,
        pack_path=isolated_pack_path,
        lock_path=isolated_lock_path,
        pack_digest=pack_digest,
        feedback_id=feedback_id,
        approval_request_id=(
            approval_request_id
        ),
    )

    validate_lock(
        lock,
        pack_digest=pack_digest,
        feedback_id=feedback_id,
        approval_request_id=(
            approval_request_id
        ),
    )

    current_path = (
        isolated_x_fb_root
        / "exchange/input/x_post_feedback"
        / feedback_id
        / "current.json"
    )
    operation_result_path = (
        isolated_x_fb_root
        / "exchange/logs"
        / f"x_fb_1_{feedback_id}_v001_result.json"
    )
    archive_root = (
        isolated_x_fb_root
        / "exchange/archive/x_post_feedback"
        / feedback_id
    )

    require(
        not current_path.exists(),
        (
            "isolated current.json "
            "already exists"
        ),
    )
    require(
        not operation_result_path.exists(),
        (
            "isolated operation result "
            "already exists"
        ),
    )

    (
        dry_run_rc,
        dry_run_result,
        _,
        dry_run_stderr,
    ) = run_feedback_manager(
        request_path=isolated_request_path,
        isolated_root=isolated_x_fb_root,
        dry_run=True,
    )

    require(
        dry_run_rc == 0,
        (
            "X-FB manager dry-run failed: "
            f"{dry_run_stderr}"
        ),
    )
    require(
        dry_run_result.get("status")
        == "PASS_DRY_RUN_NO_WRITE",
        (
            "unexpected X-FB dry-run status"
        ),
    )
    require(
        not current_path.exists(),
        (
            "dry-run created current.json"
        ),
    )
    require(
        not operation_result_path.exists(),
        (
            "dry-run created operation result"
        ),
    )

    transaction_id = (
        "xr11-prep-"
        + uuid.uuid4().hex
    )
    consumed_at = datetime.now(
        timezone.utc
    ).isoformat()

    consumed_token = build_consumed_token(
        token,
        consumed_at=consumed_at,
        transaction_id=transaction_id,
        isolated_pack_path=(
            isolated_pack_path
        ),
        isolated_lock_path=(
            isolated_lock_path
        ),
        isolated_request_path=(
            isolated_request_path
        ),
    )
    consumed_lock = build_consumed_lock(
        lock,
        consumed_at=consumed_at,
        transaction_id=transaction_id,
        token_id=str(token["token_id"]),
    )

    backup_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    staged_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    copy_exact(
        isolated_token_path,
        backup_token_path,
    )
    copy_exact(
        isolated_lock_path,
        backup_lock_path,
    )

    atomic_write_json(
        staged_token_path,
        consumed_token,
    )
    atomic_write_json(
        staged_lock_path,
        consumed_lock,
    )

    journal = {
        "phase": "X-R11-PREP",
        "transaction_type": (
            TRANSACTION_TYPE
        ),
        "transaction_id": transaction_id,
        "state": "PREPARED",
        "feedback_id": feedback_id,
        "approval_request_id": (
            approval_request_id
        ),
        "execution_token_id": (
            token["token_id"]
        ),
        "prepared_at": consumed_at,
        "fault_injection": fault_injection,
        "isolated_only": True,
        "normal_x_fb_write_allowed": False,
        "x_api_call_allowed": False,
        "x_post_allowed": False,
        "production_status": "NO_GO",
    }

    atomic_write_json(
        journal_path,
        journal,
    )

    transaction_started = True

    try:
        (
            write_rc,
            write_result,
            _,
            write_stderr,
        ) = run_feedback_manager(
            request_path=isolated_request_path,
            isolated_root=isolated_x_fb_root,
            dry_run=False,
        )

        require(
            write_rc == 0,
            (
                "isolated X-FB write failed: "
                f"{write_stderr}"
            ),
        )
        require(
            write_result.get("status")
            == "PASS_MANUAL_RECORD_OPERATION",
            (
                "unexpected isolated X-FB "
                "write status"
            ),
        )
        require(
            current_path.is_file(),
            (
                "isolated current.json "
                "was not created"
            ),
        )
        require(
            operation_result_path.is_file(),
            (
                "isolated operation result "
                "was not created"
            ),
        )

        current = load_json_object(
            current_path
        )
        operation_result = load_json_object(
            operation_result_path
        )

        require(
            current.get("feedback_id")
            == feedback_id,
            (
                "isolated current feedback_id "
                "mismatch"
            ),
        )
        require(
            current.get("record_version") == 1,
            (
                "isolated record_version "
                "must be 1"
            ),
        )
        require(
            current.get("record_stage")
            == "DRAFT_GENERATED",
            (
                "isolated record_stage "
                "must be DRAFT_GENERATED"
            ),
        )
        require(
            current.get("review_status")
            == "UNREVIEWED",
            (
                "isolated review_status "
                "must be UNREVIEWED"
            ),
        )

        generated_text = (
            current
            .get("text_snapshots", {})
            .get("generated_text")
        )

        require(
            generated_text
            == pack.get("generated_text"),
            (
                "generated text does not "
                "match approval pack"
            ),
        )
        require(
            isinstance(generated_text, str)
            and "#PR" in generated_text,
            (
                "generated text must "
                "contain #PR"
            ),
        )
        require(
            operation_result.get("status")
            == "PASS_MANUAL_RECORD_OPERATION",
            (
                "stored operation result "
                "status mismatch"
            ),
        )

        execution_boundary = current.get(
            "execution_boundary"
        )

        require(
            isinstance(
                execution_boundary,
                dict,
            ),
            (
                "execution_boundary must "
                "be an object"
            ),
        )

        validate_execution_boundary(
            execution_boundary
        )

        inject_fault(
            fault_injection,
            "AFTER_X_FB_WRITE",
        )

        os.replace(
            staged_token_path,
            isolated_token_path,
        )

        inject_fault(
            fault_injection,
            "AFTER_TOKEN_REPLACE",
        )

        os.replace(
            staged_lock_path,
            isolated_lock_path,
        )

        inject_fault(
            fault_injection,
            "AFTER_LOCK_REPLACE",
        )

        committed_at = datetime.now(
            timezone.utc
        ).isoformat()

        journal.update(
            {
                "state": "COMMITTED",
                "committed_at": committed_at,
                "isolated_current_record_written": (
                    True
                ),
                "isolated_operation_result_written": (
                    True
                ),
                "execution_token_consumed": True,
                "preflight_lock_consumed": True,
            }
        )

        atomic_write_json(
            journal_path,
            journal,
        )

        consumed_token_actual = (
            load_json_object(
                isolated_token_path
            )
        )
        consumed_lock_actual = (
            load_json_object(
                isolated_lock_path
            )
        )

        require(
            consumed_token_actual.get(
                "token_state"
            )
            == CONSUMED_TOKEN_STATE,
            "consumed token state mismatch",
        )
        require(
            consumed_token_actual.get(
                "execution_token_consumed"
            )
            is True,
            (
                "execution token was not "
                "marked consumed"
            ),
        )
        require(
            consumed_token_actual.get(
                "preflight_lock_consumed"
            )
            is True,
            (
                "token did not record lock "
                "consumption"
            ),
        )
        require(
            consumed_lock_actual.get(
                "lock_state"
            )
            == CONSUMED_LOCK_STATE,
            "consumed lock state mismatch",
        )
        require(
            consumed_lock_actual.get(
                "consumed"
            )
            is True,
            (
                "preflight lock was not "
                "marked consumed"
            ),
        )

        normal_snapshot_after = (
            json_storage_snapshot(
                normal_x_fb_root
            )
        )

        require(
            normal_snapshot_before
            == normal_snapshot_after,
            (
                "normal X-FB storage "
                "was modified"
            ),
        )

        normal_matches = (
            find_normal_x_fb_matches(
                repository_root=(
                    normal_x_fb_root
                ),
                feedback_id=feedback_id,
            )
        )

        require(
            not normal_matches,
            (
                "normal X-FB contains "
                f"transaction artifacts: "
                f"{normal_matches}"
            ),
        )

        source_hashes_after = {
            "approval_pack": sha256_file(
                approval_pack_path
            ),
            "preflight_lock": sha256_file(
                preflight_lock_path
            ),
            "approval_token": sha256_file(
                approval_token_path
            ),
            "initialize_request": sha256_file(
                initialize_request_path
            ),
        }

        require(
            source_hashes_before
            == source_hashes_after,
            (
                "source approval artifacts "
                "were modified"
            ),
        )

        result = {
            "phase": "X-R11-PREP",
            "status": (
                "PASS_ISOLATED_ATOMIC_"
                "TOKEN_LOCK_CONSUMPTION"
            ),
            "transaction_id": transaction_id,
            "transaction_state": "COMMITTED",
            "run_root": str(run_root),
            "isolated_x_fb_root": str(
                isolated_x_fb_root
            ),
            "isolated_approval_pack_path": str(
                isolated_pack_path
            ),
            "consumed_token_path": str(
                isolated_token_path
            ),
            "consumed_lock_path": str(
                isolated_lock_path
            ),
            "isolated_initialize_request_path": str(
                isolated_request_path
            ),
            "isolated_current_record_path": str(
                current_path
            ),
            "isolated_operation_result_path": str(
                operation_result_path
            ),
            "transaction_journal_path": str(
                journal_path
            ),
            "feedback_id": feedback_id,
            "approval_request_id": (
                approval_request_id
            ),
            "execution_token_id": (
                token["token_id"]
            ),
            "approval_pack_digest_sha256": (
                pack_digest
            ),
            "original_execution_token_digest_sha256": (
                token_digest
            ),
            "manager_dry_run_status": (
                dry_run_result["status"]
            ),
            "manager_write_status": (
                write_result["status"]
            ),
            "isolated_current_record_written": True,
            "isolated_operation_result_written": True,
            "execution_token_consumed": True,
            "preflight_lock_consumed": True,
            "approval_label_consumed": True,
            "archive_created": (
                archive_root.exists()
                and any(
                    archive_root.glob("*.json")
                )
            ),
            "rollback_required": False,
            "source_artifacts_unchanged": True,
            "normal_x_fb_storage_modified": False,
            "normal_x_fb_write_allowed": False,
            "database_read": False,
            "database_write": False,
            "workflow_write": False,
            "wordpress_write": False,
            "x_api_call": False,
            "x_post": False,
            "external_api_call": False,
            "production_execution": False,
            "production_status": "NO_GO",
            "safety_state": (
                "ISOLATED_ATOMIC_"
                "CONSUMPTION_ONLY"
            ),
        }

        evidence_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        atomic_write_json(
            evidence_path,
            result,
        )

        return result

    except Exception as exc:
        rollback_errors: list[str] = []

        if transaction_started:
            try:
                atomic_write_bytes(
                    isolated_token_path,
                    backup_token_path.read_bytes(),
                )
            except Exception as restore_exc:
                rollback_errors.append(
                    "token_restore:"
                    f"{restore_exc}"
                )

            try:
                atomic_write_bytes(
                    isolated_lock_path,
                    backup_lock_path.read_bytes(),
                )
            except Exception as restore_exc:
                rollback_errors.append(
                    "lock_restore:"
                    f"{restore_exc}"
                )

            try:
                current_path.unlink(
                    missing_ok=True
                )
            except Exception as cleanup_exc:
                rollback_errors.append(
                    "current_cleanup:"
                    f"{cleanup_exc}"
                )

            try:
                operation_result_path.unlink(
                    missing_ok=True
                )
            except Exception as cleanup_exc:
                rollback_errors.append(
                    "result_cleanup:"
                    f"{cleanup_exc}"
                )

            try:
                if archive_root.exists():
                    shutil.rmtree(
                        archive_root
                    )
            except Exception as cleanup_exc:
                rollback_errors.append(
                    "archive_cleanup:"
                    f"{cleanup_exc}"
                )

            staged_token_path.unlink(
                missing_ok=True
            )
            staged_lock_path.unlink(
                missing_ok=True
            )

            rollback_result = {
                "phase": "X-R11-PREP",
                "status": (
                    "ROLLBACK_COMPLETED"
                    if not rollback_errors
                    else "ROLLBACK_INCOMPLETE"
                ),
                "transaction_id": (
                    transaction_id
                ),
                "transaction_state": (
                    "ROLLED_BACK"
                ),
                "error": str(exc),
                "rollback_errors": (
                    rollback_errors
                ),
                "isolated_current_record_exists": (
                    current_path.exists()
                ),
                "isolated_operation_result_exists": (
                    operation_result_path.exists()
                ),
                "execution_token_restored": (
                    isolated_token_path.is_file()
                    and load_json_object(
                        isolated_token_path
                    ).get("token_state")
                    == TOKEN_STATE
                ),
                "preflight_lock_restored": (
                    isolated_lock_path.is_file()
                    and load_json_object(
                        isolated_lock_path
                    ).get("lock_state")
                    == EXPECTED_LOCK_STATE
                ),
                "normal_x_fb_write_allowed": False,
                "x_api_call": False,
                "x_post": False,
                "production_status": "NO_GO",
            }

            atomic_write_json(
                rollback_path,
                rollback_result,
            )

            journal.update(
                {
                    "state": "ROLLED_BACK",
                    "rolled_back_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "error": str(exc),
                    "rollback_errors": (
                        rollback_errors
                    ),
                }
            )

            atomic_write_json(
                journal_path,
                journal,
            )

        if rollback_errors:
            raise XR11PrepError(
                f"{exc}; rollback errors="
                f"{rollback_errors}"
            ) from exc

        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--approval-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--preflight-lock",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--approval-token",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--initialize-request",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--run-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--evidence-path",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--normal-x-fb-root",
        type=Path,
        default=ROOT,
    )
    parser.add_argument(
        "--fault-injection",
        choices=sorted(
            value
            for value in ALLOWED_FAULTS
            if value is not None
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_x_r11_prep(
            approval_pack_path=(
                args.approval_pack
            ),
            preflight_lock_path=(
                args.preflight_lock
            ),
            approval_token_path=(
                args.approval_token
            ),
            initialize_request_path=(
                args.initialize_request
            ),
            run_root=args.run_root,
            evidence_path=args.evidence_path,
            normal_x_fb_root=(
                args.normal_x_fb_root
            ),
            fault_injection=(
                args.fault_injection
            ),
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": "X-R11-PREP",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "normal_x_fb_write_allowed": False,
                    "database_write": False,
                    "workflow_write": False,
                    "wordpress_write": False,
                    "x_api_call": False,
                    "x_post": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
