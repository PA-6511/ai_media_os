"""
block_template_spec.py — IR5-T1

汎用ブロックAIが生成するブロックAI雛形の仕様を定義します。
外部通信・自動実行・export は一切行いません。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TEMPLATE_SPEC_SCHEMA_VERSION = "template_spec_v1"

# mode / operation_mode は dry_run / OBSERVE 固定。spec から変更不可。
_FIXED_MODE = "dry_run"
_FIXED_OPERATION_MODE = "OBSERVE"
_FIXED_AUTO_EXECUTE_ALLOWED = False
_FIXED_REQUIRES_HUMAN_APPROVAL = True

# 全テンプレートに必ず付与する forbidden_actions（上書き不可の共通禁止リスト）
_BASE_FORBIDDEN_ACTIONS: list[str] = [
    "delete_block",
    "export_block",
    "sell_block",
    "change_core_policy",
    "disable_audit",
    "auto_publish_without_approval",
    "handle_adult_content",
]

ALLOWED_RISK_LEVELS = {"low", "medium", "high"}
ALLOWED_CATEGORIES = {"generic", "affiliate", "media", "analytics", "notification"}

AFFILIATE_REQUIRED_DISCLAIMER = "This content may include affiliate links."
AFFILIATE_ALLOWED_PRODUCT_SOURCES = [
    "official_api",
    "approved_feed",
    "manual_review_queue",
]


@dataclass
class BlockTemplateSpec:
    """ブロックAI雛形の仕様。"""

    block_id: str
    display_name: str
    version: str
    category: str
    risk_level: str
    capabilities: dict[str, bool]
    # 追加の forbidden_actions（_BASE_FORBIDDEN_ACTIONS に結合して使用）
    extra_forbidden_actions: list[str] = field(default_factory=list)
    description: str = ""
    policy_environment: str = "dev"
    policy_version: str = "v1.0.0"
    policy_change_reason: str = "initial template generation"

    @property
    def forbidden_actions(self) -> list[str]:
        merged = list(_BASE_FORBIDDEN_ACTIONS)
        for a in self.extra_forbidden_actions:
            if a not in merged:
                merged.append(a)
        return merged

    def as_manifest_dict(self) -> dict[str, Any]:
        manifest: dict[str, Any] = {
            "block_id": self.block_id,
            "display_name": self.display_name,
            "version": self.version,
            "category": self.category,
            "operation_mode": _FIXED_OPERATION_MODE,
            "mode": _FIXED_MODE,
            "risk_level": self.risk_level,
            "capabilities": dict(self.capabilities),
            "approval_policy": {
                "requires_human_approval": _FIXED_REQUIRES_HUMAN_APPROVAL,
                "auto_execute_allowed": _FIXED_AUTO_EXECUTE_ALLOWED,
            },
            "forbidden_actions": self.forbidden_actions,
        }
        if self.category == "affiliate":
            manifest["affiliate_safety"] = {
                "require_disclosure": True,
                "disclosure_text": AFFILIATE_REQUIRED_DISCLAIMER,
                "allow_external_checkout": False,
                "allow_pii_storage": False,
                "allowed_product_sources": list(AFFILIATE_ALLOWED_PRODUCT_SOURCES),
            }
        return manifest

    def validate(self) -> list[str]:
        """仕様の検証。エラーメッセージのリストを返す（空 = OK）。"""
        errors: list[str] = []
        if not self.block_id.strip():
            errors.append("block_id is required")
        if not self.display_name.strip():
            errors.append("display_name is required")
        if not self.version.strip():
            errors.append("version is required")
        if self.category not in ALLOWED_CATEGORIES:
            errors.append(f"category must be one of {sorted(ALLOWED_CATEGORIES)}")
        if self.risk_level not in ALLOWED_RISK_LEVELS:
            errors.append(f"risk_level must be one of {sorted(ALLOWED_RISK_LEVELS)}")
        if not isinstance(self.capabilities, dict):
            errors.append("capabilities must be a dict")
        return errors


# ─── 組み込みスペック ───────────────────────────────────────────────────────────

AFFILIATE_BLOCK_SPEC = BlockTemplateSpec(
    block_id="affiliate_block",
    display_name="アフィリエイトブロックAI",
    version="0.1.0",
    category="affiliate",
    risk_level="medium",
    description="アフィリエイト商品の収集・スコアリング・レビューパッケージ生成を担当するブロックAI。",
    capabilities={
        "collect_data": True,
        "analyze": True,
        "generate_report": True,
        "notify_slack": True,
        "publish_content": False,
        "delete_data": False,
        "change_config": False,
    },
    extra_forbidden_actions=[
        "direct_purchase",
        "store_payment_info",
        "auto_place_order",
    ],
    policy_environment="dev",
    policy_version="v1.0.0",
    policy_change_reason="IR5-T4 affiliate block skeleton initial spec",
)
