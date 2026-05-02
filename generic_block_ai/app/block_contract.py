from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_RISK_LEVELS = {"low", "medium", "high"}


@dataclass(frozen=True)
class BlockManifest:
    block_id: str
    display_name: str
    version: str
    category: str
    mode: str
    risk_level: str
    capabilities: dict[str, bool]
    requires_human_approval: bool
    auto_execute_allowed: bool
    forbidden_actions: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlockManifest":
        capabilities = data.get("capabilities")
        approval_policy = data.get("approval_policy")

        if not isinstance(capabilities, dict):
            raise ValueError("manifest.capabilities must be an object")
        if not isinstance(approval_policy, dict):
            raise ValueError("manifest.approval_policy must be an object")

        risk_level = str(data.get("risk_level", "")).strip().lower()
        if risk_level not in ALLOWED_RISK_LEVELS:
            raise ValueError(f"manifest.risk_level must be one of {sorted(ALLOWED_RISK_LEVELS)}")

        mode = str(data.get("mode", "")).strip().lower()
        if mode != "dry_run":
            raise ValueError("manifest.mode must be dry_run for Phase G-1")

        forbidden_actions_raw = data.get("forbidden_actions", [])
        if not isinstance(forbidden_actions_raw, list):
            raise ValueError("manifest.forbidden_actions must be an array")

        forbidden_actions = [str(item).strip() for item in forbidden_actions_raw if str(item).strip()]

        return cls(
            block_id=str(data.get("block_id", "")).strip(),
            display_name=str(data.get("display_name", "")).strip(),
            version=str(data.get("version", "")).strip(),
            category=str(data.get("category", "")).strip(),
            mode=mode,
            risk_level=risk_level,
            capabilities={str(k): bool(v) for k, v in capabilities.items()},
            requires_human_approval=bool(approval_policy.get("requires_human_approval", True)),
            auto_execute_allowed=bool(approval_policy.get("auto_execute_allowed", False)),
            forbidden_actions=forbidden_actions,
        )

    @classmethod
    def from_json_file(cls, path: Path) -> "BlockManifest":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("manifest root must be an object")
        manifest = cls.from_dict(payload)
        manifest.validate_required_fields()
        return manifest

    def validate_required_fields(self) -> None:
        required_text_fields = {
            "block_id": self.block_id,
            "display_name": self.display_name,
            "version": self.version,
            "category": self.category,
        }
        for field_name, value in required_text_fields.items():
            if not value:
                raise ValueError(f"manifest.{field_name} is required")
