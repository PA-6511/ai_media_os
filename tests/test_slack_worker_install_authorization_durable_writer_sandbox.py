from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import stat

import pytest


repo = Path(__file__).resolve().parents[1]

module_path = (
    repo
    / "scripts/"
    "slack_worker_install_"
    "authorization_durable_writer_"
    "sandbox.py"
)

capsule_policy_path = (
    repo
    / "config/"
    "slack_worker_install_"
    "authorization_capsule_policy.json"
)


spec = importlib.util.spec_from_file_location(
    "durable_writer_sandbox",
    module_path,
)

assert spec is not None
assert spec.loader is not None

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(module)


NOW = datetime(
    2026,
    7,
    15,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)

TRANSACTION_ID = (
    "00112233445566778899aabbccddeeff"
)


def load_capsule_policy() -> dict:
    return json.loads(
        capsule_policy_path.read_text(
            encoding="utf-8"
        )
    )


def valid_document() -> dict:
    policy = load_capsule_policy()

    contract = policy[
        "capsule_document_contract"
    ]

    return {
        "schema_version": 1,
        "authorization_id": (
            "auth-"
            "0123456789abcdef"
            "0123456789abcdef"
        ),
        "operation": (
            contract[
                "operation_value"
            ]
        ),
        "release_id": (
            contract[
                "release_id_value"
            ]
        ),
        "issued_at": (
            "2026-07-15T11:59:30Z"
        ),
        "expires_at": (
            "2026-07-15T12:10:00Z"
        ),
        "nonce": (
            "0123456789abcdef"
            "0123456789abcdef"
            "fedcba9876543210"
            "fedcba9876543210"
        ),
        "issuer": {
            "kind": (
                contract[
                    "issuer_kind_value"
                ]
            ),
            "uid": (
                contract[
                    "issuer_uid_value"
                ]
            ),
        },
        "bindings": policy[
            "expected_bindings"
        ],
        "constraints": policy[
            "expected_constraints"
        ],
    }


def consume(
    document: dict,
    sandbox_root: Path,
    *,
    transaction_id: str = TRANSACTION_ID,
):
    return module.consume_to_sandbox(
        json.dumps(
            document,
            ensure_ascii=False,
        ),
        now_utc=NOW,
        transaction_id=transaction_id,
        sandbox_root=sandbox_root,
    )


def test_writer_policy_passes() -> None:
    policy, reference = (
        module.validate_writer_policy()
    )

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2B-7"
    )

    assert hasattr(
        reference,
        "validate_capsule_document_text",
    )


def test_valid_document_creates_final_record(
    tmp_path: Path,
) -> None:
    root = tmp_path / "state"

    result = consume(
        valid_document(),
        root,
    )

    final_path = Path(
        result[
            "sandbox_record_path"
        ]
    )

    assert final_path.is_file()

    assert final_path.name == (
        "auth-"
        "0123456789abcdef"
        "0123456789abcdef"
        ".json"
    )

    assert stat.S_IMODE(
        final_path.stat().st_mode
    ) == 0o600

    records = list(
        (root / "records").iterdir()
    )

    assert records == [
        final_path
    ]


def test_valid_result_remains_no_go(
    tmp_path: Path,
) -> None:
    result = consume(
        valid_document(),
        tmp_path / "state",
    )

    assert result[
        "authorization_consumed_in_sandbox"
    ] is True

    assert result[
        "authorization_consumed_on_host"
    ] is False

    assert result[
        "host_consumption_record_created"
    ] is False

    assert result[
        "root_file_custody_validated"
    ] is False

    assert result[
        "execution_allowed"
    ] is False

    assert result[
        "root_release_install_authorized"
    ] is False

    assert result[
        "root_release_install_executed"
    ] is False

    assert result[
        "final_decision"
    ] == "NO_GO"


def test_same_authorization_replay_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "state"
    document = valid_document()

    consume(document, root)

    with pytest.raises(
        module.SandboxWriterError,
        match=(
            "AUTHORIZATION_ID_REPLAY_REJECTED"
        ),
    ):
        consume(
            document,
            root,
            transaction_id=(
                "ffeeddccbbaa99887766554433221100"
            ),
        )


