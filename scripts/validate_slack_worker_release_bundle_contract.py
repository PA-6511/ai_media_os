from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

try:
    from scripts.lib.secure_release_file_reader import (
        RELEASE_FILE_SHA_MISMATCH,
        ReleaseFileError,
        read_secure_release_file,
        resolve_secure_source_path,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/ on sys.path.
    from lib.secure_release_file_reader import (  # type: ignore[no-redef]
        RELEASE_FILE_SHA_MISMATCH,
        ReleaseFileError,
        read_secure_release_file,
        resolve_secure_source_path,
    )


repo = Path(__file__).resolve().parents[1]

policy_path = (
    repo
    / "config/"
    "slack_worker_release_bundle_policy.json"
)

manifest_path = (
    repo
    / "config/"
    "slack_worker_release_source_manifest.json"
)

hash_lock_path = (
    repo
    / "config/"
    "slack_worker_release_"
    "requirements_hash_locked.txt"
)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SystemExit("MANIFEST_JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _decode_json(data: bytes, *, error_code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(error_code) from exc
    if not isinstance(value, dict):
        raise SystemExit(error_code)
    return value


def validate_production_manifest_contract(manifest: dict[str, Any]) -> None:
    """Reject candidate documents before evaluating the production schema."""

    candidate_markers = (
        manifest.get("release_status") == "CANDIDATE_NOT_APPROVED"
        or manifest.get("schema_version")
        == "slack_worker_release_manifest_candidate_v1"
        or "candidate_manifest_content_sha256" in manifest
        or "candidate_id" in manifest
    )
    if candidate_markers:
        raise SystemExit("CANDIDATE_MANIFEST_NOT_VALID_AS_PRODUCTION_RELEASE")
    if manifest.get("schema_version") != 1:
        raise SystemExit("PRODUCTION_MANIFEST_SCHEMA_INVALID")
    required_fields = {
        "manifest_content_sha256",
        "release_id_candidate",
        "phase",
        "design_source_commit",
        "source_file_count",
        "source_files",
        "wheel_count",
        "wheels",
        "requirements_hash_lock",
    }
    if not required_fields.issubset(manifest):
        raise SystemExit("PRODUCTION_MANIFEST_SCHEMA_INVALID")
    if (
        not isinstance(manifest["source_files"], list)
        or not isinstance(manifest["wheels"], list)
        or not isinstance(manifest["requirements_hash_lock"], dict)
        or manifest["source_file_count"] != len(manifest["source_files"])
        or manifest["wheel_count"] != len(manifest["wheels"])
        or any(
            not isinstance(item, dict)
            or not {"path", "sha256", "size"}.issubset(item)
            for item in manifest["source_files"]
        )
    ):
        raise SystemExit("PRODUCTION_MANIFEST_SCHEMA_INVALID")


def load_production_manifest(
    repository_root: Path,
    path: Path,
) -> tuple[dict[str, Any], str]:
    config_root = repository_root.resolve(strict=True) / "config"
    expected = config_root / "slack_worker_release_source_manifest.json"
    try:
        snapshot = read_secure_release_file(
            path,
            allowed_root=config_root,
            expected_path=expected,
        )
    except ReleaseFileError as exc:
        raise SystemExit(exc.code) from exc
    manifest = _decode_json(snapshot.data, error_code="MANIFEST_JSON_INVALID")
    validate_production_manifest_contract(manifest)
    return manifest, snapshot.sha256


def canonical_sha256(
    value: dict[str, object],
) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def validate(
    repository_root: Path = repo,
    production_manifest_path: Path = manifest_path,
    bundle_policy_path: Path = policy_path,
    requirements_lock_path: Path = hash_lock_path,
) -> None:
    root = repository_root.resolve(strict=True)
    config_root = root / "config"
    try:
        policy_snapshot = read_secure_release_file(
            bundle_policy_path,
            allowed_root=config_root,
            expected_path=config_root / "slack_worker_release_bundle_policy.json",
        )
    except ReleaseFileError as exc:
        raise SystemExit(exc.code) from exc
    policy = _decode_json(policy_snapshot.data, error_code="POLICY_JSON_INVALID")
    manifest, _manifest_file_sha = load_production_manifest(
        root, production_manifest_path
    )

    if policy["phase"] != (
        "SQL-B2-4B-5G-3B-1D-1C"
    ):
        raise SystemExit(
            "POLICY_PHASE_INVALID"
        )

    if policy["result"] != (
        "PASS_ROOT_MANAGED_RELEASE_"
        "BUNDLE_CONTRACT_DESIGN_ONLY_"
        "NO_HOST_CHANGE_NO_GO"
    ):
        raise SystemExit(
            "POLICY_RESULT_INVALID"
        )

    content = {
        key: value
        for key, value in manifest.items()
        if key not in {
            "manifest_content_sha256",
            "release_id_candidate",
        }
    }

    expected_digest = canonical_sha256(
        content
    )

    if manifest[
        "manifest_content_sha256"
    ] != expected_digest:
        raise SystemExit(
            "MANIFEST_CONTENT_SHA_INVALID"
        )

    expected_release_id = (
        "slack-worker-"
        + manifest[
            "design_source_commit"
        ][:7]
        + "-"
        + expected_digest[:12]
    )

    if manifest[
        "release_id_candidate"
    ] != expected_release_id:
        raise SystemExit(
            "RELEASE_ID_INVALID"
        )

    source_files = manifest["source_files"]

    if len(source_files) != 16:
        raise SystemExit(
            "SOURCE_FILE_COUNT_INVALID"
        )

    forbidden_roots = {
        ".git",
        ".venv",
        "backup",
        "data",
        "exchange",
        "reports",
    }

    seen_paths: set[str] = set()
    for item in source_files:
        try:
            relative_text, source = resolve_secure_source_path(root, item["path"])
        except ReleaseFileError as exc:
            raise SystemExit(f"{exc.code}: {item.get('path', '<missing>')}") from exc

        if relative_text in seen_paths:
            raise SystemExit(f"DUPLICATE_SOURCE_PATH: {relative_text}")
        seen_paths.add(relative_text)
        relative = Path(relative_text)

        if (
            not relative.parts
            or relative.parts[0]
            in forbidden_roots
        ):
            raise SystemExit(
                "FORBIDDEN_SOURCE_PATH: "
                f"{relative}"
            )

        try:
            snapshot = read_secure_release_file(
                source,
                allowed_root=root,
                expected_sha256=item["sha256"],
            )
        except ReleaseFileError as exc:
            if exc.code == RELEASE_FILE_SHA_MISMATCH:
                raise SystemExit(f"SOURCE_SHA_MISMATCH: {relative_text}") from exc
            raise SystemExit(f"{exc.code}: {relative_text}") from exc

        if snapshot.size != item["size"]:
            raise SystemExit(
                "SOURCE_SIZE_MISMATCH: "
                f"{relative_text}"
            )

    wheels = manifest["wheels"]

    if len(wheels) != 5:
        raise SystemExit(
            "WHEEL_COUNT_INVALID"
        )

    expected_versions = {
        "greenlet": "3.5.3",
        "slack-bolt": "1.29.0",
        "slack-sdk": "3.43.0",
        "sqlalchemy": "2.0.51",
        "typing-extensions": "4.16.0",
    }

    actual_versions = {
        item["canonical_name"]: (
            item["version"]
        )
        for item in wheels
    }

    if actual_versions != (
        expected_versions
    ):
        raise SystemExit(
            "WHEEL_VERSION_SET_INVALID"
        )

    for item in wheels:
        if not re.fullmatch(
            r"[0-9a-f]{64}",
            item["sha256"],
        ):
            raise SystemExit(
                "WHEEL_SHA_INVALID: "
                f"{item['canonical_name']}"
            )

        if not item[
            "compatible_tags"
        ]:
            raise SystemExit(
                "WHEEL_COMPATIBLE_TAG_MISSING: "
                f"{item['canonical_name']}"
            )

    lock = manifest[
        "requirements_hash_lock"
    ]

    try:
        lock_snapshot = read_secure_release_file(
            requirements_lock_path,
            allowed_root=config_root,
            expected_path=(
                config_root / "slack_worker_release_requirements_hash_locked.txt"
            ),
            expected_sha256=lock["sha256"],
        )
    except ReleaseFileError as exc:
        if exc.code == RELEASE_FILE_SHA_MISMATCH:
            raise SystemExit("HASH_LOCK_SHA_MISMATCH") from exc
        raise SystemExit(exc.code) from exc

    try:
        lock_text = lock_snapshot.data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit("HASH_LOCK_ENCODING_INVALID") from exc
    lock_lines = [line for line in lock_text.splitlines() if line.strip()]

    if len(lock_lines) != 5:
        raise SystemExit(
            "HASH_LOCK_LINE_COUNT_INVALID"
        )

    governance = policy[
        "governance"
    ]

    required_false = (
        "root_release_install_executed",
        "secret_migration_executed",
        "host_change_allowed",
        "unit_change_allowed",
        "daemon_reload_allowed",
        "gate_creation_allowed",
        "systemd_block_test_allowed",
        "service_start_allowed",
        "unit_enable_allowed",
        "production_database_write_allowed",
    )

    for key in required_false:
        if governance[key] is not False:
            raise SystemExit(
                f"GOVERNANCE_FALSE_INVALID: {key}"
            )

    if governance[
        "production_status"
    ] != "NO_GO":
        raise SystemExit(
            "PRODUCTION_STATUS_INVALID"
        )

    if governance[
        "final_decision"
    ] != "NO_GO":
        raise SystemExit(
            "FINAL_DECISION_INVALID"
        )

    if policy.get(
        "contract_revision"
    ) != 2:
        raise SystemExit(
            "CONTRACT_REVISION_INVALID"
        )

    if policy.get(
        "correction_phase"
    ) != (
        "SQL-B2-4B-5G-3B-1D-1C-1"
    ):
        raise SystemExit(
            "CORRECTION_PHASE_INVALID"
        )

    verification = policy[
        "verification_contract"
    ]

    if (
        "release_tree_symlink_rejected"
        in verification
    ):
        raise SystemExit(
            "AMBIGUOUS_RELEASE_TREE_"
            "SYMLINK_RULE_STILL_PRESENT"
        )

    required_symlink_rules = (
        "source_tree_symlink_rejected",
        "manifest_tree_symlink_rejected",
        "unapproved_release_symlink_rejected",
        "venv_internal_symlinks_allowed",
        "venv_python_symlink_allowed",
        (
            "venv_python_symlink_target_"
            "must_be_root_managed"
        ),
        (
            "venv_python_symlink_target_"
            "must_not_be_service_user_"
            "writable"
        ),
        (
            "current_link_exception_"
            "governed_by_activation_contract"
        ),
    )

    for key in required_symlink_rules:
        if verification.get(key) is not True:
            raise SystemExit(
                "SYMLINK_RULE_INVALID: "
                f"{key}"
            )

    activation = policy[
        "activation_contract"
    ]

    if activation[
        "current_link_allowed"
    ] is not True:
        raise SystemExit(
            "CURRENT_LINK_NOT_ALLOWED"
        )

    if activation[
        "current_link_owner"
    ] != "root":
        raise SystemExit(
            "CURRENT_LINK_OWNER_INVALID"
        )

    if activation[
        "current_link_group"
    ] != "root":
        raise SystemExit(
            "CURRENT_LINK_GROUP_INVALID"
        )

    if activation[
        "current_link_target_must_be_"
        "direct_child_of_release_root"
    ] is not True:
        raise SystemExit(
            "CURRENT_LINK_TARGET_BOUNDARY_INVALID"
        )

    if activation[
        "current_link_target_must_not_be_"
        "writable_by_service_user"
    ] is not True:
        raise SystemExit(
            "CURRENT_LINK_WRITE_BOUNDARY_INVALID"
        )

    secret = policy[
        "secret_boundary_contract"
    ]

    if secret["owner"] != "root":
        raise SystemExit(
            "SECRET_OWNER_INVALID"
        )

    if secret["group"] != "root":
        raise SystemExit(
            "SECRET_GROUP_INVALID"
        )

    if secret["mode"] != "0600":
        raise SystemExit(
            "SECRET_MODE_INVALID"
        )

    if secret[
        "service_user_write_allowed"
    ] is not False:
        raise SystemExit(
            "SECRET_WRITE_STATE_INVALID"
        )

    print(
        "RELEASE_SOURCE_MANIFEST: PASS"
    )

    print(
        "SOURCE_FILE_HASH_BINDING: PASS"
    )

    print(
        "TRANSITIVE_WHEEL_CONTRACT: PASS"
    )

    print(
        "HASH_LOCK_BINDING: PASS"
    )

    print(
        "ROOT_MANAGED_RELEASE_LAYOUT: PASS"
    )

    print(
        "ROOT_MANAGED_SECRET_CONTRACT: PASS"
    )

    print(
        "SYMLINK_BOUNDARY_CONTRACT: PASS"
    )

    print(
        "ROOT_RELEASE_INSTALL_EXECUTED: FALSE"
    )

    print(
        "SECRET_MIGRATION_EXECUTED: FALSE"
    )

    print(
        "UNIT_CHANGE_ALLOWED: FALSE"
    )

    print(
        "SERVICE_START_ALLOWED: FALSE"
    )

    print(
        "UNIT_ENABLE_ALLOWED: FALSE"
    )

    print("FINAL_DECISION: NO_GO")

    print(
        "SQL_B2_4B_5G_3B_1D_1C_"
        "RELEASE_BUNDLE_CONTRACT: PASS"
    )


if __name__ == "__main__":
    validate()
