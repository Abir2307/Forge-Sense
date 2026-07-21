import cv2
import numpy as np
from PySide6.QtCore import QObject, QTimer
from safetwin.core.blocks_analysis import analyze_blocks
from safetwin.core.signals import bus
from safetwin.core.zone_config import load_zone_config, normalize_polygon, point_in_polygon, resolve_zone_type_for_point
from safetwin.model.model import get_runtime_model
from safetwin.services.safety_orchestrator import CompoundRiskEngine, HazardLogic
from safetwin.services.state_manager import SafetyStateManager
from safetwin.services.sensor_manager import local_sensor_manager

class SafetyEngine(QObject):
    def __init__(self, output_dir, block_size=30, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.risk_engine = CompoundRiskEngine(block_size=block_size)
        self.hazard_logic = HazardLogic()
        self.block_size = block_size
        self.state_manager = SafetyStateManager()
        self.model = get_runtime_model()
        self.last_detections = []
        self.view_mode = "perspective"
        self.zone_config = load_zone_config()
        self.local_sensor_manager = local_sensor_manager
        self.override_mode_active = False
        self.override_timer = QTimer(self)
        self.override_timer.setSingleShot(True)
        self.override_timer.timeout.connect(self._clear_override_mode)
        bus.FORCE_SENSOR_STATE.connect(self._handle_force_sensor_state)

    def run_yolo(self, frame):
        """Run YOLO inference and return a clean list of detections."""
        results = self.model(frame, verbose=False)
        detections = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
                class_id = int(box.cls[0].cpu().numpy())
                class_name = self.model.names.get(class_id, str(class_id))
                detections.append({
                    'box': (float(x1), float(y1), float(x2), float(y2)),
                    'class_id': class_id,
                    'class_name': class_name,
                })

        return detections

    def process_frame(self, frame, frame_id, sensor_data=None):
        detections = self.run_yolo(frame)
        self.last_detections = detections

        if sensor_data is None:
            sensor_data = self.local_sensor_manager.get_latest()

        frame_for_display = frame.copy()
        zone_map = None
        danger_zones = []
        hazard_events = []

        if self.view_mode == "top_down":
            grayscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            feature_density = grayscale_frame.astype(np.float32) / 255.0
            stats = analyze_blocks(feature_density, self.block_size)
            mean_map = stats['mean']
            frame_h, frame_w = frame.shape[:2]

            target_h, target_w = 3, 3
            zone_entries = []
            for i in range(target_h):
                y0 = int((i * frame_h) / target_h)
                y1 = int(((i + 1) * frame_h) / target_h)
                for j in range(target_w):
                    x0 = int((j * frame_w) / target_w)
                    x1 = int(((j + 1) * frame_w) / target_w)

                    block = mean_map[
                        int((y0 * mean_map.shape[0]) / frame_h):int((y1 * mean_map.shape[0]) / frame_h),
                        int((x0 * mean_map.shape[1]) / frame_w):int((x1 * mean_map.shape[1]) / frame_w),
                    ]
                    valid = block[~np.isnan(block)] if block.size else np.array([])
                    score = float(np.mean(valid)) if valid.size > 0 else 0.0
                    zone_type = 'CAUTION'
                    if score >= 0.75:
                        zone_type = 'DANGEROUS'
                    elif score >= 0.45:
                        zone_type = 'WARNING'

                    base_score = float(np.clip(score, 0.0, 1.0))
                    zone_entries.append({
                        'id': f'topdown_{i}_{j}',
                        'name': f'TopDown {i+1}-{j+1}',
                        'type': zone_type,
                        'risk_score': base_score,
                    })

            zone_lookup = {entry['id']: entry for entry in zone_entries}

            for detection in detections:
                x1, y1, x2, y2 = detection['box']
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                by = min(target_h - 1, int(center_y * target_h / frame_h))
                bx = min(target_w - 1, int(center_x * target_w / frame_w))
                zone_id = f'topdown_{by}_{bx}'
                zone_entry = zone_lookup.get(zone_id)
                zone_type = zone_entry['type'] if zone_entry else 'CAUTION'

                worker_detected = str(detection.get('class_name', '')).lower() in {'person', 'worker', 'human'}
                machine_detected = str(detection.get('class_name', '')).lower() in {'machine', 'machinery', 'forklift', 'vehicle', 'equipment'}

                hazard_result = self.hazard_logic.calculate_hazard_level(worker_detected, zone_type, sensor_data or {})
                hazard_result['detection'] = detection
                hazard_result['zone_index'] = {'by': int(by), 'bx': int(bx)}
                hazard_result['zone_type'] = zone_type
                
                # Apply override logic if environmental hazard is injected
                if self.override_mode_active:
                    self._handle_override_logic(zone_type, worker_detected, machine_detected, hazard_result, detection, by, bx, sensor_data)
                
                hazard_events.append(hazard_result)

                if zone_entry is not None:
                    adjustment = 0.0
                    level = hazard_result.get('level', '').upper()
                    if level == 'CRITICAL':
                        adjustment = 0.30
                    elif level == 'WARNING':
                        adjustment = 0.15
                    elif level == 'CAUTION':
                        adjustment = 0.08
                    zone_entry['risk_score'] = min(1.0, zone_entry.get('risk_score', 0.0) + adjustment)

                try:
                    self._annotate_detection(frame_for_display, detection, hazard_result)
                except Exception:
                    pass

                if hazard_result.get('level') == 'CRITICAL':
                    bus.hazard_detected.emit('CRITICAL_COMPOUND_RISK', hazard_result)

            risk_map = self.risk_engine.calculate_risk(frame.shape, detections, sensor_data)
            danger_zones = self.risk_engine.analyze_safety_zones(risk_map)
            for (by, bx) in danger_zones:
                y1 = by * self.block_size
                x1 = bx * self.block_size
                cv2.rectangle(frame_for_display, (x1, y1), (x1 + self.block_size, y1 + self.block_size), (0, 0, 255), 2)

            zone_map = {'zones': zone_entries}

        else:
            zone_map = []
            zones = self.zone_config.get('zones', [])
            height, width = frame.shape[:2]
            for zone in zones:
                polygon = normalize_polygon(zone.get('polygon', []), width, height)
                zone_map.append({
                    'id': zone.get('id', 'zone'),
                    'name': zone.get('name', 'Zone'),
                    'type': zone.get('type', 'CAUTION'),
                    'polygon': polygon,
                    'risk_score': self._zone_type_risk_score(zone.get('type', 'CAUTION')),
                })

            zone_lookup = {zone['id']: zone for zone in zone_map}

            for detection in detections:
                x1, y1, x2, y2 = detection['box']
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                matched_zone = None
                for zone in zone_map:
                    if point_in_polygon((center_x, center_y), zone['polygon']):
                        matched_zone = zone
                        break

                zone_type = matched_zone['type'] if matched_zone else 'CAUTION'
                if matched_zone is None:
                    zone_type = resolve_zone_type_for_point((center_x, center_y), self.zone_config.get('zones', []))
                worker_detected = str(detection.get('class_name', '')).lower() in {'person', 'worker', 'human'}
                machine_detected = str(detection.get('class_name', '')).lower() in {'machine', 'machinery', 'forklift', 'vehicle', 'equipment'}
                # Sanitize crowding fields out when using perspective view
                sensor_for_logic = dict(sensor_data or {})
                if self.view_mode == 'perspective':
                    sensor_for_logic.pop('crowd_count', None)
                    sensor_for_logic.pop('crowd', None)

                hazard_result = self.hazard_logic.calculate_hazard_level(worker_detected, zone_type, sensor_for_logic)
                hazard_result['detection'] = detection
                hazard_result['zone_type'] = zone_type
                hazard_result['zone_id'] = matched_zone['id'] if matched_zone else None
                
                # Apply override logic if environmental hazard is injected
                if self.override_mode_active:
                    self._handle_override_logic(zone_type, worker_detected, machine_detected, hazard_result, detection, center_x, center_y, sensor_for_logic)
                
                hazard_events.append(hazard_result)

                if matched_zone is not None:
                    matched_zone['risk_score'] = min(
                        1.0,
                        matched_zone.get('risk_score', 0.0) + self._zone_risk_adjustment(hazard_result)
                    )

                if hazard_result.get('level') == 'CRITICAL':
                    bus.hazard_detected.emit('CRITICAL_COMPOUND_RISK', hazard_result)

                self._annotate_detection(frame_for_display, detection, hazard_result)

            for zone in zone_map:
                polygon = np.array(zone['polygon'], dtype=np.int32)
                cv2.polylines(frame_for_display, [polygon], isClosed=True, color=(0, 255, 255), thickness=2)
                cv2.putText(frame_for_display, zone['id'], (int(polygon[0][0]), int(polygon[0][1])), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        self.state_manager.update_state(danger_zones, sensor_data)

        # For perspective mode wrap zone_map into a stable dict shape expected by the UI
        if self.view_mode == 'perspective' and isinstance(zone_map, list):
            zone_map_out = {'zones': zone_map}
        else:
            zone_map_out = zone_map

        return {
            'frame': frame_for_display,
            'frame_id': frame_id,
            'detections': detections,
            'danger_zones': danger_zones,
            'zone_map': zone_map_out,
            'hazards': hazard_events,
            'view_mode': self.view_mode,
            'sensor_data': sensor_data or {},
        }

    def _annotate_detection(self, frame, detection, hazard_result):
        x1, y1, x2, y2 = [int(value) for value in detection['box']]
        color = (0, 255, 0)
        if hazard_result.get('level') in {'MEDIUM', 'CRITICAL'}:
            color = (0, 0, 255)
        elif hazard_result.get('level') == 'LOW':
            color = (0, 255, 0)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{detection.get('class_name', 'object')} | {hazard_result.get('level', 'LOW')}"
        cv2.putText(frame, label, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def set_view_mode(self, view_mode):
        normalized = str(view_mode).lower()
        if normalized not in {"top_down", "perspective"}:
            raise ValueError(f"Unsupported view mode: {view_mode}")
        self.view_mode = normalized
        self.zone_config = load_zone_config()

    def _handle_force_sensor_state(self, payload: dict):
        gas_val = payload.get('gas', 0.0)
        temp_val = payload.get('temp', 25.0)
        self.local_sensor_manager.inject_hazard(gas_val, temp_val)
        self.override_mode_active = True
        self.override_timer.start(10_000)

    def _clear_override_mode(self):
        self.override_mode_active = False
        self.local_sensor_manager.restore_state()

    def _zone_type_risk_score(self, zone_type: str) -> float:
        mapping = {
            'SAFE': 0.05,
            'CAUTION': 0.20,
            'MAINTENANCE': 0.25,
            'RESTRICTED': 0.50,
            'WARNING': 0.60,
            'DANGEROUS': 0.95,
            'CRITICAL': 1.00,
            'DANGER': 0.95,
            'UNDEFINED': 0.35,
        }
        return float(np.clip(mapping.get(str(zone_type).upper(), 0.35), 0.0, 1.0))

    def _zone_risk_adjustment(self, hazard_result: dict) -> float:
        level = str(hazard_result.get('level', '')).upper()
        if level == 'CRITICAL':
            return 0.30
        if level == 'HIGH':
            return 0.20
        if level == 'WARNING':
            return 0.12
        if level == 'CAUTION':
            return 0.08
        return 0.04

    def _handle_override_logic(self, zone_type, worker_detected, machine_detected, hazard_result, detection, coord_x, coord_y, sensor_data):
        """Apply injected environmental hazard override to escalate risk immediately."""
        if not self.override_mode_active:
            return False

        hazard_result['override_mode'] = True
        target_zone = str(zone_type).upper() not in {'SAFE', 'CAUTION', 'MAINTENANCE'}
        entity_present = worker_detected or machine_detected

        # If any entity is in any zone during override, escalate
        if entity_present:
            hazard_result['level'] = 'CRITICAL'
            hazard_result['reason'] = f'🚨 OVERRIDE: {detection.get("class_name", "entity")} detected during environmental hazard injection in {zone_type}'
            hazard_result['action'] = 'TRIGGER_EMERGENCY_SHUTDOWN'
            hazard_result['sensor_data'] = sensor_data
            return True
        
        # Even without entity, mark the zone as high risk during override
        if target_zone:
            hazard_result['level'] = 'HIGH'
            hazard_result['reason'] = f'⚠️ OVERRIDE: Environmental hazard active in sensitive zone {zone_type}'
            hazard_result['score'] = 0.85

        return False

def get_sensor_data():
    return local_sensor_manager.get_latest()
def main(source=0):
    print("Initializing Industrial Safety System...")
    engine = SafetyEngine(output_dir="output_safety")
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print("Error: Could not open video source.")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            sensor_data = get_sensor_data()
            
            processed_frame, _ = engine.process_frame(
                frame, 
                frame_id=int(cap.get(cv2.CAP_PROP_POS_FRAMES)), 
                sensor_data=sensor_data
            )
            
            # Display current state status in window title
            state = engine.state_manager.get_current_state()
            cv2.putText(processed_frame, f"Status: {state['status']}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow("Industrial Safety Twin", processed_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            
    except KeyboardInterrupt:
        print("System shutdown.")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()