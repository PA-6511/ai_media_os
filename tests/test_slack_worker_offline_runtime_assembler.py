from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import pytest


repo = Path(__file__).resolve().parents[1]

assembler_path = (
    repo
    / "scripts/"
    "slack_worker_offline_runtime_assembler.py"
)

specification = (
    importlib.util
    .spec_from_file_location(
        "offline_runtime_assembler",
        assembler_path,
    )
)

assert specification is not None
assert specification.loader is not None

assembler = (
    importlib.util
    .module_from_spec(
        specification
    )
)

specification.loader.exec_module(
    assembler
)


wheelhouse = Path(
    "/tmp/"
    "sql_b2_4b_5g_3b_1d_1b_"
    "locked_wheelhouse"
)

now_utc = datetime(
    2026,
    7,
    16,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)

transaction_id = (
    "0123456789abcdef"
    "fedcba9876543210"
)


def test_policy_revision_2_passes() -> None:
    policy, adapter, core = (
        assembler.validate_policy()
    )

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2C-3C"
    )

    assert policy["revision"] == 2

    assert policy[
        "smoke_contract"
    ][
        "engine_creation_count_required"
    ] == 1

    assert policy[
        "smoke_contract"
    ][
        "sqlalchemy_connection_allowed"
    ] is False

    assert hasattr(
        adapter,
        "prepare_real_bundle",
    )

    assert hasattr(
        core,
        "load_and_validate_manifest",
    )


def test_runtime_outside_tmp_rejected() -> None:
    with pytest.raises(
        assembler.RuntimeAssemblerError,
        match=(
            "RUNTIME_OUTPUT_ROOT_"
            "OUTSIDE_TMP_REJECTED"
        ),
    ):
        assembler.assemble_real_runtime(
            wheelhouse_root=wheelhouse,
            runtime_output_root=Path(
                "/home/deploy/"
                "forbidden-runtime"
            ),
            transaction_id=(
                transaction_id
            ),
            now_utc=now_utc,
        )


def test_invalid_transaction_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        assembler.RuntimeAssemblerError,
        match="TRANSACTION_ID_INVALID",
    ):
        assembler.assemble_real_runtime(
            wheelhouse_root=wheelhouse,
            runtime_output_root=(
                tmp_path / "runtime"
            ),
            transaction_id="invalid",
            now_utc=now_utc,
        )


def test_naive_time_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        assembler.RuntimeAssemblerError,
        match="NOW_TIMEZONE_REQUIRED",
    ):
        assembler.assemble_prepared_runtime(
            prepared_bundle_root=(
                tmp_path / "missing"
            ),
            runtime_output_root=(
                tmp_path / "runtime"
            ),
            transaction_id=(
                transaction_id
            ),
            now_utc=datetime(
                2026,
                7,
                16,
                12,
                0,
                0,
            ),
        )
