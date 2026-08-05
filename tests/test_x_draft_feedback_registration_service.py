from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from app.services.x_draft_feedback_registration_service import (
    ROOT,
    XDraftFeedbackRegistrationError,
    XDraftFeedbackRegistrationService,
)
from app.services.x_draft_generation_service import (
    XDraftInput,
)


def valid_input(**overrides: object) -> XDraftInput:
    values = {
        "ebook_item_id": "x-r4-test-001",
        "title": "X-R4 テスト作品",
        "volume_label": "第1巻",
        "release_date": "2026-07-17",
        "category": "コミック新刊",
        "author_name": "山田 太郎",
        "article_url": (
            "https://books.example.jp/posts/"
            "x-r4-test-001"
        ),
        "wordpress_draft_id": 40001,
        "wordpress_status": "DRAFT",
    }
    values.update(overrides)
    return XDraftInput(**values)


@pytest.fixture
def x_fb_root(tmp_path: Path) -> Path:
    root = tmp_path / "x_fb_root"

    (root / "config").mkdir(
        parents=True,
        exist_ok=True,
    )
    (root / "scripts").mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        ROOT
        / "config/x_post_wording_feedback_schema.json",
        root
        / "config/x_post_wording_feedback_schema.json",
    )
    shutil.copy2(
        ROOT
        / "config/x_fb_manual_operation_policy.json",
        root
        / "config/x_fb_manual_operation_policy.json",
    )
    shutil.copy2(
        ROOT / "scripts/build_x_fb_0.py",
        root / "scripts/build_x_fb_0.py",
    )

    return root


def file_snapshot(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file()
    )


def test_dry_run_integrates_generation_and_x_fb(
    x_fb_root: Path,
) -> None:
    service = XDraftFeedbackRegistrationService()

    result = service.dry_run_register(
        valid_input(),
        storage_root=x_fb_root,
    )

    assert result.status == "PASS_DRY_RUN_NO_WRITE"
    assert result.dry_run is True
    assert result.current_record_existed_before is False
    assert result.current_record_written is False
    assert result.operation_result_written is False
    assert result.contains_pr is True
    assert result.character_count <= 280

    normalized = result.normalized_record

    assert normalized["feedback_id"] == (
        result.feedback_id
    )
    assert normalized["record_version"] == 1
    assert normalized["record_stage"] == (
        "DRAFT_GENERATED"
    )
    assert normalized["review_status"] == (
        "UNREVIEWED"
    )
    assert normalized["text_snapshots"][
        "generated_text"
    ] == result.generated_text


def test_dry_run_creates_no_files(
    x_fb_root: Path,
) -> None:
    service = XDraftFeedbackRegistrationService()

    before = file_snapshot(x_fb_root)

    result = service.dry_run_register(
        valid_input(),
        storage_root=x_fb_root,
    )

    after = file_snapshot(x_fb_root)

    assert before == after
    assert not Path(
        result.current_record_path
    ).exists()
    assert not Path(
        result.operation_result_path
    ).exists()


def test_existing_current_record_rejects_initialize(
    x_fb_root: Path,
) -> None:
    service = XDraftFeedbackRegistrationService()

    first = service.dry_run_register(
        valid_input(),
        storage_root=x_fb_root,
    )

    current_path = Path(
        first.current_record_path
    )
    current_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    current_path.write_text(
        json.dumps(
            first.normalized_record,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    before_digest = hashlib.sha256(
        current_path.read_bytes()
    ).hexdigest()

    with pytest.raises(
        XDraftFeedbackRegistrationError,
        match=(
            "INITIALIZE is forbidden because "
            "current record exists"
        ),
    ):
        service.dry_run_register(
            valid_input(),
            storage_root=x_fb_root,
        )

    after_digest = hashlib.sha256(
        current_path.read_bytes()
    ).hexdigest()

    assert before_digest == after_digest


def test_unsafe_policy_boundary_is_rejected(
    x_fb_root: Path,
) -> None:
    policy_path = (
        x_fb_root
        / "config/x_fb_manual_operation_policy.json"
    )

    policy = json.loads(
        policy_path.read_text(encoding="utf-8")
    )
    policy["execution_boundary"][
        "x_post_allowed"
    ] = True

    policy_path.write_text(
        json.dumps(
            policy,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    service = XDraftFeedbackRegistrationService()

    with pytest.raises(
        XDraftFeedbackRegistrationError,
        match="x_post_allowed must be false",
    ):
        service.dry_run_register(
            valid_input(),
            storage_root=x_fb_root,
        )


def test_missing_validator_is_rejected(
    x_fb_root: Path,
) -> None:
    (
        x_fb_root
        / "scripts/build_x_fb_0.py"
    ).unlink()

    service = XDraftFeedbackRegistrationService()

    with pytest.raises(
        XDraftFeedbackRegistrationError,
        match="required Python module missing",
    ):
        service.dry_run_register(
            valid_input(),
            storage_root=x_fb_root,
        )


def test_service_exposes_no_write_api() -> None:
    service = XDraftFeedbackRegistrationService()

    assert not hasattr(service, "write")
    assert not hasattr(service, "register")
    assert not hasattr(service, "commit")
    assert hasattr(service, "dry_run_register")


def test_result_is_json_serializable(
    x_fb_root: Path,
) -> None:
    service = XDraftFeedbackRegistrationService()

    result = service.dry_run_register(
        valid_input(),
        storage_root=x_fb_root,
    )

    serialized = json.dumps(
        result.to_dict(),
        ensure_ascii=False,
    )

    assert "PASS_DRY_RUN_NO_WRITE" in serialized
    assert "DRAFT_GENERATED" in serialized
    assert "X-R4 テスト作品" in serialized
