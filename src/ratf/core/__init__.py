"""Framework-independent contracts and evaluation engine for R-ATF."""

from .config import CoreConfig
from .models import (
    EvaluationRequest,
    EvaluationResult,
    Identity,
    RequestContext,
    StepUpChallenge,
)
from .ports import IdentityProvider, StepUpHandler
from .profile import PolicyProfile


def __getattr__(name: str):
    if name == "RATFEngine":
        from .engine import RATFEngine

        return RATFEngine
    raise AttributeError(name)

__all__ = [
    "CoreConfig",
    "EvaluationRequest",
    "EvaluationResult",
    "Identity",
    "IdentityProvider",
    "PolicyProfile",
    "RATFEngine",
    "RequestContext",
    "StepUpChallenge",
    "StepUpHandler",
]
