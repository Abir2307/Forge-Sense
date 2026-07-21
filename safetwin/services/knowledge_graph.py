"""
Knowledge Graph - Equipment, Permit, and Risk Relationship Management
Establishes and maintains semantic relationships between equipment, work permits,
and identified hazards for intelligent risk assessment and decision support.
"""

from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
import json
from safetwin.db.database import (
    register_equipment, get_equipment_by_id, get_equipment_by_location,
    get_active_permits, get_permit_hazards, link_permit_hazard,
    get_equipment_hazard_profile
)

class KnowledgeGraphNode:
    """Represents a node in the knowledge graph."""
    
    def __init__(self, node_id: str, node_type: str, properties: Dict):
        self.node_id = node_id
        self.node_type = node_type  # 'EQUIPMENT', 'PERMIT', 'HAZARD', 'LOCATION'
        self.properties = properties
        self.created_at = datetime.now().isoformat()
        self.edges = []  # Connected nodes
    
    def to_dict(self) -> Dict:
        return {
            'node_id': self.node_id,
            'type': self.node_type,
            'properties': self.properties,
            'created_at': self.created_at,
            'edge_count': len(self.edges)
        }

class KnowledgeGraphEdge:
    """Represents a relationship/edge in the knowledge graph."""
    
    def __init__(self, source_id: str, target_id: str, relation_type: str, 
                 attributes: Dict = None):
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type  # 'USES', 'REQUIRES_PERMIT', 'HAS_HAZARD', etc.
        self.attributes = attributes or {}
        self.created_at = datetime.now().isoformat()
        self.weight = attributes.get('risk_weight', 1.0) if attributes else 1.0
    
    def to_dict(self) -> Dict:
        return {
            'source': self.source_id,
            'target': self.target_id,
            'relation': self.relation_type,
            'attributes': self.attributes,
            'weight': self.weight,
            'created_at': self.created_at
        }

