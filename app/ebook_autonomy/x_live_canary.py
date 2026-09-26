from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.ebook_autonomy.x_publisher import (
    XPostPlan,
    XPublisherError,
    XPublisherPreSendError,
    _atomic_json_write,
    _require_live_unlock,
    now_jst,
    prepare_current_xnr_post,
    publish_live,
)


ROOT = Path(
    "/home/deploy/ai_media_os"
)

DELIVERY_STATE_ROOT = (
    ROOT
    / "exchange/state/"
    "ebook_autonomy/x_delivery"
)


class XLiveCanaryError(
    RuntimeError
):
    pass


def _state_path(
    plan: XPostPlan,
) -> Path:
    return (
        DELIVERY_STATE_ROOT
        / (
            plan.draft_sha256
            + ".json"
        )
    )


def _load_state(
    path: Path,
) -> dict[str, Any]:
    if not path.is_file():
        return {}

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        raise XLiveCanaryError(
            "DELIVERY_STATE_INVALID:"
            + type(exc).__name__
        ) from exc

    if not isinstance(
        value,
        dict,
    ):
        raise XLiveCanaryError(
            "DELIVERY_STATE_INVALID_TYPE"
        )

    return value


def inspect_delivery_state(
    plan: XPostPlan,
) -> dict[str, Any]:
    path = _state_path(plan)
    state = _load_state(path)

    return {
        "path": str(path),
        "exists": bool(state),
        "status": str(
            state.get("status")
            or ""
        ),
        "x_post_id": str(
            state.get("x_post_id")
            or ""
        ),
    }


def _write_state(
    plan: XPostPlan,
    *,
    status: str,
    extra: dict[str, Any] | None = None,
) -> Path:
    target = _state_path(plan)

    payload: dict[str, Any] = {
        "schema":
            "ebook_autonomy_x_delivery_v1",
        "status":
            status,
        "updated_at":
            now_jst().isoformat(),
        "source_run_id":
            plan.run_id,
        "article_url":
            plan.article_url,
        "draft_path":
            plan.draft_path,
        "source_draft_sha256":
            plan.source_draft_sha256,
        "payload_draft_sha256":
            plan.draft_sha256,
        "weighted_length":
            plan.weighted_length,
    }

    if extra:
        payload.update(extra)

    _atomic_json_write(
        target,
        payload,
    )

    return target


def preflight_live_canary(
    plan: XPostPlan,
) -> dict[str, Any]:
    state_info = (
        inspect_delivery_state(plan)
    )

    status = state_info[
        "status"
    ]

    if status in {
        "POSTING",
        "UNKNOWN_DELIVERY",
    }:
        raise XLiveCanaryError(
            "DELIVERY_RETRY_BLOCKED:"
            + status
        )

    if status == "POSTED":
        return {
            "status":
                "SKIPPED_ALREADY_POSTED",
            "x_post_id":
                state_info[
                    "x_post_id"
                ],
            "delivery_state":
                state_info["path"],
            "x_post_executed":
                False,
        }

    if plan.already_posted:
        return {
            "status":
                "SKIPPED_ALREADY_POSTED",
            "x_post_id":
                plan.existing_post_id,
            "x_post_executed":
                False,
        }

    if plan.manual_post_evidence:
        return {
            "status":
                "SKIPPED_MANUAL_POST_EVIDENCE",
            "manual_post_evidence":
                plan.manual_post_evidence,
            "x_post_executed":
                False,
        }

    return {
        "status":
            "READY_FOR_LIVE_CANARY",
        "delivery_state":
            state_info["path"],
        "x_post_executed":
            False,
    }


def run_live_canary(
    *,
    confirm: str,
) -> dict[str, Any]:
    plan = (
        prepare_current_xnr_post()
    )

    preflight = (
        preflight_live_canary(
            plan
        )
    )

    if (
        preflight["status"]
        != "READY_FOR_LIVE_CANARY"
    ):
        return preflight

    # Validate ALL live locks before
    # creating POSTING state.
    _require_live_unlock(
        confirm
    )

    state_path = _write_state(
        plan,
        status="POSTING",
        extra={
            "started_at":
                now_jst().isoformat(),
            "x_post_executed":
                False,
        },
    )

    try:
        result = publish_live(
            plan,
            confirm=confirm,
        )

    # X_CANARY_PRE_SEND_CLASSIFICATION_V1
    except XPublisherPreSendError as exc:
        # The publisher guarantees this class is raised
        # before POST /2/tweets. Delivery is therefore
        # known NOT to have occurred.
        _write_state(
            plan,
            status="PRE_SEND_BLOCKED",
            extra={
                "failure_type":
                    type(exc).__name__,
                "failure_message":
                    str(exc)[:500],
                "x_post_executed":
                    False,
            },
        )

        raise XLiveCanaryError(
            "X_PRE_SEND_BLOCKED:"
            + str(exc)
        ) from exc

    except BaseException as exc:
        # Once delivery may have begun, fail closed.
        # treat ANY failure as ambiguous delivery.
        #
        # The next automatic attempt MUST NOT post again.
        _write_state(
            plan,
            status="UNKNOWN_DELIVERY",
            extra={
                "failure_type":
                    type(exc).__name__,
                "failure_message":
                    str(exc)[:500],
                "x_post_executed":
                    "UNKNOWN",
            },
        )

        raise XLiveCanaryError(
            "X_DELIVERY_UNKNOWN:"
            + type(exc).__name__
        ) from exc

    status = str(
        result.get("status")
        or ""
    )

    if status == "POSTED":
        x_post_id = str(
            result.get("x_post_id")
            or ""
        ).strip()

        if not x_post_id:
            _write_state(
                plan,
                status="UNKNOWN_DELIVERY",
                extra={
                    "failure_type":
                        "POST_ID_MISSING",
                    "x_post_executed":
                        "UNKNOWN",
                },
            )

            raise XLiveCanaryError(
                "X_DELIVERY_UNKNOWN:"
                "POST_ID_MISSING"
            )

        _write_state(
            plan,
            status="POSTED",
            extra={
                "posted_at":
                    now_jst().isoformat(),
                "x_post_id":
                    x_post_id,
                "x_post_url":
                    str(
                        result.get(
                            "x_post_url"
                        )
                        or ""
                    ),
                "publisher_evidence":
                    str(
                        result.get(
                            "evidence_path"
                        )
                        or ""
                    ),
                "x_post_executed":
                    True,
            },
        )

        output = dict(result)
        output[
            "delivery_state"
        ] = str(state_path)

        return output

    # An unexpected non-POSTED result after
    # entering POSTING is also fail-closed.
    _write_state(
        plan,
        status="UNKNOWN_DELIVERY",
        extra={
            "failure_type":
                "UNEXPECTED_PUBLISH_RESULT",
            "publisher_status":
                status,
            "x_post_executed":
                "UNKNOWN",
        },
    )

    raise XLiveCanaryError(
        "X_DELIVERY_UNKNOWN:"
        "UNEXPECTED_PUBLISH_RESULT"
    )


def current_canary_preflight() -> dict[str, Any]:
    plan = (
        prepare_current_xnr_post()
    )

    result = (
        preflight_live_canary(
            plan
        )
    )

    return {
        "plan": asdict(plan),
        "preflight": result,
    }
