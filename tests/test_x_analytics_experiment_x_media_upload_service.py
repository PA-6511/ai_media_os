from __future__ import annotations

from dataclasses import replace

import pytest

from app.services.x_analytics_experiment_x_media_upload_service import (
    XExperimentMediaUploadError,
    XExperimentMediaUploadResult,
    upload_verified_treatment_cover,
)


class _Response:
    def __init__(
        self,
        *,
        status_code=200,
        payload=None,
        content=b"",
        headers=None,
    ):
        self.status_code = status_code
        self._payload = (
            payload
            if payload is not None
            else {}
        )
        self.content = content
        self.headers = (
            headers
            if headers is not None
            else {}
        )

    def json(self):
        return self._payload


class _Transport:
    def __init__(self):
        self.calls = []

    def get(
        self,
        url,
        **kwargs,
    ):
        self.calls.append(
            (
                "GET",
                url,
                kwargs,
            )
        )

        return _Response(
            status_code=200,
            content=(
                b"\xff\xd8\xff"
                + b"x" * 2000
            ),
            headers={
                "Content-Type":
                    "image/jpeg",
            },
        )

    def post(
        self,
        url,
        **kwargs,
    ):
        self.calls.append(
            (
                "POST",
                url,
                kwargs,
            )
        )

        if url.endswith(
            "/initialize"
        ):
            return _Response(
                status_code=201,
                payload={
                    "data": {
                        "id":
                            "media-123",
                    }
                },
            )

        if url.endswith(
            "/append"
        ):
            return _Response(
                status_code=204,
                payload={},
            )

        if url.endswith(
            "/finalize"
        ):
            return _Response(
                status_code=200,
                payload={
                    "data": {
                        "id":
                            "media-123",
                    }
                },
            )

        raise AssertionError(
            url
        )


def _intent():
    return {
        "schema":
            "x_analytics_experiment_media_intent_v1",
        "status":
            "VERIFIED_COVER_READY",
        "experiment_id":
            "xexp-test",
        "role":
            "TREATMENT",
        "cover_status":
            "AVAILABLE",
        "cover_url":
            "https://example.test/cover.jpg",
        "attachment_intent":
            True,
        "verified_cover_media_available":
            True,
        "media_upload_executed":
            False,
        "execution_allowed":
            False,
        "automatic_x_post_allowed":
            False,
        "x_post_executed":
            False,
    }


def test_x_v2_media_upload_contract_with_fake_transport():
    transport = _Transport()

    result = (
        upload_verified_treatment_cover(
            _intent(),
            auth=object(),
            transport=transport,
        )
    )

    assert result.media_id == (
        "media-123"
    )

    assert result.media_type == (
        "image/jpeg"
    )

    assert result.media_upload_executed is True

    methods_urls = [
        (
            method,
            url,
        )
        for (
            method,
            url,
            _kwargs,
        ) in transport.calls
    ]

    assert methods_urls == [
        (
            "GET",
            "https://example.test/cover.jpg",
        ),
        (
            "POST",
            "https://api.x.com/2/media/upload/initialize",
        ),
        (
            "POST",
            "https://api.x.com/2/media/upload/media-123/append",
        ),
        (
            "POST",
            "https://api.x.com/2/media/upload/media-123/finalize",
        ),
    ]

    init_kwargs = (
        transport.calls[1][2]
    )

    assert init_kwargs[
        "json"
    ][
        "media_category"
    ] == "tweet_image"

    append_kwargs = (
        transport.calls[2][2]
    )

    assert append_kwargs[
        "data"
    ][
        "segment_index"
    ] == "0"

    assert (
        "media"
        in append_kwargs[
            "files"
        ]
    )


def test_unverified_intent_fails_closed():
    intent = _intent()

    intent[
        "cover_status"
    ] = "PENDING"

    with pytest.raises(
        XExperimentMediaUploadError,
        match="AVAILABLE_COVER_REQUIRED",
    ):
        upload_verified_treatment_cover(
            intent,
            auth=object(),
            transport=_Transport(),
        )


