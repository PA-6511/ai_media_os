from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from generic_inference_block_ai.src.gib_alpha_policy import REQUIRED_ALLOWED_TASK_TYPES

SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"credential\.env", re.IGNORECASE),
    re.compile(r"\baccess_token\s*=", re.IGNORECASE),
    re.compile(r"password\s*=", re.IGNORECASE),
    re.compile(r"\bsecret\s*=", re.IGNORECASE),
    re.compile(r"\bapi_key\s*=", re.IGNORECASE),
    re.compile(r"\btoken\s*=", re.IGNORECASE),
    re.compile(r"\bapp_password\b", re.IGNORECASE),
]


@dataclass
class GIBAlphaRequest:
    task_type: str
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class GIBAlphaResponse:
    task_type: str
    status: str
    model_runtime: str
    execution_effect: str
    output: dict[str, Any]
    blocked: bool
    block_reason: str | None


def contains_secret_like_text(value: Any) -> bool:
    text = _flatten_to_text(value)
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def _flatten_to_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{k} {_flatten_to_text(v)}" for k, v in value.items())
    if isinstance(value, list):
        return " ".join(_flatten_to_text(item) for item in value)
    return str(value)


class StubInferenceAdapter:
    """Alpha-stage deterministic adapter.

    This class intentionally does not call any local model, external API,
    network socket, WordPress endpoint, credential file, or system command.
    It only returns predictable dry-run output for contract validation.
    """

    model_runtime = "stub_no_model_loaded"
    execution_effect = "none"

    def generate(self, request: GIBAlphaRequest) -> GIBAlphaResponse:
        if request.task_type not in REQUIRED_ALLOWED_TASK_TYPES:
            raise ValueError(f"Unsupported task_type: {request.task_type}")

        if contains_secret_like_text(request.input):
            return GIBAlphaResponse(
                task_type=request.task_type,
                status="BLOCKED_SECRET_LIKE_INPUT_DETECTED",
                model_runtime=self.model_runtime,
                execution_effect=self.execution_effect,
                output={
                    "summary": "Input was blocked because it appears to contain secret-like material.",
                    "risk_notes": [
                        "No model call was made.",
                        "No credential value was printed.",
                        "Human review is required.",
                    ],
                    "human_review_notes": [
                        "Remove credential-like strings before using GIB.",
                    ],
                },
                blocked=True,
                block_reason="secret_like_input_detected",
            )

        output = self._build_stub_output(request.task_type, request.input)
        return GIBAlphaResponse(
            task_type=request.task_type,
            status="DRY_RUN_STUB_OUTPUT",
            model_runtime=self.model_runtime,
            execution_effect=self.execution_effect,
            output=output,
            blocked=False,
            block_reason=None,
        )

    def _build_stub_output(self, task_type: str, data: dict[str, Any]) -> dict[str, Any]:
        if task_type == "phase_log_summary":
            return {
                "summary": f"Phase {data.get('phase_name', 'unknown')} remains in dry-run review state: {data.get('status', 'unknown')}.",
                "remaining_blockers": [
                    "Credential readiness must be confirmed outside GIB.",
                    "Execution approval must remain outside GIB.",
                ],
                "human_review_notes": [
                    "GIB can summarize the phase but cannot approve execution.",
                ],
            }

        if task_type == "validator_result_explain":
            return {
                "summary": f"Validator {data.get('validator_name', 'unknown')} returned {data.get('result', 'unknown')}.",
                "risk_notes": list(data.get("issues", [])),
                "next_checkpoints": [
                    "Confirm missing values through approved credential route only.",
                    "Do not print or expose credential values.",
                ],
            }

        if task_type == "product_summary":
            return {
                "summary": f"{data.get('title', 'unknown title')} from {data.get('publisher', 'unknown publisher')} is prepared for dry-run product summarization.",
                "selling_points": [
                    "Use only verified product metadata.",
                    "Keep campaign and price claims outside GIB unless supplied by a trusted upstream source.",
                ],
                "caution_notes": [
                    "No live price check was performed.",
                    "No affiliate link was generated.",
                ],
            }

        if task_type == "social_post_draft":
            return {
                "draft_candidates": [
                    f"【DRY_RUN】{data.get('topic', 'sample topic')} の紹介文候補です。公開前に人間レビューが必要です。",
                    f"【DRY_RUN】{data.get('source_summary', 'sample summary')} を短く整理した投稿案です。",
                ],
                "risk_notes": [
                    "Draft only. No social posting action is allowed.",
                ],
                "human_review_notes": [
                    "Check campaign accuracy, prohibited claims, and affiliate disclosure before use.",
                ],
            }

        if task_type == "article_outline":
            return {
                "outline": [
                    "Introduction",
                    "Key points",
                    "Reader benefits",
                    "Caution notes",
                    "Human review checklist",
                ],
                "title_candidates": [
                    f"【DRY_RUN】{data.get('topic', 'sample topic')} の紹介タイトル案",
                    f"【DRY_RUN】{data.get('target_reader', 'reader')}向け記事構成案",
                ],
                "human_review_notes": [
                    "No WordPress draft was created.",
                    "Article claims must be verified before publication.",
                ],
            }

        if task_type == "compliance_classify":
            return {
                "classification_label": "requires_human_review",
                "risk_notes": [
                    "GIB alpha does not make legal conclusions.",
                    "Forward to Legal / Compliance Gate AI for formal review.",
                ],
                "requires_human_review": True,
            }

        if task_type == "security_log_explain":
            return {
                "summary": "Security log excerpt was converted into a human-review note.",
                "risk_notes": [
                    "GIB alpha does not block, isolate, freeze, or rollback systems.",
                    "Security action must remain under approved S-series procedures.",
                ],
                "recommended_human_checks": [
                    "Check timestamp range.",
                    "Check source IP / account pattern.",
                    "Check whether detector result was recommendation-only.",
                ],
            }

        raise ValueError(f"Unhandled task_type: {task_type}")
