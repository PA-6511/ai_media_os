from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATH = (
    REPO_ROOT
    / "systemd/"
    / "slack-autostart-verifier.py"
)

SPEC = importlib.util.spec_from_file_location(
    "slack_trusted_autostart_verifier",
    SOURCE_PATH,
)

assert SPEC is not None
assert SPEC.loader is not None

verifier = importlib.util.module_from_spec(
    SPEC
)

sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


NOW = datetime(
    2026,
    7,
    15,
    12,
    0,
    tzinfo=timezone.utc,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def prepare_artifacts(
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    verifier_path = (
        tmp_path / "verifier.py"
    )

    installed_unit_path = (
        tmp_path / "unit.service"
    )

    gate_path = (
        tmp_path / "gate.json"
    )

    shutil.copyfile(
        SOURCE_PATH,
        verifier_path,
    )

    verifier_path.chmod(0o755)

    installed_unit_path.write_text(
        "[Service]\n"
        "User=deploy\n"
        "ExecCondition=/usr/bin/python3 -I "
        "/usr/local/libexec/ai-media-os/"
        "slack-autostart-verifier.py "
        "--check-autostart\n",
        encoding="utf-8",
    )

    installed_unit_path.chmod(0o644)

    return (
        gate_path,
        installed_unit_path,
        verifier_path,
    )


def valid_payload(
    installed_unit_path: Path,
    verifier_path: Path,
) -> dict[str, object]:
    return {
        "schema_version": 2,
        "approval_label": (
            "APPROVED_FOR_SLACK_"
            "READINESS_AUTOSTART_ONLY"
        ),
        "target_unit": (
            "ai-media-os-slack-approval-"
            "readiness.service"
        ),
        "installed_unit_sha256": (
            sha256(installed_unit_path)
        ),
        "verifier_sha256": (
            sha256(verifier_path)
        ),
        "approved_by": "human-operator",
        "approved_at": (
            NOW - timedelta(minutes=1)
        ).isoformat(),
        "expires_at": (
            NOW + timedelta(hours=1)
        ).isoformat(),
        "production_status": "NO_GO",
        "safety_scope": (
            "READINESS_DRY_RUN_AUTOSTART_ONLY"
        ),
        "slack_mode": "DRY_RUN",
        "production_database_allowed": False,
        "automatic_start_allowed": True,
    }


def write_gate(
    gate_path: Path,
    payload: dict[str, object],
) -> None:
    gate_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    gate_path.chmod(0o644)


def validate(
    gate_path: Path,
    installed_unit_path: Path,
    verifier_path: Path,
):
    return verifier.validate_autostart_approval(
        gate_path=gate_path,
        installed_unit_path=(
            installed_unit_path
        ),
        verifier_path=verifier_path,
        trusted_root=gate_path.parent,
        now=NOW,
        expected_uid=os.getuid(),
        expected_gid=os.getgid(),
    )


def test_valid_gate_is_approved(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    write_gate(
        gate,
        valid_payload(unit, verifier_path),
    )

    approval = validate(
        gate,
        unit,
        verifier_path,
    )

    assert approval.installed_unit_sha256 == (
        sha256(unit)
    )

    assert approval.verifier_sha256 == (
        sha256(verifier_path)
    )


def test_missing_gate_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_gate_symlink_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    real_gate = tmp_path / "real-gate.json"

    write_gate(
        real_gate,
        valid_payload(unit, verifier_path),
    )

    gate.symlink_to(real_gate)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_wrong_gate_mode_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    write_gate(
        gate,
        valid_payload(unit, verifier_path),
    )

    gate.chmod(0o600)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_wrong_gate_owner_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    write_gate(
        gate,
        valid_payload(unit, verifier_path),
    )

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        verifier.validate_autostart_approval(
            gate_path=gate,
            installed_unit_path=unit,
            verifier_path=verifier_path,
            now=NOW,
            expected_uid=os.getuid() + 1,
            expected_gid=os.getgid(),
        )


def test_malformed_json_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    gate.write_text(
        "{invalid",
        encoding="utf-8",
    )
    gate.chmod(0o644)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_duplicate_field_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )

    text = json.dumps(payload)

    text = text.replace(
        '"schema_version": 2',
        (
            '"schema_version": 2, '
            '"schema_version": 2'
        ),
        1,
    )

    gate.write_text(
        text,
        encoding="utf-8",
    )
    gate.chmod(0o644)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_unexpected_field_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["unexpected"] = True

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_missing_field_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    del payload["verifier_sha256"]

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_installed_unit_hash_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["installed_unit_sha256"] = (
        "a" * 64
    )

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_verifier_hash_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["verifier_sha256"] = (
        "b" * 64
    )

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_expired_gate_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["expires_at"] = (
        NOW - timedelta(seconds=1)
    ).isoformat()

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_future_approval_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["approved_at"] = (
        NOW + timedelta(minutes=6)
    ).isoformat()

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_excessive_validity_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["approved_at"] = NOW.isoformat()
    payload["expires_at"] = (
        NOW + timedelta(hours=25)
    ).isoformat()

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_wrong_approval_label_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["approval_label"] = "WRONG"

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_wrong_target_unit_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["target_unit"] = "wrong.service"

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_wrong_safety_scope_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["safety_scope"] = "PRODUCTION"

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_wrong_slack_mode_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )
    payload["slack_mode"] = "LIVE"

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_production_database_allowed_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )

    payload[
        "production_database_allowed"
    ] = True

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_automatic_start_false_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )

    payload[
        "automatic_start_allowed"
    ] = False

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_credential_shape_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    payload = valid_payload(
        unit,
        verifier_path,
    )

    payload["approved_by"] = (
        "xoxb-" + ("A" * 24)
    )

    write_gate(gate, payload)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        validate(gate, unit, verifier_path)


