from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


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

from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
)
from app.services.workflow_approved_x_draft_read_service import (
    WorkflowApprovedXDraftReadService,
    normalize_wordpress_base_url,
)
from app.services.x_draft_feedback_registration_service import (
    XDraftFeedbackRegistrationService,
)


ROOT = REPOSITORY_ROOT

SCHEMA_RELATIVE_PATH = Path(
    "config/x_post_wording_feedback_schema.json"
)
POLICY_RELATIVE_PATH = Path(
    "config/x_fb_manual_operation_policy.json"
)
VALIDATOR_RELATIVE_PATH = Path(
    "scripts/build_x_fb_0.py"
)


class XR7IsolatedE2EError(RuntimeError):
    """Raised when X-R7 isolated E2E validation fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR7IsolatedE2EError(message)


def sha256_file(path: Path) -> str:
    require(
        path.is_file(),
        f"file is missing: {path}",
    )

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def sqlite_backup_read_only(
    source_path: Path,
    destination_path: Path,
) -> None:
    """
    Creates a consistent SQLite backup without opening the
    production database in write mode.
    """

    require(
        source_path.is_file(),
        f"source database is missing: {source_path}",
    )
    require(
        not destination_path.exists(),
        (
            "destination database already exists: "
            f"{destination_path}"
        ),
    )

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded_path = quote(
        str(source_path.resolve()),
        safe="/",
    )
    source_uri = (
        f"file:{encoded_path}?mode=ro"
    )

    source_connection = sqlite3.connect(
        source_uri,
        uri=True,
    )
    destination_connection = sqlite3.connect(
        str(destination_path)
    )

    try:
        source_connection.backup(
            destination_connection
        )
    finally:
        destination_connection.close()
        source_connection.close()


def prepare_isolated_x_fb_root(
    *,
    isolated_root: Path,
    repository_root: Path,
) -> None:
    (isolated_root / "config").mkdir(
        parents=True,
        exist_ok=True,
    )
    (isolated_root / "scripts").mkdir(
        parents=True,
        exist_ok=True,
    )
    (
        isolated_root
        / "exchange/input/x_post_feedback"
    ).mkdir(
        parents=True,
        exist_ok=True,
    )
    (
        isolated_root
        / "exchange/archive/x_post_feedback"
    ).mkdir(
        parents=True,
        exist_ok=True,
    )
    (
        isolated_root
        / "exchange/logs"
    ).mkdir(
        parents=True,
        exist_ok=True,
    )

    for relative_path in (
        SCHEMA_RELATIVE_PATH,
        POLICY_RELATIVE_PATH,
        VALIDATOR_RELATIVE_PATH,
    ):
        source = (
            repository_root / relative_path
        )
        destination = (
            isolated_root / relative_path
        )

        require(
            source.is_file(),
            f"required source file missing: {source}",
        )

        shutil.copy2(
            source,
            destination,
        )


def file_snapshot(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )


def seed_isolated_candidate(
    copied_database_path: Path,
) -> dict[str, Any]:
    """
    Writes one synthetic eligible record to the isolated DB copy.

    No production database connection is used here.
    """

    token = uuid.uuid4().hex
    approval_id = f"approval-x-r7-{token}"
    source_item_id = f"x-r7-item-{token}"

    wordpress_post_id = (
        70_000_000
        + int(token[:8], 16)
        % 20_000_000
    )

    now = datetime.now(timezone.utc)

    engine = create_engine(
        f"sqlite:///{copied_database_path}"
    )

    try:
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            item = EbookItem(
                source_name=(
                    "x-r7-isolated-e2e"
                ),
                source_item_id=source_item_id,
                title=(
                    "X-R7 隔離DB "
                    "End-to-End確認作品"
                ),
                normalized_title=(
                    "X-R7 隔離DB "
                    "End-to-End確認作品"
                ),
                volume_label="第1巻",
                author_name="山田 太郎",
                publisher_name="X-R7テスト出版社",
                release_date=date(2026, 7, 17),
                item_type="tankobon",
                is_excluded=False,
                workflow_status="READY",
                wordpress_status="DRAFT",
                wordpress_post_id=(
                    wordpress_post_id
                ),
                review_status="APPROVED",
            )

            session.add(item)
            session.flush()

            approval = WorkflowApprovalRequest(
                id=approval_id,
                ebook_item_id=item.id,
                approval_type="REVIEW_READY",
                expected_current_status="REVIEW",
                requested_status="READY",
                status="APPROVED",
                request_nonce_hash=(
                    hashlib.sha256(
                        approval_id.encode(
                            "utf-8"
                        )
                    ).hexdigest()
                ),
                requested_by="x-r7-isolated-e2e",
                requested_at=(
                    now - timedelta(hours=2)
                ),
                expires_at=(
                    now + timedelta(days=1)
                ),
                decided_by="human-reviewer",
                decided_at=(
                    now - timedelta(hours=1)
                ),
                decision_note=(
                    "Synthetic isolated X-R7 "
                    "E2E candidate"
                ),
            )

            session.add(approval)

            # Isolated copied database only.
            session.commit()

            ebook_item_id = item.id

    finally:
        engine.dispose()

    return {
        "approval_request_id": approval_id,
        "ebook_item_database_id": (
            ebook_item_id
        ),
        "source_item_id": source_item_id,
        "wordpress_post_id": (
            wordpress_post_id
        ),
    }


def find_normal_x_fb_matches(
    *,
    repository_root: Path,
    feedback_id: str,
) -> list[str]:
    matches: list[str] = []

    for relative_root in (
        Path("exchange/input/x_post_feedback"),
        Path("exchange/archive/x_post_feedback"),
        Path("exchange/logs"),
    ):
        search_root = (
            repository_root / relative_root
        )

        if not search_root.exists():
            continue

        for path in search_root.rglob("*"):
            if feedback_id in str(path):
                matches.append(str(path))

    return sorted(matches)


def run_x_r7(
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
        normalized_wordpress_base_url = (
            normalize_wordpress_base_url(
                wordpress_base_url
            )
        )
    except Exception as exc:
        raise XR7IsolatedE2EError(
            "wordpress_base_url validation "
            f"failed: {exc}"
        ) from exc

    copied_database_path = (
        run_root
        / "database"
        / "ebook_affiliate_x_r7.db"
    )
    isolated_x_fb_root = (
        run_root / "x_fb_root"
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
            "isolated database did not change "
            "after candidate seed"
        ),
    )

    prepare_isolated_x_fb_root(
        isolated_root=isolated_x_fb_root,
        repository_root=repository_root,
    )

    x_fb_files_before = file_snapshot(
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
                        normalized_wordpress_base_url
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
                    "seeded approval was not returned "
                    "as an eligible candidate"
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

    current_path = Path(
        registration.current_record_path
    )
    operation_result_path = Path(
        registration.operation_result_path
    )

    require(
        not current_path.exists(),
        (
            "X-R7 unexpectedly created "
            "current.json"
        ),
    )
    require(
        not operation_result_path.exists(),
        (
            "X-R7 unexpectedly created "
            "operation result JSON"
        ),
    )

    x_fb_files_after = file_snapshot(
        isolated_x_fb_root
    )

    require(
        x_fb_files_before == x_fb_files_after,
        (
            "isolated X-FB storage changed "
            "during dry-run"
        ),
    )

    normal_matches = (
        find_normal_x_fb_matches(
            repository_root=repository_root,
            feedback_id=(
                registration.feedback_id
            ),
        )
    )

    require(
        not normal_matches,
        (
            "normal X-FB storage contains "
            f"X-R7 files: {normal_matches}"
        ),
    )

    source_sha_after = sha256_file(
        source_database_path
    )

    require(
        source_sha_before == source_sha_after,
        "production source database changed",
    )

    normalized_record = (
        registration.normalized_record
    )

    summary = {
        "phase": "X-R7",
        "status": (
            "PASS_ISOLATED_DATABASE_E2E_DRY_RUN"
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
        "database_mode": (
            "PRODUCTION_RO_BACKUP_"
            "ISOLATED_SEED_"
            "ISOLATED_RO_E2E"
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
        "registration_status": (
            registration.status
        ),
        "source_approval_type": (
            read_result.source_approval_type
        ),
        "mapped_approval_scope": (
            read_result.mapped_approval_scope
        ),
        "article_url_source": (
            read_result.article_url_source
        ),
        "feedback_id": (
            registration.feedback_id
        ),
        "record_version": (
            normalized_record[
                "record_version"
            ]
        ),
        "record_stage": (
            normalized_record[
                "record_stage"
            ]
        ),
        "review_status": (
            normalized_record[
                "review_status"
            ]
        ),
        "character_count": (
            registration.character_count
        ),
        "contains_pr": (
            registration.contains_pr
        ),
        "source_database_sha256_before": (
            source_sha_before
        ),
        "source_database_sha256_after": (
            source_sha_after
        ),
        "source_database_unchanged": True,
        "isolated_database_seed_write": True,
        "isolated_database_read_only_e2e": True,
        "current_record_written": False,
        "operation_result_written": False,
        "isolated_x_fb_storage_modified": False,
        "normal_x_fb_storage_modified": False,
        "database_read": True,
        "production_database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "external_api_call": False,
        "production_status": "NO_GO",
        "safety_state": "DRY_RUN_ONLY",
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
        summary = run_x_r7(
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
                    "phase": "X-R7",
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
            summary,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
