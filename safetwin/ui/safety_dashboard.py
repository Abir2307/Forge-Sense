"""
SafeTwin - Safety Dashboard UI Component
Displays real-time risk assessment, permits, compliance, and incidents
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QProgressBar, QScrollArea, QGridLayout, QTableView, QHeaderView
)
from PySide6.QtCore import Qt, QSize, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QFont, QIcon
from datetime import datetime
import numpy as np

from safetwin.core.risk_utils import derive_risk_level, normalize_compliance_score
from safetwin.services.evaluation_metrics import build_assessment_evaluation_summary


class ZoneStatsTableModel(QAbstractTableModel):
    """Track per-zone critical and total frame counts for live analysis."""

    headers = ["Zone ID", "Critical Frame Count", "Total Frames"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._stats = {}
        self._row_lookup = {}

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.headers)

    def clear(self):
        self.beginResetModel()
        self._rows = []
        self._stats = {}
        self._row_lookup = {}
        self.endResetModel()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows):
            return None

        zone_id = self._rows[index.row()]
        stats = self._stats.get(zone_id, {"critical_frames": 0, "total_frames": 0})

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return zone_id
            if index.column() == 1:
                return stats["critical_frames"]
            if index.column() == 2:
                return stats["total_frames"]

        if role == Qt.TextAlignmentRole and index.column() in {1, 2}:
            return Qt.AlignCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal and section < len(self.headers):
            return self.headers[section]

        return section + 1

    def update_zone_stats(self, zone_id, is_critical):
        zone_id = str(zone_id)
        is_new_zone = zone_id not in self._stats

        if is_new_zone:
            row_index = len(self._rows)
            self.beginInsertRows(QModelIndex(), row_index, row_index)
            self._rows.append(zone_id)
            self._row_lookup[zone_id] = row_index
            self._stats[zone_id] = {"critical_frames": 0, "total_frames": 0}
            self.endInsertRows()

        stats = self._stats[zone_id]
        stats["total_frames"] += 1
        if is_critical:
            stats["critical_frames"] += 1

        row_index = self._row_lookup[zone_id]
        top_left = self.index(row_index, 0)
        bottom_right = self.index(row_index, 2)
        self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])

    def _is_hotspot_critical(self, hs) -> bool:
        """Check whether a hotspot entry indicates CRITICAL-level hazard."""
        if isinstance(hs, dict):
            return str(hs.get('level', 'LOW')).upper() == 'CRITICAL'
        return False

    def record_frame(self, zone_map, hotspots):
        """Record one processed frame for every zone in the current grid."""
        if zone_map is None:
            return
        # Build a mapping: zone_id -> bool indicating if at least one CRITICAL hazard exists
        hotspot_critical_map = {}
        for hs in (hotspots or []):
            is_critical = self._is_hotspot_critical(hs)
            if isinstance(hs, dict):
                zone_id = None
                if 'zone_id' in hs:
                    zone_id = str(hs['zone_id'])
                elif 'id' in hs:
                    zone_id = str(hs['id'])
                # For grid-style hotspots, build the canonical key
                if zone_id is None and 'by' in hs and 'bx' in hs:
                    zone_id = f"{int(hs['by'])}:{int(hs['bx'])}"
                if zone_id:
                    # Keep True if already critical in this frame
                    hotspot_critical_map[zone_id] = hotspot_critical_map.get(zone_id, False) or is_critical
            elif isinstance(hs, (tuple, list)) and len(hs) >= 2:
                zone_id = str((int(hs[0]), int(hs[1])))
                hotspot_critical_map[zone_id] = hotspot_critical_map.get(zone_id, False) or is_critical

        # Perspective-style zone list
        if isinstance(zone_map, dict) or isinstance(zone_map, list):
            zones = zone_map.get('zones') if isinstance(zone_map, dict) else zone_map
            if not self._rows:
                self.beginResetModel()
                self._rows = []
                self._stats = {}
                self._row_lookup = {}
                for z in zones:
                    zid = str(z.get('id', f"zone_{len(self._rows)+1}"))
                    self._rows.append(zid)
                    self._row_lookup[zid] = len(self._rows) - 1
                    is_critical = hotspot_critical_map.get(zid, False)
                    self._stats[zid] = {"critical_frames": 1 if is_critical else 0, "total_frames": 1}
                self.endResetModel()
                return

            updated_rows = []
            for z in zones:
                zid = str(z.get('id', f"zone_{len(self._rows)+1}"))
                if zid not in self._stats:
                    insert_row = len(self._rows)
                    self.beginInsertRows(QModelIndex(), insert_row, insert_row)
                    self._rows.append(zid)
                    self._row_lookup[zid] = insert_row
                    self._stats[zid] = {"critical_frames": 0, "total_frames": 0}
                    self.endInsertRows()

                stats = self._stats[zid]
                stats["total_frames"] += 1
                if hotspot_critical_map.get(zid, False):
                    stats["critical_frames"] += 1
                updated_rows.append(self._row_lookup[zid])

            if updated_rows:
                top_row = min(updated_rows)
                bottom_row = max(updated_rows)
                self.dataChanged.emit(self.index(top_row, 0), self.index(bottom_row, 2), [Qt.DisplayRole])
            return

        # Fallback: keep original grid handling
        zone_array = np.asarray(zone_map)
        if zone_array.ndim != 2:
            return

        # Build grid hotspot lookup: (row, col) -> is_critical
        hotspot_lookup = {}
        for hs in (hotspots or []):
            norm = self._normalize_hotspot(hs)
            if norm is not None:
                is_critical = self._is_hotspot_critical(hs)
                hotspot_lookup[norm] = hotspot_lookup.get(norm, False) or is_critical

        updated_rows = []

        if not self._rows:
            self.beginResetModel()
            self._rows = []
            self._stats = {}
            self._row_lookup = {}

            for row_index in range(zone_array.shape[0]):
                for column_index in range(zone_array.shape[1]):
                    zone_id = f"{row_index}:{column_index}"
                    self._rows.append(zone_id)
                    self._row_lookup[zone_id] = len(self._rows) - 1
                    is_critical = hotspot_lookup.get((row_index, column_index), False)
                    self._stats[zone_id] = {"critical_frames": 1 if is_critical else 0, "total_frames": 1}

            self.endResetModel()
            return

        for row_index in range(zone_array.shape[0]):
            for column_index in range(zone_array.shape[1]):
                zone_id = f"{row_index}:{column_index}"
                if zone_id not in self._stats:
                    insert_row = len(self._rows)
                    self.beginInsertRows(QModelIndex(), insert_row, insert_row)
                    self._rows.append(zone_id)
                    self._row_lookup[zone_id] = insert_row
                    self._stats[zone_id] = {"critical_frames": 0, "total_frames": 0}
                    self.endInsertRows()

                stats = self._stats[zone_id]
                stats["total_frames"] += 1
                if hotspot_lookup.get((row_index, column_index), False):
                    stats["critical_frames"] += 1
                updated_rows.append(self._row_lookup[zone_id])

        if updated_rows:
            top_row = min(updated_rows)
            bottom_row = max(updated_rows)
            self.dataChanged.emit(self.index(top_row, 0), self.index(bottom_row, 2), [Qt.DisplayRole])

    def _normalize_hotspot(self, hotspot):
        if isinstance(hotspot, dict):
            row_index = hotspot.get("row", hotspot.get("by", hotspot.get("y")))
            column_index = hotspot.get("column", hotspot.get("bx", hotspot.get("x")))
        elif isinstance(hotspot, (tuple, list)) and len(hotspot) >= 2:
            row_index, column_index = hotspot[0], hotspot[1]
        else:
            return None

        try:
            return int(row_index), int(column_index)
        except (TypeError, ValueError):
            return None


class RiskIndicator(QFrame):
    """Visual risk level indicator"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(2)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.risk_level_label = QLabel("RISK LEVEL")
        self.risk_level_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.risk_level_label.setAlignment(Qt.AlignCenter)
        
        self.risk_score_bar = QProgressBar()
        self.risk_score_bar.setMinimum(0)
        self.risk_score_bar.setMaximum(100)
        self.risk_score_bar.setTextVisible(True)
        
        self.risk_details = QLabel("No data")
        self.risk_details.setFont(QFont("Arial", 10))
        self.risk_details.setAlignment(Qt.AlignCenter)

        self.evaluation_metrics_label = QLabel("Evaluation: N/A")
        self.evaluation_metrics_label.setFont(QFont("Arial", 9))
        self.evaluation_metrics_label.setAlignment(Qt.AlignCenter)
        self.evaluation_metrics_label.setWordWrap(True)

        self.recommendations_label = QLabel("Recommendations: None")
        self.recommendations_label.setFont(QFont("Arial", 9))
        self.recommendations_label.setWordWrap(True)
        self.recommendations_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.risk_level_label)
        layout.addWidget(self.risk_score_bar)
        layout.addWidget(self.risk_details)
        layout.addWidget(self.evaluation_metrics_label)
        layout.addWidget(self.recommendations_label)
    
    def update_risk(self, risk_data: dict):
        """Update risk indicator with new data"""
        normalized_payload = risk_data or {}
        risk_level = derive_risk_level(normalized_payload).upper()
        risk_score = float(normalized_payload.get('risk_score', normalized_payload.get('score', 0.0)))
        
        permit_risks = risk_data.get('permit_risks', {}) or {}
        if isinstance(permit_risks, dict):
            permit_count = len(permit_risks.get('high_risk_alerts', [])) + len(permit_risks.get('warnings', []))
        else:
            permit_count = 0

        compliance_gaps = risk_data.get('compliance_gaps', {}) or {}
        if isinstance(compliance_gaps, dict):
            compliance_score = normalize_compliance_score(compliance_gaps)
            overdue_checks = compliance_gaps.get('overdue_checks', 0)
        else:
            compliance_score = 0.0
            overdue_checks = 0

        incident_risks = risk_data.get('incident_risks', {}) or {}
        if isinstance(incident_risks, dict):
            incident_count = incident_risks.get('total_incidents', 0)
        else:
            incident_count = 0

        # 1. Update label
        color_map = {
            'LOW': '#4CAF50',
            'MEDIUM': '#FFC107',
            'HIGH': '#FF9800',
            'CRITICAL': '#F44336'
        }
        color = color_map.get(risk_level, '#9E9E9E')
        self.risk_level_label.setText(f"RISK LEVEL: {risk_level}")
        self.risk_level_label.setStyleSheet(f"color: white; background-color: {color}; padding: 8px; border-radius: 4px;")
        
        # 2. Update Progress Bar (Scale to 100 for higher precision)
        self.risk_score_bar.setMaximum(100)
        score_val = round(risk_score * 100)
        self.risk_score_bar.setValue(score_val)
        
        # 3. Update details label to show raw score without duplication
        alerts_count = len(risk_data.get('critical_alerts', []))
        details = (
            f"Risk Score: {risk_score:.3f} | Active Alerts: {alerts_count} | "
            f"Permits: {permit_count} | Compliance: {float(compliance_score):.0f}% | Incidents: {incident_count}"
        )
        if overdue_checks:
            details += f" | Overdue checks: {overdue_checks}"
        self.risk_details.setText(details)

        evaluation_summary = build_assessment_evaluation_summary(risk_data)
        if (
            evaluation_summary['false_negative_rate'] is None
            and evaluation_summary['lead_time_minutes'] is None
            and evaluation_summary['geospatial_quality'] is None
        ):
            eval_text = "Eval: N/A"
        else:
            fnr_text = (
                f"{evaluation_summary['false_negative_rate']:.2f}"
                if evaluation_summary['false_negative_rate'] is not None
                else "N/A"
            )
            lead_text = (
                f"{evaluation_summary['lead_time_minutes']:.1f}m"
                if evaluation_summary['lead_time_minutes'] is not None
                else "N/A"
            )
            geo_text = (
                f"{evaluation_summary['geospatial_quality']:.2f}"
                if evaluation_summary['geospatial_quality'] is not None
                else "N/A"
            )
            eval_text = f"Eval: FNR {fnr_text} | Lead {lead_text} | Geo {geo_text}"
        self.evaluation_metrics_label.setText(eval_text)

        recommendations = risk_data.get('recommended_actions', []) or risk_data.get('recommendations', []) or []
        if isinstance(recommendations, str):
            recommendation_text = recommendations
        else:
            recommendation_text = "; ".join(str(item) for item in recommendations[:3]) if recommendations else "None"
        self.recommendations_label.setText(f"Recommendations: {recommendation_text}")
        
        # 4. Color logic
        if risk_score < 0.3: bar_color = "green"
        elif risk_score < 0.6: bar_color = "orange"
        else: bar_color = "red"
        
        self.risk_score_bar.setStyleSheet(f"""
            QProgressBar {{ border: 2px solid #ddd; border-radius: 5px; text-align: center; font-weight: bold; }}
            QProgressBar::chunk {{ background-color: {bar_color}; }}
        """)
        
        self.risk_score_bar.repaint()

    def reset(self):
        self.risk_level_label.setText("RISK LEVEL")
        self.risk_level_label.setStyleSheet("color: white; background-color: #0f3557; padding: 8px; border-radius: 4px;")
        self.risk_score_bar.setValue(0)
        self.risk_details.setText("No data")
        self.recommendations_label.setText("Recommendations: None")

