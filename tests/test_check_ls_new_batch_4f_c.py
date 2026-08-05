from __future__ import annotations

import importlib.util
import json
import os
import pwd
import grp
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/check_ls_new_batch_4f_c.py"
POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_production_credential_nonsecret_check_policy.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4f_c_result.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "check_ls_new_batch_4f_c_test_module",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_policy_for_current_user() -> dict:
    policy = load_json(POLICY_PATH)
    policy["credential_contract"]["expected_owner"] = (
        pwd.getpwuid(os.getuid()).pw_name
    )
    policy["credential_contract"]["expected_group"] = (
        grp.getgrgid(os.getgid()).gr_name
    )
    return policy


def write_valid_file(path: Path) -> None:
    path.write_text(
        (
            "WORDPRESS_BASE_URL=https://fixture.invalid\n"
            "WORDPRESS_READONLY_USERNAME=DUMMY_USER\n"
            "WORDPRESS_READONLY_APP_PASSWORD=DUMMY_PASSWORD\n"
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def test_policy_keeps_external_access_closed() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert boundary["credential_metadata_read_allowed"] is True
    assert boundary["credential_structure_read_allowed"] is True
    assert boundary["credential_value_output_allowed"] is False
    assert boundary["network_connection_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["execution_allowed"] is False


def test_valid_file_passes_sanitized_check(
    tmp_path: Path,
) -> None:
    module = load_module()
    path = tmp_path / "valid.env"
    write_valid_file(path)

    evidence = module.perform_nonsecret_check(
        path,
        fixture_policy_for_current_user(),
    )

    assert evidence["exists"] is True
    assert evidence["regular_file"] is True
    assert evidence["symbolic_link"] is False
    assert evidence["mode_octal"] == "0600"
    assert evidence["required_keys_present"] is True
    assert evidence["credential_values_output"] is False


def test_missing_file_blocks(tmp_path: Path) -> None:
    module = load_module()

    try:
        module.perform_nonsecret_check(
            tmp_path / "missing.env",
            fixture_policy_for_current_user(),
        )
    except module.BlockedCheck as exc:
        assert (
            exc.status
            == "BLOCKED_PRODUCTION_CREDENTIAL_FILE_MISSING"
        )
    else:
        raise AssertionError("missing file was accepted")


def test_symlink_blocks(tmp_path: Path) -> None:
    module = load_module()
    target = tmp_path / "target.env"
    link = tmp_path / "link.env"

    write_valid_file(target)
    link.symlink_to(target)

    try:
        module.perform_nonsecret_check(
            link,
            fixture_policy_for_current_user(),
        )
    except module.BlockedCheck as exc:
        assert (
            exc.status
            == "BLOCKED_PRODUCTION_CREDENTIAL_SYMLINK"
        )
    else:
        raise AssertionError("symbolic link was accepted")


def test_wrong_mode_blocks(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "wrong-mode.env"

    write_valid_file(path)
    os.chmod(path, 0o644)

    try:
        module.perform_nonsecret_check(
            path,
            fixture_policy_for_current_user(),
        )
    except module.BlockedCheck as exc:
        assert (
            exc.status
            == "BLOCKED_PRODUCTION_CREDENTIAL_MODE_MISMATCH"
        )
    else:
        raise AssertionError("mode 0644 was accepted")


def test_missing_key_blocks(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "missing-key.env"

    path.write_text(
        (
            "WORDPRESS_BASE_URL=https://fixture.invalid\n"
            "WORDPRESS_READONLY_USERNAME=DUMMY_USER\n"
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)

    try:
        module.perform_nonsecret_check(
            path,
            fixture_policy_for_current_user(),
        )
    except module.BlockedCheck as exc:
        assert (
            exc.status
            == "BLOCKED_PRODUCTION_CREDENTIAL_MISSING_KEYS"
        )
    else:
        raise AssertionError("missing key was accepted")


def test_empty_value_blocks(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "empty.env"

    path.write_text(
        (
            "WORDPRESS_BASE_URL=https://fixture.invalid\n"
            "WORDPRESS_READONLY_USERNAME=\n"
            "WORDPRESS_READONLY_APP_PASSWORD=DUMMY_PASSWORD\n"
        ),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)

    try:
        module.perform_nonsecret_check(
            path,
            fixture_policy_for_current_user(),
        )
    except module.BlockedCheck as exc:
        assert (
            exc.status
            == "BLOCKED_PRODUCTION_CREDENTIAL_EMPTY_VALUES"
        )
    else:
        raise AssertionError("empty value was accepted")


def test_duplicate_key_blocks(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "duplicate.env"

    write_valid_file(path)

    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            "WORDPRESS_READONLY_USERNAME=SECOND_USER\n"
        )

    try:
        module.perform_nonsecret_check(
            path,
            fixture_policy_for_current_user(),
        )
    except module.BlockedCheck as exc:
        assert (
            exc.status
            == "BLOCKED_PRODUCTION_CREDENTIAL_DUPLICATE_KEYS"
        )
    else:
        raise AssertionError("duplicate key was accepted")


def test_unknown_key_blocks(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "unknown.env"

    write_valid_file(path)

    with path.open("a", encoding="utf-8") as handle:
        handle.write("UNKNOWN_KEY=value\n")

    try:
        module.perform_nonsecret_check(
            path,
            fixture_policy_for_current_user(),
        )
    except module.BlockedCheck as exc:
        assert (
            exc.status
            == "BLOCKED_PRODUCTION_CREDENTIAL_UNKNOWN_KEYS"
        )
    else:
        raise AssertionError("unknown key was accepted")


def test_result_never_contains_secret_values() -> None:
    result = load_json(RESULT_PATH)
    serialized = json.dumps(result, ensure_ascii=False)

    assert "DUMMY_PASSWORD" not in serialized
    assert "DUMMY_USER" not in serialized
    assert result["credential_values_output"] is False
    assert result["credential_value_lengths_output"] is False
    assert result["credential_value_hashes_output"] is False
