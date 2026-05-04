from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.governance import (
    AuthorityRequest,
    evaluate_authority_request,
)


@dataclass
class DummyBlock:
    """Minimal block used for Core<->Block governance connection tests."""

    block_id: str = "dummy_block"
    name: str = "Dummy Block"

    def handshake(self) -> dict[str, Any]:
        return {
            "ok": True,
            "block_id": self.block_id,
            "name": self.name,
            "protocol": "phase2-handshake-v1",
        }

    def request_execution(
        self,
        *,
        actor: str,
        action: str,
        target: str,
        phase: str = "PHASE2",
        message: str = "",
        run_id: str | None = None,
        log_path: str | Path | None = None,
        kpi: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        req = AuthorityRequest(
            actor=actor,
            phase=phase,
            component="blocks",
            action=action,
            target=target,
            message=message,
            metadata={"kpi": kpi or {}},
        )
        if log_path:
            decision = evaluate_authority_request(
                req,
                run_id=run_id,
                log_path=Path(log_path),
            )
        else:
            decision = evaluate_authority_request(
                req,
                run_id=run_id,
            )
        return {
            "block_id": self.block_id,
            "decision": decision.decision.value,
            "policy_id": decision.policy_id,
            "reason": decision.reason,
            "run_id": decision.run_id,
        }
