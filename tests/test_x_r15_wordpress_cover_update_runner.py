from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.x_r15_wordpress_cover_update import (
    X15WordPressCoverUpdateResult,
)
from scripts.run_x_r15_wordpress_cover_update_once import (
    X15WordPressCoverRunnerError,
    execute_authorized_x15_cover_update_once,
)


AUTHORIZATION_SCOPE = (
    "X_R15_POST_201_COVER_MEDIA_UPLOAD_"
    "AND_DRAFT_UPDATE_ONLY"
)


def write_authorization(
    path: Path,
    **overrides,
) -> None:
    value = {
        "authorization_id": "test-authorization",
        "authorization_status": "APPROVED",
        "authorization_scope": AUTHORIZATION_SCOPE,
        "ebook_item_id": (
            "e2029b2f-f44a-462f-abc8-86c4bc74b818"
        ),
        "source_item_id": "4310000887411",
        "wordpress_post_id": 201,
        "execution_allowed": True,
        "wordpress_media_upload_allowed": True,
        "wordpress_draft_update_allowed": True,
        "publish_allowed": False,
        "schedule_allowed": False,
        "x_post_allowed": False,
        "one_shot": True,
        "production_status": "NO_GO",
    }

    value.update(overrides)

    path.write_text(
        json.dumps(value),
        encoding="utf-8",
    )


def successful_result():
    return X15WordPressCoverUpdateResult(
        ebook_item_id=(
            "e2029b2f-f44a-462f-abc8-86c4bc74b818"
        ),
        source_item_id="4310000887411",
        post_id=201,
        post_status="draft",
        media_id=321,
        media_url=(
            "https://example.test/"
            "wp-content/uploads/cover.jpg"
        ),
        image_sha256="a" * 64,
        image_width=600,
        image_height=800,
        featured_media_set=True,
        content_updated=True,
        publish_executed=False,
    )


def test_valid_authorization_is_consumed(
    tmp_path: Path,
) -> None:
    authorization_path = (
        tmp_path / "authorization.json"
    )

    write_authorization(
        authorization_path
    )

    calls = []

    def executor(**kwargs):
        calls.append(kwargs)
        return successful_result()

    result = execute_authorized_x15_cover_update_once(
        execution_authorization_path=(
            authorization_path
        ),
        item=SimpleNamespace(id="item"),
        offer=SimpleNamespace(id="offer"),
        client=SimpleNamespace(),
        executor=executor,
    )

    assert result.post_id == 201
    assert len(calls) == 1

    assert not authorization_path.exists()
    assert not (
        tmp_path
        / "authorization.claimed.json"
    ).exists()

    assert (
        tmp_path
        / "authorization.consumed.json"
    ).is_file()

    assert not (
        tmp_path
        / "authorization.failed.json"
    ).exists()


def test_invalid_authorization_blocks_executor(
    tmp_path: Path,
) -> None:
    authorization_path = (
        tmp_path / "authorization.json"
    )

    write_authorization(
        authorization_path,
        publish_allowed=True,
    )

    calls = []

    def executor(**kwargs):
        calls.append(kwargs)
        return successful_result()

    with pytest.raises(
        X15WordPressCoverRunnerError,
        match=(
            "authorization mismatch: "
            "publish_allowed"
        ),
    ):
        execute_authorized_x15_cover_update_once(
            execution_authorization_path=(
                authorization_path
            ),
            item=SimpleNamespace(),
            offer=SimpleNamespace(),
            client=SimpleNamespace(),
            executor=executor,
        )

    assert calls == []
    assert authorization_path.is_file()
    assert not (
        tmp_path
        / "authorization.consumed.json"
    ).exists()
    assert not (
        tmp_path
        / "authorization.failed.json"
    ).exists()


def test_executor_failure_marks_authorization_failed(
    tmp_path: Path,
) -> None:
    authorization_path = (
        tmp_path / "authorization.json"
    )

    write_authorization(
        authorization_path
    )

    def executor(**kwargs):
        raise RuntimeError(
            "simulated WordPress failure"
        )

    with pytest.raises(
        RuntimeError,
        match="simulated WordPress failure",
    ):
        execute_authorized_x15_cover_update_once(
            execution_authorization_path=(
                authorization_path
            ),
            item=SimpleNamespace(),
            offer=SimpleNamespace(),
            client=SimpleNamespace(),
            executor=executor,
        )

    assert not authorization_path.exists()
    assert not (
        tmp_path
        / "authorization.claimed.json"
    ).exists()
    assert not (
        tmp_path
        / "authorization.consumed.json"
    ).exists()

    assert (
        tmp_path
        / "authorization.failed.json"
    ).is_file()



def test_partial_failure_persists_media_reconciliation_evidence(
    tmp_path: Path,
) -> None:
    import json
    from types import SimpleNamespace

    import pytest

    from app.services.x_r15_wordpress_cover_update import (
        X15WordPressCoverPartialFailure,
    )

    authorization_path = (
        tmp_path / "authorization.json"
    )

    authorization_path.write_text(
        json.dumps(
            {
                "authorization_id": (
                    "test-x-r15-partial-failure"
                ),
                "authorization_status": "APPROVED",
                "authorization_scope": (
                    "X_R15_POST_201_COVER_MEDIA_"
                    "UPLOAD_AND_DRAFT_UPDATE_ONLY"
                ),
                "ebook_item_id": (
                    "e2029b2f-f44a-462f-"
                    "abc8-86c4bc74b818"
                ),
                "source_item_id": "4310000887411",
                "wordpress_post_id": 201,
                "execution_allowed": True,
                "wordpress_media_upload_allowed": True,
                "wordpress_draft_update_allowed": True,
                "publish_allowed": False,
                "schedule_allowed": False,
                "x_post_allowed": False,
                "one_shot": True,
                "production_status": "NO_GO",
            }
        ),
        encoding="utf-8",
    )

    def executor(**kwargs):
        raise X15WordPressCoverPartialFailure(
            (
                "WordPress draft update was not "
                "confirmed after media upload"
            ),
            media_id=321,
            media_url=(
                "https://hoshido.jp/"
                "wp-content/uploads/"
                "medalist-15.jpg"
            ),
            image_sha256="a" * 64,
            failure_stage=(
                "AFTER_MEDIA_UPLOAD_BEFORE_"
                "DRAFT_UPDATE_CONFIRMED"
            ),
            original_error_type="RuntimeError",
        )

    with pytest.raises(
        X15WordPressCoverPartialFailure
    ):
        execute_authorized_x15_cover_update_once(
            execution_authorization_path=(
                authorization_path
            ),
            item=SimpleNamespace(),
            offer=SimpleNamespace(),
            client=SimpleNamespace(),
            executor=executor,
        )

    failed_path = (
        tmp_path
        / "authorization.failed.json"
    )

    assert failed_path.is_file()
    assert not authorization_path.exists()

    failed = json.loads(
        failed_path.read_text(encoding="utf-8")
    )

    evidence = failed["failure_evidence"]

    assert failed["authorization_status"] == (
        "FAILED"
    )
    assert failed["authorization_consumed"] is True
    assert failed["execution_completed"] is False
    assert evidence["media_upload_completed"] is True
    assert evidence["media_id"] == 321
    assert evidence["orphan_media_possible"] is True
    assert (
        evidence["manual_reconciliation_required"]
        is True
    )
    assert (
        evidence["retry_blocked_until_reconciled"]
        is True
    )
    assert evidence["publish_executed"] is False
    assert evidence["production_status"] == "NO_GO"
