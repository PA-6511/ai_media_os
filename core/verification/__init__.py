"""core.verification — Phase1.5 検証・エスカレーションモジュール."""
from core.verification.failure_report import build_verification_failure_report
from core.verification.escalation import escalate_verification_failure
from core.verification.verification_result import VerificationResult, VerificationStatus

__all__ = [
    "build_verification_failure_report",
    "escalate_verification_failure",
    "VerificationResult",
    "VerificationStatus",
]
