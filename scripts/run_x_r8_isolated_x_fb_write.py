from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(REPOSITORY_ROOT),
    )


from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scripts.run_x_r7_isolated_e2e_dry_run import (
    find_normal_x_fb_matches,
    prepare_isolated_x_fb_root,
    seed_isolated_candidate,
    sha256_file,
    sqlite_backup_read_only,
)
from app.services.workflow_approved_x_draft_read_service import (
    WorkflowApprovedXDraftReadService,
    normalize_wordpress_base_url,
)
from app.services.x_draft_feedback_registration_service import (
    XDraftFeedbackRegistrationService,
)


ROOT = REPOSITORY_ROOT
MANAGER_PATH = (
    ROOT / "scripts/manage_x_feedback_record.py"
)


class XR8IsolatedWriteError(RuntimeError):
    """Raised when X-R8 isolated X-FB write fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR8IsolatedWriteError(message)


def load_json_object(path: Path) -> dict[str, Any]:
    require(
        path.is_file(),
        f"required JSON missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise XR8IsolatedWriteError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
    )

    return value


def json_file_snapshot(root: Path) -> set[str]:
    if not root.exists():
        return set()

    return {
        str(path.relative_to(root))
        for path in root.rglob("*.json")
        if path.is_file()
    }


def run_feedback_manager(
    *,
    request_path: Path,
    isolated_root: Path,
    dry_run: bool,
) -> tuple[
    int,
    dict[str, Any],
    str,
    str,
]:
    require(
        MANAGER_PATH.is_file(),
        f"manager script missing: {MANAGER_PATH}",
    )

    command = [
        sys.executable,
        str(MANAGER_PATH),
        "--request",
        str(request_path),
    ]

    if dry_run:
        command.append("--dry-run")

    environment = os.environ.copy()
    environment["AI_MEDIA_OS_ROOT"] = str(
        isolated_root
    )

    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    # Successful operations emit JSON to stdout.
    # Validation failures may emit JSON to stderr.
    payload_text = (
        stdout
        if stdout
        else stderr
    )

    require(
        bool(payload_text),
        (
            "feedback manager returned no JSON "
            f"output: returncode={completed.returncode}"
        ),
    )

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise XR8IsolatedWriteError(
            "feedback manager output is not JSON: "
            f"returncode={completed.returncode}, "
            f"stdout={stdout!r}, "
            f"stderr={stderr!r}"
        ) from exc

    require(
        isinstance(payload, dict),
        (
            "feedback manager result "
            "must be an object"
        ),
    )

    return (
        completed.returncode,
        payload,
        payload_text,
        stderr,
    )


def validate_execution_boundary(
    boundary: dict[str, Any],
) -> None:
    require(
        boundary.get("x_api_call_allowed")
        is False,
        "x_api_call_allowed must be false",
    )
    require(
        boundary.get("x_post_allowed")
        is False,
        "x_post_allowed must be false",
    )
    require(
        boundary.get("wordpress_write_allowed")
        is False,
        (
            "wordpress_write_allowed "
            "must be false"
        ),
    )
    require(
        boundary.get("external_api_call_allowed")
        is False,
        (
            "external_api_call_allowed "
            "must be false"
        ),
    )
    require(
        boundary.get(
            "automatic_rule_update_allowed"
        )
        is False,
        (
            "automatic_rule_update_allowed "
            "must be false"
        ),
    )
    require(
        boundary.get("production_status")
        == "NO_GO",
        "production_status must be NO_GO",
    )


def run_x_r8(
    *,
    source_database_path: Path,
    run_root: Path,
    wordpress_base_url: str,
    evidence_path: Path,
    repository_root: Path = ROOT,
) -> dict[str, Any]:
    source_database_path = (
        source_database_path.resolve()
    )
    run_root = run_root.resolve()
    evidence_path = evidence_path.resolve()
    repository_root = repository_root.resolve()

    require(
        source_database_path.is_file(),
        (
            "source database is missing: "
            f"{source_database_path}"
        ),
    )

    if run_root.exists():
        require(
            not any(run_root.iterdir()),
            (
                "run_root must be empty: "
                f"{run_root}"
            ),
        )

    run_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        normalized_base_url = (
            normalize_wordpress_base_url(
                wordpress_base_url
            )
        )
    except Exception as exc:
        raise XR8IsolatedWriteError(
            "wordpress_base_url validation "
            f"failed: {exc}"
        ) from exc

    copied_database_path = (
        run_root
        / "database"
        / "ebook_affiliate_x_r8.db"
    )
    isolated_x_fb_root = (
        run_root / "x_fb_root"
    )
    request_path = (
        run_root
        / "x_r8_initialize_request.json"
    )
    dry_run_log_path = (
        run_root
        / "x_r8_manager_dry_run.json"
    )
    write_log_path = (
        run_root
        / "x_r8_manager_write.json"
    )
    duplicate_log_path = (
        run_root
        / "x_r8_duplicate_rejection.json"
    )

    source_sha_before = sha256_file(
        source_database_path
    )

    sqlite_backup_read_only(
        source_database_path,
        copied_database_path,
    )

    copied_sha_before_seed = sha256_file(
        copied_database_path
    )

    seed = seed_isolated_candidate(
        copied_database_path
    )

    copied_sha_after_seed = sha256_file(
        copied_database_path
    )

    require(
        copied_sha_before_seed
        != copied_sha_after_seed,
        (
            "isolated database did not "
            "change after seed"
        ),
    )

    prepare_isolated_x_fb_root(
        isolated_root=isolated_x_fb_root,
        repository_root=repository_root,
    )

    json_files_before = json_file_snapshot(
        isolated_x_fb_root
    )

    database_url = (
        "sqlite:///file:"
        f"{copied_database_path}"
        "?mode=ro&uri=true"
    )

    read_engine = create_engine(
        database_url,
        connect_args={
            "check_same_thread": False,
        },
    )

    try:
        with Session(
            read_engine,
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
                    limit=100
                )
            )

            require(
                seed["approval_request_id"]
                in candidate_ids,
                (
                    "seeded approval was not "
                    "detected as eligible"
                ),
            )

            read_result = (
                read_service.read_and_adapt(
                    seed["approval_request_id"]
                )
            )

            require(
                not session.new,
                (
                    "read-only session has "
                    "new objects"
                ),
            )
            require(
                not session.dirty,
                (
                    "read-only session has "
                    "dirty objects"
                ),
            )
            require(
                not session.deleted,
                (
                    "read-only session has "
                    "deleted objects"
                ),
            )

    finally:
        read_engine.dispose()

    copied_sha_after_read = sha256_file(
        copied_database_path
    )

    require(
        copied_sha_after_seed
        == copied_sha_after_read,
        (
            "isolated database changed "
            "during read-only processing"
        ),
    )

    registration = (
        XDraftFeedbackRegistrationService()
        .dry_run_register(
            (
                read_result
                .adapter_result
                .x_draft_input
            ),
            storage_root=isolated_x_fb_root,
        )
    )

    request_path.write_text(
        json.dumps(
            registration.initialize_request,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    current_path = Path(
        registration.current_record_path
    )
    operation_result_path = Path(
        registration.operation_result_path
    )

    require(
        not current_path.exists(),
        (
            "current.json existed before "
            "X-R8 write"
        ),
    )
    require(
        not operation_result_path.exists(),
        (
            "operation result existed before "
            "X-R8 write"
        ),
    )

    (
        dry_run_rc,
        dry_run_result,
        dry_run_stdout,
        dry_run_stderr,
    ) = run_feedback_manager(
        request_path=request_path,
        isolated_root=isolated_x_fb_root,
        dry_run=True,
    )

    dry_run_log_path.write_text(
        dry_run_stdout + "\n",
        encoding="utf-8",
    )

    require(
        dry_run_rc == 0,
        (
            "manager dry-run failed: "
            f"{dry_run_stderr}"
        ),
    )
    require(
        dry_run_result.get("status")
        == "PASS_DRY_RUN_NO_WRITE",
        (
            "unexpected manager dry-run "
            f"status: {dry_run_result}"
        ),
    )
    require(
        dry_run_result.get(
            "current_record_written"
        )
        is False,
        (
            "manager dry-run reported "
            "current record write"
        ),
    )
    require(
        not current_path.exists(),
        (
            "manager dry-run created "
            "current.json"
        ),
    )
    require(
        not operation_result_path.exists(),
        (
            "manager dry-run created "
            "operation result"
        ),
    )

    (
        write_rc,
        write_result,
        write_stdout,
        write_stderr,
    ) = run_feedback_manager(
        request_path=request_path,
        isolated_root=isolated_x_fb_root,
        dry_run=False,
    )

    write_log_path.write_text(
        write_stdout + "\n",
        encoding="utf-8",
    )

    require(
        write_rc == 0,
        (
            "manager write failed: "
            f"{write_stderr}"
        ),
    )
    require(
        write_result.get("status")
        == "PASS_MANUAL_RECORD_OPERATION",
        (
            "unexpected manager write "
            f"status: {write_result}"
        ),
    )
    require(
        write_result.get(
            "current_record_written"
        )
        is True,
        (
            "manager did not report "
            "current record write"
        ),
    )
    require(
        current_path.is_file(),
        "current.json was not created",
    )
    require(
        operation_result_path.is_file(),
        (
            "operation result JSON "
            "was not created"
        ),
    )

    current = load_json_object(
        current_path
    )
    operation_result = load_json_object(
        operation_result_path
    )

    feedback_id = registration.feedback_id
    generated_text = (
        current
        .get("text_snapshots", {})
        .get("generated_text")
    )

    require(
        current.get("feedback_id")
        == feedback_id,
        "current feedback_id mismatch",
    )
    require(
        current.get("record_version") == 1,
        (
            "current record_version "
            "must be 1"
        ),
    )
    require(
        current.get("record_stage")
        == "DRAFT_GENERATED",
        (
            "current record_stage "
            "must be DRAFT_GENERATED"
        ),
    )
    require(
        current.get("review_status")
        == "UNREVIEWED",
        (
            "current review_status "
            "must be UNREVIEWED"
        ),
    )
    require(
        generated_text
        == registration.generated_text,
        "generated text mismatch",
    )
    require(
        isinstance(generated_text, str)
        and "#PR" in generated_text,
        "generated text must contain #PR",
    )
    require(
        len(generated_text) <= 280,
        (
            "generated text exceeds "
            "280 characters"
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
    require(
        operation_result.get(
            "current_record_written"
        )
        is True,
        (
            "stored operation result "
            "write flag mismatch"
        ),
    )

    execution_boundary = current.get(
        "execution_boundary"
    )

    require(
        isinstance(execution_boundary, dict),
        (
            "current execution_boundary "
            "must be an object"
        ),
    )

    validate_execution_boundary(
        execution_boundary
    )

    archive_directory = (
        isolated_x_fb_root
        / "exchange/archive/x_post_feedback"
        / feedback_id
    )

    archive_files = (
        sorted(
            archive_directory.glob("*.json")
        )
        if archive_directory.exists()
        else []
    )

    require(
        not archive_files,
        (
            "INITIALIZE unexpectedly "
            f"created archive: {archive_files}"
        ),
    )

    current_sha_before_duplicate = (
        sha256_file(current_path)
    )

    (
        duplicate_rc,
        duplicate_result,
        duplicate_stdout,
        duplicate_stderr,
    ) = run_feedback_manager(
        request_path=request_path,
        isolated_root=isolated_x_fb_root,
        dry_run=False,
    )

    duplicate_log_path.write_text(
        duplicate_stdout + "\n",
        encoding="utf-8",
    )

    require(
        duplicate_rc != 0,
        (
            "duplicate INITIALIZE "
            "was accepted"
        ),
    )
    require(
        duplicate_result.get("status")
        == "FAIL_VALIDATION",
        (
            "unexpected duplicate "
            f"status: {duplicate_result}"
        ),
    )
    require(
        duplicate_result.get("error")
        == (
            "INITIALIZE is forbidden "
            "because current record exists"
        ),
        (
            "unexpected duplicate "
            "rejection reason"
        ),
    )

    current_sha_after_duplicate = (
        sha256_file(current_path)
    )

    require(
        current_sha_before_duplicate
        == current_sha_after_duplicate,
        (
            "current.json changed after "
            "duplicate rejection"
        ),
    )

    json_files_after = json_file_snapshot(
        isolated_x_fb_root
    )

    added_json_files = (
        json_files_after
        - json_files_before
    )

    expected_added_json_files = {
        str(
            current_path.relative_to(
                isolated_x_fb_root
            )
        ),
        str(
            operation_result_path.relative_to(
                isolated_x_fb_root
            )
        ),
    }

    require(
        added_json_files
        == expected_added_json_files,
        (
            "unexpected isolated JSON files: "
            f"{sorted(added_json_files)}"
        ),
    )

    normal_matches = (
        find_normal_x_fb_matches(
            repository_root=repository_root,
            feedback_id=feedback_id,
        )
    )

    require(
        not normal_matches,
        (
            "normal X-FB storage modified: "
            f"{normal_matches}"
        ),
    )

    copied_sha_after_write = sha256_file(
        copied_database_path
    )

    require(
        copied_sha_after_seed
        == copied_sha_after_write,
        (
            "isolated database changed "
            "during X-FB write"
        ),
    )

    source_sha_after = sha256_file(
        source_database_path
    )

    require(
        source_sha_before
        == source_sha_after,
        "production source DB changed",
    )

    summary = {
        "phase": "X-R8",
        "status": (
            "PASS_ISOLATED_DATABASE_TO_X_FB_WRITE"
        ),
        "run_root": str(run_root),
        "source_database_path": str(
            source_database_path
        ),
        "copied_database_path": str(
            copied_database_path
        ),
        "isolated_x_fb_root": str(
            isolated_x_fb_root
        ),
        "request_path": str(request_path),
        "current_record_path": str(
            current_path
        ),
        "operation_result_path": str(
            operation_result_path
        ),
        "seeded_approval_request_id": (
            seed["approval_request_id"]
        ),
        "seeded_source_item_id": (
            seed["source_item_id"]
        ),
        "seeded_wordpress_post_id": (
            seed["wordpress_post_id"]
        ),
        "candidate_count": len(
            candidate_ids
        ),
        "seeded_candidate_detected": True,
        "read_service_status": (
            read_result.status
        ),
        "adapter_status": (
            read_result
            .adapter_result
            .status
        ),
        "registration_preflight_status": (
            registration.status
        ),
        "manager_dry_run_status": (
            dry_run_result["status"]
        ),
        "manager_write_status": (
            write_result["status"]
        ),
        "feedback_id": feedback_id,
        "record_version": (
            current["record_version"]
        ),
        "record_stage": (
            current["record_stage"]
        ),
        "review_status": (
            current["review_status"]
        ),
        "character_count": len(
            generated_text
        ),
        "contains_pr": True,
        "current_record_written": True,
        "operation_result_written": True,
        "archive_created": False,
        "duplicate_initialize_rejected": True,
        "duplicate_exit_code": duplicate_rc,
        "duplicate_error": (
            duplicate_result["error"]
        ),
        "current_sha256_before_duplicate": (
            current_sha_before_duplicate
        ),
        "current_sha256_after_duplicate": (
            current_sha_after_duplicate
        ),
        "current_unchanged_after_duplicate": True,
        "source_database_sha256_before": (
            source_sha_before
        ),
        "source_database_sha256_after": (
            source_sha_after
        ),
        "source_database_unchanged": True,
        "isolated_database_seed_write": True,
        "isolated_database_unchanged_after_seed": True,
        "isolated_x_fb_write": True,
        "normal_x_fb_storage_modified": False,
        "production_database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "external_api_call": False,
        "production_status": "NO_GO",
        "safety_state": (
            "MANUAL_RECORDING_ONLY"
        ),
    }

    evidence_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    evidence_path.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-db",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--run-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--wordpress-base-url",
        required=True,
    )
    parser.add_argument(
        "--evidence-path",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_x_r8(
            source_database_path=(
                args.source_db
            ),
            run_root=args.run_root,
            wordpress_base_url=(
                args.wordpress_base_url
            ),
            evidence_path=(
                args.evidence_path
            ),
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": "X-R8",
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "production_database_write": (
                        False
                    ),
                    "workflow_write": False,
                    "wordpress_write": False,
                    "x_api_call": False,
                    "x_post": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            )
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