class PermitsPanel(QWidget):
    """Permit management and conflict detection"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Active Work Permits")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)
        
        # Permits table
        self.permits_table = QTableWidget()
        self.permits_table.setColumnCount(5)
        self.permits_table.setHorizontalHeaderLabels(
            ["Permit ID", "Type", "Location", "Status", "Risk Level"]
        )
        self.permits_table.setMaximumHeight(200)
        layout.addWidget(self.permits_table)
        
        # Conflicts warning
        self.conflicts_label = QLabel("✓ No permit conflicts detected")
        self.conflicts_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.conflicts_label)
        
        layout.addStretch()
    
    def update_permits(self, permit_data: dict):
        """Update permits display"""
        alerts = permit_data.get('high_risk_alerts', [])
        warnings = permit_data.get('warnings', [])
        
        # Update conflicts warning
        if alerts or warnings:
            self.conflicts_label.setText(
                f"⚠️ {len(alerts)} critical alert(s), {len(warnings)} warning(s)"
            )
            self.conflicts_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.conflicts_label.setText("✓ No permit conflicts detected")
            self.conflicts_label.setStyleSheet("color: green; font-weight: bold;")
        
        # Show details
        self.permits_table.setRowCount(len(alerts) + len(warnings))
        
        row = 0
        for alert in alerts:
            self.permits_table.setItem(row, 0, QTableWidgetItem(alert.get('permit_id', 'N/A')))
            self.permits_table.setItem(row, 1, QTableWidgetItem(alert.get('permit_type', 'N/A')))
            self.permits_table.setItem(row, 2, QTableWidgetItem(alert.get('location', 'N/A')))
            self.permits_table.setItem(row, 3, QTableWidgetItem('⚠️ ALERT'))
            self.permits_table.setItem(row, 4, QTableWidgetItem('CRITICAL'))
            row += 1
        
        for warning in warnings:
            self.permits_table.setItem(row, 0, QTableWidgetItem(warning.get('permit_id', 'N/A')))
            self.permits_table.setItem(row, 1, QTableWidgetItem(warning.get('permit_type', 'N/A')))
            self.permits_table.setItem(row, 2, QTableWidgetItem(warning.get('location', 'N/A')))
            self.permits_table.setItem(row, 3, QTableWidgetItem('⚠️ WARNING'))
            self.permits_table.setItem(row, 4, QTableWidgetItem('HIGH'))
            row += 1

    def reset(self):
        self.conflicts_label.setText("✓ No permit conflicts detected")
        self.conflicts_label.setStyleSheet("color: green; font-weight: bold;")
        self.permits_table.setRowCount(0)


class CompliancePanel(QWidget):
    """Compliance audit and regulatory tracking"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Compliance Status")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)
        
        # Compliance score
        score_layout = QHBoxLayout()
        self.compliance_score_label = QLabel("Compliance Score:")
        self.compliance_score_value = QLabel("--")
        self.compliance_score_value.setFont(QFont("Arial", 16, QFont.Bold))
        score_layout.addWidget(self.compliance_score_label)
        score_layout.addWidget(self.compliance_score_value)
        score_layout.addStretch()
        layout.addLayout(score_layout)
        
        # Compliance table
        self.compliance_table = QTableWidget()
        self.compliance_table.setColumnCount(3)
        self.compliance_table.setHorizontalHeaderLabels(
            ["Check Type", "Status", "Due Date"]
        )
        self.compliance_table.setMaximumHeight(250)
        layout.addWidget(self.compliance_table)
        
        layout.addStretch()
    
    def update_compliance(self, compliance_data: dict):
        """Update compliance display"""
        score = normalize_compliance_score(compliance_data)
        self.compliance_score_value.setText(f"{score:.0f}%")
        
        # Color based on score
        if score >= 80:
            color = "green"
        elif score >= 60:
            color = "orange"
        else:
            color = "red"
        
        self.compliance_score_value.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        # Update table
        overdue = compliance_data.get('overdue_checks', [])
        # Some agents provide `overdue_checks` as an int count; normalize to a list.
        if isinstance(overdue, int):
            overdue_rows = [{"check_type": f"Overdue Check #{i+1}"} for i in range(overdue)]
        elif overdue is None:
            overdue_rows = []
        else:
            overdue_rows = overdue if isinstance(overdue, list) else list(overdue)

        self.compliance_table.setRowCount(len(overdue_rows))

        for i, check in enumerate(overdue_rows):
            self.compliance_table.setItem(i, 0, QTableWidgetItem(
                check.get('check_type', 'Unknown') if isinstance(check, dict) else str(check)
            ))
            self.compliance_table.setItem(i, 1, QTableWidgetItem("OVERDUE"))
            self.compliance_table.setItem(i, 2, QTableWidgetItem("ASAP"))

    def reset(self):
        self.compliance_score_value.setText("--")
        self.compliance_score_value.setStyleSheet("color: #64748b; font-weight: bold;")
        self.compliance_table.setRowCount(0)



