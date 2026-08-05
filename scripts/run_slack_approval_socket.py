from __future__ import annotations

import argparse
from collections.abc import Callable
import logging
import os
from pathlib import Path
import signal
import sys
from typing import Any


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


from app.db.session import SessionLocal  # noqa: E402
from app.services.slack_approval_socket_service import (  # noqa: E402
    SlackApprovalSocketConfig,
    SlackApprovalSocketError,
    SlackApprovalSocketService,
    parse_slack_approval_interaction,
)


ACTION_IDS = (
    "ebook_approval_approve",
    "ebook_approval_reject",
    "ebook_approval_hold",
)

SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE = (
    "SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE"
)


class SlackBoltDependencyNotAvailable(RuntimeError):
    """Raised without leaking import context when the runtime is incomplete."""


def load_slack_runtime() -> tuple[Callable[..., Any], Callable[..., Any]]:
    """Load Slack Bolt only when worker construction is explicitly requested."""

    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        raise SlackBoltDependencyNotAvailable(
            SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE
        ) from None
    return App, SocketModeHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the electronic-book Slack "
            "approval Socket Mode worker."
        )
    )

    group = parser.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--check-config",
        action="store_true",
        help=(
            "Validate environment configuration "
            "without connecting to Slack."
        ),
    )

    group.add_argument(
        "--start",
        action="store_true",
        help="Start the Socket Mode worker.",
    )

    return parser.parse_args()


def load_config() -> SlackApprovalSocketConfig:
    return SlackApprovalSocketConfig.from_mapping(
        os.environ
    )


def print_config_status(
    config: SlackApprovalSocketConfig,
) -> None:
    print("SLACK_SOCKET_CONFIG: PASS")
    print(f"MODE: {config.mode}")
    print("BOT_TOKEN: SET")
    print("APP_TOKEN: SET")
    print("TEAM_ID: SET")
    print("CHANNEL_ID: SET")
    print(
        "APPROVER_COUNT: "
        f"{len(config.approver_user_ids)}"
    )
    print(
        "DATABASE_WRITES: "
        + (
            "ENABLED"
            if config.mode == "LIVE"
            else "DISABLED"
        )
    )


def safe_ephemeral(
    *,
    client: Any,
    channel_id: str,
    user_id: str,
    text: str,
    logger: logging.Logger,
) -> None:
    try:
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=text,
        )
    except Exception:
        logger.exception(
            "Failed to post safe ephemeral response"
        )


def build_app(
    config: SlackApprovalSocketConfig,
    *,
    app_factory: Callable[..., Any] | None = None,
) -> Any:
    if app_factory is None:
        app_factory, _ = load_slack_runtime()

    app = app_factory(
        token=config.bot_token,
    )

    def handle_approval_action(
        ack: Any,
        body: dict[str, Any],
        client: Any,
        logger: logging.Logger,
    ) -> None:
        # Slackへ最初に受付確認を返す。
        ack()

        interaction = None

        try:
            interaction = (
                parse_slack_approval_interaction(body)
            )

            with SessionLocal() as session:
                result = SlackApprovalSocketService(
                    session,
                    config,
                ).process_interaction(
                    interaction
                )

            if result.dry_run:
                safe_ephemeral(
                    client=client,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user_id,
                    text=(
                        "DRY_RUNのため承認内容を"
                        "検証しましたが、DBは変更して"
                        "いません。"
                    ),
                    logger=logger,
                )

                logger.info(
                    "Slack approval DRY_RUN passed: "
                    "request_id=%s decision=%s",
                    result.request_id,
                    result.decision,
                )
                return

            payload = result.update_payload

            if payload is None:
                raise SlackApprovalSocketError(
                    "missing_update_payload",
                    "Slack update payload is missing.",
                )

            client.chat_update(
                channel=interaction.channel_id,
                ts=interaction.message_ts,
                text=payload["text"],
                blocks=payload["blocks"],
                unfurl_links=False,
                unfurl_media=False,
            )

            logger.info(
                "Slack approval applied: "
                "request_id=%s decision=%s "
                "workflow=%s->%s",
                result.request_id,
                result.decision,
                result.before_workflow_status,
                result.after_workflow_status,
            )

        except SlackApprovalSocketError as exc:
            logger.warning(
                "Slack approval rejected: code=%s",
                exc.code,
            )

            if interaction is not None:
                safe_ephemeral(
                    client=client,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user_id,
                    text=(
                        "承認操作を実行できませんでした。"
                        f"エラーコード: {exc.code}"
                    ),
                    logger=logger,
                )

        except Exception:
            logger.exception(
                "Unexpected Slack approval failure"
            )

            if interaction is not None:
                safe_ephemeral(
                    client=client,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user_id,
                    text=(
                        "承認処理中に予期しない"
                        "エラーが発生しました。"
                    ),
                    logger=logger,
                )

    for action_id in ACTION_IDS:
        app.action(action_id)(
            handle_approval_action
        )

    return app


def _raise_worker_stop(
    signum: int,
    frame: object,
) -> None:
    del signum
    del frame
    raise KeyboardInterrupt


class WorkerStopController:
    """Coordinate signal stop and idempotent handler closure."""

    def __init__(self, handler: Any) -> None:
        self.handler = handler
        self.stop_requested = False
        self._closed = False

    def close_once(self) -> None:
        if self._closed:
            return
        self._closed = True
        close = getattr(self.handler, "close", None)
        if callable(close):
            close()

    def request_stop(
        self,
        signum: int,
        frame: object,
    ) -> None:
        del signum
        del frame
        self.stop_requested = True
        self.close_once()
        raise KeyboardInterrupt


def main(
    *,
    handler_factory: Callable[..., Any] | None = None,
) -> int:
    args = parse_args()
    config = load_config()

    if args.check_config:
        print_config_status(config)
        return 0

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "%(name)s %(message)s"
        ),
    )

    logger = logging.getLogger(
        "slack_approval_socket"
    )

    logger.info(
        "Starting Slack approval worker "
        "in mode=%s",
        config.mode,
    )

    try:
        app = build_app(config)
        if handler_factory is None:
            _, handler_factory = load_slack_runtime()
        handler = handler_factory(
            app,
            config.app_token,
        )
    except SlackBoltDependencyNotAvailable:
        print(
            SLACK_BOLT_DEPENDENCY_NOT_AVAILABLE,
            file=sys.stderr,
        )
        return 3

    stop_controller = WorkerStopController(handler)

    previous_sigterm_handler = (
        signal.getsignal(signal.SIGTERM)
    )

    signal.signal(
        signal.SIGTERM,
        stop_controller.request_stop,
    )

    try:
        handler.start()
    except KeyboardInterrupt:
        logger.info(
            "Slack approval worker stopped "
            "by operator or service manager"
        )
        return 0
    finally:
        stop_controller.close_once()
        signal.signal(
            signal.SIGTERM,
            previous_sigterm_handler,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
