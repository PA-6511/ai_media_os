from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.ebook_autonomy.command_center import (
    load_latest_autonomy_summary,
)
from app.services.xnr_roundup_content import (
    _x_weighted_length,
)


ROOT = Path("/home/deploy/ai_media_os")

TOKYO = ZoneInfo("Asia/Tokyo")

X_POST_ENDPOINT = (
    "https://api.x.com/2/tweets"
)

X_MAX_WEIGHTED_LENGTH = 280

POSTED_EVIDENCE_ROOT = (
    ROOT
    / "exchange/evidence/"
    "ebook_autonomy/x_posts"
)

DRY_RUN_EVIDENCE_ROOT = (
    ROOT
    / "exchange/evidence/"
    "ebook_autonomy/x_publisher_dry_run"
)

MANUAL_APPROVED_ROOT = (
    ROOT
    / "exchange/approved/x_posts"
)

REQUIRED_CREDENTIALS = (
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
)


class XPublisherError(RuntimeError):
    pass


class XPublisherPreSendError(
    XPublisherError
):
    """Failure known to occur before POST /2/tweets."""


# X_PUBLIC_ARTICLE_LIVE_GATE_V1
def verify_public_article_url(
    article_url: str,
) -> dict[str, object]:
    import requests

    try:
        response = requests.get(
            article_url,
            headers={
                "User-Agent":
                    "AI-Media-OS-X-Publisher/1.0",
                "Accept":
                    "text/html,application/xhtml+xml",
            },
            timeout=15,
            allow_redirects=True,
        )

    except requests.RequestException as exc:
        raise XPublisherPreSendError(
            "ARTICLE_PUBLIC_CHECK_NETWORK_ERROR:"
            + type(exc).__name__
        ) from exc

    final_url = str(
        response.url
        or ""
    ).strip()

    status = int(
        response.status_code
    )

    if status != 200:
        raise XPublisherPreSendError(
            "ARTICLE_PUBLIC_HTTP_NOT_200:"
            + str(status)
        )

    if not final_url.startswith(
        "https://"
    ):
        raise XPublisherPreSendError(
            "ARTICLE_PUBLIC_FINAL_URL_INVALID"
        )

    if (
        "/wp-admin/" in final_url.lower()
        or "{ARTICLE_URL}" in final_url
    ):
        raise XPublisherPreSendError(
            "ARTICLE_PUBLIC_FINAL_URL_UNSAFE"
        )

    return {
        "status_code": status,
        "requested_url":
            article_url,
        "final_url":
            final_url,
        "publicly_reachable":
            True,
    }


@dataclass(frozen=True)
class XPostPlan:
    run_id: str
    article_url: str
    draft_path: str
    # X_PUBLISHER_DUAL_DIGEST_V1
    #
    # source_draft_sha256:
    #   exact on-disk draft bytes/text
    #
    # draft_sha256:
    #   canonical text actually sent to X
    source_draft_sha256: str
    draft_sha256: str
    weighted_length: int
    text: str
    already_posted: bool
    existing_post_id: str
    manual_post_evidence: str


