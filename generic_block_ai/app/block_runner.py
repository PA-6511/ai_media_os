from __future__ import annotations

from pathlib import Path
from typing import Any

from .block_contract import BlockManifest
from .result_schema import build_block_result
from .safety_guard import evaluate_actions, load_policy


class GenericBlockRunner:
    def __init__(self, manifest_path: Path, policy_path: Path) -> None:
        self.manifest = BlockManifest.from_json_file(manifest_path)
        self.policy = load_policy(policy_path)

    def run(self, requested_actions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        actions = requested_actions or []
        guard_decision = evaluate_actions(self.manifest, actions, self.policy)

        decision = "human_review" if self.manifest.requires_human_approval else "decision"
        status = "success"
        errors: list[str] = []
        warnings = list(guard_decision.warnings)

        if guard_decision.blocked_actions:
            status = "blocked"
            if decision == "decision":
                decision = "recheck"

        if self.manifest.auto_execute_allowed:
            warnings.append("auto_execute_allowed is ignored in Phase G-1")

        summary = (
            f"planned={len(actions)}, allowed={len(guard_decision.allowed_actions)}, "
            f"blocked={len(guard_decision.blocked_actions)}"
        )

        return build_block_result(
            status=status,
            decision=decision,
            summary=summary,
            risk_level=self.manifest.risk_level,
            needs_approval=self.manifest.requires_human_approval,
            mode=self.manifest.mode,
            actual_execution=False,
            actions=guard_decision.allowed_actions,
            warnings=warnings,
            errors=errors,
            block_id=self.manifest.block_id,
            version=self.manifest.version,
        )
