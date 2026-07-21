import json
import pathlib
from typing import Dict, List, Optional, Sequence, Tuple


VIEW_MODES = ("top_down", "perspective")
DEFAULT_ZONE_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "perspective_zones.json"


def _default_zones() -> List[Dict]:
    return [
        {"id": "zone_1", "name": "Zone 1", "type": "UNDEFINED", "polygon": [[0.00, 0.00], [0.33, 0.00], [0.33, 0.33], [0.00, 0.33]]},
        {"id": "zone_2", "name": "Zone 2", "type": "UNDEFINED", "polygon": [[0.33, 0.00], [0.66, 0.00], [0.66, 0.33], [0.33, 0.33]]},
        {"id": "zone_3", "name": "Zone 3", "type": "UNDEFINED", "polygon": [[0.66, 0.00], [1.00, 0.00], [1.00, 0.33], [0.66, 0.33]]},
        {"id": "zone_4", "name": "Zone 4", "type": "UNDEFINED", "polygon": [[0.00, 0.33], [0.33, 0.33], [0.33, 0.66], [0.00, 0.66]]},
        {"id": "zone_5", "name": "Zone 5", "type": "UNDEFINED", "polygon": [[0.33, 0.33], [0.66, 0.33], [0.66, 0.66], [0.33, 0.66]]},
        {"id": "zone_6", "name": "Zone 6", "type": "UNDEFINED", "polygon": [[0.66, 0.33], [1.00, 0.33], [1.00, 0.66], [0.66, 0.66]]},
        {"id": "zone_7", "name": "Zone 7", "type": "UNDEFINED", "polygon": [[0.00, 0.66], [0.33, 0.66], [0.33, 1.00], [0.00, 1.00]]},
        {"id": "zone_8", "name": "Zone 8", "type": "UNDEFINED", "polygon": [[0.33, 0.66], [0.66, 0.66], [0.66, 1.00], [0.33, 1.00]]},
        {"id": "zone_9", "name": "Zone 9", "type": "UNDEFINED", "polygon": [[0.66, 0.66], [1.00, 0.66], [1.00, 1.00], [0.66, 1.00]]},
    ]


def load_zone_config(config_path: Optional[str] = None) -> Dict:
    path = pathlib.Path(config_path) if config_path else DEFAULT_ZONE_CONFIG_PATH
    if not path.exists():
        return {"view_mode": "perspective", "zones": _default_zones()}

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("Zone config must be a JSON object")

    view_mode = str(payload.get("view_mode", "perspective")).lower()
    if view_mode not in VIEW_MODES:
        raise ValueError(f"Unsupported view mode: {view_mode}")

    zones = payload.get("zones") or _default_zones()
    if not isinstance(zones, list):
        raise ValueError("Zone config 'zones' must be a list")

    return {"view_mode": view_mode, "zones": zones}


def point_in_polygon(point: Sequence[float], polygon: Sequence[Sequence[float]]) -> bool:
    if not polygon:
        return False

    x, y = point
    inside = False
    for index, current in enumerate(polygon):
        next_point = polygon[(index + 1) % len(polygon)]
        x1, y1 = current
        x2, y2 = next_point

        intersects = ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1)
        if intersects:
            inside = not inside

    return inside


def normalize_polygon(polygon: Sequence[Sequence[float]], width: int, height: int) -> List[Tuple[float, float]]:
    normalized: List[Tuple[float, float]] = []
    for x_norm, y_norm in polygon:
        normalized.append((float(x_norm) * width, float(y_norm) * height))
    return normalized


def resolve_zone_type_for_point(point: Sequence[float], zones: Sequence[Dict]) -> str:
    """Return the configured zone type for a point using the user-defined zone polygons."""
    for zone in zones or []:
        polygon = zone.get("polygon") or []
        if not polygon:
            continue
        if point_in_polygon(point, polygon):
            return str(zone.get("type", "CAUTION")).upper()
    return "CAUTION"
