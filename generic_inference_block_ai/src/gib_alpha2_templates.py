"""
GIB-alpha2 prompt template loader and renderer.

Loads per-task-type prompt templates from config.
Renders them via simple str.format_map substitution (no external libs).
Validates:
  - All 7 task types have a template.
  - Required variables are present before rendering.
  - Rendered output does not exceed max_rendered_length.
  - Rendered output does not contain forbidden patterns.

No LLM call, no network, no credential access, no execution.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_policy import REQUIRED_ALLOWED_TASK_TYPES

_HERE = Path(__file__).parent
_ROOT = _HERE.parent
TEMPLATES_PATH = _ROOT / "config" / "gib_alpha2_prompt_templates.json"

REQUIRED_TEMPLATE_FIELDS: list[str] = [
    "system_prompt",
    "user_prompt_template",
    "required_variables",
    "forbidden_output_patterns",
    "max_rendered_length",
]


# ── schema validation ─────────────────────────────────────────────────────────

def validate_template_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if config.get("schema_version") != "gib.alpha2.prompt_templates.v0.1":
        issues.append("schema_version must be gib.alpha2.prompt_templates.v0.1")
    if config.get("model_runtime_enabled") is not False:
        issues.append("model_runtime_enabled must be false")
    if config.get("real_llm_call_allowed") is not False:
        issues.append("real_llm_call_allowed must be false")
    if config.get("execution_allowed") is not False:
        issues.append("execution_allowed must be false")

    task_templates = config.get("task_templates")
    if not isinstance(task_templates, dict):
        return issues + ["task_templates must be an object"]

    configured = list(task_templates.keys())
    if configured != REQUIRED_ALLOWED_TASK_TYPES:
        issues.append("task_templates must cover exactly the 7 required task types in order")

    for task_type, tmpl in task_templates.items():
        if not isinstance(tmpl, dict):
            issues.append(f"{task_type}: template must be an object")
            continue
        for field in REQUIRED_TEMPLATE_FIELDS:
            if field not in tmpl:
                issues.append(f"{task_type}: missing field {field}")
        if not isinstance(tmpl.get("required_variables"), list):
            issues.append(f"{task_type}: required_variables must be a list")
        if not isinstance(tmpl.get("forbidden_output_patterns"), list):
            issues.append(f"{task_type}: forbidden_output_patterns must be a list")
        if not isinstance(tmpl.get("max_rendered_length"), int):
            issues.append(f"{task_type}: max_rendered_length must be an integer")
        if not isinstance(tmpl.get("system_prompt"), str) or not tmpl["system_prompt"].strip():
            issues.append(f"{task_type}: system_prompt must be a non-empty string")
        if not isinstance(tmpl.get("user_prompt_template"), str) or not tmpl["user_prompt_template"].strip():
            issues.append(f"{task_type}: user_prompt_template must be a non-empty string")

    return issues


def load_template_config(path: Path | None = None) -> dict[str, Any]:
    target = path or TEMPLATES_PATH
    with target.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Template config root must be an object: {target}")
    issues = validate_template_config(data)
    if issues:
        raise RuntimeError("GIB alpha2 template config validation failed: " + "; ".join(issues))
    return data


def get_task_template(task_type: str, config: dict[str, Any]) -> dict[str, Any]:
    templates = config.get("task_templates", {})
    if task_type not in templates:
        raise KeyError(f"No template defined for task_type: {task_type}")
    return templates[task_type]


# ── rendering ─────────────────────────────────────────────────────────────────

class TemplateRenderError(ValueError):
    """Raised when template rendering cannot proceed safely."""


def render_user_prompt(
    task_type: str,
    variables: dict[str, Any],
    config: dict[str, Any],
) -> str:
    """Render the user prompt template for *task_type* with *variables*.

    Raises TemplateRenderError if:
    - Required variables are missing.
    - Rendered text exceeds max_rendered_length.
    - Rendered text contains forbidden patterns.
    """
    tmpl = get_task_template(task_type, config)

    required = tmpl["required_variables"]
    missing = [v for v in required if v not in variables]
    if missing:
        raise TemplateRenderError(
            f"Missing required variables for {task_type}: {missing}"
        )

    # Coerce values to strings for safe substitution
    safe_vars = {k: _safe_str(v) for k, v in variables.items()}
    rendered = tmpl["user_prompt_template"].format_map(safe_vars)

    max_len = tmpl["max_rendered_length"]
    if len(rendered) > max_len:
        raise TemplateRenderError(
            f"Rendered prompt for {task_type} exceeds max_rendered_length "
            f"({len(rendered)} > {max_len})"
        )

    forbidden_patterns = tmpl["forbidden_output_patterns"]
    for pattern in forbidden_patterns:
        if re.search(re.escape(pattern), rendered, re.IGNORECASE):
            raise TemplateRenderError(
                f"Rendered prompt for {task_type} contains forbidden pattern: {pattern!r}"
            )

    return rendered


def get_system_prompt(task_type: str, config: dict[str, Any]) -> str:
    return get_task_template(task_type, config)["system_prompt"]


def _safe_str(value: Any) -> str:
    """Convert a value to a safe string for template substitution."""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
