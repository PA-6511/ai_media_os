from typing import Dict, List

from config.core_runtime_config import get_core_runtime_str
from core.interfaces import (
    BlockResult,
    build_core_input,
    build_pipeline_task,
    new_event_id,
    normalize_block_result,
    normalize_core_decision,
)


INVALID_TRANSITION_FALLBACK = get_core_runtime_str("core.invalid_transition_fallback", "review").strip() or "review"


class CouncilRuntime:
    def __init__(self, blocks, core_ai, pipeline, logger):
        self.blocks = blocks
        self.core_ai = core_ai
        self.pipeline = pipeline
        self.logger = logger

    def collect_proposals(self, *, event_id: str) -> List[BlockResult]:
        proposals: List[BlockResult] = []
        for block in self.blocks:
            generated = block.run()
            if not isinstance(generated, list):
                self.logger.warning("[Runtime] block output is not list block=%s event_id=%s", block.__class__.__name__, event_id)
                continue

            for row in generated:
                normalized = normalize_block_result(row, block_name=block.__class__.__name__, event_id=event_id)
                if normalized is None:
                    self.logger.warning("[Runtime] block output dropped due to invalid payload block=%s event_id=%s", block.__class__.__name__, event_id)
                    continue
                proposals.append(normalized)
        return proposals

    def run_once(self) -> Dict:
        event_id = new_event_id()
        self.logger.info("[Runtime] 提案収集を開始 event_id=%s", event_id)
        proposals = self.collect_proposals(event_id=event_id)
        core_input = build_core_input(proposals, event_id=event_id)
        self.logger.info("[Runtime] 収集した提案数: %d event_id=%s", len(core_input["proposals"]), event_id)

        selected = self.core_ai.evaluate(core_input["proposals"])
        if not selected:
            self.logger.info("[Runtime] 提案がないため終了 event_id=%s", event_id)
            return {"status": "no_task", "event_id": event_id}

        selected_block_name = "core_selected"
        if isinstance(selected, dict):
            selected_block_name = str(selected.get("source", "core_selected"))

        selected_block = normalize_block_result(
            selected,
            block_name=selected_block_name,
            event_id=event_id,
        )
        if selected_block is None:
            self.logger.warning("[Runtime] core selected payload invalid. freeze event_id=%s", event_id)
            return {
                "status": INVALID_TRANSITION_FALLBACK,
                "event_id": event_id,
                "decision": "freeze",
                "next_action": "freeze",
                "requires_human_review": True,
                "reason": "selected_payload_invalid",
            }

        decision = normalize_core_decision(selected, event_id=event_id)
        if decision["next_action"] != "run_pipeline":
            self.logger.warning(
                "[Runtime] decision blocked decision=%s next_action=%s reason=%s event_id=%s",
                decision["decision"],
                decision["next_action"],
                decision["reason"],
                event_id,
            )
            return {
                "status": INVALID_TRANSITION_FALLBACK,
                **decision,
                "item_id": selected_block.get("item_id", ""),
                "block_name": selected_block.get("block_name", ""),
            }

        task = build_pipeline_task(selected_block, decision)

        self.logger.info(
            "[Runtime] 採用タスク: source=%s action=%s target=%s priority=%.2f event_id=%s",
            task.get("source"),
            task.get("action"),
            task.get("target"),
            float(task.get("priority", 0.0)),
            event_id,
        )

        result = self.pipeline.run(task)
        if isinstance(result, dict):
            result.setdefault("event_id", event_id)
            result.setdefault("decision", decision["decision"])
            result.setdefault("next_action", decision["next_action"])
            return result
        return {"status": "unknown", "event_id": event_id}
