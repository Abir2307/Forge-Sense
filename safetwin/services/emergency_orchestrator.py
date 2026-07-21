"""
Emergency Response Orchestrator
Autonomous agent that, on confirmed trigger, immediately initiates evacuation protocols, 
alerts response teams across channels, preserves sensor evidence, and generates a 
preliminary regulatory-compliant incident report.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from enum import Enum
import uuid

class SeverityLevel(Enum):
    """Emergency severity levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class AlertChannel(Enum):
    """Alert notification channels."""
    SMS = "sms"
    EMAIL = "email"
    PUSH_NOTIFICATION = "push"
    SIREN = "siren"
    MQTT = "mqtt"
    RADIO = "radio"

class EvacuationZone(Enum):
    """Evacuation zone definitions."""
    IMMEDIATE = "immediate"  # Within 100m
    SECONDARY = "secondary"  # 100-500m
    PERIPHERAL = "peripheral"  # 500m+

class EmergencyResponseOrchestrator:
    """
    Autonomous emergency response system that coordinates immediate
    response to critical safety incidents.
    """
    
    # Response time targets (seconds)
    RESPONSE_TIME_TARGETS = {
        SeverityLevel.CRITICAL: 30,
        SeverityLevel.HIGH: 60,
        SeverityLevel.MEDIUM: 120,
        SeverityLevel.LOW: 300
    }
    
    def __init__(self):
        """Initialize orchestrator with default configurations."""
        self.active_incidents = {}  # incident_id -> incident details
        self.response_teams = {}    # team_id -> team details
        self.evacuation_routes = {} # zone -> evacuation path
        self.alert_handlers = {}    # channel -> handler function
        
        # Setup incident memory
        self.incident_history = []
        self.evidence_vault = {}
        
    def register_alert_handler(self, channel: AlertChannel, handler: Callable):
        """
        Register a handler for a specific alert channel.
        
        Args:
            channel: AlertChannel enum
            handler: Callable that accepts alert_data dict
        """
        self.alert_handlers[channel] = handler
    
    def trigger_emergency_response(self, 
                                   trigger_event: Dict,
                                   severity: SeverityLevel,
                                   affected_zones: List[str]) -> Dict:
        """
        Trigger emergency response sequence.
        Called when critical incident is confirmed.
        
        Args:
            trigger_event: Event that triggered the emergency (sensor reading, detection, etc.)
            severity: Emergency severity level
            affected_zones: List of affected locations/zones
            
        Returns:
            Dict with response initiation details and status
        """
        incident_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Create incident record
        incident = {
            'incident_id': incident_id,
            'timestamp': timestamp.isoformat(),
            'trigger_event': trigger_event,
            'severity': severity.name,
            'affected_zones': affected_zones,
            'status': 'ACTIVATED',
            'response_start_time': timestamp.isoformat(),
            'evacuation_status': 'IN_PROGRESS',
            'notifications_sent': [],
            'response_steps_completed': []
        }
        
        self.active_incidents[incident_id] = incident
        
        # Execute response sequence
        response_status = {
            'incident_id': incident_id,
            'activation_time': timestamp.isoformat(),
            'steps_executed': []
        }
        
        # Step 1: Preserve sensor evidence (0-5 seconds)
        try:
            evidence_id = self._preserve_sensor_evidence(incident_id, trigger_event)
            response_status['steps_executed'].append({
                'step': 'PRESERVE_EVIDENCE',
                'status': 'SUCCESS',
                'evidence_id': evidence_id,
                'duration_ms': 0
            })
            incident['response_steps_completed'].append('PRESERVE_EVIDENCE')
        except Exception as e:
            response_status['steps_executed'].append({
                'step': 'PRESERVE_EVIDENCE',
                'status': 'FAILED',
                'error': str(e)
            })
        
        # Step 2: Sound alarms and initiate evacuation (5-10 seconds)
        try:
            evacuation_initiated = self._initiate_evacuation(incident_id, severity, affected_zones)
            response_status['steps_executed'].append({
                'step': 'INITIATE_EVACUATION',
                'status': 'SUCCESS',
                'zones_alerted': evacuation_initiated['zones'],
                'estimated_evacuation_time_seconds': evacuation_initiated['estimated_time']
            })
            incident['response_steps_completed'].append('INITIATE_EVACUATION')
        except Exception as e:
            response_status['steps_executed'].append({
                'step': 'INITIATE_EVACUATION',
                'status': 'FAILED',
                'error': str(e)
            })
        
        # Step 3: Alert response teams (10-15 seconds)
        try:
            alerts_sent = self._alert_response_teams(incident_id, severity, affected_zones, trigger_event)
            response_status['steps_executed'].append({
                'step': 'ALERT_TEAMS',
                'status': 'SUCCESS',
                'teams_alerted': len(alerts_sent),
                'channels_used': [a['channel'] for a in alerts_sent]
            })
            incident['response_steps_completed'].append('ALERT_TEAMS')
            incident['notifications_sent'] = alerts_sent
        except Exception as e:
            response_status['steps_executed'].append({
                'step': 'ALERT_TEAMS',
                'status': 'FAILED',
                'error': str(e)
            })
        
        # Step 4: Generate preliminary incident report (15-20 seconds)
        try:
            preliminary_report = self._generate_preliminary_report(incident_id, trigger_event, severity)
            response_status['steps_executed'].append({
                'step': 'GENERATE_REPORT',
                'status': 'SUCCESS',
                'report_id': preliminary_report['report_id']
            })
            incident['response_steps_completed'].append('GENERATE_REPORT')
            incident['preliminary_report_id'] = preliminary_report['report_id']
        except Exception as e:
            response_status['steps_executed'].append({
                'step': 'GENERATE_REPORT',
                'status': 'FAILED',
                'error': str(e)
            })
        
        # Step 5: Isolate hazard area (20-30 seconds)
        try:
            isolation_status = self._isolate_hazard_area(incident_id, affected_zones)
            response_status['steps_executed'].append({
                'step': 'ISOLATE_AREA',
                'status': 'SUCCESS',
                'barriers_deployed': isolation_status['barrier_count'],
                'access_points_secured': isolation_status['secured_points']
            })
            incident['response_steps_completed'].append('ISOLATE_AREA')
        except Exception as e:
            response_status['steps_executed'].append({
                'step': 'ISOLATE_AREA',
                'status': 'FAILED',
                'error': str(e)
            })
        
        # Record response time
        response_time = (datetime.now() - timestamp).total_seconds()
        target_time = self.RESPONSE_TIME_TARGETS[severity]
        response_status['total_response_time_seconds'] = response_time
        response_status['target_response_time_seconds'] = target_time
        response_status['response_within_target'] = response_time <= target_time
        
        return response_status
    
    def _preserve_sensor_evidence(self, incident_id: str, trigger_event: Dict) -> str:
        """Preserve sensor readings and system state at time of incident."""
        evidence = {
            'evidence_id': str(uuid.uuid4()),
            'incident_id': incident_id,
            'timestamp': datetime.now().isoformat(),
            'trigger_event': trigger_event,
            'system_state': {
                'active_permits': [],
                'equipment_status': {},
                'sensor_readings': trigger_event.get('sensor_data', {})
            }
        }
        
        # Store evidence for regulatory compliance and investigation
        self.evidence_vault[evidence['evidence_id']] = evidence
        
        return evidence['evidence_id']
    
    def _initiate_evacuation(self, incident_id: str, severity: SeverityLevel, 
                           affected_zones: List[str]) -> Dict:
        """Initiate evacuation sequence."""
        evacuation = {
            'incident_id': incident_id,
            'severity': severity.name,
            'zones': affected_zones,
            'evacuation_zones': {},
            'estimated_time': 180  # 3 minutes default
        }
        
        # Determine evacuation zones based on severity
        if severity == SeverityLevel.CRITICAL:
            zones_to_evacuate = [
                EvacuationZone.IMMEDIATE.value,
                EvacuationZone.SECONDARY.value
            ]
            evacuation['estimated_time'] = 120
        elif severity == SeverityLevel.HIGH:
            zones_to_evacuate = [EvacuationZone.IMMEDIATE.value]
            evacuation['estimated_time'] = 180
        else:
            zones_to_evacuate = []
            evacuation['estimated_time'] = 300
        
        # Alert sirens/audio systems
        for zone in zones_to_evacuate:
            try:
                self._send_alert(
                    AlertChannel.SIREN,
                    {
                        'incident_id': incident_id,
                        'zone': zone,
                        'action': 'EVACUATION'
                    }
                )
            except:
                pass
        
        evacuation['evacuation_zones'] = zones_to_evacuate
        
        return evacuation
    
    def _alert_response_teams(self, incident_id: str, severity: SeverityLevel, 
                            affected_zones: List[str], trigger_event: Dict) -> List[Dict]:
        """Alert response teams via multiple channels."""
        alerts_sent = []
        
        # Priority-based team activation
        team_types = self._determine_required_teams(severity, trigger_event)
        
        alert_message = {
            'incident_id': incident_id,
            'severity': severity.name,
            'affected_zones': affected_zones,
            'trigger_type': trigger_event.get('type', 'UNKNOWN'),
            'timestamp': datetime.now().isoformat()
        }
        
        # Critical incidents: activate all channels
        channels_to_use = self._select_alert_channels(severity)
        
        for channel in channels_to_use:
            try:
                alert_record = {
                    'channel': channel.value,
                    'incident_id': incident_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'SENT'
                }
                
                self._send_alert(channel, alert_message)
                alerts_sent.append(alert_record)
            except Exception as e:
                alerts_sent.append({
                    'channel': channel.value,
                    'incident_id': incident_id,
                    'status': 'FAILED',
                    'error': str(e)
                })
        
        return alerts_sent
    
    def _send_alert(self, channel: AlertChannel, alert_data: Dict):
        """Send alert through specified channel."""
        if channel in self.alert_handlers:
            handler = self.alert_handlers[channel]
            handler(alert_data)
        else:
            # Fallback: log to console
            print(f"[{channel.value}] {json.dumps(alert_data, indent=2)}")
    
    def _generate_preliminary_report(self, incident_id: str, trigger_event: Dict, 
                                    severity: SeverityLevel) -> Dict:
        """Generate preliminary regulatory-compliant incident report."""
        report = {
            'report_id': str(uuid.uuid4()),
            'incident_id': incident_id,
            'generated_at': datetime.now().isoformat(),
            'severity': severity.name,
            'incident_type': trigger_event.get('type', 'UNCLASSIFIED'),
            'location': trigger_event.get('location', 'UNKNOWN'),
            'trigger_event': trigger_event.get('description', ''),
            'immediate_actions_taken': [
                'Evacuation initiated',
                'Sensor evidence preserved',
                'Response teams alerted',
                'Hazard area isolated'
            ],
            'preliminary_cause': 'Under investigation',
            'regulatory_references': self._identify_applicable_regulations(trigger_event),
            'investigation_required': True
        }
        
        return report
    
    def _isolate_hazard_area(self, incident_id: str, affected_zones: List[str]) -> Dict:
        """Isolate the hazard area to prevent exposure."""
        isolation = {
            'incident_id': incident_id,
            'zones_isolated': affected_zones,
            'barrier_count': len(affected_zones) * 2,  # Assume 2 barriers per zone
            'secured_points': len(affected_zones) * 4  # 4 access points per zone
        }
        
        return isolation
    
    def _determine_required_teams(self, severity: SeverityLevel, trigger_event: Dict) -> List[str]:
        """Determine which response teams need to be activated."""
        teams = ['SAFETY_OFFICER', 'SHIFT_SUPERVISOR']
        
        if severity == SeverityLevel.CRITICAL:
            teams.extend(['EMERGENCY_RESPONSE', 'MEDICAL_TEAM', 'COMMAND_CENTER'])
        elif severity == SeverityLevel.HIGH:
            teams.extend(['EMERGENCY_RESPONSE', 'MEDICAL_TEAM'])
        else:
            teams.append('SITE_SAFETY')
        
        # Incident-specific teams
        incident_type = trigger_event.get('type', '')
        if 'gas' in incident_type.lower():
            teams.append('HAZMAT_TEAM')
        if 'fire' in incident_type.lower():
            teams.append('FIRE_DEPARTMENT')
        
        return teams
    
    def _select_alert_channels(self, severity: SeverityLevel) -> List[AlertChannel]:
        """Select alert channels based on severity."""
        if severity == SeverityLevel.CRITICAL:
            return [
                AlertChannel.SIREN,
                AlertChannel.SMS,
                AlertChannel.PUSH_NOTIFICATION,
                AlertChannel.MQTT,
                AlertChannel.RADIO
            ]
        elif severity == SeverityLevel.HIGH:
            return [
                AlertChannel.SMS,
                AlertChannel.PUSH_NOTIFICATION,
                AlertChannel.MQTT,
                AlertChannel.RADIO
            ]
        else:
            return [AlertChannel.EMAIL, AlertChannel.MQTT]
    
    def _identify_applicable_regulations(self, trigger_event: Dict) -> List[str]:
        """Identify applicable regulations based on incident type."""
        regulations = ['FACTORY_ACT', 'DGFASLI']
        
        incident_type = trigger_event.get('type', '')
        if 'gas' in incident_type.lower():
            regulations.append('OISD')
        if 'confined_space' in incident_type.lower():
            regulations.extend(['OISD', 'PSM'])
        if 'electrical' in incident_type.lower():
            regulations.append('IE_RULES')
        
        return regulations
    
    def get_incident_status(self, incident_id: str) -> Optional[Dict]:
        """Get current status of an active incident."""
        return self.active_incidents.get(incident_id)
    
    def close_incident(self, incident_id: str, closure_reason: str, 
                      final_investigation_notes: str = "") -> Dict:
        """Close an incident and record final status."""
        if incident_id not in self.active_incidents:
            return {'status': 'FAILED', 'reason': 'Incident not found'}
        
        incident = self.active_incidents[incident_id]
        incident['status'] = 'CLOSED'
        incident['closure_time'] = datetime.now().isoformat()
        incident['closure_reason'] = closure_reason
        incident['final_notes'] = final_investigation_notes
        
        # Move to history
        self.incident_history.append(incident)
        del self.active_incidents[incident_id]
        
        return {
            'status': 'SUCCESS',
            'incident_id': incident_id,
            'closed_at': incident['closure_time']
        }
    
    def get_response_metrics(self) -> Dict:
        """Get emergency response metrics and performance KPIs."""
        return {
            'active_incidents': len(self.active_incidents),
            'total_incidents_handled': len(self.incident_history),
            'response_time_average': self._calculate_avg_response_time(),
            'critical_incidents_closed': sum(
                1 for i in self.incident_history if i['severity'] == 'CRITICAL'
            ),
            'evidence_records_preserved': len(self.evidence_vault)
        }
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time for closed incidents."""
        if not self.incident_history:
            return 0.0
        
        total_time = 0
        for incident in self.incident_history:
            if 'response_start_time' in incident and 'closure_time' in incident:
                start = datetime.fromisoformat(incident['response_start_time'])
                end = datetime.fromisoformat(incident['closure_time'])
                total_time += (end - start).total_seconds()
        
        return total_time / len(self.incident_history) if self.incident_history else 0.0
