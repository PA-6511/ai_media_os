from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest


repo = Path(__file__).resolve().parents[1]

module_path = (
    repo
    / "scripts/"
    "slack_worker_root_installer_"
    "sandbox_core.py"
)

policy_path = (
    repo
    / "config/"
    "slack_worker_root_installer_"
    "sandbox_core_policy.json"
)


spec = importlib.util.spec_from_file_location(
    "root_installer_sandbox_core",
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


def load_policy() -> dict:
    return json.loads(
        policy_path.read_text(
            encoding="utf-8"
        )
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(
        value
    ).hexdigest()


def build_bundle(
    root: Path,
) -> tuple[
    Path,
    dict,
]:
    policy = load_policy()

    contract = policy[
        "prepared_bundle_contract"
    ]

    bundle = root / "bundle"
    payload = bundle / "payload"

    payload.mkdir(
        parents=True,
    )

    files: list[dict] = []

    for index in range(
        contract[
            "source_file_count"
        ]
    ):
        relative = (
            f"src/module_{index:02d}.py"
        )

        content = (
            f"SOURCE_{index:02d}\n"
        ).encode("utf-8")

        path = payload / relative

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(content)
        os.chmod(path, 0o644)

        files.append(
            {
                "path": relative,
                "sha256": (
                    sha256_bytes(content)
                ),
                "size": len(content),
                "mode": "0644",
            }
        )

    for index in range(
        contract["wheel_count"]
    ):
        relative = (
            "wheelhouse/"
            f"package_{index:02d}.whl"
        )

        content = (
            f"WHEEL_{index:02d}\n"
        ).encode("utf-8")

        path = payload / relative

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(content)
        os.chmod(path, 0o644)

        files.append(
            {
                "path": relative,
                "sha256": (
                    sha256_bytes(content)
                ),
                "size": len(content),
                "mode": "0644",
            }
        )

    manifest = {
        "schema_version": (
            contract[
                "manifest_schema_version"
            ]
        ),
        "release_id": (
            contract["release_id"]
        ),
        "source_manifest_sha256": (
            contract[
                "source_manifest_sha256"
            ]
        ),
        "requirements_hash_lock_sha256": (
            contract[
                "requirements_hash_lock_sha256"
            ]
        ),
        "root_install_policy_sha256": (
            contract[
                "root_install_policy_sha256"
            ]
        ),
        "source_file_count": (
            contract[
                "source_file_count"
            ]
        ),
        "wheel_count": (
            contract["wheel_count"]
        ),
        "files": files,
    }

    (
        bundle
        / "bundle-manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return bundle, manifest


def install(
    bundle: Path,
    install_root: Path,
    *,
    fault_point: str | None = None,
    transaction_id: str = TRANSACTION_ID,
):
    return module.install_prepared_bundle(
        bundle_root=bundle,
        sandbox_install_root=(
            install_root
        ),
        transaction_id=transaction_id,
        now_utc=NOW,
        fault_point=fault_point,
    )


def test_policy_passes() -> None:
    policy = module.validate_policy()

    assert policy["phase"] == (
        "SQL-B2-4B-5G-3B-1D-2C-1"
    )

    assert policy[
        "governance"
    ][
        "root_release_install_authorized"
    ] is False


def test_successful_install_creates_final_release(
    tmp_path: Path,
) -> None:
    bundle, manifest = build_bundle(
        tmp_path
    )

    install_root = (
        tmp_path / "install"
    )

    result = install(
        bundle,
        install_root,
    )

    final_path = Path(
        result[
            "sandbox_final_path"
        ]
    )

    assert result["state"] == (
        "SANDBOX_RELEASE_INSTALLED"
    )

    assert final_path.is_dir()

    assert (
        final_path.name
        == manifest["release_id"]
    )

    assert (
        final_path
        / ".install-receipt.json"
    ).is_file()

    assert result[
        "sandbox_install_executed"
    ] is True

    assert result[
        "root_release_install_executed"
    ] is False


def test_install_does_not_create_current_link(
    tmp_path: Path,
) -> None:
    bundle, _ = build_bundle(
        tmp_path
    )

    install_root = (
        tmp_path / "install"
    )

    result = install(
        bundle,
        install_root,
    )

    assert result[
        "current_link_created"
    ] is False

    assert not os.path.lexists(
        os.fspath(
            install_root / "current"
        )
    )


def test_second_install_is_idempotent(
    tmp_path: Path,
) -> None:
    bundle, _ = build_bundle(
        tmp_path
    )

    install_root = (
        tmp_path / "install"
    )

    first = install(
        bundle,
        install_root,
    )

    second = install(
        bundle,
        install_root,
        transaction_id=(
            "ffeeddccbbaa99887766554433221100"
        ),
    )

    assert first["state"] == (
        "SANDBOX_RELEASE_INSTALLED"
    )

    assert second["state"] == (
        "SANDBOX_RELEASE_ALREADY_INSTALLED"
    )

    assert second[
        "sandbox_install_executed"
    ] is False

    assert second[
        "idempotent_existing_release"
    ] is True


def test_modified_final_release_is_rejected(
    tmp_path: Path,
) -> None:
    bundle, _ = build_bundle(
        tmp_path
    )

    install_root = (
        tmp_path / "install"
    )

    result = install(
        bundle,
        install_root,
    )

    final_path = Path(
        result[
            "sandbox_final_path"
        ]
    )

    target = (
        final_path
        / "src/module_00.py"
    )

    target.write_text(
        "MUTATED\n",
        encoding="utf-8",
    )

    with pytest.raises(
        module.SandboxInstallerError,
        match="INSTALLED_FILE_MISMATCH",
    ):
        install(
            bundle,
            install_root,
            transaction_id=(
                "ffeeddccbbaa99887766554433221100"
            ),
        )


def test_payload_hash_mismatch_rejected_before_install(
    tmp_path: Path,
) -> None:
    bundle, _ = build_bundle(
        tmp_path
    )

    (
        bundle
        / "payload/src/module_00.py"
    ).write_text(
        "MUTATED\n",
        encoding="utf-8",
    )

    install_root = (
        tmp_path / "install"
    )

    with pytest.raises(
        module.SandboxInstallerError,
        match="PAYLOAD_.*MISMATCH",
    ):
        install(
            bundle,
            install_root,
        )

    assert not install_root.exists()


def test_payload_symlink_is_rejected(
    tmp_path: Path,
) -> None:
    bundle, _ = build_bundle(
        tmp_path
    )

    target = (
        bundle
        / "payload/src/module_00.py"
    )

    target.unlink()

    target.symlink_to(
        bundle
        / "payload/src/module_01.py"
    )

    with pytest.raises(
        module.SandboxInstallerError,
        match=(
            "PAYLOAD_FILE_TYPE_INVALID"
            "|FILE_OPEN_FAILED"
        ),
    ):
        install(
            bundle,
            tmp_path / "install",
        )


def test_manifest_parent_traversal_is_rejected(
    tmp_path: Path,
) -> None:
    bundle, manifest = build_bundle(
        tmp_path
    )

    manifest["files"][0][
        "path"
    ] = "../escape.py"

    (
        bundle
        / "bundle-manifest.json"
    ).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(
        module.SandboxInstallerError,
        match="MANIFEST_PATH",
    ):
        install(
            bundle,
            tmp_path / "install",
        )


def test_duplicate_manifest_path_is_rejected(
    tmp_path: Path,
) -> None:
    bundle, manifest = build_bundle(
        tmp_path
    )

    manifest["files"][1][
        "path"
    ] = manifest["files"][0][
        "path"
    ]

    (
        bundle
        / "bundle-manifest.json"
    ).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(
        module.SandboxInstallerError,
        match="BUNDLE_DUPLICATE_PATH",
    ):
        install(
            bundle,
            tmp_path / "install",
        )


def test_existing_staging_path_blocks(
    tmp_path: Path,
) -> None:
    bundle, manifest = build_bundle(
        tmp_path
    )

    install_root = (
        tmp_path / "install"
    )

    staging = (
        install_root
        / "staging"
        / (
            ".install-"
            f"{manifest['release_id']}-"
            f"{TRANSACTION_ID}"
        )
    )

    staging.mkdir(
        parents=True,
    )

    with pytest.raises(
        module.SandboxInstallerError,
        match="STAGING_PATH_ALREADY_PRESENT",
    ):
        install(
            bundle,
            install_root,
        )


@pytest.mark.parametrize(
    "fault_point",
    [
        "AFTER_COPY_BEFORE_RECEIPT",
        "AFTER_RECEIPT_BEFORE_COMMIT",
    ],
)
def test_precommit_failure_rolls_back_staging(
    tmp_path: Path,
    fault_point: str,
) -> None:
    bundle, manifest = build_bundle(
        tmp_path
    )

    install_root = (
        tmp_path / "install"
    )

    with pytest.raises(
        module.SandboxInstallerError,
        match="INJECTED_",
    ):
        install(
            bundle,
            install_root,
            fault_point=fault_point,
        )

    staging_root = (
        install_root / "staging"
    )

    assert list(
        staging_root.iterdir()
    ) == []

    final_path = (
        install_root
        / "releases"
        / manifest["release_id"]
    )

    assert not final_path.exists()


def test_bundle_outside_tmp_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        module.SandboxInstallerError,
        match="BUNDLE_ROOT_OUTSIDE_TMP_REJECTED",
    ):
        module.install_prepared_bundle(
            bundle_root=Path(
                "/home/deploy/"
                "forbidden-bundle"
            ),
            sandbox_install_root=(
                tmp_path / "install"
            ),
            transaction_id=(
                TRANSACTION_ID
            ),
            now_utc=NOW,
        )


def test_install_root_outside_tmp_is_rejected(
    tmp_path: Path,
) -> None:
    bundle, _ = build_bundle(
        tmp_path
    )

    with pytest.raises(
        module.SandboxInstallerError,
        match=(
            "SANDBOX_INSTALL_ROOT_"
            "OUTSIDE_TMP_REJECTED"
        ),
    ):
        install(
            bundle,
            Path(
                "/home/deploy/"
                "forbidden-install"
            ),
        )


def test_success_result_remains_no_go(
    tmp_path: Path,
) -> None:
    bundle, _ = build_bundle(
        tmp_path
    )

    result = install(
        bundle,
        tmp_path / "install",
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