def now_jst() -> datetime:
    return datetime.now(TOKYO)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def _atomic_json_write(
    target: Path,
    payload: dict[str, Any],
) -> None:
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temp_name = tempfile.mkstemp(
        prefix="."
        + target.name
        + ".",
        suffix=".tmp",
        dir=str(target.parent),
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(
                handle.fileno()
            )

        Path(temp_name).replace(
            target
        )

    finally:
        Path(temp_name).unlink(
            missing_ok=True
        )


def _load_json(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {}

    return (
        value
        if isinstance(value, dict)
        else {}
    )


def _posted_evidence_path(
    draft_sha256: str,
) -> Path:
    return (
        POSTED_EVIDENCE_ROOT
        / f"{draft_sha256}.json"
    )


def _existing_post_id(
    draft_sha256: str,
) -> str:
    path = _posted_evidence_path(
        draft_sha256
    )

    if not path.is_file():
        return ""

    payload = _load_json(path)

    if (
        payload.get("status")
        != "POSTED"
    ):
        return ""

    return str(
        payload.get("x_post_id")
        or ""
    ).strip()


def _find_manual_post_evidence(
    *draft_sha256s: str,
) -> str:
    if not MANUAL_APPROVED_ROOT.is_dir():
        return ""

    candidates = {
        str(value).strip()
        for value in draft_sha256s
        if str(value).strip()
    }

    if not candidates:
        return ""

    digest_keys = (
        "x_draft_text_sha256",
        "source_draft_sha256",
        "draft_sha256",
        "x_draft_sha256",
    )

    for path in sorted(
        MANUAL_APPROVED_ROOT.glob(
            "*.json"
        )
    ):
        payload = _load_json(path)

        posting_status = str(
            payload.get(
                "posting_status"
            )
            or ""
        ).strip()

        if not posting_status.startswith(
            "POSTED"
        ):
            continue

        for key in digest_keys:
            digest = str(
                payload.get(key)
                or ""
            ).strip()

            if digest in candidates:
                return str(path)

    return ""


# X_DAILY_CONTEXT_OVERRIDE_V2
def _load_x_publisher_summary():
    """
    Use the current in-progress Daily Cycle context when
    supplied by x_publish.

    Otherwise preserve the existing latest-evidence behavior.
    """

    import json
    import os

    raw = str(
        os.environ.get(
            "EBOOK_AUTONOMY_X_CONTEXT_JSON",
            "",
        )
        or ""
    ).strip()

    if not raw:
        return load_latest_autonomy_summary()

    try:
        payload = json.loads(
            raw
        )

    except Exception as exc:
        raise XPublisherError(
            "CURRENT_X_CONTEXT_INVALID:"
            + type(exc).__name__
        ) from exc

    if not isinstance(
        payload,
        dict,
    ):
        raise XPublisherError(
            "CURRENT_X_CONTEXT_INVALID_TYPE"
        )

    return payload


def prepare_current_xnr_post() -> XPostPlan:
    summary = (
        _load_x_publisher_summary()
    )

    if not summary.get("available"):
        raise XPublisherError(
            "AUTONOMY_SUMMARY_UNAVAILABLE"
        )

    new_release = (
        summary.get("new_release")
        or {}
    )

    if (
        str(
            new_release.get("status")
            or ""
        )
        != "PASS"
    ):
        raise XPublisherError(
            "NEW_RELEASE_NOT_PASS"
        )

    if (
        str(
            new_release.get(
                "wordpress_status"
            )
            or ""
        ).lower()
        != "publish"
    ):
        raise XPublisherError(
            "WORDPRESS_NOT_PUBLISHED"
        )

    if (
        str(
            new_release.get(
                "x_article_url_state"
            )
            or ""
        )
        != "WORDPRESS_PERMALINK"
    ):
        raise XPublisherError(
            "ARTICLE_URL_NOT_FINALIZED"
        )

    article_url = str(
        new_release.get(
            "x_article_url"
        )
        or ""
    ).strip()

    if not article_url.startswith(
        "https://"
    ):
        raise XPublisherError(
            "ARTICLE_URL_INVALID"
        )

    if (
        "{ARTICLE_URL}" in article_url
        or "/wp-admin/" in (
            article_url.lower()
        )
    ):
        raise XPublisherError(
            "ARTICLE_URL_UNSAFE"
        )

    draft_path = Path(
        str(
            new_release.get(
                "x_draft_path"
            )
            or ""
        )
    )

    if not draft_path.is_file():
        raise XPublisherError(
            "X_DRAFT_NOT_FOUND"
        )

    source_text = draft_path.read_text(
        encoding="utf-8"
    )

    source_draft_sha256 = (
        _sha256_text(
            source_text
        )
    )

    # Network payload canonicalization:
    # discard only terminal CR/LF characters.
    text = source_text.rstrip(
        "\r\n"
    )

    if not text.strip():
        raise XPublisherError(
            "X_DRAFT_EMPTY"
        )

    if "{ARTICLE_URL}" in text:
        raise XPublisherError(
            "ARTICLE_URL_PLACEHOLDER_REMAINS"
        )

    if article_url not in text:
        raise XPublisherError(
            "ARTICLE_URL_MISMATCH"
        )

    weighted_length = (
        _x_weighted_length(
            text
        )
    )

    if (
        weighted_length
        > X_MAX_WEIGHTED_LENGTH
    ):
        raise XPublisherError(
            "X_WEIGHTED_LENGTH_OVER_280"
        )

    draft_sha256 = _sha256_text(
        text
    )

    existing_post_id = (
        _existing_post_id(
            draft_sha256
        )
    )

    manual_evidence = (
        _find_manual_post_evidence(
            draft_sha256,
            source_draft_sha256,
        )
    )

    return XPostPlan(
        run_id=str(
            summary.get("run_id")
            or ""
        ),
        article_url=article_url,
        draft_path=str(draft_path),
        source_draft_sha256=(
            source_draft_sha256
        ),
        draft_sha256=draft_sha256,
        weighted_length=(
            weighted_length
        ),
        text=text,
        already_posted=bool(
            existing_post_id
        ),
        existing_post_id=(
            existing_post_id
        ),
        manual_post_evidence=(
            manual_evidence
        ),
    )


def _credential_presence() -> dict[str, bool]:
    return {
        key: bool(
            os.environ.get(
                key,
                ""
            ).strip()
        )
        for key
        in REQUIRED_CREDENTIALS
    }


def run_dry_run(
    plan: XPostPlan,
    *,
    experiment_media_intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = now_jst()

    run_id = (
        timestamp.strftime(
            "%Y%m%d_%H%M%S_%f"
        )
    )

    status = "READY_FOR_CREDENTIALS"

    if plan.already_posted:
        status = (
            "SKIPPED_ALREADY_POSTED"
        )

    elif plan.manual_post_evidence:
        status = (
            "SKIPPED_MANUAL_POST_EVIDENCE"
        )

    from app.services.x_analytics_experiment_candidate_service import (
        load_x_analytics_experiment_candidate,
    )
    from app.services.x_analytics_experiment_approval_service import (
        DEFAULT_APPROVED_ROOT,
        load_matching_approval,
    )

    experiment_candidate = (
        load_x_analytics_experiment_candidate()
    )

    experiment_approval = (
        load_matching_approval(
            approved_root=DEFAULT_APPROVED_ROOT,
            candidate=experiment_candidate,
        )
        if experiment_candidate is not None
        else None
    )

    if experiment_approval is None:
        experiment_media_intent = None

    experiment_annotation = {
        "status": (
            "HUMAN_APPROVED_MATCH"
            if experiment_approval is not None
            else (
                "CANDIDATE_AVAILABLE"
                if experiment_candidate is not None
                else "NO_CANDIDATE"
            )
        ),
        "candidate":
            experiment_candidate,
        "approval":
            experiment_approval,
        "media_intent":
            experiment_media_intent,
        "treatment_media_ready": (
            experiment_media_intent is not None
        ),
        "human_approval_verified": (
            experiment_approval is not None
        ),
        "experiment_dry_run_allowed": (
            experiment_approval is not None
        ),
        "annotation_only":
            True,
        "human_review_required": (
            experiment_candidate is not None
        ),
        "execution_allowed":
            False,
        "x_payload_changed":
            False,
        "schedule_changed":
            False,
        "template_changed":
            False,
        "media_changed":
            False,
    }

    payload = {
        "schema":
            "ebook_autonomy_x_publisher_v1",
        "mode": "DRY_RUN",
        "status": status,
        "generated_at":
            timestamp.isoformat(),
        "x_endpoint":
            X_POST_ENDPOINT,
        "network_request_executed":
            False,
        "x_post_executed":
            False,
        "database_write_executed":
            False,
        "experiment_annotation":
            experiment_annotation,
        "plan": asdict(plan),
        "credential_presence":
            _credential_presence(),
        "required_credentials":
            list(
                REQUIRED_CREDENTIALS
            ),
        "live_guard": {
            "requires_mode_live":
                True,
            "requires_confirmation":
                "LIVE_X_POST",
            "requires_environment":
                "X_AUTOPUBLISH_ENABLED=1",
        },
        "request_preview": {
            "method": "POST",
            "url": X_POST_ENDPOINT,
            "json": {
                "text": plan.text,
            },
        },
    }

    target = (
        DRY_RUN_EVIDENCE_ROOT
        / run_id
        / "summary.json"
    )

    _atomic_json_write(
        target,
        payload,
    )

    payload["evidence_path"] = str(
        target
    )

    return payload


def _require_live_unlock(
    confirm: str,
) -> None:
    if confirm != "LIVE_X_POST":
        raise XPublisherError(
            "LIVE_CONFIRMATION_REQUIRED"
        )

    if (
        os.environ.get(
            "X_AUTOPUBLISH_ENABLED",
            "",
        ).strip()
        != "1"
    ):
        raise XPublisherError(
            "X_AUTOPUBLISH_DISABLED"
        )

    missing = [
        key
        for key, present
        in _credential_presence().items()
        if not present
    ]

    if missing:
        raise XPublisherError(
            "X_CREDENTIALS_MISSING:"
            + ",".join(missing)
        )


def publish_live(
    plan: XPostPlan,
    *,
    confirm: str,
    verified_cover_media_intent: dict[str, Any] | None = None,
    experiment_media_intent: dict[str, Any] | None = None,
    experiment_confirm: str = "",
) -> dict[str, Any]:
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

    normal_cover_url = ""

    if (
        verified_cover_media_intent is not None
        and experiment_media_intent is not None
    ):
        raise XPublisherError(
            "MULTIPLE_MEDIA_INTENTS_NOT_ALLOWED"
        )

    if verified_cover_media_intent is not None:
        if (
            verified_cover_media_intent.get(
                "schema"
            )
            != "ebook_autonomy_verified_cover_media_v1"
        ):
            raise XPublisherError(
                "VERIFIED_COVER_MEDIA_SCHEMA_INVALID"
            )

        if (
            verified_cover_media_intent.get(
                "cover_status"
            )
            != "AVAILABLE"
        ):
            raise XPublisherError(
                "VERIFIED_COVER_MEDIA_NOT_AVAILABLE"
            )

        normal_cover_url = str(
            verified_cover_media_intent.get(
                "cover_url"
            )
            or ""
        ).strip()

        if not normal_cover_url.startswith(
            "https://"
        ):
            raise XPublisherError(
                "VERIFIED_COVER_MEDIA_URL_INVALID"
            )

    if experiment_media_intent is not None:
        if (
            experiment_confirm
            != "LIVE_X_EXPERIMENT_TREATMENT"
        ):
            raise XPublisherError(
                "LIVE_X_EXPERIMENT_CONFIRMATION_REQUIRED"
            )

    _require_live_unlock(
        confirm
    )

    # Re-check the actual public article immediately
    # before X delivery.  Do not trust only the older
    # Daily Cycle summary.
    article_preflight = (
        verify_public_article_url(
            plan.article_url
        )
    )

    from requests_oauthlib import (
        OAuth1,
    )
    import requests

    auth = OAuth1(
        os.environ["X_API_KEY"],
        os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"],
        os.environ[
            "X_ACCESS_TOKEN_SECRET"
        ],
    )

    media_upload = None

    x_payload: dict[str, Any] = {
        "text": plan.text,
    }

    if verified_cover_media_intent is not None:
        from app.services.x_analytics_experiment_x_media_upload_service import (
            upload_verified_cover_url,
        )

        media_upload = (
            upload_verified_cover_url(
                normal_cover_url,
                auth=auth,
            )
        )

    elif experiment_media_intent is not None:
        from app.services.x_analytics_experiment_x_media_upload_service import (
            upload_verified_treatment_cover,
        )

        media_upload = (
            upload_verified_treatment_cover(
                experiment_media_intent,
                auth=auth,
            )
        )

    if media_upload is not None:
        x_payload[
            "media"
        ] = {
            "media_ids": [
                media_upload.media_id,
            ],
        }

    response = requests.post(
        X_POST_ENDPOINT,
        auth=auth,
        json=x_payload,
        timeout=30,
    )

    try:
        body = response.json()
    except Exception:
        body = {}

    if response.status_code != 201:
        raise XPublisherError(
            "X_API_POST_FAILED:"
            + str(
                response.status_code
            )
        )

    data = (
        body.get("data")
        if isinstance(body, dict)
        else {}
    )

    if not isinstance(data, dict):
        data = {}

    x_post_id = str(
        data.get("id")
        or ""
    ).strip()

    if not x_post_id:
        raise XPublisherError(
            "X_API_POST_ID_MISSING"
        )

    timestamp = now_jst()

    evidence = {
        "schema":
            "ebook_autonomy_x_post_v1",
        "status": "POSTED",
        "posted_at":
            timestamp.isoformat(),
        "x_post_id":
            x_post_id,
        "x_post_url":
            (
                "https://x.com/i/web/status/"
                + x_post_id
            ),
        "source_draft_sha256":
            plan.source_draft_sha256,
        "draft_sha256":
            plan.draft_sha256,
        "weighted_length":
            plan.weighted_length,
        "article_url":
            plan.article_url,
        "article_public_preflight":
            article_preflight,
        "draft_path":
            plan.draft_path,
        "source_run_id":
            plan.run_id,
        "experiment_id": (
            str(
                experiment_media_intent.get(
                    "experiment_id"
                )
                or ""
            )
            if experiment_media_intent
            is not None
            else ""
        ),
        "variant_role": (
            "TREATMENT"
            if experiment_media_intent
            is not None
            else ""
        ),
        "media_id": (
            media_upload.media_id
            if media_upload is not None
            else ""
        ),
        "media_source_url": (
            media_upload.source_url
            if media_upload is not None
            else ""
        ),
        "media_upload_executed": (
            media_upload is not None
        ),
        "x_post_executed":
            True,
        "database_write_executed":
            False,
    }

    target = _posted_evidence_path(
        plan.draft_sha256
    )

    _atomic_json_write(
        target,
        evidence,
    )

    evidence["evidence_path"] = str(
        target
    )

    return evidence