def test_publish_live_treatment_uses_media_id_and_attribution(
    monkeypatch,
    tmp_path,
):
    import requests

    import app.ebook_autonomy.x_publisher as xpub
    import app.services.x_analytics_experiment_x_media_upload_service as media_service

    monkeypatch.setattr(
        xpub,
        "_require_live_unlock",
        lambda _confirm:
            None,
    )

    monkeypatch.setattr(
        xpub,
        "verify_public_article_url",
        lambda _url: {
            "status": "PASS",
        },
    )

    monkeypatch.setattr(
        xpub,
        "_posted_evidence_path",
        lambda _digest:
            tmp_path
            / "posted.json",
    )

    monkeypatch.setattr(
        media_service,
        "upload_verified_treatment_cover",
        lambda *_args, **_kwargs:
            XExperimentMediaUploadResult(
                media_id="media-123",
                source_url=(
                    "https://example.test/"
                    "cover.jpg"
                ),
                media_type=(
                    "image/jpeg"
                ),
                byte_count=2003,
            ),
    )

    captured = {}

    class _PostResponse:
        status_code = 201

        def json(self):
            return {
                "data": {
                    "id":
                        "post-999",
                }
            }

    def fake_post(
        url,
        *,
        auth,
        json,
        timeout,
    ):
        captured[
            "url"
        ] = url

        captured[
            "json"
        ] = json

        return _PostResponse()

    monkeypatch.setattr(
        requests,
        "post",
        fake_post,
    )

    monkeypatch.setenv(
        "X_API_KEY",
        "test-key",
    )

    monkeypatch.setenv(
        "X_API_SECRET",
        "test-secret",
    )

    monkeypatch.setenv(
        "X_ACCESS_TOKEN",
        "test-token",
    )

    monkeypatch.setenv(
        "X_ACCESS_TOKEN_SECRET",
        "test-token-secret",
    )

    plan = xpub.XPostPlan(
        run_id="r15-f4-r3b",
        article_url=(
            "https://example.test/"
            "daily-new-releases"
        ),
        draft_path=(
            "/tmp/r15-f4-r3b.txt"
        ),
        source_draft_sha256="a" * 64,
        draft_sha256="b" * 64,
        weighted_length=120,
        text="same treatment text",
        already_posted=False,
        existing_post_id="",
        manual_post_evidence="",
    )

    evidence = xpub.publish_live(
        plan,
        confirm="LIVE_X_POST",
        experiment_media_intent=(
            _intent()
        ),
        experiment_confirm=(
            "LIVE_X_EXPERIMENT_TREATMENT"
        ),
    )

    assert captured[
        "json"
    ] == {
        "text":
            plan.text,
        "media": {
            "media_ids": [
                "media-123",
            ],
        },
    }

    assert evidence[
        "x_post_id"
    ] == "post-999"

    assert evidence[
        "experiment_id"
    ] == "xexp-test"

    assert evidence[
        "variant_role"
    ] == "TREATMENT"

    assert evidence[
        "media_id"
    ] == "media-123"

    assert evidence[
        "media_upload_executed"
    ] is True


def test_treatment_live_requires_separate_confirmation(
    monkeypatch,
):
    import app.ebook_autonomy.x_publisher as xpub

    plan = xpub.XPostPlan(
        run_id="r15-f4-r3b-block",
        article_url=(
            "https://example.test/"
            "daily-new-releases"
        ),
        draft_path=(
            "/tmp/r15-f4-r3b-block.txt"
        ),
        source_draft_sha256="a" * 64,
        draft_sha256="b" * 64,
        weighted_length=120,
        text="blocked treatment",
        already_posted=False,
        existing_post_id="",
        manual_post_evidence="",
    )

    with pytest.raises(
        xpub.XPublisherError,
        match=(
            "LIVE_X_EXPERIMENT_CONFIRMATION_REQUIRED"
        ),
    ):
        xpub.publish_live(
            plan,
            confirm="LIVE_X_POST",
            experiment_media_intent=(
                _intent()
            ),
            experiment_confirm="",
        )