class IncidentsPanel(QWidget):
    """Incident analysis and pattern detection"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Incident Analysis")
        header.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(header)
        
        # Stats layout
        stats_layout = QHBoxLayout()
        self.total_incidents_label = QLabel("Total Incidents: 0")
        self.near_misses_label = QLabel("Near-Misses: 0")
        self.escalation_risk_label = QLabel("Escalation Risk: 0%")
        stats_layout.addWidget(self.total_incidents_label)
        stats_layout.addWidget(self.near_misses_label)
        stats_layout.addWidget(self.escalation_risk_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Incidents table
        self.incidents_table = QTableWidget()
        self.incidents_table.setColumnCount(4)
        self.incidents_table.setHorizontalHeaderLabels(
            ["Incident Type", "Count", "Severity", "Recommendation"]
        )
        self.incidents_table.setMaximumHeight(250)
        layout.addWidget(self.incidents_table)
        
        layout.addStretch()
    
    def update_incidents(self, incident_data: dict):
        """Update incidents display"""
        total = incident_data.get('total_incidents', 0)
        near_misses = incident_data.get('total_near_misses', 0)
        risk_score = incident_data.get('risk_score', 0.0)
        
        self.total_incidents_label.setText(f"Total Incidents: {total}")
        self.near_misses_label.setText(f"Near-Misses: {near_misses}")
        self.escalation_risk_label.setText(f"Escalation Risk: {risk_score*100:.0f}%")
        
        # Update table with incident types
        incident_ranking = incident_data.get('incident_type_ranking', [])
        self.incidents_table.setRowCount(len(incident_ranking))
        
        for i, incident_type in enumerate(incident_ranking):
            self.incidents_table.setItem(i, 0, QTableWidgetItem(
                incident_type.get('type', 'Unknown')
            ))
            self.incidents_table.setItem(i, 1, QTableWidgetItem(
                str(incident_type.get('count', 0))
            ))
            self.incidents_table.setItem(i, 2, QTableWidgetItem(
                incident_type.get('max_severity', 'UNKNOWN')
            ))
            self.incidents_table.setItem(i, 3, QTableWidgetItem("Review"))

    def reset(self):
        self.total_incidents_label.setText("Total Incidents: 0")
        self.near_misses_label.setText("Near-Misses: 0")
        self.escalation_risk_label.setText("Escalation Risk: 0%")
        self.incidents_table.setRowCount(0)


class SafetyDashboard(QWidget):
    """Main safety intelligence dashboard"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🛡️ Industrial Safety Intelligence Dashboard")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(title)
        
        # Tab widget for different views
        self.tabs = QTabWidget()
        
        # Risk Assessment Tab
        self.risk_indicator = RiskIndicator()
        self.tabs.addTab(self.risk_indicator, "Real-Time Risk")
        
        # Permits Tab
        self.permits_panel = PermitsPanel()
        self.tabs.addTab(self.permits_panel, "Permits")
        
        # Compliance Tab
        self.compliance_panel = CompliancePanel()
        self.tabs.addTab(self.compliance_panel, "Compliance")
        
        # Incidents Tab
        self.incidents_panel = IncidentsPanel()
        self.tabs.addTab(self.incidents_panel, "Incidents")

        # Zone Stats Tab
        self.zone_stats_model = ZoneStatsTableModel(self)
        self.zone_stats_table = QTableView()
        self.zone_stats_table.setModel(self.zone_stats_model)
        self.zone_stats_table.setAlternatingRowColors(True)
        self.zone_stats_table.setSelectionBehavior(QTableView.SelectRows)
        self.zone_stats_table.setEditTriggers(QTableView.NoEditTriggers)
        # Improve sizing so rows are fully visible and compact
        self.zone_stats_table.setStyleSheet("QTableView { font-size: 12px; }")
        self.zone_stats_table.verticalHeader().setDefaultSectionSize(22)
        self.zone_stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.zone_stats_table.horizontalHeader().setStretchLastSection(True)
        self.zone_stats_table.setMinimumHeight(140)
        self.tabs.addTab(self.zone_stats_table, "Zone Stats")
        
        layout.addWidget(self.tabs)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.btn_start_monitoring = QPushButton("Start Monitoring")
        self.btn_start_monitoring.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.btn_stop_monitoring = QPushButton("Stop Monitoring")
        self.btn_stop_monitoring.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        self.btn_run_audit = QPushButton("Run Compliance Audit")
        self.btn_run_audit.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        
        button_layout.addWidget(self.btn_start_monitoring)
        button_layout.addWidget(self.btn_stop_monitoring)
        button_layout.addWidget(self.btn_run_audit)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def update_all_data(self, assessment: dict):
        """Update all dashboard panels with assessment data"""
        assessment = assessment or {}
        self.risk_indicator.update_risk(assessment)
        self.permits_panel.update_permits(assessment.get('permit_risks', {}))
        self.compliance_panel.update_compliance(assessment.get('compliance_gaps', {}))
        self.incidents_panel.update_incidents(assessment.get('incident_risks', {}))
        
        self.risk_indicator.risk_score_bar.repaint()
        self.risk_indicator.repaint()

    def reset_view(self):
        self.risk_indicator.reset()
        self.permits_panel.reset()
        self.compliance_panel.reset()
        self.incidents_panel.reset()
        self.zone_stats_model.clear()

    def set_emergency_mode(self, color: str = 'red', event_data: dict = None):
        """Switch the dashboard into a visual hazard state."""
        event_data = event_data or {}
        color = (color or 'red').lower()
        palette = {
            'red': '#F44336',
            'yellow': '#FFC107',
            'orange': '#FF9800',
            'green': '#4CAF50',
        }
        accent = palette.get(color, '#F44336')

        if color == 'red':
            critical_assessment = {
                'overall_risk_level': 'CRITICAL',
                'risk_score': 1.0,
                'critical_alerts': [event_data] if event_data else [{'event_type': 'CRITICAL_COMPOUND_RISK'}],
            }
        elif color in {'yellow', 'orange'}:
            critical_assessment = {
                'overall_risk_level': 'WARNING',
                'risk_score': 0.45,
                'critical_alerts': [event_data] if event_data else [{'event_type': 'WARNING'}],
            }
        else:
            critical_assessment = {
                'overall_risk_level': 'READY',
                'risk_score': 0.0,
                'critical_alerts': [],
                'permit_risks': {'high_risk_alerts': [], 'warnings': []},
                'compliance_gaps': {'score': 100.0, 'compliance_score': 100.0, 'overdue_checks': 0},
                'incident_risks': {'total_incidents': 0, 'total_near_misses': 0},
            }

        self.risk_indicator.update_risk(critical_assessment)
        self.tabs.setStyleSheet(f"QTabWidget::pane {{ border: 2px solid {accent}; }}")
        self.risk_indicator.risk_level_label.setStyleSheet(
            f"color: white; background-color: {accent}; padding: 8px; border-radius: 4px;"
        )