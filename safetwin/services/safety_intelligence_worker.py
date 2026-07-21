"""
SafeTwin - Safety Intelligence Worker Thread
Runs the safety platform services in background with signal-based communication
"""

from PySide6.QtCore import QObject, Signal, QTimer
from datetime import datetime
from safetwin.services.safety_intelligence_platform import SafetyIntelligencePlatform
from safetwin.services.sensor_manager import local_sensor_manager
import json

class SafetyIntelligenceWorker(QObject):
    """Worker thread for continuous safety monitoring"""
    
    # Signals for UI updates
    risk_assessment_updated = Signal(dict)  # Real-time risk data
    permit_alert = Signal(dict)  # Permit warnings/conflicts
    incident_alert = Signal(dict)  # Incident analysis alerts
    compliance_status_updated = Signal(dict)  # Compliance dashboard
    emergency_triggered = Signal(dict)  # Emergency response
    platform_status_updated = Signal(dict)  # Platform health
    log_message = Signal(str)  # Status messages
    
    def __init__(self):
        super().__init__()
        self.platform = SafetyIntelligencePlatform()
        self.monitoring_active = False
        
        # 1. Pass 'self' as the parent so the timer lifecycle is bound to the worker
        self.monitoring_timer = QTimer(self) 
        
        # 2. Ensure connection is explicit and stable
        self.monitoring_timer.timeout.connect(self._perform_monitoring)
        
        self.current_location = None
        self.sensor_data = {}
        self.monitoring_interval_ms = 5000
        self.latest_frame_hazards = []  # Store latest hazards from video processing
        
    def initialize_facility(self, facility_config: dict):
        """Initialize facility with equipment and permits"""
        try:
            # Register equipment
            for equipment in facility_config.get('equipment', []):
                result = self.platform.register_equipment(
                    equipment['id'],
                    equipment['name'],
                    equipment['location'],
                    equipment['type'],
                    equipment['risk_category']
                )
                self.log_message.emit(f"✓ Equipment registered: {equipment['name']}")
            
            # Create permits
            for permit in facility_config.get('permits', []):
                result = self.platform.create_work_permit(
                    permit['id'],
                    permit['type'],
                    permit['equipment_id'],
                    permit['location'],
                    permit['start_time'],
                    permit['end_time'],
                    permit['authorized_by'],
                    permit.get('hazards', [])
                )
                self.log_message.emit(f"✓ Permit created: {permit['id']}")
            
            self.log_message.emit("Facility initialization complete")
            
        except Exception as e:
            self.log_message.emit(f"✗ Error initializing facility: {str(e)}")
    
    def start_monitoring(self, location: str, monitoring_interval_ms: int = 5000):
        """Start continuous safety monitoring"""
        self.current_location = location
        self.monitoring_interval_ms = monitoring_interval_ms
        self.monitoring_active = True
        self.monitoring_timer.start(monitoring_interval_ms)
        self.log_message.emit(f"🟢 Monitoring started for {location}")
    
    def stop_monitoring(self):
        """Stop continuous safety monitoring"""
        self.monitoring_active = False
        self.monitoring_timer.stop()
        self.log_message.emit("🔴 Monitoring stopped")
    
    def _perform_monitoring(self):
        """Run real-time risk assessment with latest frame hazards."""
        if not self.current_location:
            return
        
        try:
            self.sensor_data = local_sensor_manager.get_latest()

            # Perform comprehensive risk assessment with current frame hazards
            assessment = self.platform.perform_real_time_risk_assessment(
                sensor_data=self.sensor_data,
                location=self.current_location,
                frame_hazards=self.latest_frame_hazards  # Pass real-time hazards
            )
            
            # Emit risk assessment data (this triggers the UI update)
            self.risk_assessment_updated.emit(assessment)
            
            # Check for critical alerts
            if assessment.get('critical_alerts'):
                for alert in assessment['critical_alerts']:
                    if alert['type'] == 'PERMIT_CONFLICT':
                        self.permit_alert.emit(alert)
                    elif alert['type'] == 'ESCALATION_WARNING':
                        self.incident_alert.emit(alert)
            
            # Check for emergency trigger
            if assessment.get('emergency_trigger'):
                self.emergency_triggered.emit(assessment)
        
        except Exception as e:
            self.log_message.emit(f"⚠️ Monitoring error: {str(e)}")
    
    def update_frame_hazards(self, hazards: list):
        """Update with latest hazards from frame processing. Called from video worker."""
        self.latest_frame_hazards = hazards or []
            
    def update_sensor_data(self, sensor_data: dict):
        """Update current sensor readings via external injection"""
        self.sensor_data = sensor_data
    
    def conduct_audit(self, audit_scope: list, auditor_name: str):
        """Run compliance audit"""
        try:
            audit = self.platform.conduct_compliance_audit(
                location=self.current_location,
                audit_scope=audit_scope,
                auditor_name=auditor_name
            )
            self.compliance_status_updated.emit(audit)
            self.log_message.emit(f"✓ Audit completed: {audit['audit_id']}")
        except Exception as e:
            self.log_message.emit(f"✗ Audit error: {str(e)}")
    
    def trigger_emergency(self, trigger_event: dict):
        """Trigger emergency response"""
        try:
            emergency = self.platform.trigger_emergency_incident(
                trigger_event=trigger_event,
                location=self.current_location,
                severity=trigger_event.get('severity', 'CRITICAL')
            )
            self.emergency_triggered.emit(emergency)
            self.log_message.emit("🚨 EMERGENCY RESPONSE ACTIVATED")
        except Exception as e:
            self.log_message.emit(f"✗ Emergency trigger error: {str(e)}")
    
    def get_location_profile(self):
        """Get comprehensive location safety profile"""
        try:
            profile = self.platform.get_location_safety_profile(self.current_location)
            return profile
        except Exception as e:
            self.log_message.emit(f"✗ Profile error: {str(e)}")
            return None
    
    def get_platform_status(self):
        """Get platform health status"""
        return self.platform.get_platform_status()
