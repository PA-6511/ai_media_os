from __future__ import annotations

import builtins
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.db.access_guard import assert_database_target_allowed
from app.db.config import PRODUCTION_SQLITE_PATH


PRODUCTION_CREDENTIAL_PATH = Path(
    "/etc/ai-media-os/credential.env"
)
REQUIRED_WORDPRESS_CREDENTIAL_ENV = (
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
)

PHASE_K_PREIMAGE_FIXTURE_ROOT = (
    ROOT
    / "tests/fixtures/ls_new_batch_4g_2e_recovery/phase_k_preimage"
)
PHASE_K_PREIMAGE_ARTICLE = Path(
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
PHASE_K_PREIMAGE_SHA256 = (
    "849a37519c6af70d2212ec01d5cddef5"
    "793bfa811e97ca9f248ce099a0350bf4"
)
PHASE_K_TERMINAL_POSTIMAGE_SHA256 = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
PHASE_K_FIXTURE_ERROR = (
    "HISTORICAL_PHASE_K_FIXTURE_INTEGRITY_FAILED"
)


def _phase_k_fixture_fail(detail: str) -> None:
    raise AssertionError(
        f"{PHASE_K_FIXTURE_ERROR}: {detail}"
    )


def _phase_k_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_phase_k_preimage_fixture(
    fixture_root: Path,
) -> dict[str, str]:
    manifest_path = fixture_root / "fixture_manifest.json"
    snapshot_root = fixture_root / "snapshot"

    if not manifest_path.is_file():
        _phase_k_fixture_fail("manifest missing")
    if manifest_path.is_symlink():
        _phase_k_fixture_fail("manifest must not be a symlink")

    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        _phase_k_fixture_fail(
            f"manifest is not valid JSON: {exc}"
        )

    expected_manifest_values = {
        "fixture_id": "LS_NEW_BATCH_4G_2E_PHASE_K_PREIMAGE",
        "phase": "K",
        "source_item_id": "new-release-comic-20260703-001",
        "source_phase": "LS-NEW-BATCH-4G-2E-RECOVERY-K",
        "original_artifact_path": PHASE_K_PREIMAGE_ARTICLE.as_posix(),
        "original_artifact_sha256": PHASE_K_PREIMAGE_SHA256,
        "fixture_artifact_path": (
            "snapshot/" + PHASE_K_PREIMAGE_ARTICLE.as_posix()
        ),
        "fixture_artifact_sha256": PHASE_K_PREIMAGE_SHA256,
        "expected_article_sha256": PHASE_K_PREIMAGE_SHA256,
        "terminal_postimage_sha256": (
            PHASE_K_TERMINAL_POSTIMAGE_SHA256
        ),
        "provenance_type": (
            "DETERMINISTIC_REGENERATION_FROM_FORMAL_PHASE_K_INPUTS"
        ),
        "immutable": True,
        "terminal_artifact": False,
        "postimage_artifact": False,
    }
    for field, expected in expected_manifest_values.items():
        if manifest.get(field) != expected:
            _phase_k_fixture_fail(
                f"manifest field mismatch: {field}"
            )

    dependencies = manifest.get("historical_dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        _phase_k_fixture_fail(
            "historical dependency manifest missing"
        )

    fingerprints: dict[str, str] = {
        "fixture_manifest.json": _phase_k_file_sha256(
            manifest_path
        )
    }
    declared_paths: set[str] = set()
    for entry in dependencies:
        if not isinstance(entry, dict):
            _phase_k_fixture_fail(
                "historical dependency entry must be an object"
            )
        relative_value = entry.get("path")
        expected_sha = entry.get("sha256")
        if (
            not isinstance(relative_value, str)
            or not isinstance(expected_sha, str)
            or entry.get("included_or_bound_only") != "INCLUDED"
        ):
            _phase_k_fixture_fail(
                "historical dependency entry is incomplete"
            )
        relative = Path(relative_value)
        if relative.is_absolute() or ".." in relative.parts:
            _phase_k_fixture_fail(
                f"unsafe historical dependency path: {relative_value}"
            )
        if relative_value in declared_paths:
            _phase_k_fixture_fail(
                f"duplicate historical dependency: {relative_value}"
            )
        declared_paths.add(relative_value)
        artifact = snapshot_root / relative
        if not artifact.is_file() or artifact.is_symlink():
            _phase_k_fixture_fail(
                f"historical dependency missing or unsafe: {relative_value}"
            )
        actual_sha = _phase_k_file_sha256(artifact)
        if actual_sha != expected_sha:
            _phase_k_fixture_fail(
                f"historical dependency SHA mismatch: {relative_value}"
            )
        fingerprints[
            "snapshot/" + relative_value
        ] = actual_sha

    actual_paths = {
        path.relative_to(snapshot_root).as_posix()
        for path in snapshot_root.rglob("*")
        if path.is_file()
    }
    if actual_paths != declared_paths:
        _phase_k_fixture_fail(
            "snapshot tree does not exactly match manifest"
        )

    article_path = snapshot_root / PHASE_K_PREIMAGE_ARTICLE
    article_sha = _phase_k_file_sha256(article_path)
    if article_sha != PHASE_K_PREIMAGE_SHA256:
        _phase_k_fixture_fail("article SHA mismatch")
    if article_sha == PHASE_K_TERMINAL_POSTIMAGE_SHA256:
        _phase_k_fixture_fail("terminal postimage supplied as preimage")

    try:
        article = json.loads(
            article_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        _phase_k_fixture_fail(
            f"article is not valid JSON: {exc}"
        )
    if article.get("content_item_id") != manifest["source_item_id"]:
        _phase_k_fixture_fail("article source item mismatch")

    content = article.get("content_html")
    if not isinstance(content, str):
        _phase_k_fixture_fail("article content_html missing")
    if "https://al.dmm.com/" in content or "https://book.dmm.com/" in content:
        _phase_k_fixture_fail("DMM affiliate URL present")
    if "<a " in content.lower() or "href=" in content.lower():
        _phase_k_fixture_fail("store slot is clickable")
    if content.count("<span ") != 3:
        _phase_k_fixture_fail("store slot count mismatch")

    reserved_dmm_slot = (
        '<span class="ls-store-btn ls-store-dmm ls-store-disabled" '
        'aria-disabled="true">DMMブックスで確認（再確認待ち）</span>'
    )
    if content.count(reserved_dmm_slot) != 1:
        _phase_k_fixture_fail("reserved DMM slot count mismatch")

    expected_cover = (
        '<figure class="ls-book-cover">\n'
        '      <img src="https://shop.r10s.jp/rakutenkobo-ebooks/'
        'cabinet/6485/2000020786485.jpg" '
        'alt="ダークギャザリング 第20巻 書影" loading="lazy">\n'
        "    </figure>"
    )
    if expected_cover not in content:
        _phase_k_fixture_fail("expected unlinked cover missing")

    return fingerprints


@pytest.fixture
def phase_k_preimage_root(tmp_path: Path):
    """Return a verified regular-copy snapshot of immutable Phase K data."""

    canonical_before = _verify_phase_k_preimage_fixture(
        PHASE_K_PREIMAGE_FIXTURE_ROOT
    )
    isolated_fixture = tmp_path / "phase_k_preimage"
    shutil.copytree(
        PHASE_K_PREIMAGE_FIXTURE_ROOT,
        isolated_fixture,
        symlinks=False,
    )
    isolated_fingerprint = _verify_phase_k_preimage_fixture(
        isolated_fixture
    )
    if isolated_fingerprint != canonical_before:
        _phase_k_fixture_fail("isolated fixture copy mismatch")

    yield isolated_fixture / "snapshot"

    canonical_after = _verify_phase_k_preimage_fixture(
        PHASE_K_PREIMAGE_FIXTURE_ROOT
    )
    if canonical_after != canonical_before:
        _phase_k_fixture_fail(
            "canonical fixture changed during test"
        )


_PHASE_K_ARTICLE = PHASE_K_PREIMAGE_ARTICLE.as_posix()
_PHASE_K_CONSUMPTION = (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "offline_content_generation_consumption.json"
)
_PHASE_K_TARGET_BINDINGS: dict[str, dict[str, str]] = {
    **{
        node: {
            "OUTPUT": _PHASE_K_ARTICLE,
            "CONSUMPTION": _PHASE_K_CONSUMPTION,
        }
        for node in (
            "tests/test_build_ls_new_batch_4g_2e_recovery_k.py::test_article_output_digest",
            "tests/test_build_ls_new_batch_4g_2e_recovery_k.py::test_current_cover_is_rendered_unlinked",
            "tests/test_build_ls_new_batch_4g_2e_recovery_k.py::test_store_slots_are_non_clickable",
            "tests/test_build_ls_new_batch_4g_2e_recovery_k.py::test_no_store_or_dmm_urls",
            "tests/test_build_ls_new_batch_4g_2e_recovery_k.py::test_consumption_binds_generated_output",
        )
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_l.py::test_generated_article_is_preserved": {
        "REQUEST": (
            "exchange/examples/new_release_wp_fresh_article_"
            "content_human_review_request.example.json"
        ),
        "ARTICLE": _PHASE_K_ARTICLE,
    },
    **{
        node: {
            "REQUEST": (
                "exchange/examples/new_release_wp_fresh_"
                "store_link_finalization_plan_request.example.json"
            ),
            "ARTICLE": _PHASE_K_ARTICLE,
            "CONTENT_REVIEW": (
                "exchange/reviews/new_release/fresh/"
                "new-release-comic-20260703-001."
                "article_content_human_review.json"
            ),
            "CONSUMPTION": _PHASE_K_CONSUMPTION,
        }
        for node in (
            "tests/test_build_ls_new_batch_4g_2e_recovery_m0.py::test_article_and_review_are_preserved",
            "tests/test_build_ls_new_batch_4g_2e_recovery_m0.py::test_article_still_has_no_links",
        )
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_m1.py::test_source_artifacts_are_preserved": {
        "ROOT": ".",
        "REQUEST": (
            "exchange/examples/new_release_wp_fresh_dmm_latest_"
            "alias_recheck_authorization_request.example.json"
        ),
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_m3.py::test_historical_artifacts_are_preserved": {
        "ROOT": ".",
        "REQUEST": (
            "exchange/examples/new_release_wp_fresh_dmm_post_"
            "parser_fix_recheck_authorization_request.example.json"
        ),
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_m5.py::test_historical_sources_unchanged": {
        "ROOT": ".",
        "M5_APPROVAL": (
            "exchange/approvals/ls_new_batch_4g_2e_recovery_"
            "m5_historical_evidence_human_review_approval.json"
        ),
    },
    **{
        node: {
            "ARTICLE": _PHASE_K_ARTICLE,
            "BUILDER": (
                "scripts/build_ls_new_batch_4g_2e_recovery_m8_fix1.py"
            ),
        }
        for node in (
            "tests/test_build_ls_new_batch_4g_2e_recovery_m8_fix1.py::test_html_slot_parser_exact_match",
            "tests/test_build_ls_new_batch_4g_2e_recovery_m8_fix1.py::test_article_preimage_unchanged",
        )
    },
    "tests/test_execute_ls_new_batch_4g_2e_recovery_m2.py::test_article_and_plan_are_preserved": {
        "ROOT": ".",
        "REQUEST": (
            "exchange/examples/new_release_wp_fresh_dmm_latest_"
            "alias_recheck_execute_request.example.json"
        ),
        "ARTICLE": _PHASE_K_ARTICLE,
        "PLAN": (
            "exchange/plans/new_release/fresh/"
            "new-release-comic-20260703-001."
            "store_link_finalization_plan.json"
        ),
    },
    "tests/test_execute_ls_new_batch_4g_2e_recovery_m4.py::test_article_and_plan_are_preserved": {
        "ROOT": ".",
        "REQUEST": (
            "exchange/examples/new_release_wp_fresh_dmm_post_"
            "parser_fix_recheck_execute_request.example.json"
        ),
    },
    "tests/test_run_ls_new_batch_4g_2e_recovery_m7.py::test_source_bindings_unchanged": {
        "ROOT": ".",
        "APPROVAL": (
            "exchange/approvals/"
            "ls_new_batch_4g_2e_recovery_m7_execute_now_approval.json"
        ),
    },
}


@pytest.fixture(autouse=True)
def _bind_phase_k_historical_target_artifacts(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
):
    bindings = _PHASE_K_TARGET_BINDINGS.get(
        request.node.nodeid
    )
    if bindings is None:
        yield
        return

    snapshot_root = request.getfixturevalue(
        "phase_k_preimage_root"
    )
    for attribute, relative_value in bindings.items():
        target = (
            snapshot_root
            if relative_value == "."
            else snapshot_root / relative_value
        )
        if not target.exists():
            _phase_k_fixture_fail(
                f"target binding missing: {relative_value}"
            )
        monkeypatch.setattr(
            request.module,
            attribute,
            target,
        )

    yield


PHASE_ABSENCE_FIXTURE_ROOT = (
    ROOT
    / "tests/fixtures/ls_new_batch_4g_2e_recovery/"
    "phase_absence_states"
)
PHASE_STATE_FIXTURE_ERROR = (
    "HISTORICAL_PHASE_STATE_FIXTURE_INTEGRITY_FAILED"
)
_PHASE_STATE_DEFINITIONS = {
    "phase_i_pre_content_generation": (
        "I",
        "LS_NEW_BATCH_4G_2E_PHASE_I_PRE_CONTENT_GENERATION",
    ),
    "phase_j_pre_content_generation": (
        "J",
        "LS_NEW_BATCH_4G_2E_PHASE_J_PRE_CONTENT_GENERATION",
    ),
    "phase_k0_pre_content_generation": (
        "K0",
        "LS_NEW_BATCH_4G_2E_PHASE_K0_PRE_CONTENT_GENERATION",
    ),
    "phase_k_preflight_pre_content_generation": (
        "K-PREFLIGHT",
        "LS_NEW_BATCH_4G_2E_PHASE_K_PREFLIGHT_PRE_CONTENT_GENERATION",
    ),
    "phase_m1_pre_first_recheck": (
        "M1",
        "LS_NEW_BATCH_4G_2E_PHASE_M1_PRE_FIRST_RECHECK",
    ),
    "phase_m3_pre_post_parser_recheck": (
        "M3",
        "LS_NEW_BATCH_4G_2E_PHASE_M3_PRE_POST_PARSER_RECHECK",
    ),
    "phase_m13_pre_network": (
        "M13-PRE-NETWORK",
        "LS_NEW_BATCH_4G_2E_PHASE_M13_PRE_NETWORK",
    ),
    "phase_m13_pre_writer": (
        "M13-PRE-WRITER",
        "LS_NEW_BATCH_4G_2E_PHASE_M13_PRE_WRITER",
    ),
}
_PHASE_STATE_NODE_BINDINGS: dict[str, dict[str, Any]] = {
    "tests/test_build_ls_new_batch_4g_2e_recovery_i.py::test_reserved_content_output_is_absent": {
        "state": "phase_i_pre_content_generation",
        "bindings": {
            "RESERVED_OUTPUT": _PHASE_K_ARTICLE,
        },
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_j.py::test_reserved_output_is_absent": {
        "state": "phase_j_pre_content_generation",
        "bindings": {
            "RESERVED_OUTPUT": _PHASE_K_ARTICLE,
        },
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_k0.py::test_no_consumption_or_content_output": {
        "state": "phase_k0_pre_content_generation",
        "bindings": {
            "CONSUMPTION": _PHASE_K_CONSUMPTION,
            "OUTPUT": _PHASE_K_ARTICLE,
        },
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_k_preflight.py::test_no_consumption_or_content_output": {
        "state": "phase_k_preflight_pre_content_generation",
        "bindings": {
            "CONSUMPTION": _PHASE_K_CONSUMPTION,
            "OUTPUT": _PHASE_K_ARTICLE,
        },
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_m1.py::test_no_recheck_outputs_exist": {
        "state": "phase_m1_pre_first_recheck",
        "bindings": {
            "RECHECK_RESULT": (
                "exchange/rechecks/new_release/fresh/"
                "new-release-comic-20260703-001."
                "dmm_latest_alias_recheck_result.json"
            ),
            "CONSUMPTION": (
                "exchange/authorizations/new_release/fresh/"
                "new-release-comic-20260703-001."
                "dmm_latest_alias_recheck_consumption.json"
            ),
        },
    },
    "tests/test_build_ls_new_batch_4g_2e_recovery_m3.py::test_new_terminal_artifacts_do_not_exist": {
        "state": "phase_m3_pre_post_parser_recheck",
        "bindings": {
            "PLANNED_RECHECK": (
                "exchange/rechecks/new_release/fresh/"
                "new-release-comic-20260703-001."
                "dmm_latest_alias_recheck_post_parser_fix_result.json"
            ),
            "PLANNED_CONSUMPTION": (
                "exchange/authorizations/new_release/fresh/"
                "new-release-comic-20260703-001."
                "dmm_latest_alias_recheck_post_parser_fix_consumption.json"
            ),
        },
    },
    "tests/test_validate_ls_new_batch_4g_2e_recovery_m13_pre_network.py::test_get_only_and_no_consumption": {
        "state": "phase_m13_pre_network",
        "bindings": {
            "RESULT": (
                "exchange/logs/"
                "ls_new_batch_4g_2e_recovery_m13_pre_network_result.json"
            ),
            "M13_CONSUMPTION": (
                "exchange/authorizations/new_release/fresh/"
                "new-release-comic-20260703-001."
                "wordpress_draft_creation_consumption.json"
            ),
        },
    },
    "tests/test_validate_ls_new_batch_4g_2e_recovery_m13_pre_writer.py::test_m12_authorization_unchanged": {
        "state": "phase_m13_pre_writer",
        "bindings": {
            "RESULT": (
                "exchange/logs/"
                "ls_new_batch_4g_2e_recovery_m13_pre_writer_result.json"
            ),
            "M12_AUTH": (
                "exchange/authorizations/new_release/fresh/"
                "new-release-comic-20260703-001."
                "wordpress_draft_creation_authorization.json"
            ),
            "M13_CONSUMPTION": (
                "exchange/authorizations/new_release/fresh/"
                "new-release-comic-20260703-001."
                "wordpress_draft_creation_consumption.json"
            ),
        },
    },
}


def _phase_state_fixture_fail(detail: str) -> None:
    raise AssertionError(
        f"{PHASE_STATE_FIXTURE_ERROR}: {detail}"
    )


def _verify_phase_state_fixture(
    state_root: Path,
    state_name: str,
) -> dict[str, str]:
    expected_phase, expected_fixture_id = (
        _PHASE_STATE_DEFINITIONS[state_name]
    )
    manifest_path = state_root / "fixture_manifest.json"
    snapshot_root = state_root / "snapshot"

    if not manifest_path.is_file() or manifest_path.is_symlink():
        _phase_state_fixture_fail("manifest missing or unsafe")
    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        _phase_state_fixture_fail(
            f"manifest is not valid JSON: {exc}"
        )

    expected_values = {
        "fixture_id": expected_fixture_id,
        "phase": expected_phase,
        "source_item_id": "new-release-comic-20260703-001",
        "immutable": True,
        "terminal_namespace": False,
    }
    for field, expected in expected_values.items():
        if manifest.get(field) != expected:
            _phase_state_fixture_fail(
                f"manifest field mismatch: {field}"
            )
    for field in (
        "purpose",
        "state_boundary",
        "absence_reason",
        "later_writer_phase",
        "provenance_type",
        "created_at",
    ):
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            _phase_state_fixture_fail(
                f"manifest field missing: {field}"
            )
    if not isinstance(manifest.get("update_policy"), dict):
        _phase_state_fixture_fail("fixture update policy missing")

    for path in state_root.rglob("*"):
        if path.is_symlink():
            _phase_state_fixture_fail(
                f"symlink prohibited: {path.relative_to(state_root)}"
            )

    required_present = manifest.get("required_present")
    required_absent = manifest.get("required_absent")
    if not isinstance(required_present, list):
        _phase_state_fixture_fail("required_present missing")
    if not isinstance(required_absent, list) or not required_absent:
        _phase_state_fixture_fail("required_absent missing")

    declared_present: set[str] = set()
    fingerprints: dict[str, str] = {
        "fixture_manifest.json": _phase_k_file_sha256(
            manifest_path
        )
    }
    if manifest_path.stat().st_nlink != 1:
        _phase_state_fixture_fail("manifest hard link prohibited")

    for entry in required_present:
        if not isinstance(entry, dict):
            _phase_state_fixture_fail(
                "required_present entry must be an object"
            )
        relative_value = entry.get("path")
        expected_sha = entry.get("sha256")
        if not isinstance(relative_value, str) or not isinstance(
            expected_sha, str
        ):
            _phase_state_fixture_fail(
                "required_present entry incomplete"
            )
        relative = Path(relative_value)
        if relative.is_absolute() or ".." in relative.parts:
            _phase_state_fixture_fail(
                f"unsafe required_present path: {relative_value}"
            )
        if relative_value in declared_present:
            _phase_state_fixture_fail(
                f"duplicate required_present path: {relative_value}"
            )
        declared_present.add(relative_value)
        artifact = snapshot_root / relative
        if not artifact.is_file() or artifact.is_symlink():
            _phase_state_fixture_fail(
                f"required artifact missing: {relative_value}"
            )
        if artifact.stat().st_nlink != 1:
            _phase_state_fixture_fail(
                f"hard link prohibited: {relative_value}"
            )
        actual_sha = _phase_k_file_sha256(artifact)
        if actual_sha != expected_sha:
            _phase_state_fixture_fail(
                f"required artifact SHA mismatch: {relative_value}"
            )
        if manifest.get("present_artifact_sha256", {}).get(
            relative_value
        ) != expected_sha:
            _phase_state_fixture_fail(
                f"present SHA map mismatch: {relative_value}"
            )
        if artifact.suffix == ".json":
            try:
                value = json.loads(
                    artifact.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as exc:
                _phase_state_fixture_fail(
                    f"required artifact invalid JSON: {relative_value}: {exc}"
                )
            if (
                isinstance(value, dict)
                and "content_item_id" in value
                and value["content_item_id"]
                != manifest["source_item_id"]
            ):
                _phase_state_fixture_fail(
                    f"source item mismatch: {relative_value}"
                )
        fingerprints[
            "snapshot/" + relative_value
        ] = actual_sha

    declared_absent: set[str] = set()
    for entry in required_absent:
        if not isinstance(entry, dict):
            _phase_state_fixture_fail(
                "required_absent entry must be an object"
            )
        relative_value = entry.get("relative_path")
        relative = Path(relative_value) if isinstance(
            relative_value, str
        ) else Path("..")
        if (
            not isinstance(relative_value, str)
            or relative.is_absolute()
            or ".." in relative.parts
            or entry.get("absence_required_by_phase") is not True
            or not isinstance(
                entry.get("first_phase_allowed_to_create"), str
            )
            or not isinstance(entry.get("artifact_role"), str)
        ):
            _phase_state_fixture_fail(
                "required_absent entry incomplete or unsafe"
            )
        if relative_value in declared_absent:
            _phase_state_fixture_fail(
                f"duplicate required_absent path: {relative_value}"
            )
        declared_absent.add(relative_value)
        if (snapshot_root / relative).exists():
            _phase_state_fixture_fail(
                f"required absent artifact exists: {relative_value}"
            )

    if declared_present & declared_absent:
        _phase_state_fixture_fail(
            "artifact declared both present and absent"
        )
    actual_present = {
        path.relative_to(snapshot_root).as_posix()
        for path in snapshot_root.rglob("*")
        if path.is_file()
    }
    if actual_present != declared_present:
        _phase_state_fixture_fail(
            "snapshot tree does not match required_present"
        )
    expected_state_files = {
        "fixture_manifest.json",
        *{"snapshot/" + path for path in declared_present},
    }
    actual_state_files = {
        path.relative_to(state_root).as_posix()
        for path in state_root.rglob("*")
        if path.is_file()
    }
    if actual_state_files != expected_state_files:
        _phase_state_fixture_fail(
            "unexpected file outside snapshot manifest"
        )

    return fingerprints


def _phase_state_terminal_fingerprints() -> dict[str, dict[str, Any]]:
    relative_paths = {
        entry["relative_path"]
        for state_name in _PHASE_STATE_DEFINITIONS
        for entry in json.loads(
            (
                PHASE_ABSENCE_FIXTURE_ROOT
                / state_name
                / "fixture_manifest.json"
            ).read_text(encoding="utf-8")
        )["required_absent"]
    }
    result: dict[str, dict[str, Any]] = {}
    for relative_value in relative_paths:
        path = ROOT / relative_value
        if not path.exists():
            result[relative_value] = {
                "exists": False,
                "size": None,
                "sha256": None,
            }
        else:
            result[relative_value] = {
                "exists": True,
                "size": path.stat().st_size,
                "sha256": _phase_k_file_sha256(path),
            }
    return result


@pytest.fixture
def phase_absence_state_root(
    request: pytest.FixtureRequest,
    tmp_path: Path,
):
    specification = _PHASE_STATE_NODE_BINDINGS[
        request.node.nodeid
    ]
    state_name = specification["state"]
    canonical_root = PHASE_ABSENCE_FIXTURE_ROOT / state_name
    canonical_before = _verify_phase_state_fixture(
        canonical_root,
        state_name,
    )
    phase_k_before = _verify_phase_k_preimage_fixture(
        PHASE_K_PREIMAGE_FIXTURE_ROOT
    )
    terminal_before = _phase_state_terminal_fingerprints()

    isolated_root = tmp_path / state_name
    shutil.copytree(
        canonical_root,
        isolated_root,
        symlinks=False,
    )
    isolated_fingerprint = _verify_phase_state_fixture(
        isolated_root,
        state_name,
    )
    if isolated_fingerprint != canonical_before:
        _phase_state_fixture_fail("isolated fixture copy mismatch")

    yield isolated_root / "snapshot"

    if _verify_phase_state_fixture(
        canonical_root,
        state_name,
    ) != canonical_before:
        _phase_state_fixture_fail(
            "canonical phase fixture changed during test"
        )
    if _verify_phase_k_preimage_fixture(
        PHASE_K_PREIMAGE_FIXTURE_ROOT
    ) != phase_k_before:
        _phase_state_fixture_fail(
            "Phase K fixture changed during phase-state test"
        )
    if _phase_state_terminal_fingerprints() != terminal_before:
        _phase_state_fixture_fail(
            "terminal artifact changed during phase-state test"
        )


@pytest.fixture(autouse=True)
def _bind_phase_absence_target_artifacts(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
):
    specification = _PHASE_STATE_NODE_BINDINGS.get(
        request.node.nodeid
    )
    if specification is None:
        yield
        return

    snapshot_root = request.getfixturevalue(
        "phase_absence_state_root"
    )
    for attribute, relative_value in specification[
        "bindings"
    ].items():
        monkeypatch.setattr(
            request.module,
            attribute,
            snapshot_root / relative_value,
        )

    yield


@pytest.fixture
def isolated_missing_credential_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """Provide deterministic missing credentials without touching production."""

    missing_path = (
        tmp_path / "missing" / "credential.env"
    )
    production_access_attempts: list[str] = []

    for name in REQUIRED_WORDPRESS_CREDENTIAL_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AI_MEDIA_OS_TESTING", "1")

    def is_production_credential_path(value: Any) -> bool:
        try:
            absolute = Path(
                os.path.abspath(os.fspath(value))
            )
        except TypeError:
            return False
        return absolute == PRODUCTION_CREDENTIAL_PATH

    original_builtin_open = builtins.open
    original_path_open = Path.open

    def guarded_builtin_open(
        file: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if is_production_credential_path(file):
            production_access_attempts.append(str(file))
            raise AssertionError(
                "PRODUCTION_CREDENTIAL_ACCESS_BLOCKED_DURING_TEST"
            )
        return original_builtin_open(file, *args, **kwargs)

    def guarded_path_open(
        path: Path,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if is_production_credential_path(path):
            production_access_attempts.append(str(path))
            raise AssertionError(
                "PRODUCTION_CREDENTIAL_ACCESS_BLOCKED_DURING_TEST"
            )
        return original_path_open(path, *args, **kwargs)

    monkeypatch.setattr(
        builtins,
        "open",
        guarded_builtin_open,
    )
    monkeypatch.setattr(
        Path,
        "open",
        guarded_path_open,
    )

    assert not missing_path.exists()
    return {
        "path": missing_path,
        "production_access_attempts": (
            production_access_attempts
        ),
    }


def _file_fingerprint(path: Path) -> dict[str, Any]:
    try:
        stat_result = path.stat()
    except FileNotFoundError:
        return {"exists": False, "size": None, "mtime_ns": None, "sha256": None}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "exists": True,
        "size": stat_result.st_size,
        "mtime_ns": stat_result.st_mtime_ns,
        "sha256": digest.hexdigest(),
    }


def production_sqlite_fingerprint() -> dict[str, dict[str, Any]]:
    """Fingerprint production files via OS reads; never open SQLite."""

    return {
        "database": _file_fingerprint(PRODUCTION_SQLITE_PATH),
        "wal": _file_fingerprint(Path(f"{PRODUCTION_SQLITE_PATH}-wal")),
        "shm": _file_fingerprint(Path(f"{PRODUCTION_SQLITE_PATH}-shm")),
    }


def _material_fingerprint(value: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Ignore only SHM mtime; compare SHM content and size."""

    return {
        "database": value["database"],
        "wal": value["wal"],
        "shm": {
            key: value["shm"][key]
            for key in ("exists", "size", "sha256")
        },
    }


# Capture before setting the inherited subprocess flag.  Reading here uses
# only stat/open/hashlib and cannot invoke SQLite.
PRODUCTION_FINGERPRINT_BEFORE = production_sqlite_fingerprint()
os.environ["AI_MEDIA_OS_TESTING"] = "1"
_subprocess_guard_directory = ROOT / "tests" / "pytest_subprocess_guard"
_python_path_entries = [str(_subprocess_guard_directory), str(ROOT)]
if os.environ.get("PYTHONPATH"):
    _python_path_entries.append(os.environ["PYTHONPATH"])
os.environ["PYTHONPATH"] = os.pathsep.join(_python_path_entries)


if not getattr(sqlite3, "_ai_media_os_guard_installed", False):
    _original_sqlite_connect = sqlite3.connect

    def _guarded_sqlite_connect(database: Any, *args: Any, **kwargs: Any):
        assert_database_target_allowed(
            database,
            operation="sqlite3.connect during pytest",
            testing=True,
        )
        return _original_sqlite_connect(database, *args, **kwargs)

    sqlite3.connect = _guarded_sqlite_connect
    sqlite3.dbapi2.connect = _guarded_sqlite_connect
    sqlite3._ai_media_os_guard_installed = True


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    after = production_sqlite_fingerprint()
    session.config._production_sqlite_fingerprint_after = after
    if _material_fingerprint(after) != _material_fingerprint(
        PRODUCTION_FINGERPRINT_BEFORE
    ):
        session.exitstatus = 1
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_sep(
                "!",
                "PRODUCTION SQLITE FILE GUARD FAILED: DB/WAL/SHM content changed",
                red=True,
            )
