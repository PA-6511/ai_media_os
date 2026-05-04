"""verification_result.py — 検証結果の値オブジェクト."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VerificationStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    FAILURE = "FAILURE"


@dataclass
class VerificationResult:
    """単一検証の結果を保持する。"""

    check_name: str
    status: VerificationStatus
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def is_ok(self) -> bool:
        return self.status == VerificationStatus.OK

    @property
    def is_failure(self) -> bool:
        return self.status == VerificationStatus.FAILURE

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "message": self.message,
            "detail": self.detail,
            "checked_at": self.checked_at,
        }
