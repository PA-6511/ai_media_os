from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]

RUNNER = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_m2.py"
)
POLICY = (
    ROOT
    / "config/"
    "new_release_wp_fresh_dmm_recheck_"
    "parser_failure_remediation_policy.json"
)
APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m2_fix1_"
    "parser_remediation_approval.json"
)
M2_RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m2_result.json"
)
RECHECK = (
    ROOT
    / "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_result.json"
)
CONSUMPTION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_consumption.json"
)
EXECUTE_APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m2_"
    "execute_now_approval.json"
)


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def load_runner_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "recovery_m2_fix1_runner",
        RUNNER,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


def test_policy_is_offline_remediation_only() -> None:
    policy = load_json(POLICY)
    boundary = policy["execution_boundary"]

    assert boundary["parser_source_patch_allowed"] is True
    assert (
        boundary["regression_test_creation_allowed"]
        is True
    )
    assert (
        boundary[
            "new_recheck_authorization_creation_allowed"
        ]
        is False
    )
    assert (
        boundary["existing_authorization_reuse_allowed"]
        is False
    )
    assert boundary["network_connection_allowed"] is False
    assert boundary["http_request_allowed"] is False
    assert boundary["dmm_recheck_allowed"] is False
    assert boundary["wordpress_access_allowed"] is False


def test_remediation_approval_digest() -> None:
    approval = load_json(APPROVAL)
    comparable = copy.deepcopy(approval)
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval["human_explicit_approval"] is True
    assert (
        approval["approval_label"]
        == (
            "DMM_RECHECK_PARSER_FAILURE_"
            "REMEDIATION_APPROVED"
        )
    )


def test_null_safe_patch_is_present() -> None:
    source = RUNNER.read_text(
        encoding="utf-8"
    )

    assert '''            name = (
                values.get("property")
                or values.get("name")
                or ""
            ).lower()
''' in source

    assert '''            name = (
                values.get("property")
                or values.get("name")
            ).lower()
''' not in source


def test_meta_without_property_or_name_is_safe() -> None:
    module = load_runner_module()
    parser = module.MinimalPageParser()

    parser.feed(
        '<meta charset="utf-8">'
        '<meta content="value">'
    )

    assert parser.meta == {}


def test_meta_none_attribute_values_are_safe() -> None:
    module = load_runner_module()
    parser = module.MinimalPageParser()

    parser.handle_starttag(
        "meta",
        [
            ("name", None),
            ("property", None),
            ("content", None),
        ],
    )

    assert parser.meta == {}


def test_normal_meta_is_captured() -> None:
    module = load_runner_module()
    parser = module.MinimalPageParser()

    parser.feed(
        '<meta property="og:title" '
        'content="ダークギャザリング 第20巻">'
        '<meta name="author" '
        'content="近藤憲一">'
    )

    assert parser.meta["og:title"] == [
        "ダークギャザリング 第20巻"
    ]
    assert parser.meta["author"] == [
        "近藤憲一"
    ]


def test_canonical_link_is_captured() -> None:
    module = load_runner_module()
    parser = module.MinimalPageParser()

    parser.feed(
        '<link rel="alternate canonical" '
        'href="https://book.dmm.com/'
        'product/861056/example-product/">'
    )

    assert parser.canonical_urls == [
        (
            "https://book.dmm.com/"
            "product/861056/example-product/"
        )
    ]


def test_json_ld_and_identity_extraction() -> None:
    module = load_runner_module()

    html = """
    <html>
      <head>
        <title>ダークギャザリング 第20巻</title>
        <meta name="author" content="近藤憲一">
        <link
          rel="canonical"
          href="https://book.dmm.com/product/861056/example-product/"
        >
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Book",
          "name": "ダークギャザリング 第20巻",
          "author": {"name": "近藤憲一"},
          "publisher": {"name": "集英社"},
          "url": "https://book.dmm.com/product/861056/example-product/"
        }
        </script>
      </head>
      <body>
        ダークギャザリング 第20巻 近藤憲一 集英社
      </body>
    </html>
    """

    extracted = module.extract_identity(
        decoded_body=html.encode("utf-8"),
        charset="utf-8",
        target_url=(
            "https://book.dmm.com/"
            "product/861056/latest/"
        ),
        final_url=(
            "https://book.dmm.com/"
            "product/861056/latest/"
        ),
    )

    assert (
        extracted[
            "identity_matches"
        ]["work_title_match"]
        is True
    )
    assert (
        extracted[
            "identity_matches"
        ]["volume_match"]
        is True
    )
    assert (
        extracted[
            "identity_matches"
        ]["author_match"]
        is True
    )
    assert (
        extracted[
            "identity_matches"
        ]["publisher_match"]
        is True
    )
    assert (
        extracted[
            "identity_matches"
        ]["series_identity_match"]
        is True
    )
    assert (
        extracted[
            "identity_matches"
        ]["canonical_product_url_resolved"]
        is True
    )
    assert (
        extracted[
            "all_required_identity_fields_match"
        ]
        is True
    )


def test_historical_m2_artifacts_are_unchanged() -> None:
    approval = load_json(APPROVAL)
    bindings = approval[
        "historical_source_bindings"
    ]["bindings"]

    path_map = {
        "m2_result": M2_RESULT,
        "m2_recheck_result": RECHECK,
        "m2_consumption": CONSUMPTION,
        "m2_execute_approval": EXECUTE_APPROVAL,
    }

    for label, path in path_map.items():
        assert (
            file_sha256(path)
            == bindings[label]["file_sha256"]
        )

    recheck = load_json(RECHECK)

    assert (
        recheck["network"]["response_body_sha256"]
        == (
            "23e47df44282982a6b92d07d5137d1d8"
            "97c070e9e611c18779bcab720378ee53"
        )
    )
    assert (
        recheck["network"]["network_error_type"]
        == "AttributeError"
    )


def test_consumed_authorization_rerun_stays_blocked() -> None:
    recheck_before = file_sha256(RECHECK)
    consumption_before = file_sha256(
        CONSUMPTION
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--execute",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    blocked = json.loads(
        completed.stderr
    )

    assert (
        blocked["status"]
        == (
            "BLOCKED_DMM_RECHECK_"
            "AUTHORIZATION_ALREADY_CONSUMED"
        )
    )
    assert (
        blocked["authorization_reuse_allowed"]
        is False
    )
    assert (
        blocked["automatic_retry_allowed"]
        is False
    )

    assert file_sha256(RECHECK) == recheck_before
    assert (
        file_sha256(CONSUMPTION)
        == consumption_before
    )
