from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


repo = Path(__file__).resolve().parents[1]

adapter_path = (
    repo
    / "scripts/"
    "slack_worker_real_release_"
    "bundle_sandbox_adapter.py"
)

core_path = (
    repo
    / "scripts/"
    "slack_worker_root_installer_"
    "sandbox_core.py"
)


def load_module(
    name: str,
    path: Path,
):
    specification = (
        importlib.util
        .spec_from_file_location(
            name,
            path,
        )
    )

    assert specification is not None
    assert specification.loader is not None

    module = (
        importlib.util
        .module_from_spec(
            specification
        )
    )

    specification.loader.exec_module(
        module
    )

    return module


adapter = load_module(
    "real_bundle_adapter",
    adapter_path,
)

core = load_module(
    "sandbox_installer_core_for_adapter",
    core_path,
)


TRANSACTION_ID = (
    "00112233445566778899aabbccddeeff"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def build_synthetic_inventory(
    root: Path,
):
    policy, _, _ = (
        adapter.validate_policy()
    )

    source_root = root / "source"
    wheelhouse = root / "wheelhouse"

    source_root.mkdir()
    wheelhouse.mkdir()

    source_entries = []
    wheel_entries = []

    for index in range(
        policy[
            "bindings"
        ]["source_file_count"]
    ):
        relative = (
            f"package/module_{index:02d}.py"
        )

        payload = (
            f"SOURCE_{index:02d}\n"
        ).encode("utf-8")

        path = source_root / relative

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(payload)
        os.chmod(path, 0o664)

        source_entries.append(
            {
                "path": relative,
                "sha256": (
                    sha256_bytes(payload)
                ),
                "size": len(payload),
                "mode": "0664",
            }
        )

    for index in range(
        policy[
            "bindings"
        ]["wheel_count"]
    ):
        filename = (
            f"package_{index:02d}-1.0-"
            "py3-none-any.whl"
        )

        payload = (
            f"WHEEL_{index:02d}\n"
        ).encode("utf-8")

        path = wheelhouse / filename

        path.write_bytes(payload)
        os.chmod(path, 0o664)

        wheel_entries.append(
            {
                "filename": filename,
                "sha256": (
                    sha256_bytes(payload)
                ),
                "size": len(payload),
            }
        )

    return (
        policy,
        source_root,
        source_entries,
        wheelhouse,
        wheel_entries,
    )


def prepare_synthetic(
    tmp_path: Path,
    *,
    fault_point: str | None = None,
):
    (
        policy,
        source_root,
        source_entries,
        wheelhouse,
        wheel_entries,
    ) = build_synthetic_inventory(
        tmp_path
    )

    output = tmp_path / "prepared"

    result = adapter.prepare_from_inventory(
        policy=policy,
        sandbox_core=core,
        source_root=source_root,
        source_entries=source_entries,
        wheelhouse_root=wheelhouse,
        wheel_entries=wheel_entries,
        output_root=output,
        transaction_id=TRANSACTION_ID,
        fault_point=fault_point,
    )

    return result, output


def test_policy_passes() -> None:
    policy, manifest, loaded_core = (
        adapter.validate_policy()
    )

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2C-2"
    )

    assert len(
        manifest["source_files"]
    ) == policy[
        "bindings"
    ]["source_file_count"]

    assert hasattr(
        loaded_core,
        "load_and_validate_manifest",
    )


def test_prepared_bundle_matches_core_contract(
    tmp_path: Path,
) -> None:
    result, output = (
        prepare_synthetic(
            tmp_path
        )
    )

    manifest, _ = (
        core.load_and_validate_manifest(
            output,
            core.validate_policy(),
        )
    )

    assert result["state"] == (
        "SANDBOX_PREPARED_BUNDLE_CREATED"
    )

    assert len(manifest["files"]) == (
        result[
            "source_file_count"
        ]
        + result["wheel_count"]
    )

    assert set(
        item["mode"]
        for item in manifest["files"]
    ) == {"0644"}

    assert result[
        "legacy_bundle_used"
    ] is False


