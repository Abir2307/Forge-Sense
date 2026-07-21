from threading import Lock


class LocalSensorManager:
    def __init__(self):
        self._lock = Lock()
        self.current_sensor_state = {'gas': 0.0, 'temp': 25.0}
        self.previous_sensor_state = dict(self.current_sensor_state)

    def inject_hazard(self, gas_val, temp_val):
        with self._lock:
            self.previous_sensor_state = dict(self.current_sensor_state)
            self.current_sensor_state = {
                'gas': float(gas_val),
                'temp': float(temp_val),
            }

    def restore_state(self, state=None):
        with self._lock:
            if state is None:
                state = self.previous_sensor_state
            self.current_sensor_state = dict(state)
            self.previous_sensor_state = dict(state)

    def get_latest(self):
        with self._lock:
            return dict(self.current_sensor_state)


local_sensor_manager = LocalSensorManager()
