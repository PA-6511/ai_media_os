from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from app.services.x_r15_wordpress_cover_update import (
    X15WordPressCoverPartialFailure,
    X15WordPressCoverUpdateResult,
    execute_x_r15_wordpress_cover_update_once,
)


X_R15_EBOOK_ITEM_ID = (
    "e2029b2f-f44a-462f-abc8-86c4bc74b818"
)

X_R15_SOURCE_ITEM_ID = "4310000887411"
X_R15_WORDPRESS_POST_ID = 201

X_R15_AUTHORIZATION_SCOPE = (
    "X_R15_POST_201_COVER_MEDIA_UPLOAD_"
    "AND_DRAFT_UPDATE_ONLY"
)


class X15WordPressCoverRunnerError(RuntimeError):
    pass


def _require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise X15WordPressCoverRunnerError(message)


def _load_authorization(
    path: Path,
) -> dict[str, Any]:
    _require(
        path.is_file(),
        "execution authorization is missing",
    )
    _require(
        not path.is_symlink(),
        "execution authorization must not be a symlink",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise X15WordPressCoverRunnerError(
            "execution authorization is invalid"
        ) from exc

    _require(
        isinstance(value, dict),
        "execution authorization must be an object",
    )

    required = {
        "authorization_status": "APPROVED",
        "authorization_scope": (
            X_R15_AUTHORIZATION_SCOPE
        ),
        "ebook_item_id": X_R15_EBOOK_ITEM_ID,
        "source_item_id": X_R15_SOURCE_ITEM_ID,
        "wordpress_post_id": X_R15_WORDPRESS_POST_ID,
        "execution_allowed": True,
        "wordpress_media_upload_allowed": True,
        "wordpress_draft_update_allowed": True,
        "publish_allowed": False,
        "schedule_allowed": False,
        "x_post_allowed": False,
        "one_shot": True,
        "production_status": "NO_GO",
    }

    for key, expected in required.items():
        _require(
            value.get(key) == expected,
            f"execution authorization mismatch: {key}",
        )

    authorization_id = value.get(
        "authorization_id"
    )

    _require(
        isinstance(authorization_id, str)
        and bool(authorization_id.strip()),
        "authorization_id is required",
    )

    return value


def _transition_path(
    path: Path,
    state: str,
) -> Path:
    suffix = path.suffix

    _require(
        suffix == ".json",
        "execution authorization must use .json",
    )

    return path.with_name(
        path.stem + f".{state}.json"
    )


def _atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    try:
        os.fchmod(descriptor, 0o600)

        with os.fdopen(descriptor, "wb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())

    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass

        raise


def _build_failure_evidence(
    exc: Exception,
) -> dict[str, Any]:
    if isinstance(
        exc,
        X15WordPressCoverPartialFailure,
    ):
        return {
            "failure_stage": exc.failure_stage,
            "error_type": type(exc).__name__,
            "original_error_type": (
                exc.original_error_type
            ),
            "media_upload_completed": True,
            "media_id": exc.media_id,
            "media_url": exc.media_url,
            "image_sha256": exc.image_sha256,
            "wordpress_post_id": (
                X_R15_WORDPRESS_POST_ID
            ),
            "wordpress_post_update_confirmed": (
                False
            ),
            "orphan_media_possible": True,
            "manual_reconciliation_required": True,
            "retry_blocked_until_reconciled": True,
            "publish_executed": False,
            "production_status": "NO_GO",
        }

    return {
        "failure_stage": (
            "BEFORE_MEDIA_UPLOAD_OR_UNKNOWN"
        ),
        "error_type": type(exc).__name__,
        "media_upload_completed": "UNKNOWN",
        "wordpress_post_id": (
            X_R15_WORDPRESS_POST_ID
        ),
        "wordpress_post_update_confirmed": False,
        "manual_reconciliation_required": True,
        "retry_blocked_until_reconciled": True,
        "publish_executed": False,
        "production_status": "NO_GO",
    }


def _persist_failed_authorization(
    *,
    claimed_path: Path,
    failed_path: Path,
    exc: Exception,
) -> None:
    authorization = _load_authorization(
        claimed_path
    )

    authorization["authorization_status"] = (
        "FAILED"
    )
    authorization["authorization_consumed"] = True
    authorization["execution_completed"] = False
    authorization["failed_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    authorization["failure_evidence"] = (
        _build_failure_evidence(exc)
    )
    authorization["production_status"] = "NO_GO"

    _atomic_create_json(
        failed_path,
        authorization,
    )

    claimed_path.unlink()


def execute_authorized_x15_cover_update_once(
    *,
    execution_authorization_path: Path,
    item: Any,
    offer: Any,
    client: Any,
    executor: Callable[..., X15WordPressCoverUpdateResult] = (
        execute_x_r15_wordpress_cover_update_once
    ),
) -> X15WordPressCoverUpdateResult:
    _load_authorization(
        execution_authorization_path
    )

    claimed_path = _transition_path(
        execution_authorization_path,
        "claimed",
    )

    consumed_path = _transition_path(
        execution_authorization_path,
        "consumed",
    )

    failed_path = _transition_path(
        execution_authorization_path,
        "failed",
    )

    for path in (
        claimed_path,
        consumed_path,
        failed_path,
    ):
        _require(
            not path.exists(),
            (
                "authorization transition artifact "
                f"already exists: {path}"
            ),
        )

    execution_authorization_path.rename(
        claimed_path
    )

    try:
        result = executor(
            item=item,
            offer=offer,
            client=client,
        )

        _require(
            result.post_id
            == X_R15_WORDPRESS_POST_ID,
            "executor returned the wrong post ID",
        )

        _require(
            result.post_status == "draft",
            "executor did not preserve draft status",
        )

        _require(
            result.featured_media_set is True,
            "executor did not set featured media",
        )

        _require(
            result.content_updated is True,
            "executor did not update content",
        )

        _require(
            result.publish_executed is False,
            "executor unexpectedly published the post",
        )

    except Exception as exc:
        if claimed_path.exists():
            _persist_failed_authorization(
                claimed_path=claimed_path,
                failed_path=failed_path,
                exc=exc,
            )

        raise

    claimed_path.rename(consumed_path)

    return result


def run_production_once(
    *,
    execution_authorization_path: Path,
) -> X15WordPressCoverUpdateResult:
    from sqlalchemy import select

    from app.db.models.ebook import (
        EbookItem,
        StoreOffer,
    )
    from app.db.session import SessionLocal
    from app.integrations.wordpress_rest_client import (
        WordPressRestClient,
    )

    base_url = (
        os.environ.get("WORDPRESS_BASE_URL")
        or os.environ.get("WP_BASE_URL")
        or ""
    )

    username = (
        os.environ.get("WORDPRESS_USERNAME")
        or os.environ.get("WP_USERNAME")
        or ""
    )

    application_password = (
        os.environ.get(
            "WORDPRESS_APPLICATION_PASSWORD"
        )
        or os.environ.get(
            "WP_APPLICATION_PASSWORD"
        )
        or ""
    )

    session = SessionLocal()

    try:
        item = session.get(
            EbookItem,
            X_R15_EBOOK_ITEM_ID,
        )

        if item is None:
            raise X15WordPressCoverRunnerError(
                "X-R15 ebook item was not found"
            )

        offer = session.scalar(
            select(StoreOffer).where(
                StoreOffer.ebook_item_id
                == X_R15_EBOOK_ITEM_ID,
                StoreOffer.store_name.in_(
                    [
                        "RAKUTEN_KOBO",
                        "rakuten_kobo",
                    ]
                ),
            )
        )

        if offer is None:
            raise X15WordPressCoverRunnerError(
                "Rakuten Kobo offer was not found"
            )

        client = WordPressRestClient(
            base_url=base_url,
            username=username,
            application_password=(
                application_password
            ),
        )

        return (
            execute_authorized_x15_cover_update_once(
                execution_authorization_path=(
                    execution_authorization_path
                ),
                item=item,
                offer=offer,
                client=client,
            )
        )

    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload the approved X-R15 cover and "
            "update WordPress draft 201 exactly once."
        )
    )

    parser.add_argument(
        "--execution-authorization",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_args()

    result = run_production_once(
        execution_authorization_path=(
            arguments.execution_authorization
        )
    )

    print(
        json.dumps(
            asdict(result),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
