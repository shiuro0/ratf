from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from .config import CoreConfig


WEIGHT_NAMES = {"ip", "device", "time", "frequency", "token_history"}


@dataclass(frozen=True, slots=True)
class PolicyProfile:
    """Reusable policy overrides for one route or a group of API routes.

    Values that are not supplied inherit the application's global
    :class:`CoreConfig`. A profile therefore changes policy, not storage,
    identity validation, or the R-ATF decision flow.
    """

    name: str
    weights: Mapping[str, float] = field(default_factory=dict)
    verify_threshold: float | None = None
    allow_threshold: float | None = None
    shadow_mode: bool | None = None
    burst_soft_limit: int | None = None
    burst_hard_limit: int | None = None
    hard_burst_block: bool | None = None

    def __post_init__(self) -> None:
        normalized_name = str(self.name).strip()
        if not normalized_name:
            raise ValueError("Nama policy tidak boleh kosong")
        object.__setattr__(self, "name", normalized_name)

        normalized_weights = {str(name): float(value) for name, value in self.weights.items()}
        unknown = set(normalized_weights) - WEIGHT_NAMES
        if unknown:
            raise ValueError(f"Nama bobot tidak dikenal: {', '.join(sorted(unknown))}")
        if any(value < 0 for value in normalized_weights.values()):
            raise ValueError("Bobot tidak boleh negatif")
        object.__setattr__(self, "weights", normalized_weights)

        for label, value in (
            ("verify_threshold", self.verify_threshold),
            ("allow_threshold", self.allow_threshold),
        ):
            if value is not None and not 0 <= float(value) <= 1:
                raise ValueError(f"{label} harus berada pada rentang 0 sampai 1")
        if (
            self.verify_threshold is not None
            and self.allow_threshold is not None
            and float(self.verify_threshold) >= float(self.allow_threshold)
        ):
            raise ValueError("verify_threshold harus lebih kecil dari allow_threshold")
        if self.burst_soft_limit is not None and int(self.burst_soft_limit) < 1:
            raise ValueError("burst_soft_limit minimal 1")
        if self.burst_hard_limit is not None and int(self.burst_hard_limit) < 2:
            raise ValueError("burst_hard_limit minimal 2")
        if (
            self.burst_soft_limit is not None
            and self.burst_hard_limit is not None
            and int(self.burst_hard_limit) <= int(self.burst_soft_limit)
        ):
            raise ValueError("burst_hard_limit harus lebih besar dari burst_soft_limit")

    def resolve(self, base: CoreConfig) -> CoreConfig:
        """Return an isolated CoreConfig without mutating the global policy."""

        resolved = replace(base)
        resolved.update_policy(
            weights=self.weights or None,
            verify_threshold=self.verify_threshold,
            allow_threshold=self.allow_threshold,
            shadow_mode=self.shadow_mode,
        )
        if self.burst_soft_limit is not None:
            resolved.burst_soft_limit = int(self.burst_soft_limit)
        if self.burst_hard_limit is not None:
            resolved.burst_hard_limit = int(self.burst_hard_limit)
        if self.hard_burst_block is not None:
            resolved.hard_burst_block = bool(self.hard_burst_block)
        resolved.validate()
        return resolved

    def to_dict(self, base: CoreConfig | None = None) -> dict[str, Any]:
        overrides = {
            "name": self.name,
            "weights": dict(self.weights),
            "verify_threshold": self.verify_threshold,
            "allow_threshold": self.allow_threshold,
            "shadow_mode": self.shadow_mode,
            "burst_soft_limit": self.burst_soft_limit,
            "burst_hard_limit": self.burst_hard_limit,
            "hard_burst_block": self.hard_burst_block,
        }
        if base is not None:
            overrides["resolved"] = self.resolve(base).to_dict()
        return overrides
