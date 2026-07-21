from __future__ import annotations

from typing import Any


_ZONE_TYPE_RISK_MAPPING = {
    "SAFE": 0.05,
    "CAUTION": 0.20,
    "MAINTENANCE": 0.25,
    "RESTRICTED": 0.50,
    "WARNING": 0.60,
    "DANGEROUS": 0.95,
    "CRITICAL": 1.00,
    "DANGER": 0.95,
    "UNDEFINED": 0.35,
}


def zone_type_to_risk_score(zone_type: Any) -> float:
    """Map a zone type label to a normalized risk score for UI rendering."""
    if zone_type is None:
        return _ZONE_TYPE_RISK_MAPPING.get("CAUTION", 0.20)

    normalized = str(zone_type).strip().upper()
    return float(min(1.0, max(0.0, _ZONE_TYPE_RISK_MAPPING.get(normalized, _ZONE_TYPE_RISK_MAPPING.get("UNDEFINED", 0.30)))))


def normalize_compliance_score(payload: dict | None = None) -> float:
    """Normalize compliance score from either score or compliance_score fields."""
    payload = payload or {}
    if not isinstance(payload, dict):
        return 0.0

    value = payload.get("score", payload.get("compliance_score", 0.0))
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def derive_risk_level(payload: dict | None = None) -> str:
    """Infer a readable risk level from a safety payload without falling back to Unknown."""
    payload = payload or {}

    explicit_level = (
        payload.get("overall_risk_level")
        or payload.get("risk_level")
        or payload.get("status")
    )
    if explicit_level:
        explicit_level = str(explicit_level).upper()
        if explicit_level in {"CRITICAL", "HIGH", "MEDIUM", "WARNING", "LOW", "READY"}:
            return explicit_level

    hazards = payload.get("hazards", []) or []
    hazard_levels = [str(h.get("level", "LOW")).upper() for h in hazards if isinstance(h, dict)]
    if "CRITICAL" in hazard_levels:
        return "CRITICAL"
    if "HIGH" in hazard_levels:
        return "HIGH"
    if "MEDIUM" in hazard_levels or "WARNING" in hazard_levels:
        return "WARNING"

    score = payload.get("risk_score", payload.get("score", 0.0))
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        numeric_score = 0.0

    if numeric_score >= 0.8:
        return "CRITICAL"
    if numeric_score >= 0.6:
        return "HIGH"
    if numeric_score >= 0.3:
        return "WARNING"
    return "READY"
