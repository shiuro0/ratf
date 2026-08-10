from __future__ import annotations

from dataclasses import dataclass

from .config import Settings


@dataclass
class PolicyDecision:
    decision: str
    http_status: int
    reason_code: str


def decide(settings: Settings, trust_score: float, critical_reason: str | None = None) -> PolicyDecision:
    if critical_reason:
        return PolicyDecision("block", 401, critical_reason)
    if trust_score >= settings.allow_threshold:
        return PolicyDecision("allow", 200, "trust_score_allow")
    if trust_score >= settings.verify_threshold:
        return PolicyDecision("verify", 401, "trust_score_verify")
    return PolicyDecision("block", 403, "trust_score_block")
