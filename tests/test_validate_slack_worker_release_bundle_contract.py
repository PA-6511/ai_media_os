from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


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

validator_path = (
    repo
    / "scripts/"
    "validate_slack_worker_release_bundle_contract.py"
)


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def canonical_sha256(
    value: dict,
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


def test_validator_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(validator_path),
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout
    )

    assert (
        "SQL_B2_4B_5G_3B_1D_1C_"
        "RELEASE_BUNDLE_CONTRACT: PASS"
        in result.stdout
    )

    assert (
        "FINAL_DECISION: NO_GO"
        in result.stdout
    )


def test_manifest_digest() -> None:
    manifest = load(
        manifest_path
    )

    content = {
        key: value
        for key, value in manifest.items()
        if key not in {
            "manifest_content_sha256",
            "release_id_candidate",
        }
    }

    assert (
        manifest[
            "manifest_content_sha256"
        ]
        == canonical_sha256(content)
    )


def test_runtime_source_closure() -> None:
    manifest = load(
        manifest_path
    )

    assert (
        manifest["source_file_count"]
        == 16
    )

    assert (
        len(manifest["source_files"])
        == 16
    )

    assert (
        manifest[
            "candidate_data_files"
        ]
        == []
    )


def test_wheel_contract() -> None:
    manifest = load(
        manifest_path
    )

    versions = {
        item["canonical_name"]: (
            item["version"]
        )
        for item in manifest["wheels"]
    }

    assert versions == {
        "greenlet": "3.5.3",
        "slack-bolt": "1.29.0",
        "slack-sdk": "3.43.0",
        "sqlalchemy": "2.0.51",
        "typing-extensions": "4.16.0",
    }


def test_release_layout_is_root_managed() -> None:
    policy = load(
        policy_path
    )

    layout = policy[
        "release_layout"
    ]

    ownership = policy[
        "ownership_contract"
    ]

    assert layout[
        "release_root"
    ] == (
        "/opt/ai-media-os/"
        "slack-worker/releases"
    )

    assert ownership[
        "release_root_owner"
    ] == "root"

    assert ownership[
        "release_root_group"
    ] == "root"

    assert ownership[
        "service_user_write_allowed"
    ] is False


def test_secret_boundary_is_root_managed() -> None:
    policy = load(
        policy_path
    )

    secret = policy[
        "secret_boundary_contract"
    ]

    assert secret[
        "target_path"
    ] == (
        "/etc/ai-media-os-secrets/"
        "slack-worker.env"
    )

    assert secret["owner"] == "root"
    assert secret["group"] == "root"
    assert secret["mode"] == "0600"

    assert secret[
        "service_user_write_allowed"
    ] is False

    assert secret[
        "content_read_in_design_phase"
    ] is False

    assert secret[
        "content_hashed_in_design_phase"
    ] is False


def test_design_remains_no_go() -> None:
    policy = load(
        policy_path
    )

    governance = policy[
        "governance"
    ]

    assert governance[
        "design_only"
    ] is True

    assert governance[
        "host_change_allowed"
    ] is False

    assert governance[
        "unit_change_allowed"
    ] is False

    assert governance[
        "gate_creation_allowed"
    ] is False

    assert governance[
        "service_start_allowed"
    ] is False

    assert governance[
        "unit_enable_allowed"
    ] is False

    assert governance[
        "final_decision"
    ] == "NO_GO"



def test_symlink_contract_distinguishes_trusted_and_untrusted_links() -> None:
    policy = load(
        policy_path
    )

    assert policy[
        "contract_revision"
    ] == 2

    assert policy[
        "correction_phase"
    ] == (
        "SQL-B2-4B-5G-3B-1D-1C-1"
    )

    verification = policy[
        "verification_contract"
    ]

    assert (
        "release_tree_symlink_rejected"
        not in verification
    )

    assert verification[
        "source_tree_symlink_rejected"
    ] is True

    assert verification[
        "manifest_tree_symlink_rejected"
    ] is True

    assert verification[
        "unapproved_release_symlink_rejected"
    ] is True

    assert verification[
        "venv_internal_symlinks_allowed"
    ] is True

    assert verification[
        "venv_python_symlink_allowed"
    ] is True

    assert verification[
        "venv_python_symlink_target_must_be_root_managed"
    ] is True

    assert verification[
        "venv_python_symlink_target_must_not_be_service_user_writable"
    ] is True

    assert verification[
        "current_link_exception_governed_by_activation_contract"
    ] is True

    activation = policy[
        "activation_contract"
    ]

    assert activation[
        "current_link_allowed"
    ] is True

    assert activation[
        "current_link_owner"
    ] == "root"

    assert activation[
        "current_link_group"
    ] == "root"

    assert activation[
        "current_link_target_must_be_direct_child_of_release_root"
    ] is True

    assert activation[
        "current_link_target_must_not_be_writable_by_service_user"
    ] is True


def test_validator_reports_symlink_boundary_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(validator_path),
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout
    )

    assert (
        "SYMLINK_BOUNDARY_CONTRACT: PASS"
        in result.stdout
    )
