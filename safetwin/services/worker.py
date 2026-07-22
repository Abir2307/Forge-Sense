from PySide6.QtCore import QObject, Signal
import cv2

from safetwin.core.main import SafetyEngine, get_sensor_data
from safetwin.core.signals import bus
from safetwin.model.model import get_runtime_model


class AnalysisWorker(QObject):
    log = Signal(str)
    clear_log = Signal()
    risk_update = Signal(dict)
    finished = Signal()
    stopped = Signal()

    def __init__(self, source=0, stop_flag=None, engine=None):
        super().__init__()
        self.source = source
        self.stop_flag = stop_flag if stop_flag is not None else {"stop": False}
        self.engine = engine or SafetyEngine(output_dir=None, parent=self)
        self.model = get_runtime_model()

    def _resolve_source(self):
        """Normalize webcam indices, file paths, and stream URLs for OpenCV."""
        if isinstance(self.source, int):
            return self.source

        if isinstance(self.source, str):
            stripped = self.source.strip()
            if stripped.isdigit():
                return int(stripped)
            return stripped

        return self.source

    def run(self):
        self.log.emit("Starting real-time analysis...")
        capture = cv2.VideoCapture(self._resolve_source())
        frame_id = 0
        stopped_by_request = False

        try:
            if not capture.isOpened():
                raise RuntimeError(f"Could not open video source: {self.source}")

            while True:
                if self.stop_flag.get("stop", False):
                    stopped_by_request = True
                    break

                ret, frame = capture.read()
                if not ret:
                    self.log.emit("Video stream ended or frame capture failed.")
                    break

                frame_id += 1

                sensor_data = None
                try:
                    sensor_data = get_sensor_data()
                except Exception as sensor_error:
                    self.log.emit(f"Sensor read failed: {sensor_error}")

                frame_output = self.engine.process_frame(
                    frame=frame,
                    frame_id=frame_id,
                    sensor_data=sensor_data,
                )

                danger_zones = [tuple(zone) for zone in frame_output.get('danger_zones', [])]
                zone_map = frame_output.get('zone_map')

                # Derive hotspots from hazard events (support perspective zone_id and legacy grid hotspots)
                hazards = frame_output.get('hazards', []) or []
                hotspots = []
                for h in hazards:
                    if isinstance(h, dict):
                        entry = {
                            'level': h.get('level', 'LOW'),
                            'score': h.get('score', 0.0),
                        }
                        if 'zone_id' in h and h['zone_id'] is not None:
                            entry['zone_id'] = str(h['zone_id'])
                            hotspots.append(entry)
                        elif 'zone_index' in h:
                            zi = h['zone_index']
                            if isinstance(zi, dict):
                                entry['by'] = zi.get('by', zi.get('row', 0))
                                entry['bx'] = zi.get('bx', zi.get('column', 0))
                            elif isinstance(zi, (tuple, list)) and len(zi) >= 2:
                                entry['by'] = int(zi[0])
                                entry['bx'] = int(zi[1])
                            hotspots.append(entry)

                # Update safety worker with latest frame hazards for real-time risk calculation
                from safetwin.services.safety_intelligence_worker import SafetyIntelligenceWorker
                # Find the safety worker instance - it should be running in parallel
                # Note: This is passed through a global or can be connected via signal
                # For now, we store it for the monitoring loop to pick up

                update_payload = {
                    **frame_output,
                    'frame_id': frame_id,
                    'source': self.source,
                    'hotspots': hotspots,
                    'sensor_data': sensor_data or {},
                }

                self.risk_update.emit(update_payload)
                bus.RISK_UPDATE.emit(update_payload)

                if frame_output.get('event_type') == 'CRITICAL_COMPOUND_RISK':
                    self.log.emit("Critical compound risk observed in worker stream.")

            if stopped_by_request:
                self.stopped.emit()
            else:
                self.finished.emit()

        except Exception as error:
            self.log.emit(f"ERROR: {error}")
            import traceback

            self.log.emit(traceback.format_exc())
            if self.stop_flag.get("stop", False):
                self.stopped.emit()
            else:
                self.finished.emit()

        finally:
            capture.release()
                
