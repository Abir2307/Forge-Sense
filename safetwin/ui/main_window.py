import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QThread
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QComboBox,
    QVBoxLayout,
    QWidget,
)

import json
from pathlib import Path

from safetwin.core.QR import generate_safety_qr
from safetwin.core.risk_utils import derive_risk_level, normalize_compliance_score, zone_type_to_risk_score
from safetwin.core.signals import bus
from safetwin.core.zone_config import DEFAULT_ZONE_CONFIG_PATH, load_zone_config
from safetwin.ui.qr_popup import QrPopup


def build_zone_display_payload(zone_config: dict | None = None) -> dict:
    """Build a UI-safe payload for the dashboard from the current zone configuration."""
    config = zone_config or load_zone_config(str(DEFAULT_ZONE_CONFIG_PATH))
    zones = config.get("zones", []) or []
    payload_zones = []
    for zone in zones:
        zone_type = str(zone.get("type", "CAUTION") or "CAUTION").upper()
        payload_zones.append(
            {
                "id": zone.get("id", "zone"),
                "name": zone.get("name", "Zone"),
                "type": zone_type,
                "risk_score": _zone_type_risk_score(zone_type),
            }
        )
    return {"zones": payload_zones}


def _zone_type_risk_score(zone_type: str) -> float:
    return zone_type_to_risk_score(zone_type)
from safetwin.db.database import get_name_by_username
from safetwin.services.sensor_manager import local_sensor_manager


def build_location_risk_context(assessment: dict | None = None) -> dict:
    """Build a compact location-risk summary for the dashboard widgets."""
    assessment = assessment or {}

    explicit_level = (
        assessment.get("overall_risk_level")
        or assessment.get("risk_level")
        or assessment.get("status")
    )
    if explicit_level:
        explicit_level = str(explicit_level).upper()
    else:
        explicit_level = "READY"

    hazards = assessment.get("hazards", []) or []
    hazard_levels = [str(h.get("level", "LOW")).upper() for h in hazards if isinstance(h, dict)]
    if "CRITICAL" in hazard_levels:
        severity = "CRITICAL"
    elif "HIGH" in hazard_levels:
        severity = "HIGH"
    elif explicit_level in {"CRITICAL", "HIGH", "MEDIUM", "WARNING"}:
        severity = explicit_level
    else:
        severity = "READY"

    permit_risks = assessment.get("permit_risks", {}) or {}
    if isinstance(permit_risks, dict):
        permit_count = len(permit_risks.get("high_risk_alerts", [])) + len(permit_risks.get("warnings", []))
    else:
        permit_count = 0

    compliance_gaps = assessment.get("compliance_gaps", {}) or {}
    if isinstance(compliance_gaps, dict):
        compliance_score = normalize_compliance_score(compliance_gaps)
        overdue_checks = compliance_gaps.get("overdue_checks", 0)
    else:
        compliance_score = 0.0
        overdue_checks = 0

    incident_risks = assessment.get("incident_risks", {}) or {}
    if isinstance(incident_risks, dict):
        incident_count = incident_risks.get("total_incidents", 0)
    else:
        incident_count = 0

    summary = (
        f"Location risk: {severity} | Permits: {permit_count} | "
        f"Compliance: {float(compliance_score):.0f}% | Incidents: {incident_count}"
    )
    if overdue_checks:
        summary += f" | Overdue checks: {overdue_checks}"

    return {
        "severity": severity,
        "permit_count": permit_count,
        "compliance_score": float(compliance_score),
        "incident_count": int(incident_count),
        "summary": summary,
        "level": severity,
    }
from safetwin.services.safety_intelligence_worker import SafetyIntelligenceWorker
from safetwin.services.worker import AnalysisWorker
from safetwin.ui.heatmap_widget import HeatmapWidget
from safetwin.ui.log_popup import LogPopup
from safetwin.ui.safety_dashboard import SafetyDashboard
from safetwin.ui.video_display import VideoDisplay


