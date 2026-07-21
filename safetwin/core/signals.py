from PySide6.QtCore import QObject, Signal

class SignalBus(QObject):
    # Everything in the system talks through these signals
    risk_updated = Signal(dict)
    RISK_UPDATE = Signal(dict)
    FORCE_SENSOR_STATE = Signal(dict)
    hazard_detected = Signal(str, dict)

# The Global instance
bus = SignalBus()