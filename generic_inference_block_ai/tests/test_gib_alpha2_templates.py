"""Unit tests for GIB-alpha2 template loader and renderer."""
import pytest
from generic_inference_block_ai.src.gib_alpha2_templates import (
    load_template_config,
    get_task_template,
    render_user_prompt,
    get_system_prompt,
    validate_template_config,
    TemplateRenderError,
    REQUIRED_TEMPLATE_FIELDS,
)
from generic_inference_block_ai.src.gib_alpha_policy import REQUIRED_ALLOWED_TASK_TYPES


# ── config validation ─────────────────────────────────────────────────────────

def test_template_config_loads_and_validates() -> None:
    config = load_template_config()
    assert config["schema_version"] == "gib.alpha2.prompt_templates.v0.1"
    assert config["model_runtime_enabled"] is False
    assert config["real_llm_call_allowed"] is False
    assert config["execution_allowed"] is False


def test_all_task_types_have_templates() -> None:
    config = load_template_config()
    task_templates = config["task_templates"]
    for task_type in REQUIRED_ALLOWED_TASK_TYPES:
        assert task_type in task_templates, f"Missing template for {task_type}"


def test_all_templates_have_required_fields() -> None:
    config = load_template_config()
    for task_type, tmpl in config["task_templates"].items():
        for field in REQUIRED_TEMPLATE_FIELDS:
            assert field in tmpl, f"{task_type}: missing field {field}"


def test_template_safety_flags_false() -> None:
    config = load_template_config()
    assert config["model_runtime_enabled"] is False
    assert config["real_llm_call_allowed"] is False
    assert config["execution_allowed"] is False


def test_validator_rejects_bad_schema_version() -> None:
    config = load_template_config()
    modified = dict(config)
    modified["schema_version"] = "wrong"
    issues = validate_template_config(modified)
    assert any("schema_version" in i for i in issues)


def test_validator_rejects_model_runtime_enabled() -> None:
    config = load_template_config()
    modified = dict(config)
    modified["model_runtime_enabled"] = True
    issues = validate_template_config(modified)
    assert any("model_runtime_enabled" in i for i in issues)


# ── rendering ─────────────────────────────────────────────────────────────────

def test_render_phase_log_summary() -> None:
    config = load_template_config()
    rendered = render_user_prompt(
        "phase_log_summary",
        {"phase_name": "Phase 47-B", "status": "PASS", "log_excerpt": "all ok"},
        config,
    )
    assert "Phase 47-B" in rendered
    assert "PASS" in rendered
    assert "all ok" in rendered


def test_render_product_summary() -> None:
    config = load_template_config()
    rendered = render_user_prompt(
        "product_summary",
        {"title": "Manga Vol 1", "publisher": "Pub A", "genre": "Action"},
        config,
    )
    assert "Manga Vol 1" in rendered
    assert "Pub A" in rendered


def test_render_article_outline_list_variable() -> None:
    config = load_template_config()
    rendered = render_user_prompt(
        "article_outline",
        {"topic": "T", "target_reader": "R", "key_points": ["p1", "p2", "p3"]},
        config,
    )
    assert "p1" in rendered
    assert "p2" in rendered


def test_render_missing_required_variable_raises() -> None:
    config = load_template_config()
    with pytest.raises(TemplateRenderError, match="Missing required variables"):
        render_user_prompt(
            "phase_log_summary",
            {"phase_name": "P"},  # missing status and log_excerpt
            config,
        )


def test_render_forbidden_pattern_raises() -> None:
    config = load_template_config()
    # Manually inject a forbidden pattern into variables
    with pytest.raises(TemplateRenderError, match="forbidden pattern"):
        render_user_prompt(
            "phase_log_summary",
            {
                "phase_name": "P",
                "status": "ok",
                    "log_excerpt": "loaded from credential.env file",
            },
            config,
        )


def test_render_all_sample_task_types() -> None:
    """All 7 task types must render without error using valid minimal inputs."""
    config = load_template_config()
    minimal_inputs = {
        "phase_log_summary":        {"phase_name": "P", "status": "ok", "log_excerpt": "ok"},
        "validator_result_explain": {"validator_name": "V", "result": "PASS", "issues": []},
        "product_summary":          {"title": "T", "publisher": "Pub", "genre": "G"},
        "social_post_draft":        {"topic": "T", "source_summary": "S", "target_audience": "A"},
        "article_outline":          {"topic": "T", "target_reader": "R", "key_points": ["k1"]},
        "compliance_classify":      {"content_excerpt": "C", "context": "ctx"},
        "security_log_explain":     {"log_excerpt": "log", "detector_result": "rec"},
    }
    for task_type, inp in minimal_inputs.items():
        rendered = render_user_prompt(task_type, inp, config)
        assert isinstance(rendered, str)
        assert len(rendered) > 0


def test_system_prompt_is_non_empty_for_all_tasks() -> None:
    config = load_template_config()
    for task_type in REQUIRED_ALLOWED_TASK_TYPES:
        sp = get_system_prompt(task_type, config)
        assert isinstance(sp, str) and sp.strip(), f"Empty system_prompt for {task_type}"


def test_system_prompts_do_not_contain_forbidden_text() -> None:
    config = load_template_config()
    forbidden = ["credential.env", "password=", "secret=", "token="]
    for task_type in REQUIRED_ALLOWED_TASK_TYPES:
        sp = get_system_prompt(task_type, config).lower()
        for f in forbidden:
            assert f not in sp, f"System prompt for {task_type} contains '{f}'"
