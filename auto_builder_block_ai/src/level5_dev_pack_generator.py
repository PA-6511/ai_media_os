import json
from pathlib import Path

from auto_builder_block_ai.src.codex_preprocessor import preprocess_codex_context
from auto_builder_block_ai.src.copilot_prompt_generator import generate_copilot_prompt
from auto_builder_block_ai.src.low_token_dev_mode import (
    DEFAULT_EXECUTION_MODE,
    DEFAULT_PRODUCTION_STATUS,
)

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports/level5"


def _slugify(value: str) -> str:
    cleaned = [character.lower() if character.isalnum() else "_" for character in value]
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "level5"


def generate_level5_dev_pack(
    phase_name: str,
    objective: str,
    target_files: list[str],
    validation_commands: list[str],
    report_dir: Path | None = None,
) -> dict:
    output_dir = Path(report_dir or REPORTS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    slug = _slugify(phase_name)
    dev_pack_path = output_dir / f"dev_pack_{slug}.json"
    prompt_path = output_dir / f"copilot_prompt_{slug}.txt"
    summary_path = output_dir / f"codex_summary_{slug}.md"
    allowed_files_path = output_dir / f"allowed_files_{slug}.txt"

    forbidden_actions = [
        "Do not read credentials.",
        "Do not call external APIs.",
        "Do not write to WordPress.",
        "Do not run production execution.",
        "Do not change systemd or cron.",
    ]
    prompt_text = generate_copilot_prompt(
        phase_name=phase_name,
        objective=objective,
        target_files=target_files,
        forbidden_actions=forbidden_actions,
        validation_commands=validation_commands,
    )
    codex_summary = preprocess_codex_context(
        raw_log="Design-only Level5 dev pack generation.",
        diff_summary="Files prepared for dry-run validation.",
        failing_tests=[],
    )

    generated_artifacts = [
        str(dev_pack_path),
        str(prompt_path),
        str(summary_path),
        str(allowed_files_path),
    ]
    dev_pack = {
        "phase_name": phase_name,
        "objective": objective,
        "production_status": DEFAULT_PRODUCTION_STATUS,
        "execution_mode": DEFAULT_EXECUTION_MODE,
        "external_calls_allowed": False,
        "credential_access_allowed": False,
        "wordpress_write_allowed": False,
        "systemd_changes_allowed": False,
        "target_files": target_files,
        "validation_commands": validation_commands,
        "generated_artifacts": generated_artifacts,
    }

    dev_pack_path.write_text(json.dumps(dev_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    prompt_path.write_text(prompt_text + "\n", encoding="utf-8")
    summary_path.write_text(codex_summary + "\n", encoding="utf-8")
    allowed_files_path.write_text("\n".join(target_files) + "\n", encoding="utf-8")

    return {
        "status": "READY",
        "report_dir": str(output_dir),
        "generated_artifacts": generated_artifacts,
        "dev_pack": dev_pack,
    }