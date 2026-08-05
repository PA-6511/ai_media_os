from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
REGISTRAR = ROOT / (
    "scripts/"
    "register_ls_new_batch_4g_2e_recovery_m6_cred1.py"
)


def load_registrar() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "m6_cred1_registrar",
        REGISTRAR,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


@pytest.mark.parametrize(
    "identifier",
    [
        "Abc123-001",
        "DMMUSER9-999",
        "a1B2c3-010",
    ],
)
def test_valid_identifier_formats(
    identifier: str,
) -> None:
    module = load_registrar()
    module.validate_identifier(identifier)


@pytest.mark.parametrize(
    "identifier",
    [
        "",
        "aaa-001",
        "test-001",
        "dummy-001",
        "sample-001",
        "example-001",
        "placeholder-001",
        "changeme-001",
        "yourid-001",
        "post185-001",
        "ABC-01",
        "ABC-0001",
        "ABC_DEF-001",
        "ABC 123-001",
        "https://example.com-001",
    ],
)
def test_invalid_identifiers_rejected(
    identifier: str,
) -> None:
    module = load_registrar()

    with pytest.raises(
        module.RegistrationError
    ):
        module.validate_identifier(
            identifier
        )


def test_key_parser_ignores_comments() -> None:
    module = load_registrar()

    values = module.read_key_values(
        """
        # DMM_AFFILIATE_ID=ignored-001
        OTHER=value
        """
    )

    assert values == []


def test_key_parser_detects_plain_and_export() -> None:
    module = load_registrar()

    plain = module.read_key_values(
        "DMM_AFFILIATE_ID=Abc123-001\n"
    )
    exported = module.read_key_values(
        "export DMM_AFFILIATE_ID='Abc123-001'\n"
    )

    assert plain == ["Abc123-001"]
    assert exported == ["Abc123-001"]


def test_commitment_is_deterministic() -> None:
    module = load_registrar()

    salt = bytes.fromhex("11" * 32)

    first = module.make_commitment(
        "Abc123-001",
        salt,
    )
    second = module.make_commitment(
        "Abc123-001",
        salt,
    )

    assert first == second
    assert "Abc123-001" not in first


def test_registrar_contains_no_network_code() -> None:
    source = REGISTRAR.read_text(
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