def test_source_paths_are_mapped_below_src(
    tmp_path: Path,
) -> None:
    _, output = prepare_synthetic(
        tmp_path
    )

    manifest = json.loads(
        (
            output
            / "bundle-manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    source_paths = [
        item["path"]
        for item in manifest["files"]
        if item["path"].startswith(
            "src/"
        )
    ]

    assert len(source_paths) == 16

    assert all(
        value.startswith(
            "src/package/"
        )
        for value in source_paths
    )


def test_wheels_are_mapped_by_basename(
    tmp_path: Path,
) -> None:
    _, output = prepare_synthetic(
        tmp_path
    )

    manifest = json.loads(
        (
            output
            / "bundle-manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    wheel_paths = [
        item["path"]
        for item in manifest["files"]
        if item["path"].startswith(
            "wheelhouse/"
        )
    ]

    assert len(wheel_paths) == 5

    assert all(
        "/" not in value[
            len("wheelhouse/"):
        ]
        for value in wheel_paths
    )


def test_second_prepare_is_idempotent(
    tmp_path: Path,
) -> None:
    (
        policy,
        source_root,
        source_entries,
        wheelhouse,
        wheel_entries,
    ) = build_synthetic_inventory(
        tmp_path
    )

    output = tmp_path / "prepared"

    first = adapter.prepare_from_inventory(
        policy=policy,
        sandbox_core=core,
        source_root=source_root,
        source_entries=source_entries,
        wheelhouse_root=wheelhouse,
        wheel_entries=wheel_entries,
        output_root=output,
        transaction_id=TRANSACTION_ID,
    )

    second = adapter.prepare_from_inventory(
        policy=policy,
        sandbox_core=core,
        source_root=source_root,
        source_entries=source_entries,
        wheelhouse_root=wheelhouse,
        wheel_entries=wheel_entries,
        output_root=output,
        transaction_id=(
            "ffeeddccbbaa99887766554433221100"
        ),
    )

    assert first["state"] == (
        "SANDBOX_PREPARED_BUNDLE_CREATED"
    )

    assert second["state"] == (
        "SANDBOX_PREPARED_BUNDLE_"
        "ALREADY_EXISTS"
    )

    assert second[
        "adapter_execution_performed"
    ] is False


@pytest.mark.parametrize(
    "fault_point",
    [
        "AFTER_SOURCE_COPY",
        "AFTER_MANIFEST_BEFORE_COMMIT",
    ],
)
def test_precommit_failure_removes_staging(
    tmp_path: Path,
    fault_point: str,
) -> None:
    (
        policy,
        source_root,
        source_entries,
        wheelhouse,
        wheel_entries,
    ) = build_synthetic_inventory(
        tmp_path
    )

    output = tmp_path / "prepared"

    with pytest.raises(
        adapter.BundleAdapterError,
        match="INJECTED_",
    ):
        adapter.prepare_from_inventory(
            policy=policy,
            sandbox_core=core,
            source_root=source_root,
            source_entries=source_entries,
            wheelhouse_root=wheelhouse,
            wheel_entries=wheel_entries,
            output_root=output,
            transaction_id=TRANSACTION_ID,
            fault_point=fault_point,
        )

    assert not output.exists()

    staging = list(
        tmp_path.glob(
            ".prepare-*"
        )
    )

    assert staging == []


def test_source_hash_mismatch_rejected(
    tmp_path: Path,
) -> None:
    (
        policy,
        source_root,
        source_entries,
        wheelhouse,
        wheel_entries,
    ) = build_synthetic_inventory(
        tmp_path
    )

    (
        source_root
        / source_entries[0]["path"]
    ).write_text(
        "MUTATED\n",
        encoding="utf-8",
    )

    with pytest.raises(
        adapter.BundleAdapterError,
        match="SOURCE_.*MISMATCH",
    ):
        adapter.prepare_from_inventory(
            policy=policy,
            sandbox_core=core,
            source_root=source_root,
            source_entries=source_entries,
            wheelhouse_root=wheelhouse,
            wheel_entries=wheel_entries,
            output_root=(
                tmp_path / "prepared"
            ),
            transaction_id=TRANSACTION_ID,
        )


def test_wheel_hash_mismatch_rejected(
    tmp_path: Path,
) -> None:
    (
        policy,
        source_root,
        source_entries,
        wheelhouse,
        wheel_entries,
    ) = build_synthetic_inventory(
        tmp_path
    )

    (
        wheelhouse
        / wheel_entries[0]["filename"]
    ).write_text(
        "MUTATED\n",
        encoding="utf-8",
    )

    with pytest.raises(
        adapter.BundleAdapterError,
        match="WHEEL_.*MISMATCH",
    ):
        adapter.prepare_from_inventory(
            policy=policy,
            sandbox_core=core,
            source_root=source_root,
            source_entries=source_entries,
            wheelhouse_root=wheelhouse,
            wheel_entries=wheel_entries,
            output_root=(
                tmp_path / "prepared"
            ),
            transaction_id=TRANSACTION_ID,
        )


def test_source_symlink_rejected(
    tmp_path: Path,
) -> None:
    (
        policy,
        source_root,
        source_entries,
        wheelhouse,
        wheel_entries,
    ) = build_synthetic_inventory(
        tmp_path
    )

    target = (
        source_root
        / source_entries[0]["path"]
    )

    replacement = target.with_name(
        "replacement.py"
    )

    replacement.write_bytes(
        target.read_bytes()
    )

    target.unlink()
    target.symlink_to(replacement)

    with pytest.raises(
        (
            adapter.BundleAdapterError,
            OSError,
        )
    ):
        adapter.prepare_from_inventory(
            policy=policy,
            sandbox_core=core,
            source_root=source_root,
            source_entries=source_entries,
            wheelhouse_root=wheelhouse,
            wheel_entries=wheel_entries,
            output_root=(
                tmp_path / "prepared"
            ),
            transaction_id=TRANSACTION_ID,
        )


def test_output_outside_tmp_rejected(
    tmp_path: Path,
) -> None:
    (
        policy,
        source_root,
        source_entries,
        wheelhouse,
        wheel_entries,
    ) = build_synthetic_inventory(
        tmp_path
    )

    with pytest.raises(
        adapter.BundleAdapterError,
        match="OUTPUT_ROOT_OUTSIDE_TMP_REJECTED",
    ):
        adapter.prepare_from_inventory(
            policy=policy,
            sandbox_core=core,
            source_root=source_root,
            source_entries=source_entries,
            wheelhouse_root=wheelhouse,
            wheel_entries=wheel_entries,
            output_root=Path(
                "/home/deploy/"
                "forbidden-prepared-bundle"
            ),
            transaction_id=TRANSACTION_ID,
        )


def test_prepared_bundle_installs_in_sandbox_core(
    tmp_path: Path,
) -> None:
    _, output = prepare_synthetic(
        tmp_path
    )

    result = core.install_prepared_bundle(
        bundle_root=output,
        sandbox_install_root=(
            tmp_path / "install"
        ),
        transaction_id=(
            "ffeeddccbbaa99887766554433221100"
        ),
        now_utc=(
            __import__("datetime")
            .datetime(
                2026,
                7,
                15,
                12,
                0,
                0,
                tzinfo=(
                    __import__("datetime")
                    .timezone.utc
                ),
            )
        ),
    )

    assert result["state"] == (
        "SANDBOX_RELEASE_INSTALLED"
    )

    assert result[
        "root_release_install_executed"
    ] is False

    assert result[
        "current_link_created"
    ] is False

    assert result[
        "final_decision"
    ] == "NO_GO"


def test_success_result_remains_no_go(
    tmp_path: Path,
) -> None:
    result, _ = prepare_synthetic(
        tmp_path
    )

    assert result[
        "root_release_install_authorized"
    ] is False

    assert result[
        "root_release_install_executed"
    ] is False

    assert result[
        "authorization_capsule_consumed"
    ] is False

    assert result[
        "current_link_created"
    ] is False

    assert result[
        "final_decision"
    ] == "NO_GO"