def test_generic_verified_cover_upload_uses_existing_transport():
    import app.services.x_analytics_experiment_x_media_upload_service as media_service

    transport = _Transport()

    result = media_service.upload_verified_cover_url(
        "https://example.test/normal-cover.jpg",
        auth=object(),
        transport=transport,
    )

    assert result.media_id == "media-123"
    assert (
        result.source_url
        == "https://example.test/normal-cover.jpg"
    )
    assert result.media_upload_executed is True

    assert transport.calls[0][0] == "GET"
    assert (
        transport.calls[0][1]
        == "https://example.test/normal-cover.jpg"
    )


def test_publish_live_normal_verified_cover_uses_media_id(
    monkeypatch,
    tmp_path,
):
    import requests

    import app.ebook_autonomy.x_publisher as xpub
    import app.services.x_analytics_experiment_x_media_upload_service as media_service

    monkeypatch.setattr(
        xpub,
        "_require_live_unlock",
        lambda _confirm: None,
    )

    monkeypatch.setattr(
        xpub,
        "verify_public_article_url",
        lambda _url: {
            "status": "PASS",
        },
    )

    monkeypatch.setattr(
        xpub,
        "_posted_evidence_path",
        lambda _digest:
            tmp_path
            / "normal-posted.json",
    )

    monkeypatch.setattr(
        media_service,
        "upload_verified_cover_url",
        lambda *_args, **_kwargs:
            media_service.XExperimentMediaUploadResult(
                media_id="media-normal-1",
                source_url=(
                    "https://example.test/"
                    "normal-cover.jpg"
                ),
                media_type="image/jpeg",
                byte_count=2003,
            ),
    )

    captured = {}

    class _PostResponse:
        status_code = 201

        def json(self):
            return {
                "data": {
                    "id": "post-normal-1",
                }
            }

    def fake_post(
        url,
        *,
        auth,
        json,
        timeout,
    ):
        captured["url"] = url
        captured["json"] = json
        return _PostResponse()

    monkeypatch.setattr(
        requests,
        "post",
        fake_post,
    )

    monkeypatch.setenv(
        "X_API_KEY",
        "test-key",
    )
    monkeypatch.setenv(
        "X_API_SECRET",
        "test-secret",
    )
    monkeypatch.setenv(
        "X_ACCESS_TOKEN",
        "test-token",
    )
    monkeypatch.setenv(
        "X_ACCESS_TOKEN_SECRET",
        "test-token-secret",
    )

    plan = xpub.XPostPlan(
        run_id="f2-normal-media",
        article_url=(
            "https://example.test/"
            "daily-new-releases"
        ),
        draft_path=(
            "/tmp/f2-normal-media.txt"
        ),
        source_draft_sha256="c" * 64,
        draft_sha256="d" * 64,
        weighted_length=120,
        text="normal verified-cover post",
        already_posted=False,
        existing_post_id="",
        manual_post_evidence="",
    )

    intent = {
        "schema":
            "ebook_autonomy_verified_cover_media_v1",
        "wordpress_post_id":
            3920,
        "ebook_item_id":
            "ebook-1",
        "cover_status":
            "AVAILABLE",
        "cover_source":
            "RAKUTEN_KOBO",
        "cover_url":
            "https://example.test/normal-cover.jpg",
    }

    evidence = xpub.publish_live(
        plan,
        confirm="LIVE_X_POST",
        verified_cover_media_intent=intent,
    )

    assert captured["json"] == {
        "text": plan.text,
        "media": {
            "media_ids": [
                "media-normal-1",
            ],
        },
    }

    assert (
        evidence["x_post_id"]
        == "post-normal-1"
    )
    assert (
        evidence["media_id"]
        == "media-normal-1"
    )
    assert (
        evidence["media_source_url"]
        == "https://example.test/normal-cover.jpg"
    )
    assert (
        evidence["media_upload_executed"]
        is True
    )
