from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path
from types import ModuleType
from urllib.parse import parse_qsl, urlsplit


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_final_affiliate_link_"
    "one_shot_generation_policy.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m7_execute_now_approval.json"
)
RUNNER = ROOT / (
    "scripts/"
    "run_ls_new_batch_4g_2e_recovery_m7.py"
)
CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_consumption.json"
)
LINK_ARTIFACT = ROOT / (
    "exchange/links/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_result.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m7_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m7_"
    "dmm_final_affiliate_link_generation_report.md"
)
M6_AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_final_affiliate_link_generation_authorization.json"
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "recovery_m7_runner",
        RUNNER,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_approval_digest() -> None:
    value = load_json(APPROVAL)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored


def test_consumption_digest_and_state() -> None:
    value = load_json(CONSUMPTION)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "consumption_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["authorization_consumed"] is True
    assert value["execution_boundary_crossed"] is True
    assert value["authorization_reuse_allowed"] is False
    assert value["automatic_retry_allowed"] is False
    assert value["full_final_url_present"] is False


def test_secret_link_artifact_digest_and_mode() -> None:
    value = load_json(LINK_ARTIFACT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "secret_artifact_digest_sha256"
    )

    assert digest(comparable) == stored
    assert stat.S_IMODE(
        LINK_ARTIFACT.stat().st_mode
    ) == 0o600


def test_final_link_exact_binding_without_output() -> None:
    runner = load_runner()
    identifier, _ = runner.read_registered_identifier()
    link = load_json(LINK_ARTIFACT)
    final_url = link["final_affiliate_url"]
    parsed = urlsplit(final_url)

    if parsed.scheme != "https":
        raise AssertionError("FINAL_SCHEME_MISMATCH")
    if parsed.hostname != "al.dmm.com":
        raise AssertionError("FINAL_HOST_MISMATCH")
    if parsed.port is not None:
        raise AssertionError("FINAL_PORT_REJECTED")
    if parsed.username is not None:
        raise AssertionError("FINAL_USERINFO_REJECTED")
    if parsed.password is not None:
        raise AssertionError("FINAL_USERINFO_REJECTED")
    if parsed.path != "/":
        raise AssertionError("FINAL_PATH_MISMATCH")
    if parsed.fragment != "":
        raise AssertionError("FINAL_FRAGMENT_REJECTED")

    pairs = parse_qsl(
        parsed.query,
        keep_blank_values=True,
        strict_parsing=True,
    )

    expected = [
        (
            "lurl",
            "https://book.dmm.com/product/"
            "861056/b950yshes32617/",
        ),
        ("af_id", identifier),
        ("ch", "link_tool"),
        ("ch_id", "link"),
    ]

    if pairs != expected:
        raise AssertionError(
            "FINAL_QUERY_BINDING_MISMATCH"
        )


def test_full_url_and_identifier_only_in_secret_artifact() -> None:
    runner = load_runner()
    identifier, _ = runner.read_registered_identifier()
    link = load_json(LINK_ARTIFACT)
    final_url = link["final_affiliate_url"]

    normal_evidence = "\n".join(
        [
            POLICY.read_text(encoding="utf-8"),
            APPROVAL.read_text(encoding="utf-8"),
            CONSUMPTION.read_text(encoding="utf-8"),
            RESULT.read_text(encoding="utf-8"),
            REPORT.read_text(encoding="utf-8"),
        ]
    )

    if final_url in normal_evidence:
        raise AssertionError(
            "FULL_FINAL_URL_LEAKED_TO_NORMAL_EVIDENCE"
        )

    if identifier in normal_evidence:
        raise AssertionError(
            "IDENTIFIER_LEAKED_TO_NORMAL_EVIDENCE"
        )


def test_result_digest_and_success_state() -> None:
    value = load_json(RESULT)
    comparable = copy.deepcopy(value)
    stored = comparable.pop(
        "result_digest_sha256"
    )

    assert digest(comparable) == stored
    assert value["status"] == (
        "PASS_DMM_FINAL_AFFILIATE_LINK_"
        "GENERATED_OFFLINE_AUTHORIZATION_"
        "CONSUMED_NO_NETWORK"
    )
    assert value["authorization_consumed"] is True
    assert value["authorization_reuse_allowed"] is False
    assert value["automatic_retry_allowed"] is False


def test_m6_authorization_immutable() -> None:
    assert file_sha256(M6_AUTHORIZATION) == (
        "8e751212054d5722863984bec7faad5c"
        "0c851f28fdbebe18d5b441f34e36b4d9"
    )


def test_source_bindings_unchanged() -> None:
    approval = load_json(APPROVAL)

    for binding in approval[
        "source_bindings"
    ].values():
        path = ROOT / binding["path"]

        assert file_sha256(path) == (
            binding["file_sha256"]
        )


def test_no_network_or_article_or_wordpress_action() -> None:
    value = load_json(RESULT)

    assert value["network_connection_performed"] is False
    assert value["http_request_performed"] is False
    assert value["dmm_recheck_performed"] is False
    assert value["article_modified"] is False
    assert value["article_url_injection_performed"] is False
    assert value["article_dmm_slot_activated"] is False
    assert value["fresh_payload_created"] is False
    assert value["wordpress_access_performed"] is False
    assert value["wordpress_write_performed"] is False
    assert value["wordpress_published"] is False
    assert value["production_status"] == "NO_GO"


def test_ready_for_m8_only() -> None:
    value = load_json(RESULT)

    assert (
        value[
            "ready_for_ls_new_batch_4g_2e_recovery_m8"
        ]
        is True
    )
    assert (
        value["ready_for_article_url_injection"]
        is False
    )
    assert (
        value[
            "ready_for_article_dmm_slot_activation"
        ]
        is False
    )
    assert (
        value["ready_for_payload_generation"]
        is False
    )
    assert (
        value["ready_for_wordpress_draft"]
        is False
    )


def test_runner_contains_no_network_execution() -> None:
    source = RUNNER.read_text(encoding="utf-8")

    for forbidden in [
        "urllib.request",
        "requests.get(",
        "requests.post(",
        "urlopen(",
        "opener.open(",
        "http.client",
        "import socket",
        "socket.create_connection",
    ]:
        assert forbidden not in source