def test_source_uses_only_standard_library() -> None:
    source = SOURCE_PATH.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(source)

    forbidden_roots = {
        "app",
        "scripts",
        "sqlalchemy",
        "slack_bolt",
        "pytest",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert (
                    alias.name.split(".", 1)[0]
                    not in forbidden_roots
                )

        if isinstance(node, ast.ImportFrom):
            assert node.module is not None

            assert (
                node.module.split(".", 1)[0]
                not in forbidden_roots
            )

    assert "sys.path.insert" not in source
    assert "site.addsitedir" not in source
    assert "subprocess" not in source


def test_isolated_cli_fails_closed_without_gate() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(SOURCE_PATH),
            "--check-autostart",
        ],
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": "/untrusted/path",
        },
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 3
    assert (
        "AUTOSTART_APPROVAL: NOT_APPROVED"
        in result.stdout
    )
    assert "FINAL_DECISION: NO_GO" in (
        result.stdout
    )
    assert "xoxb-" not in result.stdout
    assert "xapp-" not in result.stdout


def test_nonisolated_cli_is_rejected() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SOURCE_PATH),
            "--check-autostart",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 3
    assert (
        "PYTHON_NOT_ISOLATED"
        in result.stdout
    )
    assert "FINAL_DECISION: NO_GO" in (
        result.stdout
    )



def test_default_gate_path_uses_dedicated_root_directory() -> None:
    assert verifier.GATE_PATH == Path(
        "/etc/ai-media-os-autostart/"
        "slack-readiness-autostart.approved"
    )


def test_path_outside_trusted_root_is_rejected(
    tmp_path: Path,
) -> None:
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    trusted_root.chmod(0o700)

    outside = tmp_path / "outside"
    outside.mkdir()
    outside.chmod(0o700)

    gate, unit, verifier_path = (
        prepare_artifacts(outside)
    )

    write_gate(
        gate,
        valid_payload(unit, verifier_path),
    )

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        verifier.validate_autostart_approval(
            gate_path=gate,
            installed_unit_path=unit,
            verifier_path=verifier_path,
            trusted_root=trusted_root,
            now=NOW,
            expected_uid=os.getuid(),
            expected_gid=os.getgid(),
        )


def test_writable_trusted_root_is_rejected(
    tmp_path: Path,
) -> None:
    gate, unit, verifier_path = (
        prepare_artifacts(tmp_path)
    )

    write_gate(
        gate,
        valid_payload(unit, verifier_path),
    )

    tmp_path.chmod(0o775)

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        verifier.validate_autostart_approval(
            gate_path=gate,
            installed_unit_path=unit,
            verifier_path=verifier_path,
            trusted_root=tmp_path,
            now=NOW,
            expected_uid=os.getuid(),
            expected_gid=os.getgid(),
        )


def test_writable_nested_ancestor_is_rejected(
    tmp_path: Path,
) -> None:
    trusted_root = tmp_path / "trusted"
    trusted_root.mkdir()
    trusted_root.chmod(0o700)

    nested = trusted_root / "nested"
    nested.mkdir()
    nested.chmod(0o775)

    gate, unit, verifier_path = (
        prepare_artifacts(nested)
    )

    write_gate(
        gate,
        valid_payload(unit, verifier_path),
    )

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        verifier.validate_autostart_approval(
            gate_path=gate,
            installed_unit_path=unit,
            verifier_path=verifier_path,
            trusted_root=trusted_root,
            now=NOW,
            expected_uid=os.getuid(),
            expected_gid=os.getgid(),
        )


def test_symlink_ancestor_is_rejected(
    tmp_path: Path,
) -> None:
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    real_directory.chmod(0o700)

    linked_directory = tmp_path / "linked"
    linked_directory.symlink_to(
        real_directory,
        target_is_directory=True,
    )

    gate, unit, verifier_path = (
        prepare_artifacts(linked_directory)
    )

    write_gate(
        gate,
        valid_payload(unit, verifier_path),
    )

    with pytest.raises(
        verifier.TrustedVerifierError
    ):
        verifier.validate_autostart_approval(
            gate_path=gate,
            installed_unit_path=unit,
            verifier_path=verifier_path,
            trusted_root=tmp_path,
            now=NOW,
            expected_uid=os.getuid(),
            expected_gid=os.getgid(),
        )
