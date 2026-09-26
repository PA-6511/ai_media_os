from __future__ import annotations

import json

import pytest

import app.ebook_autonomy.x_live_canary as mod
from app.ebook_autonomy.x_publisher import (
    XPostPlan,
)


def plan() -> XPostPlan:
    return XPostPlan(
        run_id="run-1",
        article_url=(
            "https://hoshido.jp/test/"
        ),
        draft_path="/tmp/x.txt",
        source_draft_sha256=(
            "a" * 64
        ),
        draft_sha256=(
            "b" * 64
        ),
        weighted_length=266,
        text=(
            "新刊\n"
            "https://hoshido.jp/test/"
        ),
        already_posted=False,
        existing_post_id="",
        manual_post_evidence="",
    )


def test_clean_state_ready(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        mod,
        "DELIVERY_STATE_ROOT",
        tmp_path,
    )

    result = (
        mod.preflight_live_canary(
            plan()
        )
    )

    assert (
        result["status"]
        == "READY_FOR_LIVE_CANARY"
    )


def test_unknown_delivery_blocks_retry(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        mod,
        "DELIVERY_STATE_ROOT",
        tmp_path,
    )

    mod._write_state(
        plan(),
        status="UNKNOWN_DELIVERY",
    )

    with pytest.raises(
        mod.XLiveCanaryError,
        match="DELIVERY_RETRY_BLOCKED",
    ):
        mod.preflight_live_canary(
            plan()
        )


def test_success_persists_posted(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        mod,
        "DELIVERY_STATE_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        mod,
        "prepare_current_xnr_post",
        plan,
    )

    monkeypatch.setattr(
        mod,
        "_require_live_unlock",
        lambda confirm: None,
    )

    monkeypatch.setattr(
        mod,
        "publish_live",
        lambda value, confirm: {
            "status": "POSTED",
            "x_post_id": "123456",
            "x_post_url": (
                "https://x.com/i/web/status/"
                "123456"
            ),
            "evidence_path":
                "/tmp/evidence.json",
        },
    )

    result = mod.run_live_canary(
        confirm="LIVE_X_POST"
    )

    assert (
        result["x_post_id"]
        == "123456"
    )

    state = json.loads(
        (
            tmp_path
            / (
                plan().draft_sha256
                + ".json"
            )
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        state["status"]
        == "POSTED"
    )


def test_failure_becomes_unknown_and_blocks_retry(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        mod,
        "DELIVERY_STATE_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        mod,
        "prepare_current_xnr_post",
        plan,
    )

    monkeypatch.setattr(
        mod,
        "_require_live_unlock",
        lambda confirm: None,
    )

    def fail(
        value,
        confirm,
    ):
        raise RuntimeError(
            "network timeout"
        )

    monkeypatch.setattr(
        mod,
        "publish_live",
        fail,
    )

    with pytest.raises(
        mod.XLiveCanaryError,
        match="X_DELIVERY_UNKNOWN",
    ):
        mod.run_live_canary(
            confirm="LIVE_X_POST"
        )

    state = json.loads(
        (
            tmp_path
            / (
                plan().draft_sha256
                + ".json"
            )
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        state["status"]
        == "UNKNOWN_DELIVERY"
    )

    with pytest.raises(
        mod.XLiveCanaryError,
        match="DELIVERY_RETRY_BLOCKED",
    ):
        mod.preflight_live_canary(
            plan()
        )



def test_verified_cover_media_intent_passes_to_publisher(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        mod,
        "DELIVERY_STATE_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        mod,
        "prepare_current_xnr_post",
        plan,
    )

    monkeypatch.setattr(
        mod,
        "_require_live_unlock",
        lambda confirm: None,
    )

    captured = {}

    def fake_publish(
        value,
        confirm,
        verified_cover_media_intent=None,
    ):
        captured[
            "verified_cover_media_intent"
        ] = verified_cover_media_intent

        return {
            "status": "POSTED",
            "x_post_id": "media-post-1",
            "x_post_url":
                "https://x.com/i/web/status/media-post-1",
            "evidence_path":
                "/tmp/media-evidence.json",
        }

    monkeypatch.setattr(
        mod,
        "publish_live",
        fake_publish,
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
            "https://example.test/cover.jpg",
    }

    result = mod.run_live_canary(
        confirm="LIVE_X_POST",
        verified_cover_media_intent=intent,
    )

    assert (
        captured[
            "verified_cover_media_intent"
        ]
        == intent
    )

    assert (
        result["x_post_id"]
        == "media-post-1"
    )


def test_invalid_verified_cover_media_intent_blocks_pre_send(
    monkeypatch,
):
    monkeypatch.setattr(
        mod,
        "prepare_current_xnr_post",
        plan,
    )

    with pytest.raises(
        mod.XLiveCanaryError,
        match=(
            "X_PRE_SEND_BLOCKED:"
            "VERIFIED_COVER_MEDIA_INTENT_INVALID"
        ),
    ):
        mod.run_live_canary(
            confirm="LIVE_X_POST",
            verified_cover_media_intent={
                "schema":
                    "ebook_autonomy_verified_cover_media_v1",
                "cover_status":
                    "MISSING",
                "cover_url":
                    "",
            },
        )
