from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_final_affiliate_link_"
    "generation_authorization_gate_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m6_"
    "authorization_gate_approval.json"
)
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_authorization.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m6_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m6_"
    "final_affiliate_link_generation_"
    "authorization_gate_report.md"
)
BUILDER = ROOT / (
    "scripts/"
    "build_ls_new_batch_4g_2e_recovery_m6.py"
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


def load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "recovery_m6_builder",
        BUILDER,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


def test_policy_is_authorization_only() -> None:
    boundary = load_json(POLICY)[
        "execution_boundary"
    ]

    assert (
        boundary[
            "authorization_artifact_creation_allowed"
        ]
        is True
    )
    assert (
        boundary[
            "final_affiliate_link_generation_allowed"
        ]
        is False
    )
    assert (
        boundary["network_connection_allowed"]
        is False
    )
    assert boundary["http_request_allowed"] is False
    assert boundary["dmm_recheck_allowed"] is False
    assert (
        boundary[
            "article_dmm_slot_activation_allowed"
        ]
        is False
    )
    assert (
        boundary[
            "historical_result_reclassification_allowed"
        ]
        is False
    )


def test_approval_digest() -> None:
    approval = load_json(APPROVAL)
    comparable = copy.deepcopy(approval)
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval["human_explicit_approval"] is True


def test_authorization_digest() -> None:
    authorization = load_json(AUTHORIZATION)
    comparable = copy.deepcopy(
        authorization
    )
    stored = comparable.pop(
        "authorization_digest_sha256"
    )

    assert digest(comparable) == stored


def test_result_digest() -> None:
    result = load_json(RESULT)
    comparable = copy.deepcopy(result)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored


def test_exact_verified_product_binding() -> None:
    authorized = load_json(AUTHORIZATION)[
        "authorized_input"
    ]

    assert authorized[
        "verified_product_url"
    ] == (
        "https://book.dmm.com/product/"
        "861056/b950yshes32617/"
    )
    assert authorized["volume"] == "第20巻"
    assert authorized["series_id"] == "861056"


def test_final_url_contract() -> None:
    contract = load_json(AUTHORIZATION)[
        "required_output_contract"
    ]

    assert contract["scheme"] == "https"
    assert contract["host"] == "al.dmm.com"
    assert (
        contract[
            "destination_exact_binding_required"
        ]
        is True
    )
    assert (
        contract[
            "registered_identifier_exact_binding_required"
        ]
        is True
    )
    assert contract["latest_alias_allowed"] is False
    assert (
        contract["post185_link_reuse_allowed"]
        is False
    )
    assert (
        contract[
            "automatic_fallback_url_allowed"
        ]
        is False
    )


def test_cred1_commitment_revalidates() -> None:
    builder = load_builder()
    identifier, _ = (
        builder.read_registered_identifier()
    )
    cred1_result = builder.load_json(
        builder.SOURCE_PATHS[
            "cred1_result"
        ]
    )

    builder.verify_cred1_commitment(
        identifier,
        cred1_result,
    )


def test_identifier_value_not_leaked() -> None:
    builder = load_builder()
    identifier, _ = (
        builder.read_registered_identifier()
    )

    combined = "\n".join(
        [
            APPROVAL.read_text(
                encoding="utf-8"
            ),
            AUTHORIZATION.read_text(
                encoding="utf-8"
            ),
            RESULT.read_text(
                encoding="utf-8"
            ),
            REPORT.read_text(
                encoding="utf-8"
            ),
        ]
    )

    assert identifier not in combined


def test_authorization_single_use_unconsumed() -> None:
    authorization = load_json(AUTHORIZATION)

    assert authorization["single_use"] is True
    assert (
        authorization[
            "authorization_consumed"
        ]
        is False
    )
    assert (
        authorization[
            "authorization_reuse_allowed"
        ]
        is False
    )
    assert (
        authorization[
            "automatic_retry_allowed"
        ]
        is False
    )
    assert (
        authorization[
            "actual_generation_allowed"
        ]
        is False
    )


def test_source_bindings_unchanged() -> None:
    authorization = load_json(AUTHORIZATION)

    for binding in authorization[
        "source_bindings"
    ].values():
        path = ROOT / binding["path"]

        assert (
            file_sha256(path)
            == binding["file_sha256"]
        )


def test_credential_binding_has_no_value() -> None:
    binding = load_json(AUTHORIZATION)[
        "affiliate_identifier_binding"
    ]

    assert (
        binding[
            "registration_commitment_revalidated"
        ]
        is True
    )
    assert (
        binding[
            "identifier_value_present"
        ]
        is False
    )
    assert (
        binding[
            "identifier_value_output"
        ]
        is False
    )
    assert (
        binding[
            "identifier_value_persisted_in_authorization"
        ]
        is False
    )


def test_result_ready_for_m7_only() -> None:
    result = load_json(RESULT)

    assert result["status"] == (
        "PASS_DMM_FINAL_AFFILIATE_LINK_"
        "GENERATION_ONE_SHOT_AUTHORIZATION_"
        "FIXED_NO_GENERATION_NO_NETWORK"
    )
    assert (
        result[
            "ready_for_ls_new_batch_4g_2e_recovery_m7"
        ]
        is True
    )
    assert (
        result[
            "ready_for_final_affiliate_link_generation"
        ]
        is False
    )
    assert result[
        "authorization_consumed"
    ] is False


def test_production_boundary_closed() -> None:
    result = load_json(RESULT)

    assert (
        result[
            "network_connection_performed"
        ]
        is False
    )
    assert (
        result[
            "final_affiliate_link_generated"
        ]
        is False
    )
    assert (
        result[
            "article_dmm_slot_activated"
        ]
        is False
    )
    assert result["article_modified"] is False
    assert (
        result[
            "fresh_payload_created"
        ]
        is False
    )
    assert (
        result[
            "wordpress_access_performed"
        ]
        is False
    )
    assert result["execution_allowed"] is False
    assert result["production_status"] == "NO_GO"


def test_builder_has_no_network_execution() -> None:
    source = BUILDER.read_text(
        encoding="utf-8"
    )

    for forbidden in [
        "urllib.request",
        "requests.get(",
        "urlopen(",
        "opener.open(",
        "http.client",
        "import socket",
    ]:
        assert forbidden not in source