class MainWindow(QMainWindow):
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        self.setWindowTitle("Forge-Sense: Industrial Safety Platform")
        self.setWindowState(Qt.WindowMaximized)

        self.safety_worker = SafetyIntelligenceWorker()
        self.log_popup = LogPopup(self)
        self.safety_dashboard = SafetyDashboard()
        self.selected_video_path = None
        self._last_assessment = {}
        self.selected_sensor_link = None
        self.analysis_worker = None
        self.analysis_thread = None

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        self.container = QWidget()
        self.main_layout = QVBoxLayout(self.container)

        self.navbar = self.create_navbar()
        self.main_layout.addWidget(self.navbar)

        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)

        self.control_panel = self.create_control_panel()
        self.grid.addWidget(self.control_panel, 0, 0)
        self.grid.addWidget(self.safety_dashboard, 0, 1)

        self.video_display = VideoDisplay(title="Main Content Area")
        self.grid.addWidget(self.video_display, 1, 0)

        self.heatmap_widget = HeatmapWidget(title="Heatmap")
        self.grid.addWidget(self.heatmap_widget, 1, 1)

        self.grid.setRowStretch(0, 1)
        self.grid.setRowStretch(1, 2)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

        self.main_layout.addLayout(self.grid, stretch=1)
        self.setCentralWidget(self.container)
        self.apply_styles()

    def create_control_panel(self):
        frame = QFrame()
        frame.setObjectName("controlPanel")
        layout = QVBoxLayout(frame)

        title = QLabel("Operational Controls")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        self.btn_upload = QPushButton("Upload Video")
        self.btn_sensor_link = QPushButton("Upload Sensor Link")
        self.btn_inject_hazard = QPushButton("Inject Environmental Hazard")
        self.btn_define_zone = QPushButton("Define Zone Type")
        self.btn_show_qr = QPushButton("Show QR Status")
        self.btn_reset = QPushButton("Reset System")
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Perspective", "Top-Down"])
        self.view_mode_combo.setCurrentText("Perspective")
        self.compliance_query_input = QLineEdit()
        self.compliance_query_input.setPlaceholderText("Ask Compliance: Factory Act, OISD, permits, inspections...")
        self.btn_ask_compliance = QPushButton("Ask Compliance")

        button_row = QHBoxLayout()
        button_row.addWidget(self.btn_upload)
        button_row.addWidget(self.btn_sensor_link)
        button_row.addWidget(self.btn_inject_hazard)
        button_row.addWidget(self.btn_define_zone)
        button_row.addWidget(self.btn_reset)
        layout.addLayout(button_row)

        qr_row = QHBoxLayout()
        qr_row.addWidget(self.btn_show_qr)
        qr_row.addStretch()
        layout.addLayout(qr_row)
        cam_label = QLabel("Camera / View Mode")
        cam_label.setStyleSheet("color: white; font-weight: 600;")
        layout.addWidget(cam_label)
        self.view_mode_combo.setStyleSheet("""QComboBox { color: white; background-color: transparent; }
        QComboBox QAbstractItemView { background-color: #2b2b2b; color: white; selection-background-color: #444444; }
        """)
        layout.addWidget(self.view_mode_combo)
        layout.addWidget(self.compliance_query_input)
        layout.addWidget(self.btn_ask_compliance)
        layout.addStretch()
        return frame

    def create_navbar(self):
        navbar = QFrame()
        navbar.setObjectName("navbar")
        layout = QHBoxLayout(navbar)
        full_name = get_name_by_username(self.username) if self.username else "System"

        self.status_label = QLabel(f"Operator: {full_name} | Status: Ready")
        self.status_label.setStyleSheet("color: white;")
        self.help_btn = QPushButton("Help")
        self.logout_btn = QPushButton("Logout")

        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.help_btn)
        layout.addWidget(self.logout_btn)
        return navbar

    def connect_signals(self):
        bus.risk_updated.connect(self.on_intelligent_update)
        bus.hazard_detected.connect(self.on_hazard_received)
        bus.RISK_UPDATE.connect(self.on_analysis_update)

        self.safety_dashboard.btn_start_monitoring.clicked.connect(self.start_analysis)
        self.safety_dashboard.btn_stop_monitoring.clicked.connect(self.stop_analysis)
        self.safety_dashboard.btn_run_audit.clicked.connect(
            lambda: self.safety_worker.conduct_audit(
                ["gas_detector_calibration", "fire_extinguisher"], self.username or "Admin"
            )
        )

        self.btn_upload.clicked.connect(self.upload_video)
        self.btn_sensor_link.clicked.connect(self.upload_sensor_link)
        self.btn_inject_hazard.clicked.connect(self.inject_environmental_hazard)
        self.btn_define_zone.clicked.connect(self.define_zone_type)
        self.btn_show_qr.clicked.connect(self.show_live_qr)
        self.view_mode_combo.currentTextChanged.connect(self.on_view_mode_changed)
        self.btn_reset.clicked.connect(self.reset_ui)
        self.btn_ask_compliance.clicked.connect(self.ask_compliance)
        self.logout_btn.clicked.connect(self.logout)
        self.help_btn.clicked.connect(self.open_manual)

        self.safety_worker.risk_assessment_updated.connect(self.on_intelligent_update)
        self.safety_worker.permit_alert.connect(self.on_permit_alert)
        self.safety_worker.incident_alert.connect(self.on_incident_alert)
        self.safety_worker.compliance_status_updated.connect(self.on_compliance_status_updated)
        self.safety_worker.log_message.connect(self._on_safety_log)

    def on_view_mode_changed(self, value):
        mode = "perspective" if str(value).lower() == "perspective" else "top_down"
        if self.analysis_worker and self.analysis_worker.engine:
            self.analysis_worker.engine.set_view_mode(mode)
        self.log_popup.append_log(f"View mode set to {mode}")

    def upload_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv)",
        )

        if file_path:
            self.selected_video_path = file_path
            self.selected_sensor_link = None
            if self.analysis_thread and self._thread_is_running(self.analysis_thread):
                self.stop_analysis()
            self.video_display.set_source(file_path)
            self.log_popup.append_log(f"Loading video: {Path(file_path).name}")
            self.log_popup.append_log(f"Selected video stored for analysis: {file_path}")
            self.start_analysis()

    def upload_sensor_link(self):
        link, accepted = QInputDialog.getText(
            self,
            "Upload Sensor Link",
            "Enter RTSP / HTTP / camera stream link:",
        )

        if not accepted:
            return

        link = link.strip()
        if not link:
            self.log_popup.append_log("Sensor link was empty.")
            return

        self.selected_sensor_link = link
        self.selected_video_path = None
        if self.analysis_thread and self._thread_is_running(self.analysis_thread):
            self.stop_analysis()
        self.video_display.set_source(link)
        self.log_popup.append_log(f"Selected sensor link stored for analysis: {link}")
        self.start_analysis()

    def inject_environmental_hazard(self):
        hazard_payload = {'gas': 100.0, 'temp': 90.0}
        local_sensor_manager.inject_hazard(hazard_payload['gas'], hazard_payload['temp'])
        bus.FORCE_SENSOR_STATE.emit(hazard_payload)
        self.log_popup.append_log("Environmental hazard injected: sensor state override active.")
        if not self.analysis_worker or not self._thread_is_running(self.analysis_thread):
            self.log_popup.append_log("Start analysis to apply the injected hazard state to the video stream.")

    def define_zone_type(self):
        config = load_zone_config(str(DEFAULT_ZONE_CONFIG_PATH))
        zones = config.get("zones", [])
        if not zones:
            QMessageBox.information(self, "Zone Definition", "No zones are configured yet.")
            return

        zone_names = [f"{zone.get('id', 'zone')} - {zone.get('name', 'Zone')}" for zone in zones]
        selected, ok = QInputDialog.getItem(
            self,
            "Define Zone Type",
            "Select a zone to assign",
            zone_names,
            0,
            False,
        )
        if not ok or not selected:
            return

        zone_index = zone_names.index(selected)
        zone = zones[zone_index]
        zone_types = ["SAFE", "CAUTION", "WARNING", "DANGEROUS", "RESTRICTED", "MAINTENANCE", "CRITICAL", "CONFINED_SPACE", "CHEMICAL", "HOT_WORK", "ELECTRICAL"]
        zone_type, accepted = QInputDialog.getItem(
            self,
            "Define Zone Type",
            "Choose the zone type",
            zone_types,
            zone_types.index(str(zone.get("type", "CAUTION")).upper()) if str(zone.get("type", "CAUTION")).upper() in zone_types else 0,
            False,
        )
        if not accepted:
            return

        zone["type"] = zone_type
        config_path = DEFAULT_ZONE_CONFIG_PATH
        config_path.write_text(json.dumps({"view_mode": config.get("view_mode", "perspective"), "zones": zones}, indent=2), encoding="utf-8")

        if self.analysis_worker and getattr(self.analysis_worker, "engine", None) is not None:
            self.analysis_worker.engine.zone_config = {"view_mode": config.get("view_mode", "perspective"), "zones": zones}
            self.analysis_worker.engine.set_view_mode(config.get("view_mode", "perspective"))

        payload = build_zone_display_payload({"view_mode": config.get("view_mode", "perspective"), "zones": zones})
        self.heatmap_widget.update_heatmap(payload)
        self.safety_dashboard.zone_stats_model.record_frame(payload, [])
        self.log_popup.append_log(f"Zone {zone.get('id')} updated to type {zone_type}.")

    def ask_compliance(self):
        query = self.compliance_query_input.text().strip()
        if not query:
            QMessageBox.information(self, "Ask Compliance", "Enter a compliance question first.")
            return

        try:
            agent = self.safety_worker.platform.compliance_agent
            response = agent.answer_query(query)
        except Exception as error:
            response = f"Compliance lookup failed: {error}"

        QMessageBox.information(self, "Compliance Answer", response)

    def show_live_qr(self):
        assessment = self._last_assessment or {}
        context = build_location_risk_context(assessment)
        severity = context.get("severity", "READY")

        alerts = assessment.get("critical_alerts", []) or []
        hazards = assessment.get("hazards", []) or []
        hazard_entries = []
        for alert in alerts:
            if isinstance(alert, dict):
                zone_id = alert.get("zone_id") or alert.get("location") or alert.get("type") or "UNKNOWN"
                level = str(alert.get("severity") or alert.get("level") or severity).upper()
                hazard_entries.append({
                    "lat": 0.0,
                    "lon": 0.0,
                    "level": level,
                    "zone_id": zone_id,
                    "alert_type": alert.get("type") or "ALERT",
                    "description": alert.get("reason") or alert.get("description") or "Safety alert",
                })

        for hazard in hazards:
            if isinstance(hazard, dict):
                zone_id = hazard.get("zone_id") or hazard.get("location") or "UNKNOWN"
                level = str(hazard.get("level") or severity).upper()
                hazard_entries.append({
                    "lat": 0.0,
                    "lon": 0.0,
                    "level": level,
                    "zone_id": zone_id,
                    "alert_type": hazard.get("type") or "HAZARD",
                    "description": hazard.get("description") or hazard.get("reason") or "Observed hazard",
                })

        if not hazard_entries:
            hazard_entries.append({"lat": 0.0, "lon": 0.0, "level": severity, "zone_id": assessment.get("location", "SITE"), "alert_type": "SITE_STATUS", "description": "No active alerts"})

        qr_payload = hazard_entries
        temp_path = Path(tempfile.gettempdir()) / f"forge_sense_{severity.lower()}.png"
        max_entries_per_qr = 6
        try:
            result = generate_safety_qr(qr_payload, str(temp_path), max_entries_per_qr=max_entries_per_qr)
            # `generate_safety_qr` now returns a list of produced image paths
            image_paths = []
            if isinstance(result, (list, tuple)):
                image_paths = [p for p in result if Path(p).exists()]
            elif isinstance(result, str):
                image_paths = [str(temp_path)] if temp_path.exists() else []

            if image_paths:
                popup = QrPopup(image_paths, self)
                popup.exec()
            else:
                QMessageBox.information(self, "QR Status", "QR image could not be created. Please try again after monitoring data is available.")
                self.log_popup.append_log("Unable to generate QR image for the current risk context.")
                return
            # If multiple images were produced, inform the user (pagination)
            if len(image_paths) > 1:
                QMessageBox.information(self, "QR Status", f"Generated {len(image_paths)} QR images to cover the payload. Use the arrows to navigate or Save to export individual codes.")
        except Exception as error:
            err_str = str(error)
            # Provide a clearer, actionable message for QR size/version errors
            if 'version' in err_str.lower() or 'invalid version' in err_str.lower():
                user_msg = (
                    "QR generation failed because the data is too large for a single QR code. "
                    "The app has attempted to create multiple QR images (pagination). "
                    "If that failed, try reducing hazard entries or export the hazard report to a file."
                )
            else:
                user_msg = f"QR generation failed: {err_str}"

            QMessageBox.warning(self, "QR Status", user_msg)
            # Keep full error for logs / debugging
            self.log_popup.append_log(f"QR generation failed: {err_str}")

    def start_analysis(self):
        if self.analysis_thread and self._thread_is_running(self.analysis_thread):
            self.log_popup.append_log("Analysis is already running.")
            return

        source = self.selected_sensor_link or self.selected_video_path or 0
        if source is not None:
            # Stop the preview reader so analysis can present annotated frames
            self.video_display.stop()

        self.analysis_worker = AnalysisWorker(source=source)
        selected_mode = "perspective" if self.view_mode_combo.currentText().lower() == "perspective" else "top_down"
        self.analysis_worker.engine.set_view_mode(selected_mode)
        self.analysis_thread = QThread(self)
        self.analysis_worker.moveToThread(self.analysis_thread)

        self.analysis_thread.started.connect(self.analysis_worker.run)
        self.analysis_worker.log.connect(self.log_popup.append_log)
        self.analysis_worker.finished.connect(self.analysis_thread.quit)
        self.analysis_worker.stopped.connect(self.analysis_thread.quit)
        self.analysis_thread.finished.connect(self.analysis_worker.deleteLater)
        self.analysis_thread.finished.connect(self.analysis_thread.deleteLater)

        # Start the safety monitoring in parallel
        self.safety_worker.start_monitoring(location="MainFactory", monitoring_interval_ms=3000)
        
        # Connect hazard data from video worker to safety worker for real-time risk calculation
        def pass_hazards_to_safety_worker(payload):
            hazards = payload.get('hazards', [])
            self.safety_worker.update_frame_hazards(hazards)
        self.analysis_worker.risk_update.connect(pass_hazards_to_safety_worker)
        
        self.analysis_thread.start()
        self.log_popup.append_log(f"Analysis started with source: {source}")

    def _thread_is_running(self, thread_obj):
        """Safely check if a QThread is running, handling deleted C++ objects."""
        if thread_obj is None:
            return False

        if isinstance(thread_obj, QThread):
            try:
                return bool(thread_obj.isRunning())
            except RuntimeError:
                return False

        if hasattr(thread_obj, "isRunning") and callable(getattr(thread_obj, "isRunning")):
            try:
                return bool(thread_obj.isRunning())
            except RuntimeError:
                return False

        return False

    def stop_analysis(self):
        if self.analysis_worker and hasattr(self.analysis_worker, "stop_flag"):
            try:
                self.analysis_worker.stop_flag["stop"] = True
            except Exception:
                pass

        # Attempt to gracefully quit the thread if it's still alive
        if getattr(self, "analysis_thread", None):
            try:
                if self._thread_is_running(self.analysis_thread):
                    self.analysis_thread.quit()
                    self.analysis_thread.wait(1500)
            except RuntimeError:
                pass
            finally:
                try:
                    self.analysis_thread.deleteLater()
                except Exception:
                    pass
                self.analysis_thread = None

        # Stop the safety monitoring worker
        if self.safety_worker and self.safety_worker.monitoring_active:
            self.safety_worker.stop_monitoring()

        self.video_display.stop()

    def _derive_status_level(self, payload_or_assessment):
        if not isinstance(payload_or_assessment, dict):
            return "READY"
        return derive_risk_level(payload_or_assessment)

    def _update_status_display(self, level: str, event_data=None):
        normalized_level = str(level or "LOW").upper()
        if normalized_level == "CRITICAL":
            self.safety_dashboard.set_emergency_mode(color="red", event_data=event_data)
            self.status_label.setText(
                f"Operator: {get_name_by_username(self.username) if self.username else 'System'} | Status: CRITICAL"
            )
            self.status_label.setStyleSheet(
                "color: white; background-color: #F44336; padding: 6px 10px; border-radius: 4px;"
            )
        elif normalized_level in {"HIGH", "MEDIUM", "WARNING"}:
            self.safety_dashboard.set_emergency_mode(color="yellow", event_data=event_data)
            self.status_label.setText(
                f"Operator: {get_name_by_username(self.username) if self.username else 'System'} | Status: WARNING"
            )
            self.status_label.setStyleSheet(
                "color: black; background-color: #FFC107; padding: 6px 10px; border-radius: 4px;"
            )
        else:
            self.safety_dashboard.set_emergency_mode(color="green", event_data=event_data)
            self.status_label.setText(
                f"Operator: {get_name_by_username(self.username) if self.username else 'System'} | Status: READY"
            )
            self.status_label.setStyleSheet(
                "color: white; background-color: #4CAF50; padding: 6px 10px; border-radius: 4px;"
            )

    def on_analysis_update(self, payload: dict):
        zone_model = self.safety_dashboard.zone_stats_model
        zone_model.record_frame(payload.get("zone_map"), payload.get("hotspots", []))

        base_assessment = dict(self._last_assessment or {})
        merged_payload = {**base_assessment, **payload}
        self._last_assessment = merged_payload

        self._update_status_display(self._derive_status_level(merged_payload), merged_payload)
        self.safety_dashboard.update_all_data(merged_payload)
        # Show annotated frame from analysis if provided
        frame = payload.get('frame')
        if frame is not None:
            try:
                self.video_display.show_frame(frame)
            except Exception as e:
                self.log_popup.append_log(f"Failed to display annotated frame: {e}")

    def on_intelligent_update(self, assessment):
        self._last_assessment = assessment or {}
        score = assessment.get("risk_score", 0.0)
        self._update_status_display(self._derive_status_level(assessment), assessment)
        self.safety_dashboard.update_all_data(assessment)

    def on_hazard_received(self, event_type, hazard_data):
        print(f"[MainWindow] hazard signal received: {event_type} -> {hazard_data}")
        location = hazard_data.get("location", "Unknown location")
        frame_id = hazard_data.get("frame_id", "N/A")
        zone_count = len(hazard_data.get("danger_zones", []))
        level = str(hazard_data.get("level", "LOW")).upper()
        self.log_popup.append_log(
            f"{event_type}: frame {frame_id} reported {zone_count} hazard zone(s) at {location} [{level}]",
            color="#ff4444",
        )
        self._update_status_display(level, hazard_data)
        self.log_popup.trigger_alert_flash()

    def on_permit_alert(self, alert: dict):
        """Handle permit conflict/alert from safety worker."""
        alert_type = alert.get('type', 'PERMIT_WARNING')
        description = alert.get('description', 'Permit conflict detected')
        severity = alert.get('severity', 'WARNING')
        
        log_color = '#ff4444' if severity == 'CRITICAL' else '#ffaa00'
        self.log_popup.append_log(f"⚠️ {alert_type}: {description}", color=log_color)
        
        # Update permits tab if available
        if hasattr(self.safety_dashboard, 'update_permits_data'):
            self.safety_dashboard.update_permits_data(alert)

    def on_incident_alert(self, alert: dict):
        """Handle incident analysis alert from safety worker."""
        incident_type = alert.get('type', 'INCIDENT_WARNING')
        probability = alert.get('probability', 0.0)
        actions = alert.get('actions', [])
        
        msg = f"🔔 {incident_type}: Escalation probability {probability:.1%}"
        self.log_popup.append_log(msg, color='#ff8800')
        
        for action in actions:
            self.log_popup.append_log(f"   → {action}", color='#ffaa00')
    
    def on_compliance_status_updated(self, compliance_data: dict):
        """Handle compliance audit results from safety worker."""
        audit_id = compliance_data.get('audit_id', 'audit')
        violations = compliance_data.get('violations', [])
        status = compliance_data.get('status', 'UNKNOWN')
        
        msg = f"✓ Compliance audit {audit_id}: {status} ({len(violations)} issue(s))"
        log_color = '#ff4444' if violations else '#44ff44'
        self.log_popup.append_log(msg, color=log_color)
        
        if hasattr(self.safety_dashboard, 'update_compliance_data'):
            self.safety_dashboard.update_compliance_data(compliance_data)

    def reset_ui(self):
        self.stop_analysis()
        self.safety_worker.stop_monitoring()
        self.safety_worker.update_frame_hazards([])
        self.safety_worker.sensor_data = {}
        self._last_assessment = {}
        self.selected_sensor_link = None
        self.selected_video_path = None
        self.video_display.clear()
        self.heatmap_widget.clear()
        self.safety_dashboard.reset_view()
        self._update_status_display("READY", {})
        self.log_popup.append_log("System reset: Monitoring stopped and dashboard cleared.")

    def _on_safety_log(self, message: str):
        self.log_popup.append_log(message)

    def logout(self):
        try:
            from safetwin.auth.ui.login import LoginWindow

            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()
        except ImportError:
            self.close()

    def open_manual(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile("assets/manual.pdf"))

    def apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #d7e8f6;
            }
            #navbar, #controlPanel, QWidget#controlPanel {
                background-color: #0f3557;
                border: 1px solid #24496d;
                border-radius: 6px;
                padding: 8px;
            }
            QLabel {
                font-size: 14px;
                color: #0f172a;
            }
            QPushButton {
                background-color: #0f3f72;
                color: white;
                border-radius: 6px;
                padding: 8px 14px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #145a9e;
            }
            QTableView {
                background-color: white;
                alternate-background-color: #eef6fb;
                gridline-color: #c7d2fe;
            }
            """
        )

    def closeEvent(self, event):
        self.safety_worker.stop_monitoring()
        self.stop_analysis()
        if getattr(self, "analysis_thread", None) and self._thread_is_running(self.analysis_thread):
            try:
                self.analysis_thread.quit()
                self.analysis_thread.wait()
            except RuntimeError:
                pass
        event.accept()
