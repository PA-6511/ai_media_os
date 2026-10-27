from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from app.db.repositories.amazon_x_tracking_id_pool_repository import (
    AmazonXTrackingIdPoolError,
    AmazonXTrackingIdPoolRepository,
    validate_controlled_tracking_id,
)


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "ERROR=INPUT_INVALID\n")


def _reject_shared_tracking_id(
    tracking_id: str,
) -> None:
    validate_controlled_tracking_id(
        tracking_id
    )


@dataclass(frozen=True)
class RegistrationResult:
    tracking_id: str
    status: str
    created: bool


def register_tracking_id(
    *,
    session: Any,
    tracking_id: str,
) -> RegistrationResult:
    """Commit registration or roll back on failure; caller owns session close.

    Use a dedicated session: commit/rollback affects its entire transaction.
    Input validation does not touch the session.
    Exceptions propagate to callers, which must sanitize any external output.
    The returned Tracking ID is sensitive and must not be logged unmasked.
    """
    _reject_shared_tracking_id(
        tracking_id
    )

    try:
        repo = AmazonXTrackingIdPoolRepository(
            session
        )
        row, created = repo.register_available(
            tracking_id=tracking_id
        )
        result = RegistrationResult(
            tracking_id=row.tracking_id,
            status=row.status,
            created=created,
        )
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise


def main() -> int:
    parser = _SafeArgumentParser(
        description=(
            "Register an already-existing Amazon "
            "Associates Tracking ID into the local "
            "X attribution pool."
        )
    )

    parser.add_argument(
        "--tracking-id",
        required=True,
        help=(
            "Existing Amazon Associates Tracking ID. "
            "This command does not create IDs on Amazon."
        ),
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Persist registration. Without this flag "
            "the command validates only."
        ),
    )

    args = parser.parse_args()

    tracking_id = str(
        args.tracking_id or ""
    ).strip()

    try:
        normalized = validate_controlled_tracking_id(
            tracking_id
        )
    except AmazonXTrackingIdPoolError:
        print("ERROR=INPUT_INVALID", file=sys.stderr)
        return 2

    if not args.execute:
        print(
            "VALIDATION=PASS"
        )
        print(
            "TRACKING_ID=",
            "[REDACTED]",
        )
        print(
            "DB_OPENED=NO"
        )
        print(
            "DB_WRITE=NO"
        )
        return 0

    try:
        from app.db.session import SessionLocal

        with SessionLocal() as session:
            result = register_tracking_id(
                session=session,
                tracking_id=normalized,
            )
    except Exception:
        print("ERROR=REGISTRATION_FAILED", file=sys.stderr)
        return 1

    print(
        "REGISTRATION=PASS"
    )
    print(
        "TRACKING_ID=",
        "[REDACTED]",
    )
    print(
        "STATUS=",
        result.status,
    )
    print(
        "CREATED=",
        "YES" if result.created else "NO",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