def test_duplicate_authorization_id_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "state"

    first = valid_document()
    consume(first, root)

    second = valid_document()

    second["nonce"] = (
        "aaaaaaaaaaaaaaaa"
        "aaaaaaaaaaaaaaaa"
        "bbbbbbbbbbbbbbbb"
        "bbbbbbbbbbbbbbbb"
    )

    with pytest.raises(
        module.SandboxWriterError,
        match=(
            "AUTHORIZATION_ID_REPLAY_REJECTED"
        ),
    ):
        consume(
            second,
            root,
            transaction_id=(
                "aaaaaaaaaaaaaaaa"
                "bbbbbbbbbbbbbbbb"
            ),
        )


def test_duplicate_nonce_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "state"

    first = valid_document()
    consume(first, root)

    second = valid_document()

    second["authorization_id"] = (
        "auth-"
        "aaaaaaaaaaaaaaaa"
        "bbbbbbbbbbbbbbbb"
    )

    with pytest.raises(
        module.SandboxWriterError,
        match="NONCE_REPLAY_REJECTED",
    ):
        consume(
            second,
            root,
            transaction_id=(
                "bbbbbbbbbbbbbbbb"
                "aaaaaaaaaaaaaaaa"
            ),
        )


def test_invalid_document_creates_no_record(
    tmp_path: Path,
) -> None:
    root = tmp_path / "state"

    document = valid_document()

    document["constraints"] = dict(
        document["constraints"]
    )

    document["constraints"][
        "service_start_allowed"
    ] = True

    with pytest.raises(
        module.SandboxWriterError,
        match="DOCUMENT_REJECTED",
    ):
        consume(document, root)

    assert not root.exists()


def test_unknown_entry_blocks(
    tmp_path: Path,
) -> None:
    root, records = (
        module.prepare_sandbox_root(
            tmp_path / "state"
        )
    )

    unknown = records / "unknown.txt"

    unknown.write_text(
        "unknown\n",
        encoding="utf-8",
    )

    os.chmod(
        unknown,
        0o600,
    )

    with pytest.raises(
        module.SandboxWriterError,
        match="UNKNOWN_RECORD_ENTRY",
    ):
        consume(
            valid_document(),
            root,
        )


def test_malformed_final_record_blocks(
    tmp_path: Path,
) -> None:
    root, records = (
        module.prepare_sandbox_root(
            tmp_path / "state"
        )
    )

    malformed = (
        records
        / (
            "auth-"
            "0123456789abcdef"
            "0123456789abcdef"
            ".json"
        )
    )

    malformed.write_text(
        "{not-json}\n",
        encoding="utf-8",
    )

    os.chmod(
        malformed,
        0o600,
    )

    with pytest.raises(
        module.SandboxWriterError,
        match="RECORD_DOCUMENT_INVALID",
    ):
        consume(
            valid_document(),
            root,
        )


def test_pending_record_blocks_fail_closed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "state"
    document = valid_document()

    result = consume(
        document,
        root,
    )

    final_path = Path(
        result[
            "sandbox_record_path"
        ]
    )

    pending_path = (
        final_path.parent
        / (
            ".pending-"
            f"{document['authorization_id']}-"
            f"{document['nonce']}-"
            f"{TRANSACTION_ID}.json"
        )
    )

    os.rename(
        final_path,
        pending_path,
    )

    with pytest.raises(
        module.SandboxWriterError,
        match=(
            "PENDING_RECORD_PRESENT_BLOCKS_"
            "CONSUMPTION"
        ),
    ):
        consume(
            document,
            root,
            transaction_id=(
                "ffeeddccbbaa99887766554433221100"
            ),
        )


def test_sandbox_outside_tmp_rejected() -> None:
    with pytest.raises(
        module.SandboxWriterError,
        match="SANDBOX_OUTSIDE_TMP_REJECTED",
    ):
        module.prepare_sandbox_root(
            Path(
                "/home/deploy/"
                "forbidden-sandbox"
            )
        )


def test_record_content_is_reference_only(
    tmp_path: Path,
) -> None:
    result = consume(
        valid_document(),
        tmp_path / "state",
    )

    record = json.loads(
        Path(
            result[
                "sandbox_record_path"
            ]
        ).read_text(
            encoding="utf-8"
        )
    )

    assert record[
        "record_state"
    ] == (
        "SANDBOX_DURABLE_CONSUMED_"
        "REFERENCE_ONLY"
    )

    assert record[
        "sandbox_reference_only"
    ] is True

    assert record[
        "operation"
    ] == "INSTALL_RELEASE_ONLY"
