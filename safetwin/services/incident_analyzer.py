"""
Incident Pattern Intelligence Agent
Analyzes incident history, near-miss events, and regulatory documents to identify 
recurring patterns that manual investigations miss and surfaces them as actionable 
prevention priorities. RAG-ready for integration with incident corpus and regulatory documents.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import Counter
import json
from safetwin.db.database import (
    get_incidents_by_location, get_incident_patterns, get_near_miss_events,
    get_compliance_by_regulation
)

class IncidentPatternAnalyzer:
    """
    Analyzes incident history and near-miss events to detect patterns
    and correlate with regulatory requirements.
    """
    
    # Regulatory reference mapping for Indian industrial facilities
    REGULATORY_FRAMEWORK = {
        'OISD': 'Oil Industry Safety Directorate Guidelines',
        'DGMS': 'Directorate General of Mines Safety',
        'DGFASLI': 'Directorate General of Factory Advice Service and Labour Institutes',
        'FACTORY_ACT': 'Factories Act, 1948',
        'PSM': 'Process Safety Management'
    }
    
    # Known incident cause categories
    INCIDENT_CATEGORIES = {
        'gas_exposure': ['H2S', 'CO', 'CH4', 'NH3'],
        'thermal_hazards': ['fire', 'explosion', 'extreme_heat'],
        'mechanical_hazards': ['impact', 'crushing', 'entanglement'],
        'confined_space': ['asphyxiation', 'confined_space_entry'],
        'electrical': ['shock', 'arc_flash'],
        'chemical': ['chemical_burn', 'toxic_exposure'],
        'environmental': ['slips', 'falls', 'ergonomic']
    }
    
    def __init__(self):
        self.pattern_threshold = 3  # Minimum incidents to identify pattern
        self.near_miss_weight = 0.5  # Near-misses weighted as 50% of incidents
        
    def analyze_location_patterns(self, location: str, days: int = 90) -> Dict:
        """
        Analyze incident patterns for a specific location over time.
        
        Args:
            location: Plant location/zone identifier
            days: Historical period to analyze
            
        Returns:
            Dict with pattern analysis and risk assessment
        """
        incidents = get_incidents_by_location(location, limit=100)
        near_misses = get_near_miss_events(location, days=days)
        patterns = get_incident_patterns(location, days=days)
        
        analysis = {
            'location': location,
            'analysis_period_days': days,
            'total_incidents': len(incidents),
            'total_near_misses': len(near_misses),
            'severity_distribution': {},
            'incident_type_ranking': [],
            'repeat_patterns': [],
            'regulatory_violations': [],
            'risk_score': 0.0,
            'recommendations': []
        }
        
        # Analyze severity distribution
        severity_counts = Counter()
        for incident in incidents:
            severity_counts[incident['severity_level']] += 1
        analysis['severity_distribution'] = dict(severity_counts)
        
        # Rank incident types by frequency
        if patterns:
            analysis['incident_type_ranking'] = [
                {
                    'type': p['incident_type'],
                    'count': p['count'],
                    'max_severity': p['severity_level']
                }
                for p in sorted(patterns, key=lambda x: x['count'], reverse=True)
            ]
        
        # Identify repeat patterns
        analysis['repeat_patterns'] = self._identify_repeat_patterns(incidents, near_misses)
        
        # Correlate with regulatory requirements
        analysis['regulatory_violations'] = self._correlate_regulatory_requirements(incidents)
        
        # Calculate risk score
        analysis['risk_score'] = self._calculate_risk_score(
            len(incidents), len(near_misses), 
            severity_counts.get('FATAL', 0), 
            severity_counts.get('CRITICAL', 0)
        )
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(
            analysis['repeat_patterns'],
            analysis['incident_type_ranking']
        )
        
        return analysis
    
    def _identify_repeat_patterns(self, incidents: List[Dict], near_misses: List[Dict]) -> List[Dict]:
        """
        Identify recurring incident patterns and near-miss correlations.
        Returns prioritized list of patterns indicating compound risks.
        """
        patterns = []
        
        # Temporal patterns: incidents at similar times
        time_pattern = Counter()
        for incident in incidents:
            if incident['reported_at']:
                hour = int(incident['reported_at'].split('T')[1].split(':')[0])
                time_pattern[f"{hour:02d}:00"] += 1
        
        if time_pattern:
            most_dangerous_hour = time_pattern.most_common(1)[0]
            if most_dangerous_hour[1] >= self.pattern_threshold:
                patterns.append({
                    'pattern_type': 'TEMPORAL',
                    'description': f"Clustering at hour {most_dangerous_hour[0]} ({most_dangerous_hour[1]} incidents)",
                    'frequency': most_dangerous_hour[1],
                    'severity': 'HIGH' if most_dangerous_hour[1] >= 5 else 'MEDIUM',
                    'action_items': ['Review shift handover procedures', 'Analyze operator fatigue patterns']
                })
        
        # Equipment patterns: incidents involving same equipment
        equipment_pattern = Counter()
        for incident in incidents:
            if incident['description']:
                # Simple heuristic: extract equipment names from description
                keywords = ['pump', 'compressor', 'furnace', 'reactor', 'separator', 'heat_exchanger']
                for keyword in keywords:
                    if keyword.lower() in incident['description'].lower():
                        equipment_pattern[keyword] += 1
        
        for equipment, count in equipment_pattern.most_common():
            if count >= self.pattern_threshold:
                patterns.append({
                    'pattern_type': 'EQUIPMENT',
                    'equipment': equipment,
                    'incident_count': count,
                    'severity': 'HIGH' if count >= 5 else 'MEDIUM',
                    'action_items': ['Inspect equipment', 'Review maintenance logs', 'Consider equipment replacement']
                })
        
        # Near-miss to incident escalation patterns
        near_miss_descriptions = [nm['description'] for nm in near_misses]
        incident_descriptions = [inc['description'] for inc in incidents]
        
        common_descriptions = set()
        for nm_desc in near_miss_descriptions:
            for inc_desc in incident_descriptions:
                if nm_desc and inc_desc and nm_desc.lower()[:30] in inc_desc.lower():
                    common_descriptions.add((nm_desc[:50], inc_desc[:50]))
        
        if len(common_descriptions) > 0:
            patterns.append({
                'pattern_type': 'ESCALATION',
                'description': f'Near-miss events escalated to incidents ({len(common_descriptions)} cases)',
                'near_miss_to_incident_ratio': len(near_misses) / max(1, len(incidents)),
                'severity': 'CRITICAL',
                'action_items': [
                    'Implement immediate corrective actions from near-misses',
                    'Increase frequency of safety audits',
                    'Review permit-to-work procedures'
                ]
            })
        
        return patterns
    
    def _correlate_regulatory_requirements(self, incidents: List[Dict]) -> List[Dict]:
        """
        Correlate incidents with regulatory requirements and identify compliance gaps.
        """
        violations = []
        
        for incident in incidents:
            regulatory_ref = incident.get('regulatory_reference')
            if regulatory_ref:
                # Check for compliance checks related to this regulation
                compliance_checks = get_compliance_by_regulation(regulatory_ref)
                
                if compliance_checks:
                    violations.append({
                        'incident_id': incident['incident_id'],
                        'regulation': regulatory_ref,
                        'incident_type': incident['incident_type'],
                        'compliance_gaps': [
                            {
                                'check': c['check_description'],
                                'status': c['status'],
                                'due_date': c['due_date']
                            }
                            for c in compliance_checks if c['status'] != 'COMPLIANT'
                        ]
                    })
        
        return violations
    
    def _calculate_risk_score(self, incident_count: int, near_miss_count: int, 
                             fatal_count: int, critical_count: int) -> float:
        """
        Calculate location risk score (0.0-1.0).
        Higher score indicates higher risk.
        """
        # Weighted scoring
        fatality_weight = fatal_count * 1.0
        critical_weight = critical_count * 0.7
        incident_weight = incident_count * 0.2
        near_miss_contribution = near_miss_count * self.near_miss_weight * 0.1
        
        total_score = fatality_weight + critical_weight + incident_weight + near_miss_contribution
        
        # Normalize to 0-1 range
        # Assume score > 20 indicates maximum risk
        risk_score = min(1.0, total_score / 20.0)
        
        return risk_score
    
    def _generate_recommendations(self, patterns: List[Dict], incident_ranking: List[Dict]) -> List[str]:
        """Generate actionable recommendations based on patterns."""
        recommendations = []
        
        # Pattern-based recommendations
        for pattern in patterns:
            recommendations.extend(pattern.get('action_items', []))
        
        # Top incident type recommendations
        if incident_ranking:
            top_incident = incident_ranking[0]
            incident_type = top_incident['type']
            
            type_specific = {
                'gas_exposure': [
                    'Install/upgrade gas detection systems',
                    'Review confined space entry procedures',
                    'Increase ventilation system audits'
                ],
                'thermal_hazards': [
                    'Review hot work permit procedures',
                    'Inspect fire suppression systems',
                    'Conduct heat stress management training'
                ],
                'confined_space': [
                    'Implement mandatory atmosphere testing',
                    'Require rescue team standby',
                    'Review atmospheric monitoring procedures'
                ]
            }
            
            for category, recs in type_specific.items():
                if category.lower() in incident_type.lower():
                    recommendations.extend(recs)
        
        return recommendations[:10]  # Top 10 recommendations
    
    def get_near_miss_escalation_risk(self, location: str, days: int = 30) -> Dict:
        """
        Calculate risk of near-miss events escalating to incidents.
        Returns probability and recommended preventive actions.
        """
        recent_near_misses = get_near_miss_events(location, days=days)
        recent_incidents = get_incidents_by_location(location, limit=50)
        
        # Filter to recent incidents
        recent_incidents = [
            i for i in recent_incidents 
            if i['reported_at'] and 
            (datetime.now() - datetime.fromisoformat(i['reported_at'])).days <= days
        ]
        
        escalation_risk = {
            'location': location,
            'near_miss_count': len(recent_near_misses),
            'incident_count': len(recent_incidents),
            'escalation_probability': 0.0,
            'high_risk_categories': [],
            'preventive_actions': []
        }
        
        if len(recent_near_misses) > 0:
            # Simple escalation probability
            # Assumption: 1 incident for every 3-5 near-misses indicates escalation risk
            escalation_ratio = len(recent_incidents) / len(recent_near_misses)
            escalation_risk['escalation_probability'] = min(1.0, escalation_ratio / 0.33)
            
            # Identify high-risk near-miss categories
            for nm in recent_near_misses:
                risk = nm.get('potential_risk', '')
                if risk:
                    escalation_risk['high_risk_categories'].append(risk)
            
            escalation_risk['high_risk_categories'] = list(set(escalation_risk['high_risk_categories']))[:5]
        
        # Generate preventive actions
        if escalation_risk['escalation_probability'] > 0.5:
            escalation_risk['preventive_actions'] = [
                'Conduct emergency review of near-miss management procedures',
                'Implement immediate corrective actions from near-miss reports',
                'Increase safety audits and inspections',
                'Provide safety refresher training to all personnel',
                'Review and strengthen hazard communication'
            ]
        
        return escalation_risk
    
    def generate_incident_intelligence_report(self, location: str) -> str:
        """
        Generate a comprehensive incident intelligence report (RAG-ready format).
        Can be used as context for LLM-based analysis and recommendations.
        """
        analysis = self.analyze_location_patterns(location, days=365)
        escalation_risk = self.get_near_miss_escalation_risk(location)
        
        report = f"""
