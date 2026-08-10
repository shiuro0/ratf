from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class CoreConfig:
    """Mutable policy configuration owned by the framework core."""

    allow_threshold: float = 0.82
    verify_threshold: float = 0.62
    weight_ip: float = 0.25
    weight_device: float = 0.20
    weight_time: float = 0.10
    weight_frequency: float = 0.20
    weight_token_history: float = 0.25

    replay_window_seconds: int = 300
    timestamp_skew_seconds: int = 90
    nonce_required: bool = True
    device_proof_required: bool = True
    idempotency_required: bool = True
    burst_window_seconds: int = 10
    burst_soft_limit: int = 20
    burst_hard_limit: int = 60
    hard_burst_block: bool = True
    registry_ttl_seconds: int = 86400
    token_hash_secret: str = "local-token-hash-secret-change-me"

    shadow_mode: bool = False
    learn_in_shadow: bool = False

    @classmethod
    def from_settings(cls, settings: Any, *, shadow_mode: bool | None = None) -> "CoreConfig":
        names = {field.name for field in cls.__dataclass_fields__.values()}
        values = {name: getattr(settings, name) for name in names if hasattr(settings, name)}
        if shadow_mode is not None:
            values["shadow_mode"] = shadow_mode
        return cls(**values)

    def weights(self) -> dict[str, float]:
        values = {
            "ip": float(self.weight_ip),
            "device": float(self.weight_device),
            "time": float(self.weight_time),
            "frequency": float(self.weight_frequency),
            "token_history": float(self.weight_token_history),
        }
        total = sum(values.values())
        if total <= 0:
            raise ValueError("Jumlah bobot harus lebih besar dari nol")
        return {name: value / total for name, value in values.items()}

    def validate(self) -> None:
        if not 0 <= self.verify_threshold < self.allow_threshold <= 1:
            raise ValueError("Ambang harus memenuhi 0 <= verify < allow <= 1")
        if any(value < 0 for value in self.weights().values()):
            raise ValueError("Bobot tidak boleh negatif")
        if self.burst_soft_limit < 1 or self.burst_hard_limit <= self.burst_soft_limit:
            raise ValueError("Batas burst keras harus lebih besar dari batas lunak")

    def update_policy(
        self,
        *,
        weights: Mapping[str, float] | None = None,
        allow_threshold: float | None = None,
        verify_threshold: float | None = None,
        shadow_mode: bool | None = None,
    ) -> None:
        previous = self.to_dict()
        try:
            if weights is not None:
                aliases = {
                    "ip": "weight_ip",
                    "device": "weight_device",
                    "time": "weight_time",
                    "frequency": "weight_frequency",
                    "token_history": "weight_token_history",
                }
                unknown = set(weights) - set(aliases)
                if unknown:
                    raise ValueError(f"Nama bobot tidak dikenal: {', '.join(sorted(unknown))}")
                for name, value in weights.items():
                    setattr(self, aliases[name], float(value))
            if allow_threshold is not None:
                self.allow_threshold = float(allow_threshold)
            if verify_threshold is not None:
                self.verify_threshold = float(verify_threshold)
            if shadow_mode is not None:
                self.shadow_mode = bool(shadow_mode)
            self.validate()
        except Exception:
            for name, value in previous["raw"].items():
                setattr(self, name, value)
            self.shadow_mode = previous["shadow_mode"]
            raise

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": self.weights(),
            "raw": {
                "weight_ip": self.weight_ip,
                "weight_device": self.weight_device,
                "weight_time": self.weight_time,
                "weight_frequency": self.weight_frequency,
                "weight_token_history": self.weight_token_history,
                "allow_threshold": self.allow_threshold,
                "verify_threshold": self.verify_threshold,
            },
            "allow_threshold": self.allow_threshold,
            "verify_threshold": self.verify_threshold,
            "shadow_mode": self.shadow_mode,
            "learn_in_shadow": self.learn_in_shadow,
        }
