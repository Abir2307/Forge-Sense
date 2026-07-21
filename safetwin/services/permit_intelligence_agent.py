"""
Permit Intelligence Agent
Analyzes active permits against real-time plant conditions and flags dangerous 
simultaneous operations (e.g., hot work permits issued in proximity to areas with elevated gas readings).
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from safetwin.db.database import (
    get_active_permits, get_permit_by_id, get_permit_hazards,
    get_equipment_by_location, update_permit_status, link_permit_hazard
)

class PermitIntelligenceAgent:
    """
    Validates permits against real-time sensor data and operational conditions.
    Detects dangerous permit combinations (e.g., hot work + high gas readings).
    """
    
    def __init__(self):
        self.high_risk_permit_types = ['HOT_WORK', 'CONFINED_SPACE', 'EXCAVATION', 'ELECTRICAL']
        self.gas_threshold_ppm = 500
        self.proximity_threshold_meters = 50
        self.temp_threshold_celsius = 80
        
    def validate_active_permits(self, sensor_data: Dict, location: str = None) -> Dict:
        """
        Validate all active permits against current sensor readings.
        
        Args:
            sensor_data: Dict with 'gas', 'temperature', 'humidity', etc.
            location: Optional location filter
            
        Returns:
            Dict with risk assessments for each permit
        """
        active_permits = get_active_permits(location)
        risk_assessment = {
            'total_permits': len(active_permits),
            'high_risk_alerts': [],
            'warnings': [],
            'safe_permits': []
        }
        
        for permit in active_permits:
            assessment = self._assess_permit_safety(permit, sensor_data)
            
            if assessment['risk_level'] == 'CRITICAL':
                risk_assessment['high_risk_alerts'].append(assessment)
            elif assessment['risk_level'] == 'WARNING':
                risk_assessment['warnings'].append(assessment)
            else:
                risk_assessment['safe_permits'].append(permit['permit_id'])
        
        risk_assessment['active_permits'] = active_permits
        return risk_assessment

    def get_active_permits(self, location: str = None) -> List[Dict]:
        """Expose the active permit query through the permit intelligence agent."""
        return get_active_permits(location)
    
    def _assess_permit_safety(self, permit: Dict, sensor_data: Dict) -> Dict:
        """Assess individual permit safety against sensor data."""
        permit_type = permit['permit_type']
        permit_id = permit['permit_id']
        hazards = get_permit_hazards(permit_id)
        
        assessment = {
            'permit_id': permit_id,
            'permit_type': permit_type,
            'location': permit['location'],
            'risk_level': 'LOW',
            'risk_score': 0.0,
            'timestamp': datetime.now().isoformat(),
            'reasons': [],
            'recommended_action': None,
            'hazard_count': len(hazards)
        }
        
        # Check sensor thresholds based on permit type
        if permit_type == 'HOT_WORK':
            assessment = self._check_hot_work_safety(assessment, sensor_data)
        elif permit_type == 'CONFINED_SPACE':
            assessment = self._check_confined_space_safety(assessment, sensor_data)
        elif permit_type == 'ELECTRICAL':
            assessment = self._check_electrical_safety(assessment, sensor_data)
        
        # Check for simultaneous operations
        assessment = self._check_simultaneous_operations(assessment, permit)

        assessment['risk_score'] = self._risk_level_to_score(assessment['risk_level'])
        assessment['timestamp'] = assessment.get('timestamp') or datetime.now().isoformat()
        return assessment
    
    def _check_hot_work_safety(self, assessment: Dict, sensor_data: Dict) -> Dict:
        """Check safety for hot work permits."""
        gas_level = sensor_data.get('gas', 0)
        temperature = sensor_data.get('temperature', 25)
        
        if gas_level > self.gas_threshold_ppm:
            assessment['reasons'].append(
                f"High gas concentration ({gas_level} ppm) detected near hot work area"
            )
            assessment['risk_level'] = 'CRITICAL'
            assessment['recommended_action'] = 'SUSPEND_PERMIT'
        
        if temperature > self.temp_threshold_celsius:
            assessment['reasons'].append(
                f"Elevated temperature ({temperature}°C) in work area"
            )
            if assessment['risk_level'] != 'CRITICAL':
                assessment['risk_level'] = 'WARNING'
            assessment['recommended_action'] = 'REDUCE_PERMIT_SCOPE'
        
        return assessment
    
    def _check_confined_space_safety(self, assessment: Dict, sensor_data: Dict) -> Dict:
        """Check safety for confined space work."""
        gas_level = sensor_data.get('gas', 0)
        oxygen_level = sensor_data.get('oxygen', 20.8)
        
        if gas_level > 100:  # Lower threshold for confined spaces
            assessment['reasons'].append(
                f"Hazardous gas present ({gas_level} ppm) in confined space"
            )
            assessment['risk_level'] = 'CRITICAL'
            assessment['recommended_action'] = 'SUSPEND_PERMIT'
        
        if oxygen_level < 19.5 or oxygen_level > 23.5:
            assessment['reasons'].append(
                f"Oxygen level ({oxygen_level}%) outside safe range [19.5-23.5]"
            )
            assessment['risk_level'] = 'CRITICAL'
            assessment['recommended_action'] = 'SUSPEND_PERMIT'
        
        return assessment
    
    def _check_electrical_safety(self, assessment: Dict, sensor_data: Dict) -> Dict:
        """Check safety for electrical work."""
        humidity = sensor_data.get('humidity', 50)
        moisture_detected = sensor_data.get('moisture_alert', False)
        
        if humidity > 80 or moisture_detected:
            assessment['reasons'].append(
                f"High humidity ({humidity}%) or moisture detected - electrical hazard"
            )
            assessment['risk_level'] = 'CRITICAL'
            assessment['recommended_action'] = 'SUSPEND_PERMIT'
        
        return assessment
    
    def _check_simultaneous_operations(self, assessment: Dict, permit: Dict) -> Dict:
        """Check for dangerous simultaneous operations."""
        permit_type = permit['permit_type']
        location = permit['location']
        
        # Get all other active permits at same/nearby locations
        active_permits = get_active_permits()
        simultaneous_hazards = []
        
        for other_permit in active_permits:
            if other_permit['permit_id'] != permit['permit_id']:
                # Check if permits overlap in location/time
                if self._locations_overlap(location, other_permit['location']):
                    other_type = other_permit['permit_type']
                    conflict = self._check_permit_conflict(permit_type, other_type)
                    if conflict:
                        simultaneous_hazards.append({
                            'conflicting_permit': other_permit['permit_id'],
                            'conflict_type': conflict['type'],
                            'severity': conflict['severity']
                        })
        
        if simultaneous_hazards:
            assessment['reasons'].append(
                f"Dangerous simultaneous operations detected: {len(simultaneous_hazards)} conflicts"
            )
            assessment['simultaneous_operations'] = simultaneous_hazards
            
            # Upgrade risk if any severe conflicts
            if any(h['severity'] == 'CRITICAL' for h in simultaneous_hazards):
                assessment['risk_level'] = 'CRITICAL'
            elif assessment['risk_level'] != 'CRITICAL':
                assessment['risk_level'] = 'WARNING'
        
        return assessment
    
    def _locations_overlap(self, loc1: str, loc2: str) -> bool:
        """Check if two locations are close enough to be overlapping."""
        # Simple string proximity check (in production, use GPS coordinates)
        common_words = set(loc1.split('_')) & set(loc2.split('_'))
        return len(common_words) > 0 or loc1 == loc2
    
    def _check_permit_conflict(self, permit_type1: str, permit_type2: str) -> Dict or None:
        """Check if two permit types conflict."""
        dangerous_combinations = {
            ('HOT_WORK', 'CONFINED_SPACE'): {'type': 'HOT_WORK_IN_CONFINED_SPACE', 'severity': 'CRITICAL'},
            ('HOT_WORK', 'EXCAVATION'): {'type': 'HOT_WORK_NEAR_EXCAVATION', 'severity': 'WARNING'},
            ('ELECTRICAL', 'CONFINED_SPACE'): {'type': 'ELECTRICAL_IN_CONFINED_SPACE', 'severity': 'CRITICAL'},
            ('EXCAVATION', 'CONFINED_SPACE'): {'type': 'STRUCTURAL_HAZARD', 'severity': 'WARNING'},
        }
        
        key = tuple(sorted([permit_type1, permit_type2]))
        return dangerous_combinations.get(key)
    
    def check_permit_expiry(self) -> List[Dict]:
        """Check for permits expiring soon."""
        active_permits = get_active_permits()
        expiring_soon = []
        warning_threshold = timedelta(hours=1)
        current_time = datetime.now()
        
        for permit in active_permits:
            end_time = datetime.fromisoformat(permit['end_time'])
            time_remaining = end_time - current_time
            
            if timedelta(0) < time_remaining < warning_threshold:
                expiring_soon.append({
                    'permit_id': permit['permit_id'],
                    'location': permit['location'],
                    'minutes_remaining': int(time_remaining.total_seconds() / 60)
                })
        
        return expiring_soon
    
    def flag_dangerous_proximity(self, worker_location: str, active_hazards: List[str]) -> List[Dict]:
        """
        Flag workers in dangerous proximity to hazards.
        Used for real-time worker safety alerting.
        """
        active_permits = get_active_permits()
        proximity_alerts = []
        
        for permit in active_permits:
            if self._locations_overlap(worker_location, permit['location']):
                if permit['permit_type'] in self.high_risk_permit_types:
                    proximity_alerts.append({
                        'worker_location': worker_location,
                        'permit_id': permit['permit_id'],
                        'permit_type': permit['permit_type'],
                        'alert_type': 'PROXIMITY_WARNING',
                        'severity': 'HIGH'
                    })
        
        return proximity_alerts
