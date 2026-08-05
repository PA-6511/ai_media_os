from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]

PARSER = ROOT / (
    "scripts/execute_ls_new_batch_4g_2e_recovery_m2.py"
)
M4_RUNNER = ROOT / (
    "scripts/execute_ls_new_batch_4g_2e_recovery_m4.py"
)
POLICY = ROOT / (
    "config/new_release_wp_fresh_dmm_volume_"
    "canonical_binding_remediation_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m4_fix1_"
    "volume_canonical_remediation_approval.json"
)
M4_RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m4_result.json"
)
M4_RECHECK = ROOT / (
    "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_result.json"
)
M4_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_consumption.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def load_module(
    path: Path,
    name: str,
) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parser_module() -> ModuleType:
    return load_module(PARSER, "m4_fix1_parser")


def m4_module() -> ModuleType:
    return load_module(M4_RUNNER, "m4_fix1_runner")


def test_policy_is_offline_only() -> None:
    boundary = load_json(POLICY)["execution_boundary"]

    assert boundary["parser_source_patch_allowed"] is True
    assert boundary[
        "canonical_binding_source_patch_allowed"
    ] is True
    assert boundary[
        "runner_hash_binding_update_allowed"
    ] is True
    assert boundary[
        "historical_result_reclassification_allowed"
    ] is False
    assert boundary[
        "new_authorization_creation_allowed"
    ] is False
    assert boundary["network_connection_allowed"] is False
    assert boundary["http_request_allowed"] is False
    assert boundary["dmm_recheck_allowed"] is False


def test_approval_digest() -> None:
    approval = load_json(APPROVAL)
    comparable = copy.deepcopy(approval)
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval["human_explicit_approval"] is True


@pytest.mark.parametrize(
    "candidate",
    [
        "ダークギャザリング 20",
        "ダークギャザリング 20(最新刊)",
        "ダークギャザリング 20（最新刊）",
        "ダークギャザリング 20巻",
        "ダークギャザリング 第20巻",
    ],
)
def test_supported_volume_notations(
    candidate: str,
) -> None:
    module = parser_module()

    value, source = (
        module.extract_expected_volume_from_title_candidates(
            [candidate],
            expected_work_title="ダークギャザリング",
            expected_volume_number=20,
        )
    )

    assert value == "第20巻"
    assert source == (
        "TITLE_OR_STRUCTURED_DATA_"
        "WORK_BOUND_VOLUME"
    )


@pytest.mark.parametrize(
    "candidate",
    [
        "ダークギャザリング 120",
        "ダークギャザリング 200",
        "ダークギャザリング 20円",
        "ダークギャザリング 価格20円",
        "ダークギャザリング 20%OFF",
        "別作品 20(最新刊)",
    ],
)
def test_volume_false_positives_rejected(
    candidate: str,
) -> None:
    module = parser_module()

    value, source = (
        module.extract_expected_volume_from_title_candidates(
            [candidate],
            expected_work_title="ダークギャザリング",
            expected_volume_number=20,
        )
    )

    assert value is None
    assert source is None


def test_historical_title_now_resolves() -> None:
    module = parser_module()
    identity = load_json(M4_RECHECK)[
        "extracted_identity"
    ]

    value, source = (
        module.extract_expected_volume_from_title_candidates(
            identity["page_title_candidates"],
            expected_work_title="ダークギャザリング",
            expected_volume_number=20,
        )
    )

    assert value == "第20巻"
    assert source is not None


def test_full_identity_extraction() -> None:
    module = parser_module()

    html = """
    <html>
      <head>
        <title>
          ダークギャザリング 20(最新刊) -
          近藤憲一 - 少年マンガ - DMMブックス
        </title>
        <meta name="author" content="近藤憲一">
        <meta
          property="og:url"
          content="https://book.dmm.com/product/861056/b950yshes32617/"
        >
        <script type="application/ld+json">
        {
          "@type": "Book",
          "name": "ダークギャザリング 20",
          "author": {"name": "近藤憲一"},
          "publisher": {"name": "集英社"},
          "url": "https://book.dmm.com/product/861056/b950yshes32617/"
        }
        </script>
      </head>
      <body>ダークギャザリング 近藤憲一 集英社</body>
    </html>
    """

    extracted = module.extract_identity(
        decoded_body=html.encode("utf-8"),
        charset="utf-8",
        target_url=(
            "https://book.dmm.com/product/861056/latest/"
        ),
        final_url=(
            "https://book.dmm.com/product/861056/latest/"
        ),
    )

    assert extracted["extracted_volume"] == "第20巻"
    assert extracted[
        "all_required_identity_fields_match"
    ] is True


def test_valid_canonical_binding() -> None:
    module = m4_module()

    assert module.canonical_product_url_binds_to_expected_series(
        "https://book.dmm.com/product/861056/b950yshes32617/",
        expected_series_id="861056",
    ) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://book.dmm.com/product/999999/b950yshes32617/",
        "https://book.dmm.com/product/861056/latest/",
        "https://book.dmm.com/product/861056/",
        "https://book.dmm.com/product/861056/b950yshes32617/extra/",
        "https://example.com/product/861056/b950yshes32617/",
        "http://book.dmm.com/product/861056/b950yshes32617/",
        "https://book.dmm.com:443/product/861056/b950yshes32617/",
        "https://book.dmm.com/product/861056/b950yshes32617/?x=1",
        "https://book.dmm.com/product/861056/b950yshes32617/#x",
    ],
)
def test_invalid_canonical_bindings(
    url: str,
) -> None:
    module = m4_module()

    assert module.canonical_product_url_binds_to_expected_series(
        url,
        expected_series_id="861056",
    ) is False


def test_m4_parser_hash_binding_is_current() -> None:
    module = m4_module()

    assert module.EXPECTED_RUNNER_SHA256 == (
        file_sha256(PARSER)
    )

    loaded = module.load_parser_module()

    assert hasattr(
        loaded,
        "extract_expected_volume_from_title_candidates",
    )


def test_historical_result_unchanged() -> None:
    result = load_json(M4_RESULT)
    recheck = load_json(M4_RECHECK)

    assert result["successful_match"] is False
    assert result["failure_reason_codes"] == [
        "VOLUME_MISMATCH",
        "CANONICAL_PRODUCT_SERIES_BINDING_FAILED",
    ]
    assert recheck["verification"][
        "successful_match"
    ] is False
    assert recheck["network"]["response_body_sha256"] == (
        "c0c75847c2c048ee468937c2fdf2190f"
        "3ab5586226c9854e11513b2a74a88146"
    )


def test_historical_canonical_now_binds_offline() -> None:
    module = m4_module()
    canonical = load_json(M4_RECHECK)[
        "extracted_identity"
    ]["canonical_product_url"]

    assert module.canonical_product_url_binds_to_expected_series(
        canonical,
        expected_series_id="861056",
    ) is True


def test_consumed_authorization_rerun_blocked() -> None:
    recheck_before = file_sha256(M4_RECHECK)
    consumption_before = file_sha256(
        M4_CONSUMPTION
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(M4_RUNNER),
            "--execute",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    blocked = json.loads(completed.stderr)

    assert blocked["status"] == (
        "BLOCKED_POST_FIX_DMM_RECHECK_"
        "AUTHORIZATION_ALREADY_CONSUMED"
    )
    assert blocked[
        "authorization_reuse_allowed"
    ] is False
    assert blocked["automatic_retry_allowed"] is False

    assert file_sha256(M4_RECHECK) == recheck_before
    assert file_sha256(
        M4_CONSUMPTION
    ) == consumption_before
