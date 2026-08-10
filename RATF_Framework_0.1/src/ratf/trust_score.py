from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any

from .config import Settings
from .core.models import RequestContext
from .storage import Storage


@dataclass
class ScoreResult:
    trust_score: float
    components: dict[str, float]
    reason_codes: list[str]
    request_count: int


def _ua_family(value: str) -> str:
    low = value.lower()
    for family in ["edge", "chrome", "firefox", "safari", "postman", "python", "k6", "android", "ios"]:
        if family in low:
            return family
    return low.split("/", 1)[0][:32]


def _same_network(first: str, current: str) -> bool:
    try:
        a, b = ipaddress.ip_address(first), ipaddress.ip_address(current)
        if a.version != b.version:
            return False
        prefix = 24 if a.version == 4 else 64
        return ipaddress.ip_network(f"{a}/{prefix}", strict=False) == ipaddress.ip_network(
            f"{b}/{prefix}", strict=False
        )
    except ValueError:
        return False


def _profile_key(subject: str) -> str:
    return f"family_context:{subject}"


def _history_key(subject: str) -> str:
    return f"family_history:{subject}"


def _initial_profile(
    storage: Storage,
    subject: str,
    context: RequestContext,
    token_metadata: dict[str, Any],
    ttl: int,
) -> dict[str, Any]:
    value = storage.get_json(_profile_key(subject))
    if value:
        return value
    value = {
        "first_ip": token_metadata.get("issued_ip") or context.source_ip,
        "first_user_agent": token_metadata.get("issued_user_agent") or context.user_agent,
        "first_device_id": context.device_id,
        "first_hour_utc": token_metadata.get("issued_hour_utc")
        if token_metadata.get("issued_hour_utc") is not None
        else context.hour_utc,
        "first_endpoint": context.endpoint,
        "profile_source": "token_issuance" if token_metadata.get("issued_ip") else "first_protected_request",
    }
    storage.set_json(_profile_key(subject), value, ttl_seconds=ttl)
    return value


def _get_history(storage: Storage, subject: str) -> dict[str, Any]:
    return storage.get_json(_history_key(subject)) or {
        "ips": [],
        "user_agents": [],
        "devices": [],
        "endpoints": [],
        "allowed_request_count": 0,
    }


def record_context_history(
    storage: Storage,
    subject: str,
    context: RequestContext,
    ttl: int,
) -> None:
    """Learn context only after a request is allowed.

    Blocked and verify outcomes are intentionally excluded so an attacker cannot
    poison the trusted profile by repeatedly submitting anomalous requests.
    """
    value = _get_history(storage, subject)
    for field, item in [
        ("ips", context.source_ip),
        ("user_agents", context.user_agent),
        ("devices", context.device_id),
        ("endpoints", context.endpoint),
    ]:
        if item and item not in value[field]:
            value[field].append(item)
        value[field] = value[field][-10:]
    value["last_allowed_at"] = context.timestamp
    value["allowed_request_count"] = int(value.get("allowed_request_count", 0)) + 1
    storage.set_json(_history_key(subject), value, ttl_seconds=ttl)


def compute_trust_score(
    storage: Storage,
    settings: Settings,
    subject: str,
    context: RequestContext,
    session_ttl_seconds: int,
    replay_detected: bool,
    token_metadata: dict[str, Any] | None = None,
    request_count: int = 1,
) -> ScoreResult:
    token_metadata = token_metadata or {}
    initial = _initial_profile(storage, subject, context, token_metadata, session_ttl_seconds)
    history = _get_history(storage, subject)
    reasons: list[str] = []

    if context.source_ip == initial["first_ip"]:
        cip = 1.0
    elif _same_network(str(initial["first_ip"]), context.source_ip):
        cip = 0.90
        reasons.append("ip_changed_same_network")
    elif context.source_ip in history.get("ips", []):
        cip = 0.80
        reasons.append("ip_matches_prior_allowed_network")
    elif len(history.get("ips", [])) <= 1:
        cip = 0.60
        reasons.append("ip_changed_new_network")
    else:
        cip = 0.35
        reasons.append("ip_changed_unseen_network")

    same_device = bool(context.device_id) and context.device_id == initial.get("first_device_id")
    same_ua = context.user_agent == initial.get("first_user_agent")
    same_family = _ua_family(context.user_agent) == _ua_family(str(initial.get("first_user_agent", "")))
    prior_ua = context.user_agent in history.get("user_agents", [])
    if same_device and same_ua:
        cdevice = 1.0
    elif same_device and same_family:
        cdevice = 0.90
        reasons.append("user_agent_minor_change")
    elif same_device and prior_ua:
        cdevice = 0.85
        reasons.append("user_agent_matches_prior_allowed_context")
    elif same_device:
        cdevice = 0.60
        reasons.append("user_agent_changed_same_bound_device")
    else:
        cdevice = 0.20
        reasons.append("device_changed")

    diff = abs(context.hour_utc - int(initial["first_hour_utc"]))
    diff = min(diff, 24 - diff)
    if diff <= 3:
        ctime = 1.0
    elif diff <= 8:
        ctime = 0.80
        reasons.append("access_time_shifted")
    else:
        ctime = 0.55
        reasons.append("access_time_far_from_initial")

    if request_count <= settings.burst_soft_limit:
        freq = 1.0
    elif request_count <= settings.burst_hard_limit:
        freq = 0.60
        reasons.append("request_frequency_elevated")
    else:
        freq = 0.15
        reasons.append("request_frequency_high")

    if replay_detected:
        htoken = 0.10
        reasons.append("replay_detected")
    else:
        novel_ip = context.source_ip != initial["first_ip"] and context.source_ip not in history.get("ips", [])
        novel_ua = context.user_agent != initial["first_user_agent"] and context.user_agent not in history.get("user_agents", [])
        novel_device = bool(history.get("devices")) and context.device_id not in history.get("devices", [])
        novelty_count = int(novel_ip) + int(novel_ua) + int(novel_device)
        if novelty_count == 0:
            htoken = 1.0
        elif novelty_count == 1:
            htoken = 0.80
            reasons.append("token_context_single_novelty")
        elif novelty_count == 2:
            htoken = 0.55
            reasons.append("token_context_multiple_novelty")
        else:
            htoken = 0.30
            reasons.append("token_context_high_novelty")

    components = {
        "Cip": cip,
        "Cdevice": cdevice,
        "Ctime": ctime,
        "Freq": freq,
        "Htoken": htoken,
    }
    w = settings.weights()
    score = (
        w["ip"] * cip
        + w["device"] * cdevice
        + w["time"] * ctime
        + w["frequency"] * freq
        + w["token_history"] * htoken
    )
    return ScoreResult(
        round(max(0.0, min(score, 1.0)), 4),
        components,
        reasons,
        request_count,
    )
