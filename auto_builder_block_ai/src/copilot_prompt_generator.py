from pathlib import Path

MANDATORY_SECTIONS = [
    "TASK",
    "SCOPE",
    "ALLOWED_FILES",
    "DO_NOT",
    "VALIDATION",
    "OUTPUT",
]

DEFAULT_FORBIDDEN_ACTIONS = [
    "Do not read credentials.",
    "Do not call external APIs.",
    "Do not run production execution.",
    "Do not write to WordPress.",
    "Do not change systemd, sudo, cron, timers, or services.",
]


def _normalize_lines(values: list[str]) -> list[str]:
    normalized = []
    for value in values:
        text = str(value).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _output_block(title: str, lines: list[str]) -> str:
    body = "\n".join(f"- {line}" for line in lines)
    return f"{title}:\n{body}"


def generate_copilot_prompt(
    phase_name: str,
    objective: str,
    target_files: list[str],
    forbidden_actions: list[str],
    validation_commands: list[str],
) -> str:
    allowed_files = _normalize_lines(target_files)
    blocked_actions = _normalize_lines(DEFAULT_FORBIDDEN_ACTIONS + forbidden_actions)
    validations = _normalize_lines(validation_commands)

    blocks = [
        _output_block("TASK", [f"Phase {phase_name}: {objective.strip()}"]),
        _output_block(
            "SCOPE",
            [
                "Stay within DESIGN_ONLY and DRY_RUN_ONLY.",
                "Work only on the listed files.",
            ],
        ),
        _output_block("ALLOWED_FILES", allowed_files),
        _output_block("DO_NOT", blocked_actions),
        _output_block("VALIDATION", validations),
        _output_block(
            "OUTPUT",
            [
                "Return changed files.",
                "Return generated files.",
                "Return validation results.",
                "Return final_status, production_status, and execution_mode.",
            ],
        ),
    ]
    prompt = "\n\n".join(blocks)

    for section in MANDATORY_SECTIONS:
        marker = f"{section}:"
        if marker not in prompt:
            raise ValueError(f"missing required section: {section}")

    for file_path in allowed_files:
        if Path(file_path).is_absolute() and not file_path.startswith("/"):
            raise ValueError("invalid file scope")

    return prompt