INCIDENT PATTERN INTELLIGENCE REPORT
Location: {location}
Generated: {datetime.now().isoformat()}

EXECUTIVE SUMMARY
================
Risk Score: {analysis['risk_score']:.2f}/1.0
Total Incidents (Past 90 days): {analysis['total_incidents']}
Total Near-Misses (Past 90 days): {analysis['total_near_misses']}
Escalation Probability: {escalation_risk['escalation_probability']:.2%}

SEVERITY DISTRIBUTION
=====================
{json.dumps(analysis['severity_distribution'], indent=2)}

TOP INCIDENT TYPES
==================
"""
        for rank, incident_type in enumerate(analysis['incident_type_ranking'][:5], 1):
            report += f"{rank}. {incident_type['type']}: {incident_type['count']} incidents\n"
        
        report += f"""

IDENTIFIED PATTERNS
===================
"""
        for pattern in analysis['repeat_patterns']:
            report += f"\n- {pattern['pattern_type']}: {pattern.get('description', pattern.get('equipment'))}\n"
            report += f"  Severity: {pattern.get('severity', 'UNKNOWN')}\n"
        
        report += f"""

CRITICAL RECOMMENDATIONS
========================
"""
        for i, rec in enumerate(analysis['recommendations'][:5], 1):
            report += f"{i}. {rec}\n"
        
        return report
