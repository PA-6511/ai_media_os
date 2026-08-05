from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "one_shot_recheck_policy.json"
)
REQUEST = ROOT / (
    "exchange/examples/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "recheck_execute_request.example.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m4_"
    "execute_now_approval.json"
)
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "authorization.json"
)
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "consumption.json"
)
RECHECK = ROOT / (
    "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "result.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m4_result.json"
)
RUNNER = ROOT / (
    "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_m4.py"
)
PARSER_RUNNER = ROOT / (
    "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_m2.py"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m4_"
    "post_parser_fix_dmm_recheck_report.md"
)
EVIDENCE_CHAIN_FIXTURE_ROOT = ROOT / (
    "tests/fixtures/ls_new_batch_4g_2e_recovery/"
    "phase_m2_fix1_parser_runner_evidence_chain"
)
EVIDENCE_CHAIN_ERROR = (
    "HISTORICAL_M2_RUNNER_EVIDENCE_CHAIN_"
    "INTEGRITY_FAILED"
)
HISTORICAL_PARSER_SHA256 = (
    "adfe2cbb8478458e8940eb0d67de4aa8"
    "e223ba6923353a2f0f0dc4d35e37e35f"
)
CURRENT_PARSER_SHA256 = (
    "f28ec2df1816e102673831ea9e8dfde0d"
    "b2df7df668324925f6b7f1441e306aa"
)
EXPECTED_EVIDENCE = {
    "M2_FIX1_RESULT": (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m2_fix1_result.json",
        "3f1069131bc662359fd015731637586f4"
        "c2327cbb8167c9604a718d0782c309f",
    ),
    "M2_FIX1_APPROVAL": (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m2_fix1_"
        "parser_remediation_approval.json",
        "a756fa0728c57959223d6087cb0ad0c1"
        "2c58b27f78333eced6b231ea6ac7ebaa",
    ),
    "M3_RESULT": (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m3_result.json",
        "246fe75ddbc71178c3d1b6819046472f"
        "8ba05ec5308a7814e025851b8e1ca5bf",
    ),
    "M3_AUTHORIZATION": (
        "exchange/authorizations/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_latest_alias_recheck_post_parser_fix_"
        "authorization.json",
        "39c77b363e39e2be287d009a3df3624d"
        "9dca7d510a93156309ee02d53110c541",
    ),
    "M4_EXECUTE_REQUEST": (
        "exchange/examples/"
        "new_release_wp_fresh_dmm_post_parser_fix_"
        "recheck_execute_request.example.json",
        "534bebe861761f1166f96009423c69ab"
        "247245ea7392c38adedddac2503f257f",
    ),
    "M4_EXECUTE_APPROVAL": (
        "exchange/approvals/"
        "ls_new_batch_4g_2e_recovery_m4_"
        "execute_now_approval.json",
        "db9934ae308700ad8dfd8c7c9e200e1"
        "84c611dbbc1fa7537ef23cd5ba2db767a",
    ),
    "M4_RECHECK_RESULT": (
        "exchange/rechecks/new_release/fresh/"
        "new-release-comic-20260703-001."
        "dmm_latest_alias_recheck_post_parser_fix_"
        "result.json",
        "2d921454f02f4d670bfae53447abc520"
        "ff9ee5c47ce1f92b737bf578d93365a2",
    ),
    "M4_FIX1_RESULT": (
        "exchange/logs/"
        "ls_new_batch_4g_2e_recovery_m4_fix1_result.json",
        "e45ff091abc12010d9d6f04985571a33"
        "ad7b88b0c0600aaa999f0f8893a6c511",
    ),
}


def load(path: Path) -> dict:
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


def evidence_chain_fail(detail: str) -> None:
    raise AssertionError(
        f"{EVIDENCE_CHAIN_ERROR}: {detail}"
    )


def evidence_chain_require(
    condition: bool,
    detail: str,
) -> None:
    if not condition:
        evidence_chain_fail(detail)


