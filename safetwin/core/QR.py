import json
import os
import qrcode
import re
from qrcode.exceptions import DataOverflowError


def _hazard_to_data(level: str):
    """Maps safety levels to risk codes for QR generation."""
    mapping = {
        "CRITICAL": ("3", "1", "0"), # Code: Risk Level, ImmediateAction, Pts
        "WARNING":  ("2", "0", "0"),
        "SAFE":     ("1", "0", "0")
    }
    return mapping.get(level.upper(), ("0", "0", "0"))


def generate_safety_qr(hazard_list, output_png, max_entries_per_qr: int = 8):
    """
    hazard_list = [{"lat": float, "lon": float, "level": str, "zone_id": str, "alert_type": str, "description": str}]

    max_entries_per_qr controls how many hazard entries are packed into each QR page.
    Smaller values make each QR more likely to fit and makes paging more predictable.
    """
    entries = []
    for h in hazard_list:
        if isinstance(h, dict):
            level = str(h.get("level") or h.get("severity") or "SAFE").upper()
            risk_code, action, _ = _hazard_to_data(level)
            payload = {
                "lat": float(h.get("lat", 0.0) or 0.0),
                "lon": float(h.get("lon", 0.0) or 0.0),
                "risk_code": risk_code,
                "action": action,
                "level": level,
                "zone_id": h.get("zone_id") or h.get("location") or "UNKNOWN_ZONE",
                "alert_type": h.get("alert_type") or h.get("type") or "ALERT",
                "description": h.get("description") or h.get("reason") or "Safety alert",
            }
            entries.append(json.dumps(payload))
        else:
            entries.append(str(h))

    max_entries_per_qr = max(1, int(max_entries_per_qr or 1))
    joined = "\n".join(entries)

    def _try_make_image(data_str, path) -> bool:
        try:
            qr = qrcode.QRCode(version=None, box_size=3, border=1)
            qr.add_data(data_str)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(path)
            return True
        except DataOverflowError:
            return False

    # If the caller requested a smaller page size than the full payload, paginate
    # even when a single QR could technically fit. This preserves predictable chunking.
    should_paginate = len(entries) > max_entries_per_qr
    if not should_paginate and _try_make_image(joined, output_png):
        return [output_png]

    # If it doesn't fit, or the caller wants smaller pages, paginate by splitting
    # entries into smaller groups.
    os.makedirs(os.path.dirname(output_png) or '.', exist_ok=True)

    def _paginate_and_create(items, base_path, page_index=1):
        if not items:
            return []

        chunk = items[:max_entries_per_qr]
        remaining = items[max_entries_per_qr:]
        current_path = base_path
        if page_index > 1:
            current_path = f"{os.path.splitext(base_path)[0]}_{page_index}{os.path.splitext(base_path)[1]}"

        if _try_make_image("\n".join(chunk), current_path):
            if remaining:
                next_pages = _paginate_and_create(remaining, base_path, page_index + 1)
                return [current_path] + next_pages
            return [current_path]

        # fall back to smaller chunks if the configured size is still too large
        if len(chunk) == 1:
            truncated = chunk[0][:800]
            _try_make_image(truncated, current_path)
            if remaining:
                return [current_path] + _paginate_and_create(remaining, base_path, page_index + 1)
            return [current_path]

        mid = len(chunk) // 2
        left = chunk[:mid]
        right = chunk[mid:]
        left_path = f"{os.path.splitext(current_path)[0]}_a{os.path.splitext(current_path)[1]}"
        right_path = f"{os.path.splitext(current_path)[0]}_b{os.path.splitext(current_path)[1]}"
        return _paginate_and_create(left, left_path, page_index) + _paginate_and_create(right, right_path, page_index + 1)

    parts = _paginate_and_create(entries, output_png)
    return parts

# Alias for compatibility
def generate_qr_images_from_zones(hazard_list, output_png, max_entries_per_qr: int = 8):
    """Alias for generate_safety_qr for UI compatibility"""
    return generate_safety_qr(hazard_list, output_png, max_entries_per_qr=max_entries_per_qr)