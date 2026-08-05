from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.workflow_approved_x_draft_read_service import (
    WorkflowApprovedXDraftReadService,
    normalize_wordpress_base_url,
)
from app.services.x_draft_feedback_registration_service import (
    XDraftFeedbackRegistrationService,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    sha256_file,
)


ROOT = REPOSITORY_ROOT

REQUIRED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_FB_ONE_SHOT_RECORD_ONLY"
)
CURRENT_APPROVAL_STATE = (
    "NOT_APPROVED_FOR_X_FB_ONE_SHOT_RECORD"
)


class XR9PreflightError(RuntimeError):
    """Raised when X-R9 preflight preparation fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR9PreflightError(message)


def canonical_digest(value: dict[str, Any]) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def atomic_write_text(
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )

    try:
        temporary.write_text(
            content,
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    atomic_write_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )


def create_exclusive_lock(
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
        raise XR9PreflightError(
            "one-shot preflight lock already exists: "
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


def json_storage_snapshot(
    storage_root: Path,
) -> set[str]:
    result: set[str] = set()

    for relative_root in (
        Path("exchange/input/x_post_feedback"),
        Path("exchange/archive/x_post_feedback"),
        Path("exchange/logs"),
    ):
        search_root = storage_root / relative_root

        if not search_root.exists():
            continue

        for path in search_root.rglob("*.json"):
            if path.is_file():
                result.add(
                    str(path.relative_to(storage_root))
                )

    return result


def build_diff_preview(
    generated_text: str,
) -> str:
    lines = list(
        difflib.unified_diff(
            [],
            generated_text.splitlines(),
            fromfile="EMPTY_NO_EXISTING_X_FB_RECORD",
            tofile="GENERATED_X_DRAFT",
            lineterm="",
        )
    )

    return "\n".join(lines) + "\n"


def sqlite_read_only_url(path: Path) -> str:
    encoded = quote(
        str(path.resolve()),
        safe="/",
    )

    return (
        "sqlite:///file:"
        f"{encoded}"
        "?mode=ro&uri=true"
    )


def build_no_candidate_result(
    *,
    output_root: Path,
    database_scope: str,
    source_database_path: Path,
    database_sha256: str,
) -> dict[str, Any]:
    result = {
        "phase": "X-R9",
        "status": (
            "PASS_READ_ONLY_NO_ELIGIBLE_"
            "CANDIDATE_NO_LOCK"
        ),
        "database_scope": database_scope,
        "source_database_path": str(
            source_database_path
        ),
        "candidate_count": 0,
        "approval_pack_created": False,
        "diff_preview_created": False,
        "one_shot_lock_created": False,
        "approval_state": CURRENT_APPROVAL_STATE,
        "approval_label_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
        "source_database_sha256_before": (
            database_sha256
        ),
        "source_database_sha256_after": (
            database_sha256
        ),
        "source_database_unchanged": True,
    }

    atomic_write_json(
        output_root / "x_r9_result.json",
        result,
    )

    return result


def run_x_r9(
    *,
    source_database_path: Path,
    wordpress_base_url: str,
    output_root: Path,
    lock_root: Path,
    x_fb_storage_root: Path = ROOT,
    approval_request_id: str | None = None,
    database_scope: str = "READ_ONLY_DATABASE",
) -> dict[str, Any]:
    source_database_path = (
        source_database_path.resolve()
    )
    output_root = output_root.resolve()
    lock_root = lock_root.resolve()
    x_fb_storage_root = (
        x_fb_storage_root.resolve()
    )

    require(
        source_database_path.is_file(),
        "source database is missing: "
        f"{source_database_path}",
    )

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            "output_root must be empty: "
            f"{output_root}",
        )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized_base_url = (
        normalize_wordpress_base_url(
            wordpress_base_url
        )
    )

    database_sha_before = sha256_file(
        source_database_path
    )
    x_fb_snapshot_before = (
        json_storage_snapshot(
            x_fb_storage_root
        )
    )

    engine = create_engine(
        sqlite_read_only_url(
            source_database_path
        ),
        connect_args={
            "check_same_thread": False,
        },
    )

    try:
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            read_service = (
                WorkflowApprovedXDraftReadService(
                    session,
                    wordpress_base_url=(
                        normalized_base_url
                    ),
                )
            )

            candidate_ids = (
                read_service
                .find_latest_candidate_ids(
                    limit=10
                )
            )

            selected_id = approval_request_id

            if selected_id is None:
                if not candidate_ids:
                    database_sha_after = sha256_file(
                        source_database_path
                    )

                    require(
                        database_sha_before
                        == database_sha_after,
                        "source database changed",
                    )

                    return build_no_candidate_result(
                        output_root=output_root,
                        database_scope=database_scope,
                        source_database_path=(
                            source_database_path
                        ),
                        database_sha256=(
                            database_sha_after
                        ),
                    )

                selected_id = candidate_ids[0]

            read_result = (
                read_service.read_and_adapt(
                    selected_id
                )
            )

            require(
                not session.new,
                "read-only session has new objects",
            )
            require(
                not session.dirty,
                "read-only session has dirty objects",
            )
            require(
                not session.deleted,
                "read-only session has deleted objects",
            )

    finally:
        engine.dispose()

    registration = (
        XDraftFeedbackRegistrationService()
        .dry_run_register(
            (
                read_result
                .adapter_result
                .x_draft_input
            ),
            storage_root=x_fb_storage_root,
        )
    )

    normalized_record = (
        registration.normalized_record
    )
    feedback_id = registration.feedback_id
    generated_text = registration.generated_text

    require(
        registration.status
        == "PASS_DRY_RUN_NO_WRITE",
        "X-FB preflight must remain dry-run",
    )
    require(
        not Path(
            registration.current_record_path
        ).exists(),
        "current.json already exists",
    )
    require(
        not Path(
            registration.operation_result_path
        ).exists(),
        "operation result already exists",
    )
    require(
        "#PR" in generated_text,
        "generated text must contain #PR",
    )
    require(
        len(generated_text) <= 280,
        "generated text exceeds 280 characters",
    )

    pack_path = (
        output_root
        / "x_r9_preflight_approval_pack.json"
    )
    preview_path = (
        output_root
        / "x_r9_generated_text_preview.diff"
    )
    result_path = (
        output_root / "x_r9_result.json"
    )
    lock_path = (
        lock_root / f"{feedback_id}.lock.json"
    )

    generated_at = (
        datetime.now(timezone.utc).isoformat()
    )

    pack_payload = {
        "phase": "X-R9",
        "status": (
            "READY_FOR_EXPLICIT_APPROVAL_"
            "NO_EXECUTION"
        ),
        "generated_at": generated_at,
        "database_scope": database_scope,
        "source_database_path": str(
            source_database_path
        ),
        "approval_request_id": (
            read_result
            .read_model
            .approval_request_id
        ),
        "source_approval_type": (
            read_result.source_approval_type
        ),
        "mapped_approval_scope": (
            read_result.mapped_approval_scope
        ),
        "feedback_id": feedback_id,
        "wordpress_post_id": (
            read_result
            .adapter_result
            .x_draft_input
            .wordpress_draft_id
        ),
        "article_url": (
            read_result
            .adapter_result
            .x_draft_input
            .article_url
        ),
        "generated_text": generated_text,
        "character_count": (
            registration.character_count
        ),
        "contains_pr": registration.contains_pr,
        "record_version_preview": (
            normalized_record["record_version"]
        ),
        "record_stage_preview": (
            normalized_record["record_stage"]
        ),
        "review_status_preview": (
            normalized_record["review_status"]
        ),
        "existing_current_record": False,
        "diff_base": "EMPTY_NO_EXISTING_RECORD",
        "required_approval_label": (
            REQUIRED_APPROVAL_LABEL
        ),
        "approval_state": (
            CURRENT_APPROVAL_STATE
        ),
        "approval_label_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "one_shot_lock": {
            "path": str(lock_path),
            "state": "PREPARED_NOT_EXECUTABLE",
            "consumed": False,
            "execution_allowed": False,
        },
        "safety": {
            "database_write": False,
            "workflow_write": False,
            "wordpress_write": False,
            "x_api_call": False,
            "x_post": False,
            "external_api_call": False,
            "production_status": "NO_GO",
            "safety_state": "DRY_RUN_ONLY",
        },
    }

    pack_digest = canonical_digest(
        pack_payload
    )

    approval_pack = {
        **pack_payload,
        "approval_pack_digest_sha256": (
            pack_digest
        ),
    }

    lock_payload = {
        "phase": "X-R9",
        "lock_type": (
            "X_FB_ONE_SHOT_PREFLIGHT_LOCK"
        ),
        "feedback_id": feedback_id,
        "approval_request_id": (
            read_result
            .read_model
            .approval_request_id
        ),
        "approval_pack_path": str(pack_path),
        "approval_pack_digest_sha256": (
            pack_digest
        ),
        "lock_state": (
            "PREPARED_NOT_EXECUTABLE"
        ),
        "approval_state": (
            CURRENT_APPROVAL_STATE
        ),
        "required_approval_label": (
            REQUIRED_APPROVAL_LABEL
        ),
        "approval_label_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "created_at": generated_at,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
    }

    lock_created = False

    try:
        create_exclusive_lock(
            lock_path,
            lock_payload,
        )
        lock_created = True

        atomic_write_text(
            preview_path,
            build_diff_preview(
                generated_text
            ),
        )
        atomic_write_json(
            pack_path,
            approval_pack,
        )

        database_sha_after = sha256_file(
            source_database_path
        )

        require(
            database_sha_before
            == database_sha_after,
            "source database changed",
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
            "phase": "X-R9",
            "status": (
                "PASS_PREFLIGHT_APPROVAL_"
                "PACK_LOCKED_NO_EXECUTION"
            ),
            "database_scope": database_scope,
            "source_database_path": str(
                source_database_path
            ),
            "candidate_count": len(
                candidate_ids
            ),
            "approval_request_id": (
                read_result
                .read_model
                .approval_request_id
            ),
            "feedback_id": feedback_id,
            "approval_pack_path": str(
                pack_path
            ),
            "diff_preview_path": str(
                preview_path
            ),
            "one_shot_lock_path": str(
                lock_path
            ),
            "approval_pack_digest_sha256": (
                pack_digest
            ),
            "required_approval_label": (
                REQUIRED_APPROVAL_LABEL
            ),
            "approval_state": (
                CURRENT_APPROVAL_STATE
            ),
            "approval_label_consumed": False,
            "execution_allowed": False,
            "normal_x_fb_write_allowed": False,
            "approval_pack_created": True,
            "diff_preview_created": True,
            "one_shot_lock_created": True,
            "current_record_written": False,
            "operation_result_written": False,
            "database_read": True,
            "database_write": False,
            "workflow_write": False,
            "wordpress_write": False,
            "x_api_call": False,
            "x_post": False,
            "external_api_call": False,
            "normal_x_fb_storage_modified": False,
            "source_database_sha256_before": (
                database_sha_before
            ),
            "source_database_sha256_after": (
                database_sha_after
            ),
            "source_database_unchanged": True,
            "production_status": "NO_GO",
            "safety_state": "DRY_RUN_ONLY",
        }

        atomic_write_json(
            result_path,
            result,
        )

        return result

    except Exception:
        if lock_created:
            lock_path.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-db",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--wordpress-base-url",
        required=True,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--lock-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--x-fb-storage-root",
        type=Path,
        default=ROOT,
    )
    parser.add_argument(
        "--approval-request-id",
    )
    parser.add_argument(
        "--database-scope",
        default="READ_ONLY_DATABASE",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_x_r9(
            source_database_path=args.source_db,
            wordpress_base_url=(
                args.wordpress_base_url
            ),
            output_root=args.output_root,
            lock_root=args.lock_root,
            x_fb_storage_root=(
                args.x_fb_storage_root
            ),
            approval_request_id=(
                args.approval_request_id
            ),
            database_scope=(
                args.database_scope
            ),
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": "X-R9",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
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
