import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PACKAGE_ROOT / "config"
DEFAULT_POLICY_PATH = CONFIG_DIR / "low_token_dev_mode_policy.json"

FINAL_STATUS = "AUTO_BUILDER_LEVEL5_READY_DRY_RUN_ONLY"
DEFAULT_PRODUCTION_STATUS = "NO_GO"
DEFAULT_EXECUTION_MODE = "DRY_RUN_ONLY"
REQUIRED_POLICY_KEYS = [
    "phase_id",
    "status",
    "production_status",
    "execution_mode",
    "external_calls_allowed",
    "credential_access_allowed",
    "systemd_changes_allowed",
    "wordpress_write_allowed",
    "allowed_output_blocks",
    "forbidden_actions",
    "required_prompt_sections",
]


def load_low_token_policy(path: Path | None = None) -> dict:
    policy_path = Path(path or DEFAULT_POLICY_PATH)
    return json.loads(policy_path.read_text(encoding="utf-8"))


def validate_low_token_policy(policy: dict) -> list[str]:
    errors = []
    for key in REQUIRED_POLICY_KEYS:
        if key not in policy:
            errors.append(f"missing key: {key}")

    expected_values = {
        "status": "LOW_TOKEN_DEV_MODE_POLICY_READY_DESIGN_ONLY",
        "production_status": DEFAULT_PRODUCTION_STATUS,
        "execution_mode": DEFAULT_EXECUTION_MODE,
        "external_calls_allowed": False,
        "credential_access_allowed": False,
        "systemd_changes_allowed": False,
        "wordpress_write_allowed": False,
    }
    for key, expected in expected_values.items():
        if policy.get(key) != expected:
            errors.append(f"{key} must be {expected!r}")

    if not isinstance(policy.get("allowed_output_blocks", []), list):
        errors.append("allowed_output_blocks must be a list")
    if not isinstance(policy.get("forbidden_actions", []), list):
        errors.append("forbidden_actions must be a list")
    if not isinstance(policy.get("required_prompt_sections", []), list):
        errors.append("required_prompt_sections must be a list")

    return errors


def build_status_report() -> dict:
    return {
        "level5_status": FINAL_STATUS,
        "low_token_dev_mode": "READY",
        "copilot_prompt_generator": "READY",
        "codex_preprocessor_mode": "READY",
        "phase_dev_pack_generator": "READY",
        "production_status": DEFAULT_PRODUCTION_STATUS,
        "execution_mode": DEFAULT_EXECUTION_MODE,
        "next_step": "USE_FOR_LOW_TOKEN_PHASE_DEVELOPMENT_ONLY",
    }