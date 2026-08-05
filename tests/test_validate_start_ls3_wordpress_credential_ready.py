import json
import subprocess
from pathlib import Path


def test_policy_json_is_valid_and_flags_are_false():
    policy = json.loads(Path("config/start_ls3_wordpress_credential_ready_policy.json").read_text(encoding="utf-8"))
    assert policy["phase"] == "LS-3"
    assert policy["execution_mode"] == "DRY_RUN_ONLY"
    assert policy["production_status"] == "NO_GO"

    flags = policy["safety_flags"]
    assert flags["wordpress_api_call_allowed"] is False
    assert flags["wordpress_write_allowed"] is False
    assert flags["publish_allowed"] is False
    assert flags["amazon_api_call_allowed"] is False
    assert flags["x_api_call_allowed"] is False
    assert flags["x_post_allowed"] is False
    assert flags["approval_token_consumed"] is False
    assert flags["phase_forward_execution_allowed"] is False


def test_missing_credential_env_returns_not_ready_without_secret_output(tmp_path):
    output = tmp_path / "result.json"
    report = tmp_path / "report.md"
    missing_env = tmp_path / "missing-credential.env"

    completed = subprocess.run(
        [
            "python3",
            "scripts/validate_start_ls3_wordpress_credential_ready.py",
            "--credential-env",
            str(missing_env),
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "LS3_CREDENTIAL_ENV_NOT_READY"
    assert result["credential_file_exists"] is False
    assert result["secret_values_output"] is False
    assert result["secret_lengths_output"] is False
    assert result["secret_hashes_output"] is False
    assert "credential_env_missing" in result["warnings"]
    assert "WORDPRESS_APP_PASSWORD" not in completed.stdout


def test_ready_credential_env_returns_ready_without_secret_leak(tmp_path):
    output = tmp_path / "result.json"
    report = tmp_path / "report.md"
    credential_env = tmp_path / "credential.env"
    credential_env.write_text(
        "WORDPRESS_BASE_URL=https://example.test\nWORDPRESS_USERNAME=deploy-user\nWORDPRESS_APP_PASSWORD=opaque-secret-value\n",
        encoding="utf-8",
    )
    credential_env.chmod(0o600)

    completed = subprocess.run(
        [
            "python3",
            "scripts/validate_start_ls3_wordpress_credential_ready.py",
            "--credential-env",
            str(credential_env),
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY"
    assert result["credential_file_exists"] is True
    assert result["credential_file_is_regular"] is True
    assert result["required_keys_present"] is True
    assert result["required_keys_non_empty"] is True
    assert result["secret_values_output"] is False
    assert result["secret_lengths_output"] is False
    assert result["secret_hashes_output"] is False
    assert result["wordpress_api_call_executed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_executed"] is False
    assert report.exists()
    assert "LS-3 WordPress credential.env READY Report" in report.read_text(encoding="utf-8")
    assert "opaque-secret-value" not in completed.stdout
    assert "https://example.test" not in completed.stdout
    assert "deploy-user" not in completed.stdout


def test_empty_or_missing_keys_return_not_ready_without_value_exposure(tmp_path):
    output = tmp_path / "result.json"
    report = tmp_path / "report.md"
    credential_env = tmp_path / "credential.env"
    credential_env.write_text(
        "WORDPRESS_BASE_URL=https://example.test\nWORDPRESS_USERNAME=\n",
        encoding="utf-8",
    )
    credential_env.chmod(0o600)

    completed = subprocess.run(
        [
            "python3",
            "scripts/validate_start_ls3_wordpress_credential_ready.py",
            "--credential-env",
            str(credential_env),
            "--output",
            str(output),
            "--report",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "LS3_CREDENTIAL_ENV_NOT_READY"
    assert result["required_keys_present"] is False
    assert result["required_keys_non_empty"] is False
    assert result["secret_values_output"] is False
    assert result["secret_lengths_output"] is False
    assert result["secret_hashes_output"] is False
    assert result["missing_keys"] == ["WORDPRESS_APP_PASSWORD"]
    assert "WORDPRESS_APP_PASSWORD=opaque" not in completed.stdout
    assert "https://example.test" not in completed.stdout