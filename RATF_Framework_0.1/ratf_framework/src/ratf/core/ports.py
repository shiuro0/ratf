from __future__ import annotations

from typing import Any, Callable, Protocol

from .models import (
    AuthenticationResult,
    EvaluationResult,
    Identity,
    RequestContext,
    StepUpChallenge,
)


class IdentityProvider(Protocol):
    def authenticate(self, access_token: str, context: RequestContext) -> AuthenticationResult:
        """Validate an application token and return a normalized identity."""

    def record_use(self, identity: Identity, ttl_seconds: int) -> None:
        """Optionally record successful token use."""


class StepUpHandler(Protocol):
    def create_challenge(
        self,
        context: RequestContext,
        identity: Identity,
        evaluation: EvaluationResult,
    ) -> StepUpChallenge | None:
        """Start or describe the application's additional verification flow."""


class CallbackStepUpHandler:
    def __init__(
        self,
        callback: Callable[[RequestContext, Identity, EvaluationResult], StepUpChallenge | dict[str, Any] | None],
    ):
        self.callback = callback

    def create_challenge(
        self,
        context: RequestContext,
        identity: Identity,
        evaluation: EvaluationResult,
    ) -> StepUpChallenge | None:
        value = self.callback(context, identity, evaluation)
        if value is None or isinstance(value, StepUpChallenge):
            return value
        return StepUpChallenge(**value)
