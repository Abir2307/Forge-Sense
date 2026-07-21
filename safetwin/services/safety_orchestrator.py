import numpy as np
import cv2
from safetwin.core.blocks_analysis import analyze_blocks
from safetwin.model.model import get_runtime_model

class CompoundRiskEngine:
    def __init__(self, block_size=30):
        self.block_size = block_size
        self.model = get_runtime_model()
        # Thresholds defined here for centralized control
        self.GAS_THRESHOLD = 0.5
        self.HIGH_GAS_THRESHOLD_PPM = 500
        self.RISK_DANGER_THRESHOLD = 0.7
        self.SENSOR_MAX_NORMALIZED = 1.0
        self.SENSOR_IMPORTANCE = {
            'gas': 0.35,
            'temperature': 0.18,
            'humidity': 0.08,
            'voltage': 0.18,
            'oxygen': 0.10,
            'moisture_alert': 0.11,
        }

    def run_yolo(self, frame):
        """Runs inference and returns list of dicts: {'box': (x1, y1, x2, y2), 'class': int}"""
        results = self.model(frame, verbose=False)
        detections = []
        for r in results:
            if r.boxes is not None:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cls = int(box.cls[0].cpu().numpy())
                    detections.append({'box': (x1, y1, x2, y2), 'class': cls})
        return detections

    def calculate_risk(self, frame_shape, detections, sensor_data):
        """Generates a risk heatmap based on AI input and sensor data."""
        h, w = frame_shape[:2]
        risk_map = np.zeros((h, w), dtype=np.float32)

        # 1. Map Detections (e.g., workers) to the map
        for det in detections:
            x1, y1, x2, y2 = map(int, det['box'])
            # Increase risk intensity in the worker's bounding box
            risk_map[y1:y2, x1:x2] = np.maximum(risk_map[y1:y2, x1:x2], 0.5)

        # 2. Map IoT Sensor Data
        sensor_risk = self._calculate_sensor_risk(sensor_data)
        if sensor_risk > 0.0:
            risk_map += sensor_risk

        if len(detections) > 5:
            risk_map += 0.10

        return np.clip(risk_map, 0, self.SENSOR_MAX_NORMALIZED)

    def _calculate_sensor_risk(self, sensor_data):
        if not sensor_data or not isinstance(sensor_data, dict):
            return 0.0

        normalized_scores = []
        gas_score = self._normalize_gas_value(sensor_data.get('gas', sensor_data.get('gas_level', 0)))
        normalized_scores.append(gas_score * self.SENSOR_IMPORTANCE['gas'])

        temp_score = self._normalize_temperature(sensor_data.get('temperature', sensor_data.get('temp', 0)))
        normalized_scores.append(temp_score * self.SENSOR_IMPORTANCE['temperature'])

        humidity_score = self._normalize_sensor_value(sensor_data.get('humidity', 0), scale=100.0)
        normalized_scores.append(humidity_score * self.SENSOR_IMPORTANCE['humidity'])

        voltage_score = self._normalize_voltage_value(sensor_data.get('voltage', sensor_data.get('voltage_level', 0)))
        normalized_scores.append(voltage_score * self.SENSOR_IMPORTANCE['voltage'])

        oxygen_score = self._normalize_oxygen(sensor_data.get('oxygen', sensor_data.get('oxygen_level', 21.0)))
        normalized_scores.append(oxygen_score * self.SENSOR_IMPORTANCE['oxygen'])

        moisture_score = 1.0 if sensor_data.get('moisture_alert') else 0.0
        normalized_scores.append(moisture_score * self.SENSOR_IMPORTANCE['moisture_alert'])

        compound_boost = 0.0
        if gas_score >= 0.75 and temp_score >= 0.6:
            compound_boost += 0.05
        if voltage_score >= 0.75 and humidity_score >= 0.6:
            compound_boost += 0.05
        if oxygen_score >= 0.75 and moisture_score > 0.0:
            compound_boost += 0.05

        return min(self.SENSOR_MAX_NORMALIZED, sum(normalized_scores) + compound_boost)

    def _normalize_sensor_value(self, value, scale=1.0):
        try:
            val = float(value)
        except (TypeError, ValueError):
            return 0.0
        if scale <= 0:
            return 0.0
        if val < 0:
            return 0.0
        return min(1.0, val / scale)

    def _normalize_gas_value(self, value):
        try:
            gas = float(value)
        except (TypeError, ValueError):
            return 0.0
        if gas > 10.0:
            return min(1.0, gas / 1000.0)
        return min(1.0, gas)

    def _normalize_voltage_value(self, value):
        try:
            voltage = float(value)
        except (TypeError, ValueError):
            return 0.0
        if voltage > 10.0:
            return min(1.0, voltage / 240.0)
        return min(1.0, voltage)

    def _normalize_temperature(self, value):
        try:
            temp = float(value)
        except (TypeError, ValueError):
            return 0.0
        if temp <= 1.0:
            return temp
        return min(1.0, temp / 120.0)

    def _normalize_oxygen(self, value):
        try:
            oxygen = float(value)
        except (TypeError, ValueError):
            return 0.0
        if oxygen < 19.5 or oxygen > 23.5:
            return min(1.0, abs(21.0 - oxygen) / 2.5)
        return 0.0

    def analyze_safety_zones(self, risk_map):
        """Uses your logic to extract danger zones."""
        from safetwin.core.blocks_analysis import analyze_blocks
        stats = analyze_blocks(risk_map, self.block_size)
        
        # Identify block indices that are DANGEROUS
        danger_y, danger_x = np.where(stats['mean'] > self.RISK_DANGER_THRESHOLD)
        return list(zip(danger_y, danger_x))

    def evaluate_compound_risk(self, sensor_data, video_hazards, frame_id=None, location=None):
        """Detect emergent compound hazard risk across video and sensor domains."""
        hazard_factors = {
            'restricted_zone': self._has_worker_in_restricted_zone(video_hazards),
            'high_gas': self._has_high_gas_level(sensor_data),
            'high_temp': self._has_high_temperature(sensor_data),
            'low_oxygen': self._has_low_oxygen(sensor_data),
            'moisture_issue': bool(sensor_data and sensor_data.get('moisture_alert')),
        }

        score = 0.0
        if hazard_factors['restricted_zone']:
            score += 0.25
        if hazard_factors['high_gas']:
            score += 0.30
        if hazard_factors['high_temp']:
            score += 0.15
        if hazard_factors['low_oxygen']:
            score += 0.15
        if hazard_factors['moisture_issue']:
            score += 0.10

        score = min(1.0, score)
        severity = 'LOW'
        status = 'OK'
        event_type = 'NO_COMPOUND_RISK'

        if score >= 0.75:
            severity = 'CRITICAL'
            status = 'CRITICAL'
            event_type = 'CRITICAL_COMPOUND_RISK'
        elif score >= 0.45:
            severity = 'HIGH'
            status = 'HIGH'
            event_type = 'COMPOUND_RISK'
        elif score >= 0.20:
            severity = 'MEDIUM'
            status = 'MEDIUM'
            event_type = 'ELEVATED_RISK'

        return {
            'event_type': event_type,
            'status': status,
            'severity': severity,
            'frame_id': frame_id,
            'location': location,
            'risk_score': score,
            'reason': 'Compound sensor and video hazard conditions detected',
            'hazard_factors': hazard_factors,
            'sensor_data': sensor_data or {},
            'video_hazards': video_hazards or {}
        }

    def _has_worker_in_restricted_zone(self, video_hazards):
        if not video_hazards:
            return False

        if isinstance(video_hazards, dict):
            if video_hazards.get('worker_in_restricted_zone'):
                return True
            if video_hazards.get('restricted_zone_violation'):
                return True

            danger_zones = video_hazards.get('danger_zones', [])
            return bool(danger_zones)

        return bool(video_hazards)

    def _has_high_gas_level(self, sensor_data):
        if not sensor_data:
            return False

        gas_level = sensor_data.get('gas', sensor_data.get('gas_level', 0))

        try:
            gas_level = float(gas_level)
        except (TypeError, ValueError):
            return False

        return gas_level >= self.GAS_THRESHOLD or gas_level >= self.HIGH_GAS_THRESHOLD_PPM

    def _has_high_temperature(self, sensor_data):
        if not sensor_data:
            return False

        temp = sensor_data.get('temperature', sensor_data.get('temp', 0))
        try:
            temp = float(temp)
        except (TypeError, ValueError):
            return False

        return temp >= 80.0

    def _has_low_oxygen(self, sensor_data):
        if not sensor_data:
            return False

        oxygen = sensor_data.get('oxygen', sensor_data.get('oxygen_level', 21.0))
        try:
            oxygen = float(oxygen)
        except (TypeError, ValueError):
            return False

        return oxygen < 19.5 or oxygen > 23.5


