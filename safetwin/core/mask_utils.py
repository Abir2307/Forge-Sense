import cv2
import numpy as np

def create_binary_mask(data_array, threshold, condition="greater"):
    """
    Generic mask: 1 where condition is met, 0 otherwise.
    Condition can be 'greater' or 'less'.
    """
    mask = np.zeros_like(data_array, dtype=np.uint8)
    valid = ~np.isnan(data_array)
    
    if condition == "greater":
        sel = valid & (data_array >= threshold)
    else:
        sel = valid & (data_array <= threshold)
        
    mask[sel] = 1
    return mask

def create_compound_mask(data_maps, logic_func):
    """
    Advanced compound risk detection.
    data_maps: list of arrays (e.g., [gas_map, temp_map])
    logic_func: a function that defines the 'danger' rule.
    """
    # Example logic_func: lambda g, t: (g > 0.8) | (t > 50.0)
    mask = logic_func(*data_maps)
    return mask.astype(np.uint8)

def dilate_mask(mask, size=2):
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size * 2 + 1, size * 2 + 1))
    return cv2.dilate(mask, kernel, iterations=1)

def apply_risk_overlay(image, risk_mask, color=(0, 0, 255), alpha=0.3):
    """
    Overlays a risk heatmap onto a frame.
    risk_mask: 0 (safe) to 1 (danger).
    """
    # Ensure image is BGR
    if image.ndim == 2:
        img_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        img_bgr = image.copy()

    overlay = img_bgr.copy()
    # Apply color based on risk intensity
    overlay[risk_mask > 0.5] = color 
    
    return cv2.addWeighted(overlay, alpha, img_bgr, 1 - alpha, 0)