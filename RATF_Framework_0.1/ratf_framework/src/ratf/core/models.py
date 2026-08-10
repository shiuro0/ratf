from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from .profile import PolicyProfile

Decision = Literal["allow", "verify", "block"]


@dataclass
class RequestContext:
    """Normalized request data consumed by the core.

    Adapters for Flask, AuthZEN, or another transport are responsible for
    constructing this object. The core deliberately has no HTTP-framework type.
    """

    request_id: str
    run_id: str
    scenario_label: str
    source_ip: str
    user_agent: str
    client_id: str
    device_id: str
    method: str
    endpoint: str
    timestamp: str
    request_timestamp: str | None
    hour_utc: int
    body_hash: str
    request_fingerprint: str
    nonce: str | None
    idempotency_key: str | None
    device_signature: str | None
    experiment_headers_accepted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Identity:
    subject: str
    client_id: str
    scopes: tuple[str, ...] = ()
    token_id: str = "external"
    family_id: str = "external"
    expires_at: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_scope(self, required_scope: str | None) -> bool:
        return required_scope is None or required_scope in set(self.scopes)


@dataclass
class AuthenticationResult:
    valid: bool
    identity: Identity | None = None
    reason_code: str | None = None


@dataclass
class EvaluationRequest:
    context: RequestContext
    required_scope: str | None = None
    transactional: bool = False
    enforce_request_integrity: bool = True
    request_count: int | None = None
    policy: PolicyProfile | None = None


@dataclass
class StepUpChallenge:
    challenge_type: str
    challenge_url: str | None = None
    expires_in: int = 300
    message: str = "Verifikasi tambahan diperlukan"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationResult:
    decision: Decision
    effective_decision: Decision
    http_status: int
    reason_code: str
    request_id: str
    trust_score: float | None = None
    components: dict[str, float] = field(default_factory=dict)
    reason_codes: list[str] = field(default_factory=list)
    request_count: int | None = None
    shadow_mode: bool = False
    step_up: StepUpChallenge | None = None
    policy_name: str = "default"

    @property
    def allowed(self) -> bool:
        return self.effective_decision == "allow"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["allowed"] = self.allowed
        return result
