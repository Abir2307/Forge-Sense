import pathlib
from functools import lru_cache

import cv2
import numpy as np
from ultralytics import YOLO

BACKGROUND_CLASSES = {"ST", "SWAMP", "OTHERS"}

EXPECTED_PPE_CLASSES = {
    0: "Helmet",
    1: "Gloves",
    2: "Vest",
    3: "Boots",
    4: "Goggles",
    5: "none",
    6: "Person",
    7: "no_helmet",
    8: "no_goggle",
    9: "no_gloves",
    10: "no_boots",
}


class CriticalModelMismatchError(RuntimeError):
    """Raised when the active YOLO weight file does not match the required PPE classes."""


MODEL_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = MODEL_DIR / "best.pt"


# Global stop flag for model operations
_STOP_FLAG = None


def set_model_stop_flag(flag_dict):
    """Set the stop flag for model operations"""
    global _STOP_FLAG
    _STOP_FLAG = flag_dict


def get_model_path(model_path=None):
    if model_path is None:
        return str(DEFAULT_MODEL_PATH)
    return str(pathlib.Path(model_path).expanduser())


def _normalize_model_names(names):
    if isinstance(names, dict):
        return {int(key): str(value) for key, value in names.items()}
    if isinstance(names, (list, tuple)):
        return {index: str(name) for index, name in enumerate(names)}
    raise CriticalModelMismatchError(
        f"Unsupported model.names format: {type(names).__name__}. Expected dict or list."
    )


def load_and_validate_model(model_path=None):
    resolved_path = get_model_path(model_path)
    model_file = pathlib.Path(resolved_path)

    if not model_file.exists():
        raise FileNotFoundError(f"Model weights not found at {model_file}")

    model = YOLO(str(model_file))
    normalized_names = _normalize_model_names(model.names)

    if normalized_names != EXPECTED_PPE_CLASSES:
        raise CriticalModelMismatchError(
            "CRITICAL_MODEL_MISMATCH: expected PPE classes "
            f"{EXPECTED_PPE_CLASSES}, got {normalized_names}"
        )

    return model


@lru_cache(maxsize=1)
def get_runtime_model(model_path=None):
    return load_and_validate_model(model_path=model_path)


_yolo_model = get_runtime_model()


def get_background_mask(rgb_img, stop_flag=None):
    global _STOP_FLAG

    if stop_flag is None:
        stop_flag = _STOP_FLAG

    if stop_flag is not None and stop_flag.get("stop", False):
        return None

    if rgb_img is None:
        raise ValueError("rgb_img is None")

    h, w = rgb_img.shape[:2]

    results = _yolo_model.predict(
        source=rgb_img,
        imgsz=h,
        verbose=False
    )

    r = results[0]
    if r.masks is None:
        return np.ones((h, w), dtype=np.uint8)

    masks = r.masks.data.cpu().numpy()
    classes = r.boxes.cls.cpu().numpy().astype(int)
    names = r.names

    h_m, w_m = masks.shape[1:]
    mask_model = np.ones((h_m, w_m), dtype=np.uint8)

    for m, c in zip(masks, classes):
        cls_name = names[int(c)]
        if cls_name in BACKGROUND_CLASSES:
            m_bool = m > 0.5
            mask_model[m_bool] = 0

    if mask_model.shape != (h, w):
        mask_resized = cv2.resize(mask_model, (w, h), interpolation=cv2.INTER_NEAREST)
    else:
        mask_resized = mask_model

    return mask_resized
