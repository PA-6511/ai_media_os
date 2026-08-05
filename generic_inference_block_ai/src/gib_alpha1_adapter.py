"""
GIB-alpha1 validated adapter.

Wraps StubInferenceAdapter and adds schema validation for both inputs and outputs.
Validation issues are surfaced as structured error responses, never as unhandled exceptions.
No network, credential, WordPress, systemd, or LLM operations are performed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_adapter import (
    GIBAlphaRequest,
    GIBAlphaResponse,
    StubInferenceAdapter,
)
from generic_inference_block_ai.src.gib_alpha1_schema import (
    load_input_schemas,
    load_output_schemas,
    validate_task_input,
    validate_task_output,
)

_HERE = Path(__file__).parent
_ROOT = _HERE.parent


@dataclass
class GIBAlpha1ValidationResult:
    """Full result from the validated adapter, including schema audit information."""
    response: GIBAlphaResponse
    input_schema_issues: list[str]
    output_schema_issues: list[str]
    schema_valid: bool


class ValidatedInferenceAdapter:
    """
    Alpha-1 adapter that enforces JSON Schema contracts on inputs and outputs.

    - Inputs that fail schema validation are rejected with INPUT_SCHEMA_VIOLATION status.
    - Outputs produced by StubInferenceAdapter are post-validated; violations are reported
      in the result but do NOT suppress the response (design-only stage).
    - No execution, network, credential, or LLM operations are performed.
    """

    execution_effect = "none"
    model_runtime = "stub_no_model_loaded"
    schema_version = "gib.alpha1"

    def __init__(
        self,
        input_schemas_path: Path | None = None,
        output_schemas_path: Path | None = None,
    ) -> None:
        self._input_schemas = load_input_schemas(input_schemas_path)
        self._output_schemas = load_output_schemas(output_schemas_path)
        self._stub = StubInferenceAdapter()

    def generate_validated(self, request: GIBAlphaRequest) -> GIBAlpha1ValidationResult:
        # Step 1: input schema validation
        input_issues = validate_task_input(
            request.task_type, request.input, self._input_schemas
        )

        if input_issues:
            response = GIBAlphaResponse(
                task_type=request.task_type,
                status="INPUT_SCHEMA_VIOLATION",
                model_runtime=self.model_runtime,
                execution_effect=self.execution_effect,
                output={
                    "summary": "Input was rejected due to JSON schema violation.",
                    "schema_issues": input_issues,
                    "human_review_notes": [
                        "Fix the input to conform to the required schema before retrying.",
                        "No inference was performed.",
                    ],
                },
                blocked=True,
                block_reason="input_schema_violation",
            )
            return GIBAlpha1ValidationResult(
                response=response,
                input_schema_issues=input_issues,
                output_schema_issues=[],
                schema_valid=False,
            )

        # Step 2: run stub inference (includes secret-like text detection from alpha0)
        response = self._stub.generate(request)

        # Step 3: output schema validation (post-check only in design-only stage)
        output_issues = validate_task_output(
            request.task_type,
            response.output,
            self._output_schemas,
            blocked=response.blocked,
        )

        schema_valid = (not input_issues) and (not output_issues)

        return GIBAlpha1ValidationResult(
            response=response,
            input_schema_issues=input_issues,
            output_schema_issues=output_issues,
            schema_valid=schema_valid,
        )