def load_evidence_json(
    path: Path,
    label: str,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        evidence_chain_fail(
            f"{label} is not valid JSON: {exc}"
        )

    evidence_chain_require(
        isinstance(value, dict),
        f"{label} must be a JSON object",
    )
    return value


def parse_evidence_time(
    value: object,
    label: str,
) -> datetime:
    evidence_chain_require(
        isinstance(value, str),
        f"{label} timestamp missing",
    )
    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        evidence_chain_fail(
            f"{label} timestamp invalid: {exc}"
        )
    evidence_chain_require(
        parsed.tzinfo is not None,
        f"{label} timestamp must include timezone",
    )
    return parsed


def verify_evidence_chain_fixture() -> tuple[
    dict[str, Any],
    dict[str, dict[str, Any]],
]:
    fixture_root = EVIDENCE_CHAIN_FIXTURE_ROOT
    manifest_path = fixture_root / "fixture_manifest.json"

    evidence_chain_require(
        fixture_root.is_dir()
        and not fixture_root.is_symlink(),
        "fixture root missing or unsafe",
    )
    evidence_chain_require(
        manifest_path.is_file()
        and not manifest_path.is_symlink(),
        "manifest missing or unsafe",
    )
    evidence_chain_require(
        manifest_path.stat().st_nlink == 1,
        "manifest hard link prohibited",
    )
    evidence_chain_require(
        {
            path.name
            for path in fixture_root.iterdir()
        }
        == {"fixture_manifest.json"},
        "manifest-external fixture file detected",
    )

    manifest = load_evidence_json(
        manifest_path,
        "fixture manifest",
    )
    expected_manifest = {
        "fixture_id": (
            "LS_NEW_BATCH_4G_2E_M2_FIX1_"
            "PARSER_RUNNER_EVIDENCE_CHAIN"
        ),
        "purpose": (
            "Verify the formal M2-FIX1 through M4-FIX1 runner "
            "SHA evidence chain without claiming availability or "
            "verification of the historical source body"
        ),
        "historical_source_path": (
            "scripts/execute_ls_new_batch_4g_2e_recovery_m2.py"
        ),
        "historical_source_sha256": HISTORICAL_PARSER_SHA256,
        "current_source_sha256": CURRENT_PARSER_SHA256,
        "source_body_available": False,
        "source_body_reproducible": False,
        "assurance_level": "EVIDENCE_CHAIN_ONLY",
        "unresolved_provenance_gap": True,
        "synthetic_source_created": False,
        "source_phase": "M2-FIX1",
        "consumer_phase": "M4",
        "superseded_by_phase": "M4-FIX1",
        "immutable": True,
    }
    for field, expected in expected_manifest.items():
        evidence_chain_require(
            manifest.get(field) == expected,
            f"manifest field mismatch: {field}",
        )

    evidence_chain_require(
        manifest.get("update_policy")
        == {
            "mode": "IMMUTABLE",
            "historical_hash_change_allowed": False,
            "synthetic_source_addition_allowed": False,
            "source_body_claim_requires_authoritative_body": True,
        },
        "manifest update policy invalid",
    )
    parse_evidence_time(
        manifest.get("created_at"),
        "manifest created_at",
    )

    entries = manifest.get("provenance_evidence")
    evidence_chain_require(
        isinstance(entries, list),
        "provenance evidence list missing",
    )
    evidence_chain_require(
        len(entries) == len(EXPECTED_EVIDENCE),
        "provenance evidence count mismatch",
    )

    parsed_evidence: dict[str, dict[str, Any]] = {}
    seen_roles: set[str] = set()
    for entry in entries:
        evidence_chain_require(
            isinstance(entry, dict),
            "provenance evidence entry invalid",
        )
        role = entry.get("evidence_role")
        evidence_chain_require(
            isinstance(role, str)
            and role in EXPECTED_EVIDENCE
            and role not in seen_roles,
            "provenance evidence role invalid",
        )
        seen_roles.add(role)

        expected_path, expected_sha = EXPECTED_EVIDENCE[role]
        evidence_chain_require(
            entry
            == {
                "evidence_role": role,
                "path": expected_path,
                "sha256": expected_sha,
            },
            f"provenance evidence manifest mismatch: {role}",
        )

        relative = Path(expected_path)
        evidence_chain_require(
            not relative.is_absolute()
            and ".." not in relative.parts,
            f"unsafe provenance path: {role}",
        )
        path = ROOT / relative
        evidence_chain_require(
            path.is_file() and not path.is_symlink(),
            f"provenance evidence missing or unsafe: {role}",
        )
        evidence_chain_require(
            file_sha256(path) == expected_sha,
            f"provenance evidence SHA mismatch: {role}",
        )
        parsed_evidence[role] = load_evidence_json(
            path,
            role,
        )

    evidence_chain_require(
        seen_roles == set(EXPECTED_EVIDENCE),
        "provenance evidence roles incomplete",
    )
    evidence_chain_require(
        PARSER_RUNNER.is_file()
        and not PARSER_RUNNER.is_symlink(),
        "current parser runner missing or unsafe",
    )
    evidence_chain_require(
        file_sha256(PARSER_RUNNER)
        == CURRENT_PARSER_SHA256,
        "current parser runner SHA mismatch",
    )
    evidence_chain_require(
        CURRENT_PARSER_SHA256
        != HISTORICAL_PARSER_SHA256,
        "current parser must remain a distinct successor",
    )

    return manifest, parsed_evidence


def test_policy_is_one_shot_get_only() -> None:
    policy = load(POLICY)
    contract = policy["request_contract"]

    assert contract["method"] == "GET"
    assert contract["automatic_retry_allowed"] is False
    assert contract["authentication_allowed"] is False
    assert contract["cookie_send_allowed"] is False
    assert contract["request_body_allowed"] is False
    assert (
        contract["proxy_environment_use_allowed"]
        is False
    )


def test_execute_approval_digest() -> None:
    approval = load(APPROVAL)
    comparable = copy.deepcopy(
        approval
    )
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval["human_explicit_approval"] is True


def test_source_authorization_is_preserved() -> None:
    request = load(REQUEST)
    authorization = load(AUTHORIZATION)

    assert (
        file_sha256(AUTHORIZATION)
        == request["source_bindings"][
            "m3_authorization_file_sha256"
        ]
    )
    assert (
        authorization["authorization_consumed"]
        is False
    )


def test_consumption_evidence_digest() -> None:
    evidence = load(CONSUMPTION)
    comparable = copy.deepcopy(
        evidence
    )
    stored = comparable.pop(
        "post_fix_consumption_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert evidence["authorization_consumed"] is True
    assert evidence["consumption_is_authoritative"] is True
    assert (
        evidence["authorization_reuse_allowed"]
        is False
    )
    assert (
        evidence["automatic_retry_allowed"]
        is False
    )


def test_recheck_result_digest() -> None:
    result = load(RECHECK)
    comparable = copy.deepcopy(
        result
    )
    stored = comparable.pop(
        "post_fix_dmm_recheck_result_digest_sha256"
    )

    assert digest(comparable) == stored


def test_result_binds_consumption() -> None:
    recheck = load(RECHECK)
    consumption = load(CONSUMPTION)

    assert (
        recheck[
            "consumption_evidence_digest_sha256"
        ]
        == consumption[
            "post_fix_consumption_evidence_digest_sha256"
        ]
    )
    assert (
        recheck["attempt_id"]
        == consumption["attempt_id"]
    )


def test_remediated_parser_hash_is_bound() -> None:
    manifest, evidence = (
        verify_evidence_chain_fixture()
    )

    m2_fix1 = evidence["M2_FIX1_RESULT"]
    m2_approval = evidence["M2_FIX1_APPROVAL"]
    m3_result = evidence["M3_RESULT"]
    m3_authorization = evidence["M3_AUTHORIZATION"]
    m4_request = evidence["M4_EXECUTE_REQUEST"]
    m4_approval = evidence["M4_EXECUTE_APPROVAL"]
    m4_recheck = evidence["M4_RECHECK_RESULT"]
    m4_fix1 = evidence["M4_FIX1_RESULT"]

    historical_bindings = [
        (
            "M2-FIX1 result",
            m2_fix1["remediation"]["after_sha256"],
        ),
        (
            "M3 result",
            m3_result["remediated_runner_file_sha256"],
        ),
        (
            "M3 authorization",
            m3_authorization["parser_binding"][
                "runner_file_sha256"
            ],
        ),
        (
            "M4 execute request",
            m4_request["source_bindings"][
                "remediated_runner_file_sha256"
            ],
        ),
        (
            "M4 execute approval target",
            m4_approval["approved_target"][
                "remediated_runner_sha256"
            ],
        ),
        (
            "M4 execute approval source binding",
            m4_approval["source_bindings"][
                "remediated_runner_file_sha256"
            ],
        ),
        (
            "M4 recheck result",
            m4_recheck["parser_binding"][
                "runner_file_sha256"
            ],
        ),
        (
            "M4-FIX1 before binding",
            m4_fix1["volume_remediation"][
                "before_sha256"
            ],
        ),
    ]
    for label, binding in historical_bindings:
        evidence_chain_require(
            binding == HISTORICAL_PARSER_SHA256,
            f"historical parser binding mismatch: {label}",
        )

    evidence_chain_require(
        m4_fix1["volume_remediation"]["after_sha256"]
        == CURRENT_PARSER_SHA256,
        "M4-FIX1 successor parser binding mismatch",
    )
    evidence_chain_require(
        m4_fix1["canonical_binding_remediation"][
            "expected_parser_sha256"
        ]
        == CURRENT_PARSER_SHA256,
        "M4-FIX1 parser loader binding mismatch",
    )
    evidence_chain_require(
        file_sha256(PARSER_RUNNER)
        == CURRENT_PARSER_SHA256,
        "current parser runner is not the M4-FIX1 successor",
    )

    evidence_chain_require(
        m2_approval["human_explicit_approval"] is True
        and m2_approval["approved_change"][
            "parser_patch_allowed"
        ]
        is True,
        "M2-FIX1 remediation approval invalid",
    )
    evidence_chain_require(
        m3_result["remediated_parser_bound"] is True
        and m3_authorization["parser_binding"][
            "null_safe_meta_fallback_verified"
        ]
        is True,
        "M3 parser authorization contract invalid",
    )
    evidence_chain_require(
        m4_request["phase_id"]
        == "LS-NEW-BATCH-4G-2E-RECOVERY-M4"
        and m4_approval["human_explicit_approval"] is True,
        "M4 execute request or approval invalid",
    )
    evidence_chain_require(
        m4_request["source_bindings"][
            "m2_fix1_result_file_sha256"
        ]
        == EXPECTED_EVIDENCE["M2_FIX1_RESULT"][1]
        and m4_request["source_bindings"][
            "m3_result_file_sha256"
        ]
        == EXPECTED_EVIDENCE["M3_RESULT"][1]
        and m4_request["source_bindings"][
            "m3_authorization_file_sha256"
        ]
        == EXPECTED_EVIDENCE["M3_AUTHORIZATION"][1],
        "M4 request source evidence SHA chain invalid",
    )

    m2_fixed_at = parse_evidence_time(
        m2_fix1["fixed_at_utc"],
        "M2-FIX1 fixed_at",
    )
    m3_authorized_at = parse_evidence_time(
        m3_authorization["authorized_at_utc"],
        "M3 authorized_at",
    )
    m4_approved_at = parse_evidence_time(
        m4_approval["approved_at_utc"],
        "M4 approved_at",
    )
    m4_completed_at = parse_evidence_time(
        m4_recheck["completed_at_utc"],
        "M4 completed_at",
    )
    m4_fix1_fixed_at = parse_evidence_time(
        m4_fix1["fixed_at_utc"],
        "M4-FIX1 fixed_at",
    )
    evidence_chain_require(
        m2_fixed_at
        < m3_authorized_at
        < m4_approved_at
        < m4_completed_at
        < m4_fix1_fixed_at,
        "M2-FIX1 through M4-FIX1 timeline invalid",
    )

    evidence_chain_require(
        manifest["assurance_level"]
        == "EVIDENCE_CHAIN_ONLY"
        and manifest["source_body_available"] is False
        and manifest["source_body_reproducible"] is False
        and manifest["unresolved_provenance_gap"] is True
        and manifest["synthetic_source_created"] is False,
        "historical source-body limitation contract invalid",
    )


def test_request_used_no_auth_cookie_or_proxy() -> None:
    request = load(RECHECK)["request"]

    assert request["method"] == "GET"
    assert request["request_body_used"] is False
    assert request["authentication_used"] is False
    assert request["login_used"] is False
    assert request["cookie_sent"] is False
    assert request["cookie_persisted"] is False
    assert request["credential_file_read"] is False
    assert request["proxy_environment_used"] is False
    assert request["automatic_retry_performed"] is False


def test_redirect_chain_is_allowlisted() -> None:
    network = load(RECHECK)["network"]

    assert network["redirect_count"] <= 5

    for redirect in network[
        "redirect_chain"
    ]:
        parsed = urlparse(
            redirect["to_url"]
        )

        assert parsed.scheme == "https"
        assert parsed.hostname == "book.dmm.com"
        assert parsed.username is None
        assert parsed.password is None


def test_only_allowlisted_headers_saved() -> None:
    headers = load(RECHECK)[
        "network"
    ]["response_headers_allowlisted"]

    allowed = {
        "content-type",
        "content-encoding",
        "location",
        "last-modified",
        "etag",
    }

    assert set(headers).issubset(
        allowed
    )
    assert "set-cookie" not in headers
    assert "cookie" not in headers


def test_full_response_body_not_persisted() -> None:
    result = load(RECHECK)
    serialized = json.dumps(
        result,
        ensure_ascii=False,
    )

    assert (
        result["network"][
            "full_response_body_persisted"
        ]
        is False
    )

    for forbidden in [
        "response_body_base64",
        "response_body_text",
        "raw_html",
        "full_html",
    ]:
        assert forbidden not in serialized


def test_decision_is_consistent() -> None:
    result = load(RECHECK)
    success = result[
        "verification"
    ]["successful_match"]

    if success:
        assert result["dmm_slot_available"] is True
        assert (
            result["dmm_slot_must_be_hidden"]
            is False
        )
        assert (
            result["human_review_required"]
            is False
        )
    else:
        assert result["dmm_slot_available"] is False
        assert (
            result["dmm_slot_must_be_hidden"]
            is True
        )
        assert (
            result["human_review_required"]
            is True
        )


def test_canonical_binding_is_consistent() -> None:
    result = load(RECHECK)
    verification = result[
        "verification"
    ]

    if verification["successful_match"]:
        assert (
            verification[
                "canonical_product_url_resolved"
            ]
            is True
        )
        assert (
            verification[
                "canonical_product_binding_to_expected_series"
            ]
            is True
        )


def test_historical_artifacts_are_preserved() -> None:
    request = load(REQUEST)
    bindings = request[
        "source_bindings"
    ]

    for path_field, hash_field in [
        (
            "old_m2_result_path",
            "old_m2_result_file_sha256",
        ),
        (
            "old_m2_recheck_result_path",
            "old_m2_recheck_result_file_sha256",
        ),
        (
            "old_m2_consumption_path",
            "old_m2_consumption_file_sha256",
        ),
        (
            "old_m2_execute_approval_path",
            "old_m2_execute_approval_file_sha256",
        ),
        (
            "old_m1_authorization_path",
            "old_m1_authorization_file_sha256",
        ),
        (
            "m2_fix1_result_path",
            "m2_fix1_result_file_sha256",
        ),
    ]:
        path = ROOT / bindings[
            path_field
        ]

        assert file_sha256(path) == (
            bindings[hash_field]
        )


def test_article_and_plan_are_preserved() -> None:
    request = load(REQUEST)
    bindings = request[
        "source_bindings"
    ]

    for path_field, hash_field in [
        (
            "generated_article_path",
            "generated_article_file_sha256",
        ),
        (
            "store_link_plan_path",
            "store_link_plan_file_sha256",
        ),
    ]:
        path = ROOT / bindings[
            path_field
        ]

        assert file_sha256(path) == (
            bindings[hash_field]
        )


def test_no_final_affiliate_link_generated() -> None:
    recheck = load(RECHECK)
    result = load(RESULT)

    assert (
        recheck["final_affiliate_link_generated"]
        is False
    )
    assert (
        result["final_affiliate_link_generated"]
        is False
    )
    assert (
        result["final_affiliate_link_validated"]
        is False
    )


def test_production_boundary_remains_closed() -> None:
    result = load(RESULT)

    assert result["article_modified"] is False
    assert (
        result[
            "article_url_injection_performed"
        ]
        is False
    )
    assert result["fresh_payload_created"] is False
    assert result["payload_binding_complete"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert (
        result["wordpress_access_performed"]
        is False
    )
    assert (
        result["wordpress_write_performed"]
        is False
    )
    assert result["wordpress_published"] is False
    assert result["execution_allowed"] is False
    assert result["production_status"] == "NO_GO"


def test_rerun_is_blocked_without_changes() -> None:
    consumption_before = file_sha256(
        CONSUMPTION
    )
    recheck_before = file_sha256(
        RECHECK
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

    assert blocked["status"] == (
        "BLOCKED_POST_FIX_DMM_RECHECK_"
        "AUTHORIZATION_ALREADY_CONSUMED"
    )
    assert (
        blocked["authorization_reuse_allowed"]
        is False
    )
    assert (
        blocked["automatic_retry_allowed"]
        is False
    )

    assert (
        file_sha256(CONSUMPTION)
        == consumption_before
    )
    assert (
        file_sha256(RECHECK)
        == recheck_before
    )


def test_result_records_terminal_state() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_DMM_POST_REMEDIATION_ONE_SHOT_"
        "RECHECK_EXECUTED_AUTH_CONSUMED_"
        "NO_LINK_GENERATION"
    )
    assert result["authorization_consumed"] is True
    assert result["consumption_evidence_created"] is True
    assert (
        result["authorization_reuse_allowed"]
        is False
    )
    assert (
        result["automatic_retry_allowed"]
        is False
    )
    assert result["network_attempt_performed"] is True


def test_report_confirms_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Authorization consumed: `true`" in report
    assert "Authorization reuse allowed: `false`" in report
    assert "Automatic retry allowed: `false`" in report
    assert "Full response body persisted: `false`" in report
    assert "Final affiliate link generated: `false`" in report
    assert "Article modified: `false`" in report
    assert "Production status: `NO_GO`" in report
