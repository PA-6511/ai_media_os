from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r9_preflight_approval_pack import (
    CURRENT_APPROVAL_STATE,
    REQUIRED_APPROVAL_LABEL,
    atomic_write_json,
    canonical_digest,
    json_storage_snapshot,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    sha256_file,
)


ROOT = REPOSITORY_ROOT

EXPECTED_PACK_STATUS = (
    "READY_FOR_EXPLICIT_APPROVAL_NO_EXECUTION"
)
EXPECTED_LOCK_TYPE = (
    "X_FB_ONE_SHOT_PREFLIGHT_LOCK"
)
EXPECTED_LOCK_STATE = (
    "PREPARED_NOT_EXECUTABLE"
)

TOKEN_STATE = "ISSUED_NOT_CONSUMED"
NEXT_PHASE = (
    "X-R11_ONE_SHOT_NORMAL_X_FB_WRITE_GATE"
)


class XR10ApprovalTokenError(RuntimeError):
    """Raised when X-R10 approval-token issuance fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR10ApprovalTokenError(message)


def load_json_object(path: Path) -> dict[str, Any]:
    require(
        path.is_file(),
        f"required JSON is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise XR10ApprovalTokenError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def normalize_nonempty_text(
    value: str,
    field_name: str,
) -> str:
    require(
        isinstance(value, str),
        f"{field_name} must be a string",
    )

    normalized = unicodedata.normalize(
        "NFKC",
        value,
    ).strip()

    require(
        bool(normalized),
        f"{field_name} must not be empty",
    )

    return normalized


def normalize_approved_at(value: str) -> str:
    normalized = normalize_nonempty_text(
        value,
        "approved_at",
    )

    parse_value = normalized

    if parse_value.endswith("Z"):
        parse_value = (
            parse_value[:-1] + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            parse_value
        )
    except ValueError as exc:
        raise XR10ApprovalTokenError(
            "approved_at must be ISO-8601"
        ) from exc

    require(
        parsed.tzinfo is not None
        and parsed.utcoffset() is not None,
        "approved_at must include timezone",
    )

    return parsed.isoformat()


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


def assert_diagnostic_output_path(
    path: Path,
    x_fb_storage_root: Path,
    field_name: str,
) -> None:
    forbidden_roots = (
        x_fb_storage_root
        / "exchange/input/x_post_feedback",
        x_fb_storage_root
        / "exchange/archive/x_post_feedback",
        x_fb_storage_root
        / "exchange/logs",
    )

    for forbidden_root in forbidden_roots:
        require(
            not is_within(
                path,
                forbidden_root,
            ),
            (
                f"{field_name} must not be inside "
                f"normal X-FB storage: {path}"
            ),
        )


def create_exclusive_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise XR10ApprovalTokenError(
            "approval token already exists: "
            f"{path}"
        ) from exc

    try:
        with os.fdopen(
            descriptor,
            "wb",
        ) as file:
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def validate_pack_safety(
    pack: dict[str, Any],
) -> None:
    require(
        pack.get("status")
        == EXPECTED_PACK_STATUS,
        "approval pack status is invalid",
    )
    require(
        pack.get("approval_state")
        == CURRENT_APPROVAL_STATE,
        "approval pack state is invalid",
    )
    require(
        pack.get("approval_label_consumed")
        is False,
        (
            "approval pack label must be "
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
            "approval pack normal X-FB "
            "write must be false"
        ),
    )
    require(
        pack.get("required_approval_label")
        == REQUIRED_APPROVAL_LABEL,
        (
            "approval pack required label "
            "does not match policy"
        ),
    )
    require(
        pack.get("existing_current_record")
        is False,
        (
            "approval pack reports existing "
            "current record"
        ),
    )

    safety = pack.get("safety")

    require(
        isinstance(safety, dict),
        "approval pack safety must be object",
    )

    for field_name in (
        "database_write",
        "workflow_write",
        "wordpress_write",
        "x_api_call",
        "x_post",
        "external_api_call",
    ):
        require(
            safety.get(field_name) is False,
            (
                "approval pack safety flag "
                f"must be false: {field_name}"
            ),
        )

    require(
        safety.get("production_status")
        == "NO_GO",
        (
            "approval pack production_status "
            "must be NO_GO"
        ),
    )
    require(
        safety.get("safety_state")
        == "DRY_RUN_ONLY",
        (
            "approval pack safety_state "
            "must be DRY_RUN_ONLY"
        ),
    )


def validate_lock_safety(
    lock: dict[str, Any],
) -> None:
    require(
        lock.get("lock_type")
        == EXPECTED_LOCK_TYPE,
        "one-shot lock type is invalid",
    )
    require(
        lock.get("lock_state")
        == EXPECTED_LOCK_STATE,
        "one-shot lock state is invalid",
    )
    require(
        lock.get("approval_state")
        == CURRENT_APPROVAL_STATE,
        "one-shot lock approval state is invalid",
    )
    require(
        lock.get("required_approval_label")
        == REQUIRED_APPROVAL_LABEL,
        (
            "one-shot lock required label "
            "does not match policy"
        ),
    )
    require(
        lock.get("approval_label_consumed")
        is False,
        (
            "one-shot lock approval label "
            "must be unconsumed"
        ),
    )
    require(
        lock.get("execution_allowed")
        is False,
        (
            "one-shot lock execution_allowed "
            "must be false"
        ),
    )
    require(
        lock.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "one-shot lock normal X-FB "
            "write must be false"
        ),
    )
    require(
        lock.get("production_status")
        == "NO_GO",
        (
            "one-shot lock production_status "
            "must be NO_GO"
        ),
    )
    require(
        lock.get("safety_state")
        == "DRY_RUN_ONLY",
        (
            "one-shot lock safety_state "
            "must be DRY_RUN_ONLY"
        ),
    )


def run_x_r10(
    *,
    approval_pack_path: Path,
    lock_path: Path,
    approval_label: str,
    approved_by: str,
    approved_at: str,
    output_root: Path,
    token_root: Path,
    x_fb_storage_root: Path = ROOT,
) -> dict[str, Any]:
    approval_pack_path = (
        approval_pack_path.resolve()
    )
    lock_path = lock_path.resolve()
    output_root = output_root.resolve()
    token_root = token_root.resolve()
    x_fb_storage_root = (
        x_fb_storage_root.resolve()
    )

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            (
                "output_root must be empty: "
                f"{output_root}"
            ),
        )

    assert_diagnostic_output_path(
        output_root,
        x_fb_storage_root,
        "output_root",
    )
    assert_diagnostic_output_path(
        token_root,
        x_fb_storage_root,
        "token_root",
    )

    normalized_label = (
        normalize_nonempty_text(
            approval_label,
            "approval_label",
        )
    )
    normalized_approver = (
        normalize_nonempty_text(
            approved_by,
            "approved_by",
        )
    )
    normalized_approved_at = (
        normalize_approved_at(
            approved_at
        )
    )

    require(
        normalized_label
        == REQUIRED_APPROVAL_LABEL,
        (
            "approval label must exactly match "
            f"{REQUIRED_APPROVAL_LABEL}"
        ),
    )

    pack_sha_before = sha256_file(
        approval_pack_path
    )
    lock_sha_before = sha256_file(
        lock_path
    )
    x_fb_snapshot_before = (
        json_storage_snapshot(
            x_fb_storage_root
        )
    )

    pack = load_json_object(
        approval_pack_path
    )
    lock = load_json_object(
        lock_path
    )

    validate_pack_safety(pack)
    validate_lock_safety(lock)

    stored_pack_digest = pack.get(
        "approval_pack_digest_sha256"
    )

    require(
        isinstance(stored_pack_digest, str)
        and len(stored_pack_digest) == 64,
        (
            "approval pack digest must be "
            "SHA-256"
        ),
    )

    pack_payload = {
        key: value
        for key, value in pack.items()
        if key
        != "approval_pack_digest_sha256"
    }

    recomputed_pack_digest = (
        canonical_digest(pack_payload)
    )

    require(
        recomputed_pack_digest
        == stored_pack_digest,
        (
            "approval pack tampering detected: "
            "digest mismatch"
        ),
    )
    require(
        lock.get(
            "approval_pack_digest_sha256"
        )
        == stored_pack_digest,
        (
            "one-shot lock digest does not "
            "match approval pack"
        ),
    )

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
    require(
        lock.get("feedback_id")
        == feedback_id,
        "feedback_id mismatch between pack and lock",
    )
    require(
        lock.get("approval_request_id")
        == approval_request_id,
        (
            "approval_request_id mismatch "
            "between pack and lock"
        ),
    )

    pack_lock = pack.get("one_shot_lock")

    require(
        isinstance(pack_lock, dict),
        (
            "approval pack one_shot_lock "
            "must be object"
        ),
    )
    require(
        Path(
            str(pack_lock.get("path"))
        ).resolve()
        == lock_path,
        (
            "approval pack lock path does "
            "not match supplied lock"
        ),
    )
    require(
        Path(
            str(lock.get("approval_pack_path"))
        ).resolve()
        == approval_pack_path,
        (
            "lock approval_pack_path does "
            "not match supplied pack"
        ),
    )

    current_record_path = (
        x_fb_storage_root
        / "exchange/input/x_post_feedback"
        / feedback_id
        / "current.json"
    )
    operation_result_path = (
        x_fb_storage_root
        / "exchange/logs"
        / f"x_fb_1_{feedback_id}_v001_result.json"
    )

    require(
        not current_record_path.exists(),
        (
            "normal X-FB current record "
            "already exists"
        ),
    )
    require(
        not operation_result_path.exists(),
        (
            "normal X-FB operation result "
            "already exists"
        ),
    )

    token_path = (
        token_root
        / f"{feedback_id}.token.json"
    )
    result_path = (
        output_root / "x_r10_result.json"
    )

    token_id_source = "|".join(
        (
            feedback_id,
            stored_pack_digest,
            normalized_approver,
            normalized_approved_at,
        )
    )

    token_id = (
        "xr10-"
        + hashlib.sha256(
            token_id_source.encode("utf-8")
        ).hexdigest()[:24]
    )

    issued_at = datetime.now(
        normalized_approved_at
        and datetime.fromisoformat(
            normalized_approved_at
        ).tzinfo
    ).isoformat()

    token_payload = {
        "phase": "X-R10",
        "status": (
            "APPROVAL_TOKEN_ISSUED_NO_EXECUTION"
        ),
        "token_id": token_id,
        "token_state": TOKEN_STATE,
        "feedback_id": feedback_id,
        "approval_request_id": (
            approval_request_id
        ),
        "approval_pack_path": str(
            approval_pack_path
        ),
        "one_shot_lock_path": str(
            lock_path
        ),
        "approval_pack_digest_sha256": (
            stored_pack_digest
        ),
        "approval_pack_file_sha256": (
            pack_sha_before
        ),
        "one_shot_lock_file_sha256": (
            lock_sha_before
        ),
        "approval_label": normalized_label,
        "approved_by": normalized_approver,
        "approved_at": (
            normalized_approved_at
        ),
        "issued_at": issued_at,
        "approval_label_consumed": True,
        "preflight_lock_consumed": False,
        "execution_token_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": NEXT_PHASE,
        "consumption_rules": {
            "required_token_state": (
                TOKEN_STATE
            ),
            "required_lock_state": (
                EXPECTED_LOCK_STATE
            ),
            "token_must_be_consumed_once": True,
            "lock_must_be_consumed_once": True,
            "token_and_lock_consumption_must_be_atomic": (
                True
            ),
            "second_execution_forbidden": True,
            "normal_x_fb_write_before_x_r11": False,
            "x_api_call_allowed": False,
            "x_post_allowed": False,
        },
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "external_api_call": False,
        "production_status": "NO_GO",
        "safety_state": (
            "APPROVAL_TOKEN_ONLY_NO_EXECUTION"
        ),
    }

    token_digest = canonical_digest(
        token_payload
    )

    token = {
        **token_payload,
        "execution_token_digest_sha256": (
            token_digest
        ),
    }

    token_created = False

    try:
        create_exclusive_json(
            token_path,
            token,
        )
        token_created = True

        pack_sha_after = sha256_file(
            approval_pack_path
        )
        lock_sha_after = sha256_file(
            lock_path
        )

        require(
            pack_sha_before == pack_sha_after,
            (
                "approval pack changed during "
                "token issuance"
            ),
        )
        require(
            lock_sha_before == lock_sha_after,
            (
                "one-shot lock changed during "
                "token issuance"
            ),
        )

        x_fb_snapshot_after = (
            json_storage_snapshot(
                x_fb_storage_root
            )
        )

        require(
            x_fb_snapshot_before
            == x_fb_snapshot_after,
            "normal X-FB storage changed",
        )

        result = {
            "phase": "X-R10",
            "status": (
                "PASS_APPROVAL_TOKEN_ISSUED_"
                "NO_EXECUTION"
            ),
            "feedback_id": feedback_id,
            "approval_request_id": (
                approval_request_id
            ),
            "approval_pack_path": str(
                approval_pack_path
            ),
            "one_shot_lock_path": str(
                lock_path
            ),
            "execution_token_path": str(
                token_path
            ),
            "execution_token_id": token_id,
            "approval_pack_digest_sha256": (
                stored_pack_digest
            ),
            "execution_token_digest_sha256": (
                token_digest
            ),
            "approval_label": (
                normalized_label
            ),
            "approved_by": (
                normalized_approver
            ),
            "approved_at": (
                normalized_approved_at
            ),
            "approval_label_consumed": True,
            "preflight_lock_consumed": False,
            "execution_token_consumed": False,
            "execution_allowed": False,
            "normal_x_fb_write_allowed": False,
            "pack_tampering_detected": False,
            "lock_tampering_detected": False,
            "pack_unchanged": True,
            "lock_unchanged": True,
            "current_record_written": False,
            "operation_result_written": False,
            "normal_x_fb_storage_modified": False,
            "database_read": False,
            "database_write": False,
            "workflow_write": False,
            "wordpress_write": False,
            "x_api_call": False,
            "x_post": False,
            "external_api_call": False,
            "authorized_next_phase": (
                NEXT_PHASE
            ),
            "production_status": "NO_GO",
            "safety_state": (
                "APPROVAL_TOKEN_ONLY_NO_EXECUTION"
            ),
        }

        atomic_write_json(
            result_path,
            result,
        )

        return result

    except Exception:
        if token_created:
            token_path.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--approval-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--lock-path",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--approval-label",
        required=True,
    )
    parser.add_argument(
        "--approved-by",
        required=True,
    )
    parser.add_argument(
        "--approved-at",
        required=True,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--token-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--x-fb-storage-root",
        type=Path,
        default=ROOT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_x_r10(
            approval_pack_path=(
                args.approval_pack
            ),
            lock_path=args.lock_path,
            approval_label=(
                args.approval_label
            ),
            approved_by=args.approved_by,
            approved_at=args.approved_at,
            output_root=args.output_root,
            token_root=args.token_root,
            x_fb_storage_root=(
                args.x_fb_storage_root
            ),
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": "X-R10",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "approval_label_consumed": False,
                    "preflight_lock_consumed": False,
                    "execution_token_consumed": False,
                    "execution_allowed": False,
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
