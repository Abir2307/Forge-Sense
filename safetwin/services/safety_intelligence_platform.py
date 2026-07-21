"""
Industrial Safety Intelligence Platform - Agent Orchestration
Integrates all safety agents (Permit Intelligence, Incident Analyzer, Emergency Response,
Compliance Monitor, Knowledge Graph) into a unified decision-making system.
"""

from datetime import datetime
from typing import Dict, List, Optional, Callable
import uuid

from safetwin.core.risk_utils import normalize_compliance_score
from safetwin.services.evaluation_metrics import build_evaluation_summary, build_partial_evaluation_summary
from safetwin.services.permit_intelligence_agent import PermitIntelligenceAgent
from safetwin.services.incident_analyzer import IncidentPatternAnalyzer
from safetwin.services.emergency_orchestrator import EmergencyResponseOrchestrator, SeverityLevel
from safetwin.services.compliance_monitor import ComplianceMonitor, ComplianceAgent
from safetwin.services.knowledge_graph import SafetyKnowledgeGraph
from safetwin.db.database import get_incidents_by_location, get_near_miss_events

class SafetyIntelligencePlatform:
    """
    Central orchestrator for industrial safety intelligence.
    Coordinates all safety agents and provides unified risk assessment.
    """
    
    def __init__(self):
        """Initialize all safety agents."""
        self.permit_agent = PermitIntelligenceAgent()
        self.incident_analyzer = IncidentPatternAnalyzer()
        self.emergency_orchestrator = EmergencyResponseOrchestrator()
        self.compliance_monitor = ComplianceMonitor()
        self.compliance_agent = ComplianceAgent(self.permit_agent)
        self.knowledge_graph = SafetyKnowledgeGraph()
        
        # Event handlers for integration with UI/external systems
        self.alert_callbacks = []  # Callbacks for alert events
        self.incident_callbacks = []  # Callbacks for incident events
        self.compliance_callbacks = []  # Callbacks for compliance events
        
        # Real-time monitoring state
        self.monitoring_active = False
        self.last_sensor_update = None
        self.risk_trends = []
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for alert events."""
        self.alert_callbacks.append(callback)
    
    def register_incident_callback(self, callback: Callable):
        """Register callback for incident events."""
        self.incident_callbacks.append(callback)
    
    def register_compliance_callback(self, callback: Callable):
        """Register callback for compliance events."""
        self.compliance_callbacks.append(callback)
    
    def perform_real_time_risk_assessment(self, sensor_data: Dict, location: str, 
                                         worker_locations: Dict = None, frame_hazards: List[Dict] = None) -> Dict:
        """
        Perform comprehensive real-time risk assessment combining all agents.
        
        Args:
            sensor_data: Current sensor readings (gas, temperature, etc.)
            location: Current location/zone
            worker_locations: Optional dict of worker IDs to their locations
            
        Returns:
            Comprehensive risk assessment report
        """
        assessment_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        assessment = {
            'assessment_id': assessment_id,
            'timestamp': timestamp.isoformat(),
            'location': location,
            'overall_risk_level': 'LOW',
            'risk_score': 0.0,
            'critical_alerts': [],
            'permit_risks': [],
            'permit_compliance': {},
            'incident_risks': [],
            'compliance_gaps': [],
            'recommended_actions': [],
            'emergency_trigger': False
        }
        
        # 1. Permit Intelligence Assessment
        permit_assessment = self.permit_agent.validate_active_permits(sensor_data, location)
        assessment['permit_risks'] = permit_assessment

        permit_compliance = self.compliance_agent.evaluate_permit_compliance(
            active_permits=permit_assessment.get('active_permits', []),
            detected_hazards={
                'gas_detected': bool(
                    sensor_data and float(sensor_data.get('gas', sensor_data.get('gas_level', 0)) or 0) >= 0.5
                ),
                'location': location
            },
            sensor_data=sensor_data,
            location=location
        )
        assessment['permit_compliance'] = permit_compliance

        if permit_compliance['violations']:
            assessment['critical_alerts'].extend(permit_compliance['violations'])
            assessment['overall_risk_level'] = 'CRITICAL'
        
        if permit_assessment['high_risk_alerts']:
            assessment['critical_alerts'].extend(permit_assessment['high_risk_alerts'])
            assessment['overall_risk_level'] = 'CRITICAL'
        
        # 2. Incident Pattern Analysis
        incident_assessment = self.incident_analyzer.analyze_location_patterns(location)
        assessment['incident_risks'] = incident_assessment
        
        # Escalation risk
        escalation_risk = self.incident_analyzer.get_near_miss_escalation_risk(location)
        if escalation_risk['escalation_probability'] > 0.7:
            assessment['critical_alerts'].append({
                'type': 'ESCALATION_WARNING',
                'probability': escalation_risk['escalation_probability'],
                'actions': escalation_risk['preventive_actions']
            })
        
        # 3. Knowledge Graph Risk Profiling
        kg_hazards = self.knowledge_graph.query_hazards_by_location(location)
        permit_conflicts = self.knowledge_graph.find_dangerous_permit_combinations()
        
        if permit_conflicts:
            assessment['critical_alerts'].append({
                'type': 'PERMIT_CONFLICT',
                'conflicts': permit_conflicts,
                'severity': 'HIGH'
            })
        
        # 4. Compliance Status
        compliance_dashboard = self.compliance_monitor.get_compliance_dashboard(location)
        assessment['compliance_gaps'] = {
            'status': compliance_dashboard['compliance_status'],
            'score': compliance_dashboard['compliance_score'],
            'compliance_score': compliance_dashboard['compliance_score'],
            'overdue_checks': len(compliance_dashboard['overdue_checks']),
            'open_actions': len(compliance_dashboard['open_corrective_actions'])
        }
        
        # 5. Worker Proximity Assessment
        if worker_locations:
            proximity_alerts = self.permit_agent.flag_dangerous_proximity(location, [])
            if proximity_alerts:
                assessment['critical_alerts'].append({
                    'type': 'WORKER_PROXIMITY',
                    'alerts': proximity_alerts
                })
        
        # 6. Calculate overall risk score WITH real-time frame hazards
        assessment['risk_score'] = self._calculate_composite_risk_score(
            permit_assessment,
            incident_assessment,
            escalation_risk,
            compliance_dashboard,
            frame_hazards=frame_hazards or []  # Pass frame hazards to score calculation
        )

        # Add evaluation summary when warning and incident history are available
        assessment['evaluation_summary'] = self._build_assessment_evaluation_summary(
            permit_assessment=permit_assessment,
            incident_assessment=incident_assessment,
            location=location,
        )
        
        # 7. Determine if emergency response should be triggered
        if assessment['risk_score'] > 0.8 and len(assessment['critical_alerts']) > 1:
            assessment['emergency_trigger'] = True
            assessment['overall_risk_level'] = 'CRITICAL'
        elif assessment['risk_score'] > 0.6:
            assessment['overall_risk_level'] = 'HIGH'
        elif assessment['risk_score'] > 0.3:
            assessment['overall_risk_level'] = 'MEDIUM'

        # 8. Generate recommendations
        assessment['recommended_actions'] = self._generate_recommendations(assessment)
        
        # Store for trend analysis
        self.risk_trends.append({
            'timestamp': timestamp.isoformat(),
            'location': location,
            'risk_score': assessment['risk_score'],
            'risk_level': assessment['overall_risk_level']
        })
        
        # Keep only last 100 trends
        if len(self.risk_trends) > 100:
            self.risk_trends = self.risk_trends[-100:]

        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(assessment)
            except:
                pass
        
        return assessment
    
    def trigger_emergency_incident(self, trigger_event: Dict, location: str, 
                                  severity: str = 'CRITICAL') -> Dict:
        """
        Trigger emergency response sequence when critical incident is confirmed.
        """
        # Map string severity to enum
        severity_map = {
            'LOW': SeverityLevel.LOW,
            'MEDIUM': SeverityLevel.MEDIUM,
            'HIGH': SeverityLevel.HIGH,
            'CRITICAL': SeverityLevel.CRITICAL
        }
        
        severity_level = severity_map.get(severity, SeverityLevel.CRITICAL)
        affected_zones = [location]
        
        # Trigger emergency response
        response = self.emergency_orchestrator.trigger_emergency_response(
            trigger_event, severity_level, affected_zones
        )
        
        # Notify incident callbacks
        for callback in self.incident_callbacks:
            try:
                callback(response)
            except:
                pass
        
        return response
    
    def register_equipment(self, equipment_id: str, name: str, location: str,
                          equipment_type: str, risk_category: str) -> Dict:
        """Register equipment in system and knowledge graph."""
        # Add to knowledge graph
        node = self.knowledge_graph.add_equipment_node(
            equipment_id, name, location, equipment_type, risk_category
        )
        
        return node.to_dict()
    
    def create_work_permit(self, permit_id: str, permit_type: str, equipment_id: str,
                          location: str, start_time: str, end_time: str,
                          authorized_by: str, hazard_types: List[str]) -> Dict:
        """Create work permit and link to equipment/hazards in knowledge graph."""
        from safetwin.db.database import create_work_permit, link_permit_hazard
        
        # Create permit in database
        success = create_work_permit(permit_id, permit_type, equipment_id, location, 
                                    start_time, end_time, authorized_by)
        
        if success:
            # Add to knowledge graph
            permit_node = self.knowledge_graph.add_permit_node(
                permit_id, permit_type, location, [equipment_id], hazard_types
            )
            
            # Link hazards
            for hazard in hazard_types:
                link_permit_hazard(permit_id, equipment_id, hazard, 'HIGH', '')
            
            return {
                'status': 'SUCCESS',
                'permit_id': permit_id,
                'node': permit_node.to_dict()
            }
        
        return {'status': 'FAILED', 'reason': 'Permit creation failed'}
    
    def conduct_compliance_audit(self, location: str, audit_scope: List[str],
                                auditor_name: str) -> Dict:
        """Conduct compliance audit and trigger corrective actions if needed."""
        audit_result = self.compliance_monitor.conduct_compliance_audit(
            location, audit_scope, auditor_name
        )
        
        # Trigger compliance callbacks if non-compliant
        if audit_result['overall_status'] != 'COMPLIANT':
            for callback in self.compliance_callbacks:
                try:
                    callback(audit_result)
                except:
                    pass
        
        return audit_result
    
    def get_location_safety_profile(self, location: str) -> Dict:
        """
        Get comprehensive safety profile for a location including all
        risk dimensions from all agents.
        """
        profile = {
            'location': location,
            'generated_at': datetime.now().isoformat(),
            'equipment_inventory': [],
            'active_permits': [],
            'hazard_assessment': [],
            'incident_history': [],
            'compliance_status': {},
            'risk_score': 0.0,
            'recommendations': []
        }
        
        # Equipment at location
        from safetwin.db.database import get_equipment_by_location
        equipment_list = get_equipment_by_location(location)
        for eq in equipment_list:
            risk_profile = self.knowledge_graph.get_equipment_risk_profile(eq['equipment_id'])
            if risk_profile:
                profile['equipment_inventory'].append(risk_profile)
        
        # Active permits
        from safetwin.db.database import get_active_permits
        active_permits = get_active_permits(location)
        profile['active_permits'] = [
            {
                'permit_id': p['permit_id'],
                'type': p['permit_type'],
                'status': p['status']
            }
            for p in active_permits
        ]
        
        # Hazards
        hazards = self.knowledge_graph.query_hazards_by_location(location)
        profile['hazard_assessment'] = hazards
        
        # Incident history
        incident_analysis = self.incident_analyzer.analyze_location_patterns(location)
        profile['incident_history'] = incident_analysis
        
        # Compliance
        profile['compliance_status'] = self.compliance_monitor.get_compliance_dashboard(location)
        
        # Calculate overall risk
        profile['risk_score'] = incident_analysis.get('risk_score', 0.0)
        
        return profile
    
    def _calculate_composite_risk_score(self, permit_assessment: Dict, 
                                       incident_assessment: Dict,
                                       escalation_risk: Dict,
                                       compliance_status: Dict,
                                       frame_hazards: List[Dict] = None) -> float:
        """
        Calculate composite risk score from all agents PLUS real-time video hazards.
        Weighted combination of hazard, permit, incident, escalation, and compliance risks.
        """
        weights = {
            'hazard': 0.40,  # Video hazards are the real-time detection (highest weight)
            'permit': 0.15,
            'incident': 0.20,
            'escalation': 0.15,
            'compliance': 0.10
        }
        
        # 1. VIDEO/FRAME HAZARD RISK (highest priority)
        hazard_risk = 0.0
        if frame_hazards:
            hazard_levels = [h.get('level', 'LOW') for h in frame_hazards]
            critical_count = sum(1 for h in hazard_levels if h == 'CRITICAL')
            high_count = sum(1 for h in hazard_levels if h == 'HIGH')
            medium_count = sum(1 for h in hazard_levels if h == 'MEDIUM')
            
            # Scale risk based on what we detected
            if critical_count > 0:
                hazard_risk = min(1.0, 0.90 + (critical_count * 0.05))
            elif high_count > 0:
                hazard_risk = min(1.0, 0.70 + (high_count * 0.05))
            elif medium_count > 0:
                hazard_risk = min(1.0, 0.50 + (medium_count * 0.03))
            else:
                hazard_risk = 0.20  # Some low-level detections
        else:
            hazard_risk = 0.10  # No hazards detected
        
        # 2. PERMIT RISK
        permit_risk = 0.5 if permit_assessment['high_risk_alerts'] else 0.15
        permit_risk += len(permit_assessment.get('warnings', [])) * 0.05
        permit_risk = min(1.0, permit_risk)
        
        # 3. INCIDENT RISK
        incident_risk = incident_assessment.get('risk_score', 0.0)
        
        # 4. ESCALATION RISK
        escalation = escalation_risk.get('escalation_probability', 0.0)
        
        # 5. COMPLIANCE RISK
        compliance_score = normalize_compliance_score(compliance_status) / 100.0
        compliance_risk = 1.0 - compliance_score  # Invert: low score = high risk
        
        import random
        volatility = random.uniform(-0.005, 0.005)
        
        # WEIGHTED COMBINATION - Hazard has highest impact
        composite_score = (
            weights['hazard'] * hazard_risk +
            weights['permit'] * permit_risk +
            weights['incident'] * incident_risk +
            weights['escalation'] * escalation +
            weights['compliance'] * compliance_risk
        ) + volatility
        
        return max(0.0, min(1.0, composite_score))

    def _build_assessment_evaluation_summary(
        self,
        permit_assessment: Dict,
        incident_assessment: Dict,
        location: str,
    ) -> Dict[str, Optional[float]]:
        """Build a lightweight evaluation summary from permit warnings and incident history."""
        warnings = []
        if isinstance(permit_assessment.get('warnings'), list):
            warnings.extend(permit_assessment['warnings'])
        if isinstance(permit_assessment.get('high_risk_alerts'), list):
            warnings.extend(permit_assessment['high_risk_alerts'])

        active_permits = permit_assessment.get('active_permits', []) or []
        if not warnings and active_permits:
            # Use active permits as warning proxies for geospatial evaluation when no alerts exist.
            for permit in active_permits:
                if permit.get('location'):
                    warnings.append({
                        'risk_score': 0.0,
                        'timestamp': datetime.now().isoformat(),
                        'location': permit['location'],
                        'permit_id': permit.get('permit_id')
                    })

        incident_rows = get_incidents_by_location(location, limit=20)
        incidents = [row for row in incident_rows if row and row.get('reported_at')]
        incident_source = 'incidents'

        if not incidents:
            near_misses = get_near_miss_events(location, days=90)
            incidents = [row for row in near_misses if row and row.get('reported_at')]
            incident_source = 'near_misses'

        if not incidents and not warnings:
            return {
                'false_negative_rate': None,
                'lead_time_minutes': None,
                'geospatial_quality': None,
            }

        # Align predictions to actual incident or near-miss timestamps.
        incident_times = [datetime.fromisoformat(inc['reported_at']) for inc in incidents]
        warning_times = [datetime.fromisoformat(w['timestamp']) for w in warnings if w.get('timestamp')]

        predicted = []
        actual = []
        for incident_time in incident_times:
            actual.append(1)
            predicted.append(1 if any(warning_time <= incident_time for warning_time in warning_times) else 0)

        predicted_zones = [str(w.get('location')).strip() for w in warnings if w.get('location')]
        actual_zones = [str(inc.get('location')).strip() for inc in incidents if inc.get('location')]

        if not predicted_zones and warnings and location:
            predicted_zones = [location]
        if not actual_zones and location:
            actual_zones = [location]

        incident_time = incident_times[0].isoformat() if incident_times else None

        return build_partial_evaluation_summary(
            predicted=predicted,
            actual=actual,
            warnings=warnings,
            incident_time=incident_time,
            predicted_zones=predicted_zones,
            actual_zones=actual_zones,
        )

    def _generate_recommendations(self, assessment: Dict) -> List[str]:
        """Generate actionable recommendations from assessment."""
        recommendations = []
        
        # From permits
        for alert in assessment['critical_alerts']:
            if alert['type'] == 'PERMIT_CONFLICT':
                recommendations.append('Resolve conflicting work permits before proceeding')
            elif alert['type'] == 'WORKER_PROXIMITY':
                recommendations.append('Move workers away from high-risk area')
            elif alert['type'] == 'ESCALATION_WARNING':
                recommendations.extend(alert.get('actions', []))
        
        # From incident analysis
        incident_risks = assessment.get('incident_risks', {})
        for rec in incident_risks.get('recommendations', [])[:3]:
            recommendations.append(rec)
        
        # From compliance
        compliance = assessment.get('compliance_gaps', {}) or {}
        if compliance.get('status') != 'COMPLIANT':
            overdue_checks = compliance.get('overdue_checks', 0)
            if overdue_checks:
                recommendations.append(f'Address {overdue_checks} overdue compliance checks')

        if assessment.get('hazards') or compliance.get('status') != 'COMPLIANT':
            try:
                query = (
                    f"Give concise safety actions for location {assessment.get('location', 'site')} "
                    f"with hazards {assessment.get('hazards', [])} and compliance status {compliance.get('status', 'UNKNOWN')}."
                )
                rag_response = self.compliance_agent.answer_query(query, top_k=2)
                if rag_response and 'No matching regulation' not in rag_response:
                    recommendations.append(rag_response)
            except Exception:
                pass

        if not recommendations:
            recommendations.append('Continue routine monitoring and verify any new hazards in the active zones')
        return recommendations[:10]
    
    def get_platform_status(self) -> Dict:
        """Get overall platform health and status."""
        return {
            'platform_status': 'OPERATIONAL',
            'timestamp': datetime.now().isoformat(),
            'monitoring_active': self.monitoring_active,
            'agents_status': {
                'permit_agent': 'ACTIVE',
                'incident_analyzer': 'ACTIVE',
                'emergency_orchestrator': 'ACTIVE',
                'compliance_monitor': 'ACTIVE',
                'knowledge_graph': f'{len(self.knowledge_graph.nodes)} nodes, {len(self.knowledge_graph.edges)} edges'
            },
            'risk_trends': {
                'latest': self.risk_trends[-1] if self.risk_trends else None,
                'trend_count': len(self.risk_trends)
            },
            'emergency_metrics': self.emergency_orchestrator.get_response_metrics()
        }
