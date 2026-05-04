"""Authority guard for Phase2 change requests.

This module evaluates change requests against a conservative permission matrix
and emits Phase2 runtime log events (NDJSON) for each decision.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PHASE2_LOG_PATH = BASE_DIR / "data" / "logs" / "phase2_runtime.log"

SENSITIVE_KEYWORDS = {
    "core",
    "verification",
    "phase",
    "state",
}

SENSITIVE_PATTERNS = [
    re.compile(r"(^|[\\/_.-])core([\\/_.-]|$)", re.IGNORECASE),
    re.compile(r"verification", re.IGNORECASE),
    re.compile(r"(^|[\\/_.-])phase([\\/_.-]|$)", re.IGNORECASE),
    re.compile(r"(^|[\\/_.-])state([\\/_.-]|$)", re.IGNORECASE),
]

DENY_ACTION_KEYWORDS = {
    "delete",
    "drop",
    "destroy",
    "disable_audit",
    "change_core_policy",
}

PHASE2_PERMISSION_MATRIX: dict[str, Any] = {
    "phase": "PHASE2",
    "allowed_components": {
        "blocks",
        "monitoring",
        "tools",
        "reporting",
        "docs",
        "schemas",
    },
    "allowed_actions": {
        "add",
        "update",
        "validate",
        "report",
        "test",
        "log",
    },
    "escalate_on_sensitive_keywords": sorted(SENSITIVE_KEYWORDS),
    "deny_on_action_keywords": sorted(DENY_ACTION_KEYWORDS),
}


class Decision(str, Enum):
    APPROVE = "APPROVE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


@dataclass
class AuthorityRequest:
    actor: str
    phase: str
    component: str
    action: str
    target: str = ""
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthorityDecision:
    decision: Decision
    reason: str
    policy_id: str
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "policy_id": self.policy_id,
            "run_id": self.run_id,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contains_sensitive_keyword(*values: str) -> bool:
    text = " ".join(v.lower() for v in values if isinstance(v, str))
    return any(p.search(text) is not None for p in SENSITIVE_PATTERNS)


def _contains_deny_keyword(action: str) -> bool:
    text = (action or "").lower()
    return any(k in text for k in DENY_ACTION_KEYWORDS)


def _normalize_kpi(metadata: dict[str, Any]) -> dict[str, Any]:
    kpi = metadata.get("kpi", {}) if isinstance(metadata, dict) else {}
    if not isinstance(kpi, dict):
        kpi = {}
    return {
        "failsafe_coverage": float(kpi.get("failsafe_coverage", 1.0)),
        "freeze_correctness": float(kpi.get("freeze_correctness", 1.0)),
        "policy_deny_delta": float(kpi.get("policy_deny_delta", 0.0)),
        "warning_streak": int(kpi.get("warning_streak", 0)),
    }


def _log_decision(
    request: AuthorityRequest,
    decision: AuthorityDecision,
    *,
    log_path: Path = DEFAULT_PHASE2_LOG_PATH,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": _now_iso(),
        "run_id": decision.run_id,
        "phase": request.phase,
        "component": request.component,
        "action": request.action,
        "decision": decision.decision.value,
        "result": (
            "SUCCESS"
            if decision.decision == Decision.APPROVE
            else "SKIP"
            if decision.decision == Decision.ESCALATE
            else "FAIL"
        ),
        "message": request.message,
        "kpi": _normalize_kpi(request.metadata),
        "meta": {
            "actor": request.actor,
            "target": request.target,
            "policy_id": decision.policy_id,
            "reason": decision.reason,
            "request_metadata": request.metadata,
        },
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def evaluate_authority_request(
    request: AuthorityRequest,
    *,
    run_id: str | None = None,
    log_path: Path = DEFAULT_PHASE2_LOG_PATH,
) -> AuthorityDecision:
    """Evaluate request and append one Phase2 runtime log event.

    Rules:
    - Phase mismatch => ESCALATE
    - Explicit dangerous action keywords => DENY
    - Sensitive target/component/action keywords => ESCALATE
    - Request not in allowed component/action matrix => ESCALATE
    - Otherwise => APPROVE
    """
    rid = run_id or str(uuid4())

    if request.phase != PHASE2_PERMISSION_MATRIX["phase"]:
        decision = AuthorityDecision(
            decision=Decision.ESCALATE,
            reason=f"phase mismatch: {request.phase}",
            policy_id="P2-PHASE-MISMATCH",
            run_id=rid,
        )
        _log_decision(request, decision, log_path=log_path)
        return decision

    if _contains_deny_keyword(request.action):
        decision = AuthorityDecision(
            decision=Decision.DENY,
            reason=f"denied action keyword detected: {request.action}",
            policy_id="P2-DENY-DANGEROUS-ACTION",
            run_id=rid,
        )
        _log_decision(request, decision, log_path=log_path)
        return decision

    if _contains_sensitive_keyword(request.component, request.target, request.action):
        decision = AuthorityDecision(
            decision=Decision.ESCALATE,
            reason="sensitive area keyword detected",
            policy_id="P2-ESCALATE-SENSITIVE-AREA",
            run_id=rid,
        )
        _log_decision(request, decision, log_path=log_path)
        return decision

    allowed_components = PHASE2_PERMISSION_MATRIX["allowed_components"]
    if request.component not in allowed_components:
        decision = AuthorityDecision(
            decision=Decision.ESCALATE,
            reason=f"component not in allowlist: {request.component}",
            policy_id="P2-ESCALATE-COMPONENT-NOT-ALLOWED",
            run_id=rid,
        )
        _log_decision(request, decision, log_path=log_path)
        return decision

    allowed_actions = PHASE2_PERMISSION_MATRIX["allowed_actions"]
    if request.action not in allowed_actions:
        decision = AuthorityDecision(
            decision=Decision.ESCALATE,
            reason=f"action not in allowlist: {request.action}",
            policy_id="P2-ESCALATE-ACTION-NOT-ALLOWED",
            run_id=rid,
        )
        _log_decision(request, decision, log_path=log_path)
        return decision

    decision = AuthorityDecision(
        decision=Decision.APPROVE,
        reason="request allowed by Phase2 permission matrix",
        policy_id="P2-APPROVE-ALLOWLIST",
        run_id=rid,
    )
    _log_decision(request, decision, log_path=log_path)
    return decision
