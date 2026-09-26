from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


X_MEDIA_UPLOAD_BASE = (
    "https://api.x.com/2/media/upload"
)

LOCAL_MAX_IMAGE_BYTES = (
    5 * 1024 * 1024
)

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
}


class XExperimentMediaUploadError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class XExperimentMediaUploadResult:
    media_id: str
    source_url: str
    media_type: str
    byte_count: int
    media_category: str = "tweet_image"
    upload_api: str = "X_API_V2"
    media_upload_executed: bool = True
    x_post_executed: bool = False


def _status_code(
    response: Any,
) -> int:
    try:
        return int(
            response.status_code
        )
    except Exception:
        return 0


def _require_success(
    response: Any,
    *,
    stage: str,
) -> None:
    status = _status_code(
        response
    )

    if not (
        200 <= status < 300
    ):
        raise XExperimentMediaUploadError(
            f"{stage}_HTTP_{status}"
        )


def _json(
    response: Any,
    *,
    stage: str,
) -> Mapping[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:
        raise XExperimentMediaUploadError(
            f"{stage}_JSON_INVALID"
        ) from exc

    if not isinstance(
        payload,
        Mapping,
    ):
        raise XExperimentMediaUploadError(
            f"{stage}_JSON_INVALID"
        )

    return payload


def _media_id_from_payload(
    payload: Mapping[str, Any],
) -> str:
    data = payload.get(
        "data"
    )

    if isinstance(
        data,
        Mapping,
    ):
        for key in (
            "id",
            "media_id",
            "media_id_string",
        ):
            value = str(
                data.get(key)
                or ""
            ).strip()

            if value:
                return value

    for key in (
        "media_id_string",
        "media_id",
        "id",
    ):
        value = str(
            payload.get(key)
            or ""
        ).strip()

        if value:
            return value

    return ""


def validate_treatment_media_intent(
    intent: Mapping[str, Any],
) -> None:
    if (
        intent.get("schema")
        != "x_analytics_experiment_media_intent_v1"
    ):
        raise XExperimentMediaUploadError(
            "MEDIA_INTENT_SCHEMA_INVALID"
        )

    if (
        intent.get("status")
        != "VERIFIED_COVER_READY"
    ):
        raise XExperimentMediaUploadError(
            "VERIFIED_COVER_REQUIRED"
        )

    if (
        intent.get("role")
        != "TREATMENT"
    ):
        raise XExperimentMediaUploadError(
            "TREATMENT_ROLE_REQUIRED"
        )

    if (
        intent.get("cover_status")
        != "AVAILABLE"
    ):
        raise XExperimentMediaUploadError(
            "AVAILABLE_COVER_REQUIRED"
        )

    if (
        intent.get("attachment_intent")
        is not True
    ):
        raise XExperimentMediaUploadError(
            "ATTACHMENT_INTENT_REQUIRED"
        )

    if (
        intent.get(
            "verified_cover_media_available"
        )
        is not True
    ):
        raise XExperimentMediaUploadError(
            "VERIFIED_MEDIA_REQUIRED"
        )

    cover_url = str(
        intent.get("cover_url")
        or ""
    ).strip()

    if not cover_url.startswith(
        "https://"
    ):
        raise XExperimentMediaUploadError(
            "HTTPS_COVER_URL_REQUIRED"
        )

    experiment_id = str(
        intent.get("experiment_id")
        or ""
    ).strip()

    if not experiment_id.startswith(
        "xexp-"
    ):
        raise XExperimentMediaUploadError(
            "EXPERIMENT_ID_REQUIRED"
        )

    for field in (
        "media_upload_executed",
        "execution_allowed",
        "automatic_x_post_allowed",
        "x_post_executed",
    ):
        if intent.get(field) is not False:
            raise XExperimentMediaUploadError(
                field.upper()
                + "_MUST_BE_FALSE_BEFORE_LIVE"
            )


def upload_verified_cover_url(
    cover_url: str,
    *,
    auth: Any,
    transport: Any | None = None,
) -> XExperimentMediaUploadResult:
    if transport is None:
        import requests
        transport = requests

    source_url = str(
        cover_url or ""
    ).strip()

    if not source_url.startswith(
        "https://"
    ):
        raise XExperimentMediaUploadError(
            "HTTPS_COVER_URL_REQUIRED"
        )

    cover_response = transport.get(
        source_url,
        timeout=20,
    )

    _require_success(
        cover_response,
        stage="COVER_DOWNLOAD",
    )

    headers = getattr(
        cover_response,
        "headers",
        {},
    )

    content_type = str(
        (
            headers.get(
                "Content-Type"
            )
            if isinstance(
                headers,
                Mapping,
            )
            else ""
        )
        or ""
    ).split(
        ";",
        1,
    )[0].strip().lower()

    if (
        content_type
        not in SUPPORTED_IMAGE_TYPES
    ):
        raise XExperimentMediaUploadError(
            "COVER_MEDIA_TYPE_UNSUPPORTED:"
            + content_type
        )

    image_bytes = bytes(
        getattr(
            cover_response,
            "content",
            b"",
        )
        or b""
    )

    if not image_bytes:
        raise XExperimentMediaUploadError(
            "COVER_BYTES_EMPTY"
        )

    if (
        len(image_bytes)
        > LOCAL_MAX_IMAGE_BYTES
    ):
        raise XExperimentMediaUploadError(
            "COVER_BYTES_OVER_LOCAL_LIMIT"
        )

    initialize_url = (
        X_MEDIA_UPLOAD_BASE
        + "/initialize"
    )

    initialize_response = (
        transport.post(
            initialize_url,
            auth=auth,
            json={
                "total_bytes":
                    len(image_bytes),
                "media_type":
                    content_type,
                "media_category":
                    "tweet_image",
            },
            timeout=30,
        )
    )

    _require_success(
        initialize_response,
        stage="MEDIA_INITIALIZE",
    )

    initialize_payload = _json(
        initialize_response,
        stage="MEDIA_INITIALIZE",
    )

    media_id = _media_id_from_payload(
        initialize_payload
    )

    if not media_id:
        raise XExperimentMediaUploadError(
            "MEDIA_ID_MISSING_AFTER_INITIALIZE"
        )

    extension = (
        SUPPORTED_IMAGE_TYPES[
            content_type
        ]
    )

    append_url = (
        X_MEDIA_UPLOAD_BASE
        + "/"
        + media_id
        + "/append"
    )

    append_response = (
        transport.post(
            append_url,
            auth=auth,
            data={
                "segment_index":
                    "0",
            },
            files={
                "media": (
                    "cover."
                    + extension,
                    image_bytes,
                    content_type,
                ),
            },
            timeout=30,
        )
    )

    _require_success(
        append_response,
        stage="MEDIA_APPEND",
    )

    finalize_url = (
        X_MEDIA_UPLOAD_BASE
        + "/"
        + media_id
        + "/finalize"
    )

    finalize_response = (
        transport.post(
            finalize_url,
            auth=auth,
            timeout=30,
        )
    )

    _require_success(
        finalize_response,
        stage="MEDIA_FINALIZE",
    )

    finalize_payload = _json(
        finalize_response,
        stage="MEDIA_FINALIZE",
    )

    final_media_id = (
        _media_id_from_payload(
            finalize_payload
        )
        or media_id
    )

    if final_media_id != media_id:
        raise XExperimentMediaUploadError(
            "MEDIA_ID_CHANGED_AFTER_FINALIZE"
        )

    processing = (
        finalize_payload.get(
            "data"
        )
        if isinstance(
            finalize_payload.get(
                "data"
            ),
            Mapping,
        )
        else {}
    )

    if isinstance(
        processing,
        Mapping,
    ):
        info = processing.get(
            "processing_info"
        )

        if isinstance(
            info,
            Mapping,
        ):
            state = str(
                info.get("state")
                or ""
            ).strip().lower()

            if state == "failed":
                raise XExperimentMediaUploadError(
                    "MEDIA_PROCESSING_FAILED"
                )

    return XExperimentMediaUploadResult(
        media_id=media_id,
        source_url=source_url,
        media_type=content_type,
        byte_count=len(
            image_bytes
        ),
    )


def upload_verified_treatment_cover(
    intent: Mapping[str, Any],
    *,
    auth: Any,
    transport: Any | None = None,
) -> XExperimentMediaUploadResult:
    validate_treatment_media_intent(
        intent
    )

    return upload_verified_cover_url(
        str(
            intent["cover_url"]
        ),
        auth=auth,
        transport=transport,
    )
