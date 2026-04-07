from __future__ import annotations

from typing import Any, Literal, TypedDict
from uuid import uuid4

from config.core_runtime_config import (
    get_core_runtime_bool,
    get_core_runtime_float,
    get_core_runtime_str,
)


BlockStatus = Literal["ok", "review", "reject", "error", "unknown"]
DecisionKind = Literal["accept", "review", "reject", "freeze"]
NextAction = Literal["run_pipeline", "review", "reject", "freeze"]

DEFAULT_ACTION = get_core_runtime_str("core.default_action", "generate_article")
INVALID_DECISION_FALLBACK = get_core_runtime_str("core.invalid_decision_fallback", "freeze").lower()
FREEZE_ON_INVALID_SELECTED = get_core_runtime_bool("core.freeze_on_invalid_selected", True)

PRIORITY_CLAMP_MIN = get_core_runtime_float("core.priority_clamp_min", 0.0, minimum=0.0, maximum=1.0)
PRIORITY_CLAMP_MAX = get_core_runtime_float("core.priority_clamp_max", 1.0, minimum=PRIORITY_CLAMP_MIN, maximum=1.0)
CONFIDENCE_CLAMP_MIN = get_core_runtime_float("core.confidence_clamp_min", 0.0, minimum=0.0, maximum=1.0)
CONFIDENCE_CLAMP_MAX = get_core_runtime_float("core.confidence_clamp_max", 1.0, minimum=CONFIDENCE_CLAMP_MIN, maximum=1.0)


class BlockResult(TypedDict, total=False):
    block_name: str
    item_id: str
    task_id: str
    status: BlockStatus
    action: str
    target: str
    priority: float
    confidence: float
    reason: str
    notes: str
    metadata: dict[str, Any]
    event_id: str


class CoreInput(TypedDict):
    event_id: str
    proposals: list[BlockResult]


class CoreDecision(TypedDict):
    decision: DecisionKind
    next_action: NextAction
    requires_human_review: bool
    reason: str
    event_id: str


def new_event_id() -> str:
    return uuid4().hex[:12]


def _coerce_float_clamped(value: Any, *, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(maximum, parsed))


def _resolve_decision(raw_decision: str) -> tuple[DecisionKind, NextAction]:
    if raw_decision in {"accept", "publish", "run", "approved"}:
        return "accept", "run_pipeline"
    if raw_decision in {"review", "warning", "unknown"}:
        return "review", "review"
    if raw_decision in {"reject", "deny", "blocked"}:
        return "reject", "reject"
    if raw_decision in {"freeze"}:
        return "freeze", "freeze"

    fallback = INVALID_DECISION_FALLBACK if INVALID_DECISION_FALLBACK in {"accept", "review", "reject", "freeze"} else "freeze"
    if fallback == "accept" and FREEZE_ON_INVALID_SELECTED:
        fallback = "freeze"
    return _resolve_decision(fallback)


def _normalize_block_status(value: Any) -> BlockStatus:
    text = str(value or "").strip().lower()
    if text in {"ok", "success", "passed"}:
        return "ok"
    if text in {"review", "warning"}:
        return "review"
    if text in {"reject", "blocked"}:
        return "reject"
    if text in {"error", "fail", "failed"}:
        return "error"
    if text:
        return "unknown"
    return "ok"


def normalize_block_result(raw: Any, *, block_name: str, event_id: str) -> BlockResult | None:
    # ブロック境界で型と欠損を吸収し、コアには最小共通形式だけ渡す。
    if not isinstance(raw, dict):
        return None

    normalized_block_name = str(raw.get("block_name") or block_name or "unknown_block").strip() or "unknown_block"
    target = str(raw.get("target") or raw.get("title") or "").strip()
    item_id = str(
        raw.get("item_id")
        or raw.get("task_id")
        or target
        or raw.get("title")
        or ""
    ).strip()
    if not item_id:
        return None

    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    normalized: BlockResult = {
        "block_name": normalized_block_name,
        "item_id": item_id,
        "task_id": str(raw.get("task_id") or item_id).strip(),
        "status": _normalize_block_status(raw.get("status") or raw.get("result")),
        "action": str(raw.get("action") or DEFAULT_ACTION).strip() or DEFAULT_ACTION,
        "target": target or item_id,
        "priority": _coerce_float_clamped(raw.get("priority", PRIORITY_CLAMP_MIN), minimum=PRIORITY_CLAMP_MIN, maximum=PRIORITY_CLAMP_MAX),
        "confidence": _coerce_float_clamped(
            raw.get("confidence", raw.get("priority", CONFIDENCE_CLAMP_MIN)),
            minimum=CONFIDENCE_CLAMP_MIN,
            maximum=CONFIDENCE_CLAMP_MAX,
        ),
        "reason": str(raw.get("reason") or "").strip(),
        "notes": str(raw.get("notes") or "").strip(),
        "metadata": metadata,
        "event_id": event_id,
    }
    return normalized


def build_core_input(proposals: list[BlockResult], *, event_id: str) -> CoreInput:
    return {
        "event_id": event_id,
        "proposals": proposals,
    }


def normalize_core_decision(raw: Any, *, event_id: str) -> CoreDecision:
    # 不正入力時は安全側に倒す。
    if not isinstance(raw, dict):
        return {
            "decision": "freeze",
            "next_action": "freeze",
            "requires_human_review": True,
            "reason": "core_decision_invalid_type",
            "event_id": event_id,
        }

    raw_decision = str(raw.get("decision") or "").strip().lower()
    if not raw_decision:
        raw_decision = "accept"

    decision, next_action = _resolve_decision(raw_decision)

    reason = str(raw.get("reason") or "").strip() or f"normalized_from={raw_decision}"

    return {
        "decision": decision,
        "next_action": next_action,
        "requires_human_review": next_action != "run_pipeline",
        "reason": reason,
        "event_id": event_id,
    }


def build_pipeline_task(block_result: BlockResult, decision: CoreDecision) -> dict[str, Any]:
    return {
        "source": block_result.get("block_name", "unknown_block"),
        "action": block_result.get("action", DEFAULT_ACTION),
        "target": block_result.get("target", block_result.get("item_id", "")),
        "priority": _coerce_float_clamped(
            block_result.get("priority", PRIORITY_CLAMP_MIN),
            minimum=PRIORITY_CLAMP_MIN,
            maximum=PRIORITY_CLAMP_MAX,
        ),
        "item_id": block_result.get("item_id", ""),
        "event_id": decision["event_id"],
        "decision": decision["decision"],
        "reason": decision["reason"],
    }
