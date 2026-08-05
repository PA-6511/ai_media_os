#!/usr/bin/env python3
import argparse
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

try:
    import grp
    import pwd
except ImportError:  # pragma: no cover
    grp = None
    pwd = None

REQUIRED_KEYS = [
    "WORDPRESS_BASE_URL",
    "WORDPRESS_USERNAME",
    "WORDPRESS_APP_PASSWORD",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_credential_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def inspect_owner_group_mode(path: Path) -> tuple[dict[str, bool], list[str]]:
    warnings: list[str] = []
    safe = {"owner_safe": False, "group_safe": False, "mode_safe": False}
    try:
        st = path.stat()
    except OSError as exc:
        warnings.append(f"credential_env_stat_failed: {exc.__class__.__name__}")
        return safe, warnings

    safe["mode_safe"] = stat.S_IMODE(st.st_mode) == 0o600

    if pwd is not None:
        try:
            safe["owner_safe"] = pwd.getpwuid(st.st_uid).pw_name == "deploy"
        except KeyError:
            warnings.append("credential_env_owner_lookup_unavailable")
        except OSError:
            warnings.append("credential_env_owner_lookup_failed")
    else:
        warnings.append("credential_env_owner_lookup_unavailable")

    if grp is not None:
        try:
            safe["group_safe"] = grp.getgrgid(st.st_gid).gr_name == "deploy"
        except KeyError:
            warnings.append("credential_env_group_lookup_unavailable")
        except OSError:
            warnings.append("credential_env_group_lookup_failed")
    else:
        warnings.append("credential_env_group_lookup_unavailable")

    return safe, warnings


def validate(policy: dict, credential_env_path: Path) -> tuple[dict, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    require(policy.get("phase") == "LS-3", "policy phase must be LS-3", errors)
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "policy execution_mode must be DRY_RUN_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)

    safety_flags = policy.get("safety_flags", {})
    for key, value in safety_flags.items():
        require(value is False, f"policy safety flag {key} must be false", errors)

    result = {
        "phase": "LS-3",
        "status": "LS3_CREDENTIAL_ENV_NOT_READY",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "credential_env_path": str(credential_env_path),
        "credential_file_exists": False,
        "credential_file_is_regular": False,
        "required_keys_present": False,
        "required_keys_non_empty": False,
        "owner_safe": False,
        "group_safe": False,
        "mode_safe": False,
        "missing_keys": [],
        "warnings": warnings,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_hashes_output": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "publish_executed": False,
        "approval_token_consumed": False,
        "next_phase": {
            "phase": "LS-4",
            "execution_allowed": False,
        },
    }

    if errors:
        result["warnings"].extend(errors)
        return result, warnings

    if not credential_env_path.exists():
        result["warnings"].append("credential_env_missing")
        return result, warnings

    if not credential_env_path.is_file():
        result["warnings"].append("credential_env_not_regular_file")
        return result, warnings

    result["credential_file_exists"] = True
    result["credential_file_is_regular"] = True

    owner_group_mode, ownership_warnings = inspect_owner_group_mode(credential_env_path)
    result.update(owner_group_mode)
    result["warnings"].extend(ownership_warnings)

    try:
        values = parse_credential_env(credential_env_path)
    except OSError:
        result["warnings"].append("credential_env_read_failed")
        return result, warnings

    missing_keys = [key for key in REQUIRED_KEYS if key not in values]
    empty_keys = [key for key in REQUIRED_KEYS if key in values and values[key].strip() == ""]
    result["missing_keys"] = missing_keys
    result["required_keys_present"] = not missing_keys
    result["required_keys_non_empty"] = not missing_keys and not empty_keys

    if missing_keys:
        result["warnings"].append("required_keys_missing")
    if empty_keys:
        result["warnings"].append("required_keys_empty")

    if result["required_keys_present"] and result["required_keys_non_empty"]:
        result["status"] = "LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY"
    else:
        result["status"] = "LS3_CREDENTIAL_ENV_NOT_READY"

    return result, warnings


def write_report(result: dict, output_report: Path) -> None:
    lines = [
        "# LS-3 WordPress credential.env READY Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- credential_env_path: {result['credential_env_path']}",
        f"- credential_file_exists: {result['credential_file_exists']}",
        f"- credential_file_is_regular: {result['credential_file_is_regular']}",
        f"- required_keys_present: {result['required_keys_present']}",
        f"- required_keys_non_empty: {result['required_keys_non_empty']}",
        f"- owner_safe: {result['owner_safe']}",
        f"- group_safe: {result['group_safe']}",
        f"- mode_safe: {result['mode_safe']}",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- secret_values_output: {result['secret_values_output']}",
        f"- secret_lengths_output: {result['secret_lengths_output']}",
        f"- secret_hashes_output: {result['secret_hashes_output']}",
        f"- warnings_count: {len(result.get('warnings', []))}",
        "",
        "## Next Phase",
        "",
        "Next recommended phase: LS-4 WordPress Draft Runner DRY_RUN.",
        "",
    ]
    if result.get("missing_keys"):
        lines.extend(["## Missing Keys", ""]) 
        for key in result["missing_keys"]:
            lines.append(f"- {key}")
        lines.append("")
    if result.get("warnings"):
        lines.extend(["## Warnings", ""])
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
    output_report.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls3_wordpress_credential_ready_policy.json")
    parser.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    parser.add_argument("--output", default="exchange/logs/start_ls3_wordpress_credential_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls3_wordpress_credential_ready_report.md")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    credential_env_path = Path(args.credential_env)
    output_path = Path(args.output)
    report_path = Path(args.report)

    policy = load_json(policy_path)
    result, _ = validate(policy, credential_env_path)
    result["generated_at"] = datetime.now(timezone.utc).isoformat()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, report_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())