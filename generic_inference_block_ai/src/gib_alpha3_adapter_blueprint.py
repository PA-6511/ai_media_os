from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generic_inference_block_ai.src.gib_alpha_adapter import GIBAlphaRequest
from generic_inference_block_ai.src.gib_alpha2_adapter import GIBAlpha2Result, TemplateValidatedAdapter
from generic_inference_block_ai.src.gib_alpha3_runtime_design import load_and_validate_runtime_design


@dataclass
class RuntimePlan:
    runtime: str
    endpoint: str | None
    model_placeholder: str | None
    would_call: bool
    reason: str


@dataclass
class GIBAlpha3Result:
    alpha2_result: GIBAlpha2Result
    runtime_plan: RuntimePlan

    @property
    def response(self):
        return self.alpha2_result.response

    @property
    def fully_valid(self) -> bool:
        return self.alpha2_result.fully_valid and (self.runtime_plan.would_call is False)


class RuntimeDesignOnlyAdapter:
    """
    Alpha-3 blueprint adapter.

    This adapter prepares runtime plan metadata for Ollama / llama.cpp without making
    any network request. Runtime is forced to stub in alpha stage.
    """

    def __init__(self) -> None:
        self._design = load_and_validate_runtime_design()
        self._alpha2 = TemplateValidatedAdapter()

    def generate_alpha3(self, request: GIBAlphaRequest) -> GIBAlpha3Result:
        alpha2_result = self._alpha2.generate_alpha2(request)
        runtime_plan = self._build_runtime_plan()
        return GIBAlpha3Result(alpha2_result=alpha2_result, runtime_plan=runtime_plan)

    def _build_runtime_plan(self) -> RuntimePlan:
        selection = self._design["runtime_selection"]
        active_runtime = selection["active_runtime_locked"]

        if active_runtime != "stub":
            # Guardrail: design validator should already prevent this.
            return RuntimePlan(
                runtime=active_runtime,
                endpoint=None,
                model_placeholder=None,
                would_call=False,
                reason="Blocked by alpha safety lock: active runtime must be stub.",
            )

        # Build a deterministic planning artifact for future beta runtime wiring.
        ollama = self._design["runtime_designs"]["ollama"]
        endpoint = ollama["base_url"] + ollama["generate_path"]
        return RuntimePlan(
            runtime="stub",
            endpoint=endpoint,
            model_placeholder=ollama["model_placeholder"],
            would_call=False,
            reason="Design-only stage: runtime call intentionally disabled.",
        )
