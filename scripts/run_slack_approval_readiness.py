from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


from app.services.slack_readiness_guard import (  # noqa: E402
    SlackReadinessGuardError,
    validate_slack_readiness_environment,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Slack approval readiness "
            "worker against the isolated "
            "readiness database."
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


def main() -> int:
    args = parse_args()

    try:
        config = (
            validate_slack_readiness_environment(
                os.environ
            )
        )
    except SlackReadinessGuardError as exc:
        print(
            f"SLACK_READINESS_GUARD: FAIL ({exc})",
            file=sys.stderr,
        )
        return 2

    print("SLACK_READINESS_GUARD: PASS")
    print("DATABASE_TARGET: READINESS_COPY_ONLY")
    print("MODE: DRY_RUN")
    print("PRODUCTION_DATABASE_ALLOWED: FALSE")
    print(
        "APPROVER_COUNT: "
        f"{len(config.approver_user_ids)}"
    )

    if args.check_config:
        print("SOCKET_CONNECTION_STARTED: FALSE")
        return 0

    # DB接続モジュールはガード通過後にだけimportする。
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
