from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_mode: str = os.getenv("API_MODE", "ratf").lower()
    app_env: str = os.getenv("APP_ENV", "research").lower()
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _int_env("PORT", 5000)
    strict_startup: bool = _bool_env("STRICT_STARTUP", False)

    jwt_secret: str = os.getenv("JWT_SECRET", "local-jwt-secret-change-me-32-bytes-minimum")
    jwt_issuer: str = os.getenv("JWT_ISSUER", "ratf-local-auth")
    jwt_audience: str = os.getenv("JWT_AUDIENCE", "ratf-small-business-api")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_ttl_seconds: int = _int_env("JWT_TTL_SECONDS", 900)
    max_token_ttl_seconds: int = _int_env("MAX_TOKEN_TTL_SECONDS", 3600)
    token_hash_secret: str = os.getenv("TOKEN_HASH_SECRET", "local-token-hash-secret-change-me")
    registry_ttl_seconds: int = _int_env("REGISTRY_TTL_SECONDS", 86400)
    replace_previous_access_token: bool = _bool_env("REPLACE_PREVIOUS_ACCESS_TOKEN", True)
    max_active_tokens_per_family: int = _int_env("MAX_ACTIVE_TOKENS_PER_FAMILY", 1)

    device_master_secret: str = os.getenv("DEVICE_MASTER_SECRET", "local-device-master-secret-change-me")
    device_enrollment_key: str = os.getenv("DEVICE_ENROLLMENT_KEY", "local-enrollment-key-change-me")

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "redis").lower()
    allow_memory_fallback: bool = _bool_env("ALLOW_MEMORY_FALLBACK", False)

    allow_threshold: float = _float_env("ALLOW_THRESHOLD", 0.82)
    verify_threshold: float = _float_env("VERIFY_THRESHOLD", 0.62)
    replay_window_seconds: int = _int_env("REPLAY_WINDOW_SECONDS", 300)
    timestamp_skew_seconds: int = _int_env("TIMESTAMP_SKEW_SECONDS", 90)
    nonce_required: bool = _bool_env("NONCE_REQUIRED", True)
    device_proof_required: bool = _bool_env("DEVICE_PROOF_REQUIRED", True)
    idempotency_required: bool = _bool_env("IDEMPOTENCY_REQUIRED", True)

    burst_window_seconds: int = _int_env("BURST_WINDOW_SECONDS", 10)
    burst_soft_limit: int = _int_env("BURST_SOFT_LIMIT", 20)
    burst_hard_limit: int = _int_env("BURST_HARD_LIMIT", 60)
    hard_burst_block: bool = _bool_env("HARD_BURST_BLOCK", True)

    weight_ip: float = _float_env("WEIGHT_IP", 0.25)
    weight_device: float = _float_env("WEIGHT_DEVICE", 0.20)
    weight_time: float = _float_env("WEIGHT_TIME", 0.10)
    weight_frequency: float = _float_env("WEIGHT_FREQUENCY", 0.20)
    weight_token_history: float = _float_env("WEIGHT_TOKEN_HISTORY", 0.25)

    experiment_mode: bool = _bool_env("EXPERIMENT_MODE", True)
    experiment_key: str = os.getenv("EXPERIMENT_KEY", "local-experiment-key-change-me")
    trust_proxy_headers: bool = _bool_env("TRUST_PROXY_HEADERS", False)

    log_path: str = os.getenv("LOG_PATH", "results/audit_log.jsonl")
    audit_log_secret: str = os.getenv("AUDIT_LOG_SECRET", "local-audit-log-secret-change-me")
    admin_token: str = os.getenv("ADMIN_TOKEN", "local-admin-token-change-me")
    resource_server_key: str = os.getenv("RESOURCE_SERVER_KEY", "local-resource-server-key-change-me")
    log_context_mode: str = os.getenv("LOG_CONTEXT_MODE", "hash").lower()

    max_request_body_bytes: int = _int_env("MAX_REQUEST_BODY_BYTES", 65536)
    max_payment_amount: int = _int_env("MAX_PAYMENT_AMOUNT", 50_000_000)

    def weights(self) -> dict[str, float]:
        weights = {
            "ip": self.weight_ip,
            "device": self.weight_device,
            "time": self.weight_time,
            "frequency": self.weight_frequency,
            "token_history": self.weight_token_history,
        }
        total = sum(weights.values()) or 1.0
        return {key: value / total for key, value in weights.items()}

    def public_config(self) -> dict[str, Any]:
        """Return experiment-relevant settings without exposing secrets."""
        return {
            "api_mode": self.api_mode,
            "app_env": self.app_env,
            "jwt_issuer": self.jwt_issuer,
            "jwt_audience": self.jwt_audience,
            "jwt_algorithm": self.jwt_algorithm,
            "jwt_ttl_seconds": self.jwt_ttl_seconds,
            "max_token_ttl_seconds": self.max_token_ttl_seconds,
            "replace_previous_access_token": self.replace_previous_access_token,
            "max_active_tokens_per_family": self.max_active_tokens_per_family,
            "storage_backend": self.storage_backend,
            "nonce_required": self.nonce_required,
            "device_proof_required": self.device_proof_required,
            "idempotency_required": self.idempotency_required,
            "timestamp_skew_seconds": self.timestamp_skew_seconds,
            "replay_window_seconds": self.replay_window_seconds,
            "burst_window_seconds": self.burst_window_seconds,
            "burst_soft_limit": self.burst_soft_limit,
            "burst_hard_limit": self.burst_hard_limit,
            "hard_burst_block": self.hard_burst_block,
            "allow_threshold": self.allow_threshold,
            "verify_threshold": self.verify_threshold,
            "weights": self.weights(),
            "experiment_mode": self.experiment_mode,
            "trust_proxy_headers": self.trust_proxy_headers,
            "log_context_mode": self.log_context_mode,
            "max_request_body_bytes": self.max_request_body_bytes,
            "max_payment_amount": self.max_payment_amount,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(self.public_config(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def shared_experiment_config(self) -> dict[str, Any]:
        value = dict(self.public_config())
        value.pop("api_mode", None)
        return value

    def shared_experiment_fingerprint(self) -> str:
        raw = json.dumps(self.shared_experiment_config(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def validation_report(self) -> dict[str, list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        if self.api_mode not in {"standard", "baseline", "ratf"}:
            errors.append("API_MODE must be standard, baseline, or ratf")
        if not 0 <= self.verify_threshold < self.allow_threshold <= 1:
            errors.append("Thresholds must satisfy 0 <= VERIFY_THRESHOLD < ALLOW_THRESHOLD <= 1")
        if self.burst_soft_limit < 1 or self.burst_hard_limit <= self.burst_soft_limit:
            errors.append("BURST_HARD_LIMIT must be greater than BURST_SOFT_LIMIT")
        if self.jwt_ttl_seconds < 1 or self.jwt_ttl_seconds > self.max_token_ttl_seconds:
            errors.append("JWT_TTL_SECONDS must be within MAX_TOKEN_TTL_SECONDS")
        if self.max_active_tokens_per_family < 1:
            errors.append("MAX_ACTIVE_TOKENS_PER_FAMILY must be at least 1")
        if self.storage_backend not in {"redis", "memory"}:
            errors.append("STORAGE_BACKEND must be redis or memory")
        if self.log_context_mode not in {"raw", "hash", "masked"}:
            errors.append("LOG_CONTEXT_MODE must be raw, hash, or masked")
        if any(value < 0 for value in self.weights().values()):
            errors.append("Trust-score weights cannot be negative")
        weak_values = {
            "local-jwt-secret-change-me-32-bytes-minimum",
            "local-token-hash-secret-change-me",
            "local-device-master-secret-change-me",
            "local-enrollment-key-change-me",
            "local-experiment-key-change-me",
            "local-audit-log-secret-change-me",
            "local-admin-token-change-me",
            "local-resource-server-key-change-me",
            "change-this-secret-for-local-testing",
        }
        secrets_to_check = {
            "JWT_SECRET": self.jwt_secret,
            "TOKEN_HASH_SECRET": self.token_hash_secret,
            "DEVICE_MASTER_SECRET": self.device_master_secret,
            "DEVICE_ENROLLMENT_KEY": self.device_enrollment_key,
            "EXPERIMENT_KEY": self.experiment_key,
            "AUDIT_LOG_SECRET": self.audit_log_secret,
            "ADMIN_TOKEN": self.admin_token,
            "RESOURCE_SERVER_KEY": self.resource_server_key,
        }
        for name, value in secrets_to_check.items():
            if value in weak_values or len(value) < 24:
                message = f"{name} still uses a weak local value; run scripts/init_env.py"
                if self.strict_startup:
                    errors.append(message)
                else:
                    warnings.append(message)
        if self.storage_backend == "memory":
            warnings.append("Memory storage is suitable only for unit tests, not the final experiment")
        if self.allow_memory_fallback:
            warnings.append("ALLOW_MEMORY_FALLBACK=true can invalidate Redis-based experiment assumptions")
        if self.jwt_algorithm.startswith("HS"):
            warnings.append("HS256 is retained for the local prototype; asymmetric signing is recommended in production")
        return {"errors": errors, "warnings": warnings}

    def assert_valid(self) -> None:
        report = self.validation_report()
        if report["errors"]:
            raise RuntimeError("Invalid configuration: " + "; ".join(report["errors"]))
