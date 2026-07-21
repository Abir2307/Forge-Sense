import time
import threading

class SafetyStateManager:
    """
    Acts as the 'Single Source of Truth' for the Industrial Digital Twin.
    Keeps track of the latest hazard zones, sensor readings, and system status.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._state = {
            "last_updated": 0,
            "danger_zones": [],
            "gas_level": 0.0,
            "status": "INITIALIZING"
        }

    def update_state(self, danger_zones, sensor_data):
        """Called by main.py every frame to keep the twin synchronized."""
        with self._lock:
            self._state.update({
                "last_updated": time.time(),
                "danger_zones": danger_zones,
                "gas_level": sensor_data.get('gas', 0.0),
                "status": "CRITICAL" if danger_zones else "SAFE"
            })

    def get_current_state(self):
        """Called by UI or API to get the latest twin status."""
        with self._lock:
            return self._state