class HazardLogic:
    """Rich risk classifier for worker, zone, and sensor combinations."""

    def __init__(self):
        self.zone_severity = {
            'SAFE': 0,
            'CAUTION': 1,
            'MAINTENANCE': 1,
            'RESTRICTED': 2,
            'WARNING': 2,
            'DANGEROUS': 3,
            'CRITICAL': 4,
            'DANGER': 3,
            'UNDEFINED': 1,
        }
        self.sensor_likelihood = {
            'LOW': 1,
            'WARNING': 2,
            'HIGH': 3,
        }

    def calculate_hazard_level(self, worker_detected, zone_type, sensor_data):
        zone_type = (zone_type or 'CAUTION').upper()
        sensor_level = self._sensor_level(sensor_data)
        worker_present = bool(worker_detected)
        severity = self.zone_severity.get(zone_type, 1)
        likelihood = self.sensor_likelihood.get(sensor_level, 1)
        score = severity * likelihood

        if worker_present and severity >= 3 and sensor_level == 'HIGH':
            return self._build_result(
                'CRITICAL', score, zone_type, sensor_level,
                f'Worker in {zone_type} with high sensor alert',
                'TRIGGER_EMERGENCY_SHUTDOWN'
            )

        if worker_present and zone_type in {'RESTRICTED', 'CONFINED_SPACE', 'HOT_WORK'}:
            return self._build_result(
                'HIGH', score, zone_type, sensor_level,
                'Worker present in a high-safety zone',
                'NOTIFY_SUPERVISOR_AND_VERIFY_PERMIT'
            )

        if sensor_level == 'WARNING' and severity >= 2:
            return self._build_result(
                'HIGH', score, zone_type, sensor_level,
                'Sensor warning detected in elevated hazard zone',
                'REVIEW_SENSOR_READINGS'
            )

        if sensor_level == 'WARNING' or (worker_present and severity == 1):
            return self._build_result(
                'MEDIUM', score, zone_type, sensor_level,
                'Worker present under cautionary conditions',
                'LOG_AND_MONITOR'
            )

        return self._build_result(
            'LOW', score, zone_type, sensor_level,
            'No immediate actionable hazard detected',
            'LOG_EVENT'
        )

    def _build_result(self, level, score, zone_type, sensor_level, reason, action):
        return {
            'level': level,
            'reason': reason,
            'action': action,
            'score': float(np.clip(score / 12.0, 0.0, 1.0)),
            'zone_type': zone_type,
            'sensor_level': sensor_level,
        }

    def _sensor_level(self, sensor_data):
        if not sensor_data:
            return 'LOW'

        if sensor_data.get('danger_level'):
            return str(sensor_data['danger_level']).upper()

        gas = sensor_data.get('gas', sensor_data.get('gas_level', 0))
        voltage = sensor_data.get('voltage', sensor_data.get('voltage_level', 0))
        temp = sensor_data.get('temperature', sensor_data.get('temp', 0))
        humidity = sensor_data.get('humidity', 0)
        moisture = bool(sensor_data.get('moisture_alert'))
        oxygen = sensor_data.get('oxygen', sensor_data.get('oxygen_level', 21.0))

        try:
            gas = float(gas)
        except (TypeError, ValueError):
            gas = 0.0

        try:
            voltage = float(voltage)
        except (TypeError, ValueError):
            voltage = 0.0

        try:
            temp = float(temp)
        except (TypeError, ValueError):
            temp = 0.0

        try:
            humidity = float(humidity)
        except (TypeError, ValueError):
            humidity = 0.0

        try:
            oxygen = float(oxygen)
        except (TypeError, ValueError):
            oxygen = 21.0

        high_conditions = (
            gas >= 0.8,
            voltage >= 0.8,
            temp >= 80,
            humidity >= 85,
            moisture,
            oxygen < 19.5,
            oxygen > 23.5,
        )
        warning_conditions = (
            gas >= 0.4,
            voltage >= 0.4,
            temp >= 60,
            humidity >= 70,
            oxygen < 20.5,
            oxygen > 22.5,
        )

        if any(high_conditions):
            return 'HIGH'
        if any(warning_conditions):
            return 'WARNING'
        return 'LOW'