from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

ARTICLE = ROOT / (
    "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m9_result.json"
)
M9_AUTH = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "article_dmm_link_injection_authorization.json"
)
FIXTURE_DIR = ROOT / (
    "tests/fixtures/ls_new_batch_4g_2e_recovery/"
    "phase_m9_failure_and_fix1_success"
)
FIXTURE_MANIFEST = FIXTURE_DIR / "fixture_manifest.json"
INTEGRITY_ERROR = (
    "HISTORICAL_M9_RESULT_CONTRACT_INTEGRITY_FAILED"
)
PREIMAGE_SHA256 = (
    "849a37519c6af70d2212ec01d5cddef5"
    "793bfa811e97ca9f248ce099a0350bf4"
)
POSTIMAGE_SHA256 = (
    "de2739c8ae1aa4a50973b983964b0584"
    "4086a2187b9ef337383ad6fa7123697d"
)
ORIGINAL_STATUS = (
    "FAILED_AFTER_M9_AUTHORIZATION_CONSUMPTION_"
    "NO_AUTOMATIC_RETRY"
)
FIX1_STATUS = (
    "PASS_DMM_ARTICLE_LINK_INJECTED_HTML_ENTITY_"
    "VALIDATOR_FIXED_NEW_AUTHORIZATION_CONSUMED_"
    "NO_NETWORK_NO_WORDPRESS"
)
EXPECTED_EVIDENCE = {
    "m8_result": (
        "exchange/logs/ls_new_batch_4g_2e_recovery_m8_result.json",
        "6bfecffb1c9b955a0482d2908522617b2eccbe5e9bedb64bbe1a83bd345132a8",
    ),
    "m8_fix1_approval": (
        "exchange/approvals/ls_new_batch_4g_2e_recovery_m8_fix1_html_validator_fix_approval.json",
        "fa3c9d65058bbce4464aa57f4303478267962e00b352a771c94e15fefb97eb26",
    ),
    "m8_fix1_result": (
        "exchange/logs/ls_new_batch_4g_2e_recovery_m8_fix1_result.json",
        "5c38021615d02b6abfde827a4de2653536e6bbc2b25f2c808f48b82b43414f57",
    ),
    "m9_approval": (
        "exchange/approvals/ls_new_batch_4g_2e_recovery_m9_execute_now_approval.json",
        "1d037c432a5aa61e70493d1f2e5dca75e63b27c4e044e532d0909c2d592e5443",
    ),
    "m9_authorization": (
        "exchange/authorizations/new_release/fresh/new-release-comic-20260703-001.article_dmm_link_injection_authorization.json",
        "8cec2c0c566b7e992fd3f822403d1c43f2558239aecf702de93190abb2ef83fd",
    ),
    "m9_consumption": (
        "exchange/authorizations/new_release/fresh/new-release-comic-20260703-001.article_dmm_link_injection_consumption.json",
        "7b34ad6e195d7cbe5bd061bc3edb9e001a8e2d914d956e22605dd901e67c655c",
    ),
    "m9_result": (
        "exchange/logs/ls_new_batch_4g_2e_recovery_m9_result.json",
        "4bfc26c714795030ad3c86aa5e3be0e5cd86c7622fface6cca77919053775526",
    ),
    "m9_fix1_approval": (
        "exchange/approvals/ls_new_batch_4g_2e_recovery_m9_fix1_approval.json",
        "d7b94fa3ce8ee3eae571fc826ce5da7bea546ac02f730ea95aa278a8d44b384c",
    ),
    "m9_fix1_authorization": (
        "exchange/authorizations/new_release/fresh/new-release-comic-20260703-001.article_dmm_link_injection_fix1_authorization.json",
        "737993fcf83236e610247bb5bc31c9d1966896a95b3ce602ff5d648aeb213df6",
    ),
    "m9_fix1_consumption": (
        "exchange/authorizations/new_release/fresh/new-release-comic-20260703-001.article_dmm_link_injection_fix1_consumption.json",
        "a5954bb426612296b997e26388c74f7996ac210d364b4ceca72694b81d302342",
    ),
    "m9_fix1_result": (
        "exchange/logs/ls_new_batch_4g_2e_recovery_m9_fix1_result.json",
        "d98695971f1ffb73c34958e2418a6c18155f6f8a31420c6ab2e3662114a383ab",
    ),
    "m10_approval": (
        "exchange/approvals/ls_new_batch_4g_2e_recovery_m10_gate_approval.json",
        "cdd0e18ae66467fe5454903afd195ff868b964c824542b9fac1b626fd45eacc1",
    ),
    "m10_review": (
        "exchange/reviews/new_release/fresh/new-release-comic-20260703-001.post_injection_article_human_review.json",
        "823b4ab68e1af22ea9a99d5d224604f950128ec69066a1904fc211f0f39ba4c3",
    ),
    "m10_result": (
        "exchange/logs/ls_new_batch_4g_2e_recovery_m10_result.json",
        "1a65a00b9ba8ae462665937819556799087b37c033590509ef3b6de133732ff5",
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parsed_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def verify_m9_evidence_contract() -> dict[str, Any]:
    try:
        assert FIXTURE_DIR.is_dir()
        assert not FIXTURE_DIR.is_symlink()
        assert {path.name for path in FIXTURE_DIR.iterdir()} == {
            "fixture_manifest.json"
        }
        assert FIXTURE_MANIFEST.is_file()
        assert not FIXTURE_MANIFEST.is_symlink()
        assert FIXTURE_MANIFEST.stat().st_nlink == 1

        manifest = load(FIXTURE_MANIFEST)
        assert manifest["fixture_id"] == (
            "LS_NEW_BATCH_4G_2E_M9_FAILURE_AND_FIX1_SUCCESS"
        )
        assert manifest["assurance_level"] == (
            "HASH_BOUND_SEPARATE_PHASE_EVIDENCE"
        )
        assert manifest["original_m9_assurance"] == (
            "IMMUTABLE_FAILURE_EVIDENCE"
        )
        assert manifest["fix1_assurance"] == (
            "SEPARATE_APPROVED_SUCCESS_EVIDENCE"
        )
        assert manifest["original_m9_status"] == ORIGINAL_STATUS
        assert manifest["fix1_status"] == FIX1_STATUS
        assert manifest["original_m9_article_preimage_sha256"] == PREIMAGE_SHA256
        assert manifest["original_m9_article_postcondition_sha256"] == PREIMAGE_SHA256
        assert manifest["fix1_preimage_sha256"] == PREIMAGE_SHA256
        assert manifest["fix1_postimage_sha256"] == POSTIMAGE_SHA256
        assert manifest["fix1_preimage_sha256"] != manifest["fix1_postimage_sha256"]
        assert manifest["automatic_retry_allowed"] is False
        assert manifest["original_result_overwritten"] is False
        assert manifest["synthetic_result_created"] is False
        assert manifest["immutable"] is True
        assert manifest["update_policy"] == (
            "Never rewrite historical evidence or synthesize a successful M9 result. "
            "Update only by adding a separately approved phase fixture with independently "
            "verified artifact hashes."
        )
        parsed_time(manifest["created_at"])

        entries = manifest["provenance_evidence"]
        by_role = {entry["role"]: entry for entry in entries}
        assert len(entries) == len(by_role) == len(EXPECTED_EVIDENCE)
        assert set(by_role) == set(EXPECTED_EVIDENCE)

        evidence: dict[str, dict[str, Any]] = {}
        for role, (relative, expected_sha) in EXPECTED_EVIDENCE.items():
            entry = by_role[role]
            assert entry == {
                "role": role,
                "path": relative,
                "sha256": expected_sha,
            }
            relative_path = Path(relative)
            assert not relative_path.is_absolute()
            assert ".." not in relative_path.parts
            artifact = ROOT / relative_path
            assert artifact.is_file()
            assert not artifact.is_symlink()
            assert file_sha256(artifact) == expected_sha
            evidence[role] = load(artifact)

        original_approval = evidence["m9_approval"]
        original_auth = evidence["m9_authorization"]
        original_consumption = evidence["m9_consumption"]
        original_result = evidence["m9_result"]
        fix1_approval = evidence["m9_fix1_approval"]
        fix1_auth = evidence["m9_fix1_authorization"]
        fix1_consumption = evidence["m9_fix1_consumption"]
        fix1_result = evidence["m9_fix1_result"]
        m8_fix1_result = evidence["m8_fix1_result"]
        m10_approval = evidence["m10_approval"]
        m10_review = evidence["m10_review"]
        m10_result = evidence["m10_result"]

        original_auth_id = (
            "DMM_ARTICLE_LINK_INJECTION_ONE_SHOT_AUTHORIZATION_V1"
        )
        fix1_auth_id = (
            "DMM_ARTICLE_LINK_INJECTION_FIX1_ONE_SHOT_AUTHORIZATION_V1"
        )
        original_auth_digest = (
            "d274eaf6bd14c95ac43031fbff296d0d47e6051dbb4231407327d376f93fec7f"
        )
        fix1_auth_digest = (
            "c25ddfa1023038f057ef0d403a00ffe1443f15097f8fc89c6402c7113d37b630"
        )

        approved_auth = original_approval["approved_authorization"]
        assert approved_auth["authorization_id"] == original_auth_id
        assert approved_auth["authorization_digest_sha256"] == original_auth_digest
        assert approved_auth["single_use"] is True
        assert approved_auth["reuse_allowed"] is False
        assert approved_auth["automatic_retry_allowed"] is False
        assert approved_auth["automatic_reissue_allowed"] is False
        assert original_approval["approved_article_preimage_sha256"] == PREIMAGE_SHA256
        assert original_approval["source_bindings"]["m9_authorization"]["file_sha256"] == EXPECTED_EVIDENCE["m9_authorization"][1]

        assert original_auth["authorization_id"] == original_auth_id
        assert original_auth["authorization_digest_sha256"] == original_auth_digest
        assert original_auth["article_preimage_binding"]["file_sha256"] == PREIMAGE_SHA256
        assert original_auth["single_use"] is True
        assert original_auth["authorization_consumed"] is False
        assert original_auth["authorization_reuse_allowed"] is False
        assert original_auth["automatic_retry_allowed"] is False
        assert original_auth["article_modified"] is False

        assert original_consumption["source_authorization_id"] == original_auth_id
        assert original_consumption["source_authorization_digest_sha256"] == original_auth_digest
        assert original_consumption["authorization_consumed"] is True
        assert original_consumption["execution_boundary_crossed"] is True
        assert original_consumption["consumed_before_article_mutation"] is True
        assert original_consumption["authorization_reuse_allowed"] is False
        assert original_consumption["automatic_retry_allowed"] is False
        assert original_consumption["automatic_reissue_allowed"] is False
        assert original_consumption["article_preimage_sha256"] == PREIMAGE_SHA256

        assert original_result["status"] == ORIGINAL_STATUS
        assert original_result["authorization_consumed"] is True
        assert original_result["authorization_reuse_allowed"] is False
        assert original_result["automatic_retry_allowed"] is False
        assert original_result["automatic_reissue_allowed"] is False
        assert original_result["manual_recovery_review_required"] is True
        assert original_result["production_status"] == "NO_GO"

        assert m8_fix1_result["article_file_sha256"] == PREIMAGE_SHA256
        assert m8_fix1_result["article_modified"] is False
        assert fix1_approval["old_m9_authorization_consumed"] is True
        assert fix1_approval["old_m9_authorization_reuse_allowed"] is False
        assert fix1_approval["source_bindings"]["article_preimage"]["file_sha256"] == PREIMAGE_SHA256
        for role in ("authorization", "consumption", "result"):
            bound = fix1_approval["source_bindings"]["old_m9"][role]
            expected_role = f"m9_{role}"
            assert bound["path"] == EXPECTED_EVIDENCE[expected_role][0]
            assert bound["file_sha256"] == EXPECTED_EVIDENCE[expected_role][1]

        assert fix1_auth["authorization_id"] == fix1_auth_id
        assert fix1_auth["authorization_id"] != original_auth_id
        assert fix1_auth["authorization_digest_sha256"] == fix1_auth_digest
        assert fix1_auth["article_preimage_sha256"] == PREIMAGE_SHA256
        assert fix1_auth["old_m9_failure_binding"]["authorization_digest_sha256"] == original_auth_digest
        assert fix1_auth["old_m9_failure_binding"]["authorization_consumed"] is True
        assert fix1_auth["old_m9_failure_binding"]["historical_error_code"] == original_result["error_code"]

        assert fix1_consumption["source_authorization_id"] == fix1_auth_id
        assert fix1_consumption["source_authorization_digest_sha256"] == fix1_auth_digest
        assert fix1_consumption["consumption_attempt_id"] != original_consumption["consumption_attempt_id"]
        assert fix1_consumption["authorization_consumed"] is True
        assert fix1_consumption["article_preimage_sha256"] == PREIMAGE_SHA256

        assert fix1_result["status"] == FIX1_STATUS
        assert fix1_result["authorization_path"] == EXPECTED_EVIDENCE["m9_fix1_authorization"][0]
        assert fix1_result["authorization_consumption_path"] == EXPECTED_EVIDENCE["m9_fix1_consumption"][0]
        assert fix1_result["consumption_attempt_id"] == fix1_consumption["consumption_attempt_id"]
        assert fix1_result["article_preimage_sha256"] == PREIMAGE_SHA256
        assert fix1_result["article_postimage_sha256"] == POSTIMAGE_SHA256
        assert fix1_result["old_m9_authorization_remains_consumed"] is True
        assert fix1_result["old_m9_artifacts_modified"] is False
        assert fix1_result["article_atomic_replacement_performed"] is True
        assert fix1_result["production_status"] == "NO_GO"
        assert file_sha256(ARTICLE) == POSTIMAGE_SHA256

        for role in ("authorization", "consumption", "result"):
            old_binding = m10_review["source_bindings"][f"old_m9_{role}"]
            fix_binding = m10_review["source_bindings"].get(f"m9_fix1_{role}")
            assert old_binding["file_sha256"] == EXPECTED_EVIDENCE[f"m9_{role}"][1]
            assert fix_binding["file_sha256"] == EXPECTED_EVIDENCE[f"m9_fix1_{role}"][1]
        assert m10_review["validation_results"]["old_m9_failure_evidence_preserved"] is True
        assert m10_review["validation_results"]["m9_fix1_result_verified"] is True
        assert m10_review["article_binding"]["preimage_sha256"] == PREIMAGE_SHA256
        assert m10_review["article_binding"]["postimage_sha256"] == POSTIMAGE_SHA256
        assert m10_approval["approved_article_postimage_sha256"] == POSTIMAGE_SHA256
        assert m10_result["review_file_sha256"] == EXPECTED_EVIDENCE["m10_review"][1]

        assert manifest["original_m9_result_path"] == EXPECTED_EVIDENCE["m9_result"][0]
        assert manifest["original_m9_result_sha256"] == EXPECTED_EVIDENCE["m9_result"][1]
        assert manifest["original_m9_authorization_path"] == EXPECTED_EVIDENCE["m9_authorization"][0]
        assert manifest["original_m9_authorization_sha256"] == EXPECTED_EVIDENCE["m9_authorization"][1]
        assert manifest["original_m9_consumption_path"] == EXPECTED_EVIDENCE["m9_consumption"][0]
        assert manifest["original_m9_consumption_sha256"] == EXPECTED_EVIDENCE["m9_consumption"][1]
        assert manifest["fix1_result_path"] == EXPECTED_EVIDENCE["m9_fix1_result"][0]
        assert manifest["fix1_result_sha256"] == EXPECTED_EVIDENCE["m9_fix1_result"][1]
        assert manifest["fix1_result_path"] != manifest["original_m9_result_path"]
        assert manifest["fix1_authorization_path"] == EXPECTED_EVIDENCE["m9_fix1_authorization"][0]
        assert manifest["fix1_authorization_sha256"] == EXPECTED_EVIDENCE["m9_fix1_authorization"][1]
        assert manifest["fix1_consumption_path"] == EXPECTED_EVIDENCE["m9_fix1_consumption"][0]
        assert manifest["fix1_consumption_sha256"] == EXPECTED_EVIDENCE["m9_fix1_consumption"][1]

        assert parsed_time(m8_fix1_result["completed_at_utc"]) < parsed_time(original_approval["approved_at_utc"])
        assert parsed_time(original_approval["approved_at_utc"]) < parsed_time(original_consumption["consumed_at_utc"])
        assert parsed_time(original_consumption["consumed_at_utc"]) < parsed_time(original_result["failed_at_utc"])
        assert parsed_time(original_result["failed_at_utc"]) < parsed_time(fix1_approval["approved_at_utc"])
        assert parsed_time(fix1_approval["approved_at_utc"]) < parsed_time(fix1_auth["authorized_at_utc"])
        assert parsed_time(fix1_auth["authorized_at_utc"]) < parsed_time(fix1_consumption["consumed_at_utc"])
        assert parsed_time(fix1_consumption["consumed_at_utc"]) < parsed_time(fix1_result["completed_at_utc"])
        assert parsed_time(fix1_result["completed_at_utc"]) < parsed_time(m10_approval["approved_at_utc"])
        assert parsed_time(m10_approval["approved_at_utc"]) < parsed_time(m10_review["reviewed_at_utc"])
        assert parsed_time(m10_review["reviewed_at_utc"]) < parsed_time(m10_result["completed_at_utc"])

        return {
            "manifest": manifest,
            "original_approval": original_approval,
            "original_auth": original_auth,
            "original_consumption": original_consumption,
            "original_result": original_result,
            "fix1_result": fix1_result,
        }
    except Exception as exc:
        raise AssertionError(f"{INTEGRITY_ERROR}: {exc}") from exc


def test_consumption_digest_and_state() -> None:
    value = load(CONSUMPTION)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "consumption_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value[
        "authorization_consumed"
    ] is True
    assert value[
        "authorization_reuse_allowed"
    ] is False
    assert value[
        "automatic_retry_allowed"
    ] is False


def test_result_digest_and_success() -> None:
    contract = verify_m9_evidence_contract()
    original = contract["original_result"]
    comparable = copy.deepcopy(original)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert original["status"] == ORIGINAL_STATUS

    fix1 = contract["fix1_result"]
    comparable = copy.deepcopy(fix1)
    stored = comparable.pop("result_digest_sha256")
    assert digest(comparable) == stored
    assert fix1["status"] == FIX1_STATUS
    assert fix1["phase_id"] != original["phase_id"]
    assert fix1["old_m9_artifacts_modified"] is False


def test_article_navigation_state() -> None:
    article = load(ARTICLE)
    navigation = article[
        "store_navigation"
    ]

    assert navigation[
        "render_mode"
    ] == "PARTIAL_ACTIVE_STORE_LINKS"
    assert navigation[
        "anchor_elements_included"
    ] is True
    assert navigation[
        "href_attributes_included"
    ] is True
    assert navigation[
        "final_affiliate_urls_included"
    ] is True
    assert navigation[
        "dmm_url_included"
    ] is True


def test_article_dmm_anchor_shape() -> None:
    html = load(ARTICLE)["content_html"]

    assert html.count(
        "ls-store-btn ls-store-dmm"
    ) == 1
    assert (
        "ls-store-dmm ls-store-disabled"
        not in html
    )
    assert (
        "DMMブックスで確認（再確認待ち）"
        not in html
    )
    assert html.count(
        "DMMブックスで確認"
    ) == 1
    assert 'target="_blank"' in html
    assert (
        'rel="nofollow sponsored noopener"'
        in html
    )


def test_m9_authorization_immutable() -> None:
    value = load(M9_AUTH)

    assert value[
        "authorization_digest_sha256"
    ] == (
        "d274eaf6bd14c95ac43031fbff296d0d"
        "47e6051dbb4231407327d376f93fec7f"
    )
    assert value[
        "authorization_consumed"
    ] is False


def test_external_boundaries_closed() -> None:
    contract = verify_m9_evidence_contract()
    approval = contract["original_approval"]
    authorization = contract["original_auth"]
    consumption = contract["original_consumption"]
    result = contract["original_result"]

    assert all(approval["prohibited_operations"].values())
    assert authorization["network_connection_performed"] is False
    assert authorization["article_modified"] is False
    assert authorization["article_url_injection_performed"] is False
    assert authorization["article_dmm_slot_activated"] is False
    assert authorization["payload_created"] is False
    assert authorization["wordpress_access_performed"] is False
    assert consumption["network_connection_performed"] is False
    assert consumption["wordpress_access_performed"] is False
    assert consumption["consumed_before_article_mutation"] is True
    assert result["network_connection_performed"] is False
    assert result["wordpress_access_performed"] is False
    assert result["production_status"] == "NO_GO"
    assert result["status"] == ORIGINAL_STATUS
    assert result["automatic_retry_allowed"] is False
