from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


from app.services.slack_live_copy_guard import (  # noqa: E402
    SlackLiveCopyGuardError,
    validate_slack_live_copy_environment,
)


REPO_ROOT = Path(
    "/home/deploy/ai_media_os"
)

PRODUCTION_DATABASE_PATH = (
    REPO_ROOT
    / "data/database/ebook_affiliate.db"
)

COPY_DATABASE_PATH = Path(
    "/tmp/ebook_affiliate_slack_5f.db"
)

EXPECTED_DATABASE_URL = (
    "sqlite:////tmp/ebook_affiliate_slack_5f.db"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the 5F Slack LIVE-equivalent "
            "worker against an isolated copy DB."
        )
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--check-config",
        action="store_true",
    )

    group.add_argument(
        "--start",
        action="store_true",
    )

    return parser.parse_args()


def validate_environment():
    return validate_slack_live_copy_environment(
        os.environ,
        expected_database_url=(
            EXPECTED_DATABASE_URL
        ),
        expected_database_path=(
            COPY_DATABASE_PATH
        ),
        production_database_path=(
            PRODUCTION_DATABASE_PATH
        ),
    )


def main() -> int:
    args = parse_args()

    try:
        config = validate_environment()
    except SlackLiveCopyGuardError as exc:
        print(
            f"SLACK_5F_GUARD: FAIL ({exc})",
            file=sys.stderr,
        )
        return 2

    print("SLACK_5F_LIVE_COPY_GUARD: PASS")
    print("DATABASE_TARGET: COPY_ONLY")
    print("MODE: LIVE")
    print("PRODUCTION_DATABASE_ALLOWED: FALSE")

    if args.check_config:
        print("SOCKET_CONNECTION_STARTED: FALSE")
        return 0

    # ガード通過後に初めてDB Sessionと
    # Socket Workerを読み込む。
    from scripts import (  # noqa: WPS433
        run_slack_approval_socket as runner,
    )

    original_argv = list(sys.argv)

    try:
        sys.argv = [
            original_argv[0],
            "--start",
        ]

        return runner.main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
