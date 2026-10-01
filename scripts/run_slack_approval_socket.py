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
from app.services.kobo_sale_package_slack_service import (  # noqa: E402
    ACTION_IDS as KOBO_SALE_PACKAGE_ACTION_IDS,
    KoboSalePackageSlackError,
    KoboSalePackageSlackService,
)
from app.services.slack_sale_approval_message_service import (  # noqa: E402
    ACTION_IDS as SALE_CAMPAIGN_ACTION_IDS,
)
from app.services.slack_sale_approval_socket_service import (  # noqa: E402
    SlackSaleApprovalSocketError,
    SlackSaleApprovalSocketService,
)
from app.services.x_post_draft_slack_preset_service import (  # noqa: E402
    X_POST_DRAFT_OPEN_ACTION_ID,
    X_POST_DRAFT_VIEW_CALLBACK_ID,
    SlackXPostDraftPresetError,
    XPostDraftSlackPresetService,
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

    DATE_BLOCK_ID_FALLBACK = (
        "x_post_draft_schedule_date"
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

    def handle_kobo_sale_package_action(
        ack: Any,
        body: dict[str, Any],
        client: Any,
        logger: logging.Logger,
    ) -> None:
        ack()

        interaction = None

        try:
            interaction = (
                parse_slack_approval_interaction(
                    body
                )
            )

            result = (
                KoboSalePackageSlackService(
                    config
                ).process_interaction(
                    interaction
                )
            )

            client.chat_update(
                channel=interaction.channel_id,
                ts=interaction.message_ts,
                text=result.update_payload["text"],
                blocks=result.update_payload["blocks"],
                unfurl_links=False,
                unfurl_media=False,
            )

            safe_ephemeral(
                client=client,
                channel_id=interaction.channel_id,
                user_id=interaction.user_id,
                text=result.ephemeral_text,
                logger=logger,
            )

            logger.info(
                "Kobo sale Slack decision applied: "
                "approval_id=%s decision=%s",
                result.approval_id,
                result.decision,
            )

        except KoboSalePackageSlackError as exc:
            logger.warning(
                "Kobo sale Slack action rejected: "
                "code=%s",
                exc.code,
            )

            if interaction is not None:
                safe_ephemeral(
                    client=client,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user_id,
                    text=(
                        "Koboセール承認を実行"
                        "できませんでした。"
                        f" エラーコード: {exc.code}"
                    ),
                    logger=logger,
                )

        except Exception:
            logger.exception(
                "Unexpected Kobo sale Slack failure"
            )

            if interaction is not None:
                safe_ephemeral(
                    client=client,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user_id,
                    text=(
                        "Koboセール承認処理中に"
                        "予期しないエラーが発生しました。"
                    ),
                    logger=logger,
                )

    def handle_sale_campaign_action(
        ack: Any,
        body: dict[str, Any],
        client: Any,
        logger: logging.Logger,
    ) -> None:
        ack()
        interaction = None
        try:
            interaction = parse_slack_approval_interaction(body)
            with SessionLocal() as session:
                result = SlackSaleApprovalSocketService(
                    session,
                    config,
                ).process_interaction(interaction)

            if result.dry_run:
                safe_ephemeral(
                    client=client,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user_id,
                    text=(
                        "DRY_RUNのためSale Campaign承認内容を"
                        "検証しましたが、DBは変更していません。"
                    ),
                    logger=logger,
                )
                return

            payload = result.update_payload
            if payload is None:
                raise SlackSaleApprovalSocketError(
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
                "Sale campaign Slack decision handled: "
                "request_id=%s decision=%s status=%s",
                result.request_id,
                result.decision,
                result.status,
            )
        except SlackSaleApprovalSocketError as exc:
            logger.warning(
                "Sale campaign Slack action rejected: code=%s",
                exc.code,
            )
            if interaction is not None:
                safe_ephemeral(
                    client=client,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user_id,
                    text=(
                        "Sale Campaign承認を実行できませんでした。"
                        f" エラーコード: {exc.code}"
                    ),
                    logger=logger,
                )
        except Exception:
            logger.exception("Unexpected Sale campaign Slack failure")
            if interaction is not None:
                safe_ephemeral(
                    client=client,
                    channel_id=interaction.channel_id,
                    user_id=interaction.user_id,
                    text=(
                        "Sale Campaign承認処理中に"
                        "予期しないエラーが発生しました。"
                    ),
                    logger=logger,
                )

    def handle_x_post_draft_open(
        ack: Any,
        body: dict[str, Any],
        client: Any,
        logger: logging.Logger,
    ) -> None:
        ack()

        try:
            with SessionLocal() as session:
                trigger_id, view = (
                    XPostDraftSlackPresetService(
                        session,
                        config,
                    ).build_open_view(
                        body
                    )
                )

            client.views_open(
                trigger_id=trigger_id,
                view=view,
            )

        except SlackXPostDraftPresetError as exc:
            logger.warning(
                "X draft preset open rejected: code=%s",
                exc.code,
            )

            user = body.get("user", {})
            channel = body.get(
                "channel",
                {},
            )

            user_id = str(
                user.get("id", "")
                if isinstance(user, dict)
                else ""
            )

            channel_id = str(
                channel.get("id", "")
                if isinstance(channel, dict)
                else ""
            )

            if user_id and channel_id:
                safe_ephemeral(
                    client=client,
                    channel_id=channel_id,
                    user_id=user_id,
                    text=(
                        "X下書き設定を開けませんでした。"
                        f" エラーコード: {exc.code}"
                    ),
                    logger=logger,
                )

        except Exception:
            logger.exception(
                "Unexpected X draft preset open failure"
            )

    def handle_x_post_draft_submission(
        ack: Any,
        body: dict[str, Any],
        client: Any,
        logger: logging.Logger,
    ) -> None:
        try:
            with SessionLocal() as session:
                result = (
                    XPostDraftSlackPresetService(
                        session,
                        config,
                    ).apply_submission(
                        body
                    )
                )

                if config.mode == "LIVE":
                    session.commit()
                else:
                    session.rollback()

            ack()

            if config.mode == "DRY_RUN":
                user = body.get(
                    "user",
                    {},
                )

                user_id = str(
                    user.get("id", "")
                    if isinstance(
                        user,
                        dict,
                    )
                    else ""
                )

                if user_id:
                    safe_ephemeral(
                        client=client,
                        channel_id=(
                            result.channel_id
                        ),
                        user_id=user_id,
                        text=(
                            "DRY_RUNのためX下書き設定を"
                            "検証しましたが、DBは変更して"
                            "いません。"
                        ),
                        logger=logger,
                    )

                logger.info(
                    "X draft preset DRY_RUN passed: "
                    "draft_id=%s scheduled_at=%s "
                    "paid_partnership=%s",
                    result.draft_id,
                    (
                        result.scheduled_at.isoformat()
                        if result.scheduled_at
                        else "NONE"
                    ),
                    result.paid_partnership,
                )
                return

            client.chat_update(
                channel=result.channel_id,
                ts=result.message_ts,
                text=result.update_payload["text"],
                blocks=result.update_payload["blocks"],
                unfurl_links=False,
                unfurl_media=False,
            )

            logger.info(
                "X draft preset saved: "
                "draft_id=%s scheduled_at=%s "
                "paid_partnership=%s",
                result.draft_id,
                (
                    result.scheduled_at.isoformat()
                    if result.scheduled_at
                    else "NONE"
                ),
                result.paid_partnership,
            )

        except SlackXPostDraftPresetError as exc:
            logger.warning(
                "X draft preset submission rejected: "
                "code=%s",
                exc.code,
            )

            if exc.field_errors:
                ack(
                    response_action="errors",
                    errors=exc.field_errors,
                )
            else:
                ack(
                    response_action="errors",
                    errors={
                        DATE_BLOCK_ID_FALLBACK: (
                            "設定を保存できませんでした。"
                            f" ({exc.code})"
                        )
                    },
                )

        except Exception:
            logger.exception(
                "Unexpected X draft preset "
                "submission failure"
            )

            ack(
                response_action="errors",
                errors={
                    DATE_BLOCK_ID_FALLBACK: (
                        "設定保存中に"
                        "エラーが発生しました。"
                    )
                },
            )

    for action_id in ACTION_IDS:
        app.action(action_id)(
            handle_approval_action
        )

    for action_id in KOBO_SALE_PACKAGE_ACTION_IDS:
        app.action(action_id)(
            handle_kobo_sale_package_action
        )

    for action_id in SALE_CAMPAIGN_ACTION_IDS:
        app.action(action_id)(
            handle_sale_campaign_action
        )

    app.action(
        X_POST_DRAFT_OPEN_ACTION_ID
    )(
        handle_x_post_draft_open
    )

    view_registrar = getattr(
        app,
        "view",
        None,
    )

    if callable(view_registrar):
        view_registrar(
            X_POST_DRAFT_VIEW_CALLBACK_ID
        )(
            handle_x_post_draft_submission
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
