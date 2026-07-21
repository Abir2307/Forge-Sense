from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


def calculate_false_negative_rate(predicted: Sequence[int], actual: Sequence[int]) -> float:
    """Return the proportion of actual positives that were missed by the model."""
    if not actual:
        return 0.0

    actual_positive_count = sum(1 for value in actual if value == 1)
    if actual_positive_count == 0:
        return 0.0

    missed = sum(1 for predicted_value, actual_value in zip(predicted, actual) if actual_value == 1 and predicted_value != 1)
    return missed / actual_positive_count


def evaluate_prediction_lead_time(
    warnings: Sequence[Dict[str, Any]],
    incident_time: str,
    threshold: float = 0.8,
) -> float:
    """Return the lead time from the latest warning that crossed the threshold to the incident."""
    if not warnings:
        return 0.0

    incident_dt = datetime.fromisoformat(incident_time)
    crossing_times: List[datetime] = []

    for warning in warnings:
        if float(warning.get("risk_score", 0.0)) >= threshold:
            crossing_times.append(datetime.fromisoformat(str(warning["timestamp"])))

    if not crossing_times:
        return 0.0

    latest_crossing = max(crossing_times)
    return max(0.0, (incident_dt - latest_crossing).total_seconds() / 60.0)


def evaluate_geospatial_quality(predicted_zones: Iterable[str], actual_zones: Iterable[str]) -> float:
    """Return Jaccard similarity for zone localization quality."""
    predicted_set = {str(zone).strip() for zone in predicted_zones if str(zone).strip()}
    actual_set = {str(zone).strip() for zone in actual_zones if str(zone).strip()}

    if not predicted_set and not actual_set:
        return 0.0

    overlap = predicted_set & actual_set
    union = predicted_set | actual_set
    if not union:
        return 0.0

    return len(overlap) / len(union)


def build_evaluation_summary(
    predicted: Sequence[int],
    actual: Sequence[int],
    warnings: Sequence[Dict[str, Any]],
    incident_time: str,
    predicted_zones: Iterable[str],
    actual_zones: Iterable[str],
) -> Dict[str, float]:
    """Create a compact evaluation summary for the demo and reporting deck."""
    return {
        "false_negative_rate": calculate_false_negative_rate(predicted, actual),
        "lead_time_minutes": evaluate_prediction_lead_time(warnings, incident_time),
        "geospatial_quality": evaluate_geospatial_quality(predicted_zones, actual_zones),
    }


def build_partial_evaluation_summary(
    predicted: Sequence[int],
    actual: Sequence[int],
    warnings: Sequence[Dict[str, Any]],
    incident_time: Optional[str],
    predicted_zones: Iterable[str],
    actual_zones: Iterable[str],
) -> Dict[str, Optional[float]]:
    """Create evaluation metrics while preserving partial availability."""
    false_negative_rate = (
        calculate_false_negative_rate(predicted, actual) if actual else None
    )
    lead_time_minutes = None
    if warnings and incident_time:
        try:
            lead_time_minutes = evaluate_prediction_lead_time(warnings, incident_time)
        except ValueError:
            lead_time_minutes = None

    geospatial_quality = None
    if predicted_zones or actual_zones:
        geospatial_quality = evaluate_geospatial_quality(predicted_zones, actual_zones)

    return {
        "false_negative_rate": false_negative_rate,
        "lead_time_minutes": lead_time_minutes,
        "geospatial_quality": geospatial_quality,
    }


def _assessment_has_evaluation_data(assessment: Optional[Dict[str, Any]] = None) -> bool:
    if not isinstance(assessment, dict):
        return False

    if isinstance(assessment.get("evaluation_summary"), dict):
        return bool(assessment["evaluation_summary"])

    keys = ["predicted", "actual", "warnings", "incident_time", "predicted_zones", "actual_zones"]
    for key in keys:
        value = assessment.get(key)
        if value:
            return True
    return False


def build_assessment_evaluation_summary(assessment: Optional[Dict[str, Any]] = None) -> Dict[str, Optional[float]]:
    """Build evaluation metrics from a dashboard assessment payload when present."""
    assessment = assessment or {}
    if not _assessment_has_evaluation_data(assessment):
        return {
            "false_negative_rate": None,
            "lead_time_minutes": None,
            "geospatial_quality": None,
        }

    evaluation_summary = assessment.get("evaluation_summary")
    if isinstance(evaluation_summary, dict):
        has_non_null = any(
            evaluation_summary.get(key) is not None
            for key in ["false_negative_rate", "lead_time_minutes", "geospatial_quality"]
        )
        if has_non_null:
            return {
                "false_negative_rate": evaluation_summary.get("false_negative_rate"),
                "lead_time_minutes": evaluation_summary.get("lead_time_minutes"),
                "geospatial_quality": evaluation_summary.get("geospatial_quality"),
            }

    return build_partial_evaluation_summary(
        predicted=assessment.get("predicted", []) or [],
        actual=assessment.get("actual", []) or [],
        warnings=assessment.get("warnings", []) or [],
        incident_time=str(assessment.get("incident_time") or "") or None,
        predicted_zones=assessment.get("predicted_zones", []) or [],
        actual_zones=assessment.get("actual_zones", []) or [],
    )
