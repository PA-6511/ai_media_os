"""
GIB-alpha2 template-aware adapter.

Extends alpha1 ValidatedInferenceAdapter by adding prompt template rendering.
The rendered prompt is included in dry-run response metadata for inspection only.
No LLM call is performed.  All alpha0/alpha1 safety constraints are preserved.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest, GIBAlphaResponse
from generic_inference_block_ai.src.gib_alpha1_adapter import (
    ValidatedInferenceAdapter,
    GIBAlpha1ValidationResult,
)
from generic_inference_block_ai.src.gib_alpha2_templates import (
    load_template_config,
    render_user_prompt,
    get_system_prompt,
    TemplateRenderError,
)

_HERE = Path(__file__).parent
_ROOT = _HERE.parent


@dataclass
class GIBAlpha2Result:
    """Full result from the alpha2 adapter, including rendered prompts."""
    alpha1_result: GIBAlpha1ValidationResult
    system_prompt: str | None
    rendered_user_prompt: str | None
    template_render_error: str | None
    template_rendered: bool

    @property
    def response(self) -> GIBAlphaResponse:
        return self.alpha1_result.response

    @property
    def schema_valid(self) -> bool:
        return self.alpha1_result.schema_valid

    @property
    def fully_valid(self) -> bool:
        return self.alpha1_result.schema_valid and self.template_rendered


class TemplateValidatedAdapter:
    """
    Alpha-2 adapter: schema validation (alpha1) + prompt template rendering.

    Rendered prompts are stored for dry-run inspection only.
    No LLM, no network, no credential, no execution.
    """

    execution_effect = "none"
    model_runtime = "stub_no_model_loaded"
    schema_version = "gib.alpha2"

    def __init__(
        self,
        templates_path: Path | None = None,
        input_schemas_path: Path | None = None,
        output_schemas_path: Path | None = None,
    ) -> None:
        self._template_config = load_template_config(templates_path)
        self._alpha1 = ValidatedInferenceAdapter(
            input_schemas_path=input_schemas_path,
            output_schemas_path=output_schemas_path,
        )

    def generate_alpha2(self, request: GIBAlphaRequest) -> GIBAlpha2Result:
        # Step 1: alpha1 schema-validated inference
        alpha1_result = self._alpha1.generate_validated(request)

        # If alpha1 blocked the request, skip template rendering
        if alpha1_result.response.blocked:
            return GIBAlpha2Result(
                alpha1_result=alpha1_result,
                system_prompt=None,
                rendered_user_prompt=None,
                template_render_error="Skipped: request was blocked at alpha1 stage.",
                template_rendered=False,
            )

        # Step 2: render prompt template
        try:
            system_prompt = get_system_prompt(request.task_type, self._template_config)
            rendered = render_user_prompt(
                request.task_type,
                request.input,
                self._template_config,
            )
            return GIBAlpha2Result(
                alpha1_result=alpha1_result,
                system_prompt=system_prompt,
                rendered_user_prompt=rendered,
                template_render_error=None,
                template_rendered=True,
            )
        except (TemplateRenderError, KeyError) as exc:
            return GIBAlpha2Result(
                alpha1_result=alpha1_result,
                system_prompt=None,
                rendered_user_prompt=None,
                template_render_error=str(exc),
                template_rendered=False,
            )