class SafetyKnowledgeGraph:
    """
    Knowledge graph for industrial safety domain.
    Manages relationships between equipment, permits, hazards, and locations.
    """
    
    # Predefined relationship types
    RELATION_TYPES = {
        'EQUIPMENT': {
            'LOCATED_AT': 'Equipment is located at',
            'REQUIRES_PERMIT': 'Equipment work requires permit',
            'HAS_HAZARD': 'Equipment has associated hazard',
            'OPERATED_BY': 'Equipment operated by personnel',
            'MAINTAINED_BY': 'Equipment maintained by personnel'
        },
        'PERMIT': {
            'FOR_EQUIPMENT': 'Permit is for equipment',
            'AT_LOCATION': 'Permit is at location',
            'REQUIRES_HAZARD_CONTROL': 'Permit requires hazard control',
            'CONFLICTS_WITH': 'Permit conflicts with another permit'
        },
        'HAZARD': {
            'ASSOCIATED_WITH_EQUIPMENT': 'Hazard associated with equipment',
            'MITIGATED_BY': 'Hazard mitigated by control',
            'TRIGGERED_BY': 'Hazard triggered by condition'
        },
        'LOCATION': {
            'CONTAINS_EQUIPMENT': 'Location contains equipment',
            'HAS_HAZARD': 'Location has hazard zone',
            'ADJACENT_TO': 'Location adjacent to other location'
        }
    }
    
    def __init__(self):
        """Initialize knowledge graph."""
        self.nodes = {}  # node_id -> KnowledgeGraphNode
        self.edges = []  # List of KnowledgeGraphEdge
        self.indices = {
            'by_type': {},  # type -> [node_ids]
            'by_location': {},  # location -> [node_ids]
            'hazard_map': {}  # hazard -> [equipment/locations]
        }
    
    def add_equipment_node(self, equipment_id: str, name: str, location: str,
                          equipment_type: str, risk_category: str) -> KnowledgeGraphNode:
        """Add equipment node to knowledge graph."""
        node = KnowledgeGraphNode(
            node_id=equipment_id,
            node_type='EQUIPMENT',
            properties={
                'name': name,
                'location': location,
                'type': equipment_type,
                'risk_category': risk_category,
                'maintenance_history': [],
                'incident_history': []
            }
        )
        
        self.nodes[equipment_id] = node
        
        # Update indices
        if 'EQUIPMENT' not in self.indices['by_type']:
            self.indices['by_type']['EQUIPMENT'] = []
        self.indices['by_type']['EQUIPMENT'].append(equipment_id)
        
        if location not in self.indices['by_location']:
            self.indices['by_location'][location] = []
        self.indices['by_location'][location].append(equipment_id)
        
        # Register in database
        register_equipment(equipment_id, name, location, equipment_type, 365, risk_category)
        
        return node
    
    def add_permit_node(self, permit_id: str, permit_type: str, location: str,
                       equipment_ids: List[str], hazard_types: List[str]) -> KnowledgeGraphNode:
        """Add permit node and establish relationships."""
        node = KnowledgeGraphNode(
            node_id=permit_id,
            node_type='PERMIT',
            properties={
                'type': permit_type,
                'location': location,
                'equipment_count': len(equipment_ids),
                'hazards_controlled': len(hazard_types)
            }
        )
        
        self.nodes[permit_id] = node
        
        # Create edges to equipment
        for equipment_id in equipment_ids:
            if equipment_id in self.nodes:
                edge = KnowledgeGraphEdge(
                    permit_id, equipment_id, 'FOR_EQUIPMENT',
                    {'permit_type': permit_type}
                )
                self.edges.append(edge)
                
                # Check for conflicts with other permits
                conflicts = self._check_permit_conflicts(permit_id, equipment_id)
                if conflicts:
                    for conflicting_permit in conflicts:
                        conflict_edge = KnowledgeGraphEdge(
                            permit_id, conflicting_permit, 'CONFLICTS_WITH',
                            {'conflict_severity': 'HIGH'}
                        )
                        self.edges.append(conflict_edge)
        
        # Create edges to hazards
        for hazard in hazard_types:
            edge = KnowledgeGraphEdge(
                permit_id, hazard, 'REQUIRES_HAZARD_CONTROL',
                {'hazard_type': hazard}
            )
            self.edges.append(edge)
            
            # Update hazard index
            if hazard not in self.indices['hazard_map']:
                self.indices['hazard_map'][hazard] = []
            self.indices['hazard_map'][hazard].append(permit_id)
        
        return node
    
    def add_hazard_node(self, hazard_id: str, hazard_type: str, description: str,
                       risk_level: str, mitigation_measures: List[str]) -> KnowledgeGraphNode:
        """Add hazard node to knowledge graph."""
        node = KnowledgeGraphNode(
            node_id=hazard_id,
            node_type='HAZARD',
            properties={
                'type': hazard_type,
                'description': description,
                'risk_level': risk_level,
                'mitigation_measures': mitigation_measures,
                'affected_equipment': [],
                'affected_locations': []
            }
        )
        
        self.nodes[hazard_id] = node
        
        # Update indices
        if 'HAZARD' not in self.indices['by_type']:
            self.indices['by_type']['HAZARD'] = []
        self.indices['by_type']['HAZARD'].append(hazard_id)
        
        if hazard_id not in self.indices['hazard_map']:
            self.indices['hazard_map'][hazard_id] = []
        
        return node
    
    def establish_equipment_hazard_link(self, equipment_id: str, hazard_id: str,
                                      exposure_type: str, severity: str) -> KnowledgeGraphEdge:
        """Establish relationship between equipment and hazard."""
        edge = KnowledgeGraphEdge(
            equipment_id, hazard_id, 'HAS_HAZARD',
            {'exposure_type': exposure_type, 'severity': severity}
        )
        self.edges.append(edge)
        
        # Update node properties
        if equipment_id in self.nodes:
            self.nodes[equipment_id].properties['hazards'].append(hazard_id)
        
        if hazard_id in self.nodes:
            self.nodes[hazard_id].properties['affected_equipment'].append(equipment_id)
        
        return edge
    
    def get_equipment_risk_profile(self, equipment_id: str) -> Dict:
        """
        Get comprehensive risk profile for equipment including:
        - Associated hazards
        - Active permits
        - Risk score
        - Mitigation measures
        """
        if equipment_id not in self.nodes:
            return {}
        
        equipment = self.nodes[equipment_id]
        risk_profile = {
            'equipment_id': equipment_id,
            'name': equipment.properties.get('name'),
            'location': equipment.properties.get('location'),
            'type': equipment.properties.get('type'),
            'risk_category': equipment.properties.get('risk_category'),
            'associated_hazards': [],
            'active_permits': [],
            'risk_score': 0.0,
            'mitigation_measures': set()
        }
        
        # Find hazards
        hazard_edges = [e for e in self.edges if e.source_id == equipment_id and e.relation_type == 'HAS_HAZARD']
        for edge in hazard_edges:
            if edge.target_id in self.nodes:
                hazard = self.nodes[edge.target_id]
                hazard_info = {
                    'hazard_id': edge.target_id,
                    'type': hazard.properties.get('type'),
                    'severity': edge.attributes.get('severity'),
                    'mitigation': hazard.properties.get('mitigation_measures', [])
                }
                risk_profile['associated_hazards'].append(hazard_info)
                risk_profile['mitigation_measures'].update(hazard.properties.get('mitigation_measures', []))
        
        # Find active permits
        permit_edges = [e for e in self.edges if e.target_id == equipment_id and e.relation_type == 'FOR_EQUIPMENT']
        for edge in permit_edges:
            if edge.source_id in self.nodes:
                permit = self.nodes[edge.source_id]
                risk_profile['active_permits'].append({
                    'permit_id': edge.source_id,
                    'type': permit.properties.get('type'),
                    'location': permit.properties.get('location')
                })
        
        # Calculate risk score
        risk_score = self._calculate_equipment_risk_score(equipment_id)
        risk_profile['risk_score'] = risk_score
        risk_profile['mitigation_measures'] = list(risk_profile['mitigation_measures'])
        
        return risk_profile
    
    def find_locations_with_hazards(self, hazard_type: str) -> List[Dict]:
        """Find all locations with a specific hazard type."""
        locations_with_hazard = []
        
        for hazard_id in self.indices['hazard_map'].get(hazard_type, []):
            if hazard_id in self.nodes:
                hazard = self.nodes[hazard_id]
                # Find equipment with this hazard
                affected_equipment = hazard.properties.get('affected_equipment', [])
                
                for equipment_id in affected_equipment:
                    if equipment_id in self.nodes:
                        eq = self.nodes[equipment_id]
                        location = eq.properties.get('location')
                        
                        # Check if location already in list
                        existing = next((l for l in locations_with_hazard if l['location'] == location), None)
                        if existing:
                            existing['affected_equipment'].append(equipment_id)
                        else:
                            locations_with_hazard.append({
                                'location': location,
                                'hazard_type': hazard_type,
                                'affected_equipment': [equipment_id],
                                'risk_level': hazard.properties.get('risk_level')
                            })
        
        return locations_with_hazard
    
    def find_dangerous_permit_combinations(self) -> List[Dict]:
        """
        Identify dangerous permit combinations using knowledge graph analysis.
        Returns list of conflicting permit pairs.
        """
        dangerous_combinations = []
        
        conflict_edges = [e for e in self.edges if e.relation_type == 'CONFLICTS_WITH']
        for edge in conflict_edges:
            if edge.source_id in self.nodes and edge.target_id in self.nodes:
                perm1 = self.nodes[edge.source_id]
                perm2 = self.nodes[edge.target_id]
                
                combination = {
                    'permit1_id': edge.source_id,
                    'permit1_type': perm1.properties.get('type'),
                    'permit2_id': edge.target_id,
                    'permit2_type': perm2.properties.get('type'),
                    'location': perm1.properties.get('location'),
                    'conflict_severity': edge.attributes.get('conflict_severity'),
                    'shared_equipment': self._find_shared_equipment(edge.source_id, edge.target_id)
                }
                dangerous_combinations.append(combination)
        
        return dangerous_combinations
    
    def get_related_incidents(self, equipment_id: str) -> List[Dict]:
        """Get historical incidents related to equipment."""
        if equipment_id not in self.nodes:
            return []
        
        equipment = self.nodes[equipment_id]
        return equipment.properties.get('incident_history', [])
    
    def add_incident_to_equipment(self, equipment_id: str, incident_info: Dict):
        """Record incident in equipment's history for pattern analysis."""
        if equipment_id in self.nodes:
            self.nodes[equipment_id].properties['incident_history'].append(incident_info)
    
    def query_hazards_by_location(self, location: str) -> List[Dict]:
        """Query all hazards at a location."""
        hazards = []
        
        if location in self.indices['by_location']:
            equipment_ids = self.indices['by_location'][location]
            
            for equipment_id in equipment_ids:
                # Find hazards for this equipment
                hazard_edges = [e for e in self.edges if e.source_id == equipment_id and e.relation_type == 'HAS_HAZARD']
                for edge in hazard_edges:
                    if edge.target_id in self.nodes:
                        hazard = self.nodes[edge.target_id]
                        hazard_info = {
                            'hazard_id': edge.target_id,
                            'type': hazard.properties.get('type'),
                            'equipment_id': equipment_id,
                            'severity': edge.attributes.get('severity'),
                            'mitigation': hazard.properties.get('mitigation_measures')
                        }
                        hazards.append(hazard_info)
        
        return hazards
    
    def _check_permit_conflicts(self, permit_id: str, equipment_id: str) -> List[str]:
        """Check for conflicting permits on same equipment."""
        conflicting_permits = []
        
        # Find other permits for same equipment
        permit_edges = [e for e in self.edges if e.target_id == equipment_id and e.relation_type == 'FOR_EQUIPMENT']
        
        for edge in permit_edges:
            other_permit = edge.source_id
            if other_permit != permit_id:
                # Check if permits are compatible
                if self._permits_conflict(permit_id, other_permit):
                    conflicting_permits.append(other_permit)
        
        return conflicting_permits
    
    def _permits_conflict(self, permit1_id: str, permit2_id: str) -> bool:
        """Check if two permits conflict."""
        if permit1_id not in self.nodes or permit2_id not in self.nodes:
            return False
        
        perm1_type = self.nodes[permit1_id].properties.get('type')
        perm2_type = self.nodes[permit2_id].properties.get('type')
        
        # Define conflicting permit types
        conflicts = {
            ('HOT_WORK', 'CONFINED_SPACE'),
            ('HOT_WORK', 'EXCAVATION'),
            ('ELECTRICAL', 'CONFINED_SPACE'),
            ('EXCAVATION', 'CONFINED_SPACE')
        }
        
        key = tuple(sorted([perm1_type, perm2_type]))
        return key in conflicts
    
    def _find_shared_equipment(self, permit1_id: str, permit2_id: str) -> List[str]:
        """Find equipment affected by both permits."""
        shared = []
        
        # Equipment for permit 1
        eq1_edges = [e for e in self.edges if e.source_id == permit1_id and e.relation_type == 'FOR_EQUIPMENT']
        eq1_ids = set(e.target_id for e in eq1_edges)
        
        # Equipment for permit 2
        eq2_edges = [e for e in self.edges if e.source_id == permit2_id and e.relation_type == 'FOR_EQUIPMENT']
        eq2_ids = set(e.target_id for e in eq2_edges)
        
        shared = list(eq1_ids & eq2_ids)
        return shared
    
    def _calculate_equipment_risk_score(self, equipment_id: str) -> float:
        """Calculate risk score for equipment."""
        if equipment_id not in self.nodes:
            return 0.0
        
        equipment = self.nodes[equipment_id]
        risk_category = equipment.properties.get('risk_category', 'LOW')
        
        # Base scores
        base_scores = {'LOW': 0.2, 'MEDIUM': 0.5, 'HIGH': 0.7, 'CRITICAL': 0.9}
        score = base_scores.get(risk_category, 0.5)
        
        # Hazard count adds to score
        hazard_edges = [e for e in self.edges if e.source_id == equipment_id and e.relation_type == 'HAS_HAZARD']
        hazard_modifier = min(0.2, len(hazard_edges) * 0.05)
        score += hazard_modifier
        
        # Incident history adds to score
        incidents = equipment.properties.get('incident_history', [])
        incident_modifier = min(0.1, len(incidents) * 0.02)
        score += incident_modifier
        
        return min(1.0, score)
    
    def export_graph(self) -> Dict:
        """Export knowledge graph as JSON."""
        return {
            'nodes': [node.to_dict() for node in self.nodes.values()],
            'edges': [edge.to_dict() for edge in self.edges],
            'indices': self.indices,
            'exported_at': datetime.now().isoformat()
        }
    
    def print_statistics(self) -> str:
        """Print knowledge graph statistics."""
        stats = f"""
KNOWLEDGE GRAPH STATISTICS
==========================
Total Nodes: {len(self.nodes)}
- Equipment: {len(self.indices['by_type'].get('EQUIPMENT', []))}
- Permits: {len(self.indices['by_type'].get('PERMIT', []))}
- Hazards: {len(self.indices['by_type'].get('HAZARD', []))}

Total Relationships: {len(self.edges)}
Locations Mapped: {len(self.indices['by_location'])}
Hazard Types: {len(self.indices['hazard_map'])}

Dangerous Permit Combinations: {len(self.find_dangerous_permit_combinations())}
"""
        return stats
