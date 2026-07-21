"""
Quality & Compliance Audit Agent
Continuously monitors safety procedures, inspection records, and statutory compliance 
documentation against regulatory standards (OISD, DGMS, Factory Act) — flagging 
deviations before audits and generating corrective action workflows automatically.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from enum import Enum
from pathlib import Path
import hashlib
import math
import re
import uuid

from safetwin.services.permit_intelligence_agent import PermitIntelligenceAgent

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover - lightweight fallback when langchain_core is unavailable
    class Document:  # type: ignore
        def __init__(self, page_content: str, metadata: Dict = None):
            self.page_content = page_content
            self.metadata = metadata or {}

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - PDF parsing fallback
    PdfReader = None

class ComplianceStatus(Enum):
    """Compliance status indicators."""
    COMPLIANT = "COMPLIANT"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    NON_COMPLIANT = "NON_COMPLIANT"
    EXPIRED = "EXPIRED"
    SCHEDULED = "SCHEDULED"

class RegulatoryStandard(Enum):
    """Indian industrial regulatory standards."""
    OISD = "OISD"  # Oil Industry Safety Directorate
    DGMS = "DGMS"  # Directorate General of Mines Safety
    DGFASLI = "DGFASLI"  # Factory advice service
    FACTORY_ACT = "FACTORY_ACT"  # Factories Act 1948
    IE_RULES = "IE_RULES"  # Indian Electricity Rules
    PSM = "PSM"  # Process Safety Management

class ComplianceMonitor:
    """
    Continuously monitors safety procedures and statutory compliance
    against Indian industrial regulatory standards.
    """
    
    # Compliance check intervals (days)
    CHECK_INTERVALS = {
        'gas_detector_calibration': 30,
        'fire_extinguisher_inspection': 365,
        'pressure_relief_testing': 365,
        'safety_equipment_inspection': 90,
        'confined_space_procedures': 365,
        'emergency_response_drill': 180,
        'safety_audit': 90,
        'worker_training_refresh': 365,
        'equipment_maintenance': 180,
        'permit_to_work_audit': 30
    }
    
    # Regulatory requirements mapping
    REGULATORY_CHECKLIST = {
        'OISD': {
            'gas_detector_calibration': 'OISD-GDN-121: Gas Detection System',
            'pressure_relief_testing': 'OISD-GDN-131: Pressure Relief Devices',
            'permit_to_work_audit': 'OISD-STD-149: Permit to Work'
        },
        'DGFASLI': {
            'safety_equipment_inspection': 'Safety Equipments - Factories Act',
            'worker_training_refresh': 'Worker Safety Training - Rule 98',
            'emergency_response_drill': 'Emergency Procedures - Rule 115'
        },
        'FACTORY_ACT': {
            'confined_space_procedures': 'Confined Space Procedures - Schedule 3',
            'equipment_maintenance': 'Equipment Safety - Rule 114',
            'safety_audit': 'Safety Audits - Section 42'
        }
    }
    
    def __init__(self):
        """Initialize compliance monitor."""
        self.compliance_records = {}  # check_id -> compliance record
        self.audit_findings = []  # List of audit findings
        self.corrective_actions = {}  # action_id -> action details
        self.compliance_schedule = {}  # check_type -> next check date
        
    def create_compliance_check(self, check_type: str, standard: RegulatoryStandard,
                               location: str, responsible_officer: str) -> Dict:
        """
        Create a new compliance check.
        
        Args:
            check_type: Type of check (e.g., 'gas_detector_calibration')
            standard: Applicable regulatory standard
            location: Location where check is performed
            responsible_officer: Officer conducting the check
            
        Returns:
            Dict with check details
        """
        check_id = str(uuid.uuid4())
        check = {
            'check_id': check_id,
            'check_type': check_type,
            'standard': standard.value,
            'location': location,
            'responsible_officer': responsible_officer,
            'created_at': datetime.now().isoformat(),
            'scheduled_date': self._calculate_next_check_date(check_type),
            'status': ComplianceStatus.SCHEDULED.value,
            'findings': [],
            'non_conformances': [],
            'corrective_actions': []
        }
        
        self.compliance_records[check_id] = check
        
        return check
    
    def conduct_compliance_audit(self, audit_location: str, audit_scope: List[str],
                                auditor_name: str) -> Dict:
        """
        Conduct comprehensive compliance audit for a location.
        
        Args:
            audit_location: Location being audited
            audit_scope: List of check types to audit
            auditor_name: Name of auditing officer
            
        Returns:
            Dict with audit results and findings
        """
        audit_id = str(uuid.uuid4())
        audit_start = datetime.now()
        
        audit = {
            'audit_id': audit_id,
            'location': audit_location,
            'auditor': auditor_name,
            'started_at': audit_start.isoformat(),
            'scope': audit_scope,
            'findings': [],
            'overall_status': ComplianceStatus.COMPLIANT.value,
            'non_conformances': [],
            'observations': [],
            'risk_areas': []
        }
        
        # Execute compliance checks
        for check_type in audit_scope:
            finding = self._audit_check_area(check_type, audit_location)
            audit['findings'].append(finding)
            
            if finding['status'] == ComplianceStatus.NON_COMPLIANT.value:
                audit['overall_status'] = ComplianceStatus.NON_COMPLIANT.value
                audit['non_conformances'].append(finding)
            elif finding['status'] == ComplianceStatus.NEEDS_ATTENTION.value:
                if audit['overall_status'] != ComplianceStatus.NON_COMPLIANT.value:
                    audit['overall_status'] = ComplianceStatus.NEEDS_ATTENTION.value
                audit['observations'].append(finding)
        
        # Identify risk areas
        audit['risk_areas'] = self._identify_risk_areas(audit['non_conformances'])
        
        # Generate corrective action plan
        if audit['non_conformances']:
            audit['corrective_action_plan'] = self._generate_corrective_action_plan(
                audit_id, audit['non_conformances'], audit_location
            )
        
        audit['completed_at'] = datetime.now().isoformat()
        audit['duration_minutes'] = int((datetime.now() - audit_start).total_seconds() / 60)
        
        self.audit_findings.append(audit)
        
        return audit
    
    def _audit_check_area(self, check_type: str, location: str) -> Dict:
        """Audit a specific compliance area."""
        finding = {
            'check_type': check_type,
            'location': location,
            'audit_date': datetime.now().isoformat(),
            'status': ComplianceStatus.COMPLIANT.value,
            'observations': [],
            'non_conformances': [],
            'recommendations': []
        }
        
        # Simulate compliance check based on check type
        check_logic = self._get_check_logic(check_type)
        finding.update(check_logic)
        
        return finding
    
    def _get_check_logic(self, check_type: str) -> Dict:
        """Get compliance check logic and evaluation criteria."""
        checks = {
            'gas_detector_calibration': {
                'criteria': [
                    'Calibration within past 30 days',
                    'Calibration records available',
                    'Equipment functioning properly'
                ],
                'status': ComplianceStatus.COMPLIANT.value,
                'observations': ['Gas detector calibration up to date'],
                'regulatory_reference': 'OISD-GDN-121'
            },
            'fire_extinguisher_inspection': {
                'criteria': [
                    'Annual inspection completed',
                    'Pressure gauge in green zone',
                    'No visible damage',
                    'Access not blocked'
                ],
                'status': ComplianceStatus.COMPLIANT.value,
                'observations': ['Fire extinguishers properly maintained'],
                'regulatory_reference': 'DGFASLI Guidelines'
            },
            'pressure_relief_testing': {
                'criteria': [
                    'Annual pressure test completed',
                    'Test records documented',
                    'All relief valves functional'
                ],
                'status': ComplianceStatus.NEEDS_ATTENTION.value,
                'observations': ['Last test was 13 months ago'],
                'non_conformances': ['Pressure relief test overdue by ~1 month'],
                'recommendations': ['Schedule pressure relief testing immediately'],
                'regulatory_reference': 'OISD-GDN-131'
            },
            'confined_space_procedures': {
                'criteria': [
                    'Written procedures available',
                    'Atmosphere testing before entry',
                    'Rescue equipment present',
                    'Personnel trained'
                ],
                'status': ComplianceStatus.COMPLIANT.value,
                'observations': ['Confined space procedures documented and practiced'],
                'regulatory_reference': 'Factories Act Schedule 3'
            },
            'emergency_response_drill': {
                'criteria': [
                    'Drill conducted in past 6 months',
                    'All personnel participated',
                    'Observations documented',
                    'Response time within limits'
                ],
                'status': ComplianceStatus.NEEDS_ATTENTION.value,
                'observations': ['Last drill was 5.5 months ago, schedule next one'],
                'recommendations': ['Conduct emergency response drill this month'],
                'regulatory_reference': 'DGFASLI Rule 115'
            },
            'safety_equipment_inspection': {
                'criteria': [
                    'Quarterly inspection completed',
                    'All equipment functional',
                    'Records maintained',
                    'Maintenance log updated'
                ],
                'status': ComplianceStatus.COMPLIANT.value,
                'observations': ['All safety equipment in working condition'],
                'regulatory_reference': 'DGFASLI Guidelines'
            },
            'permit_to_work_audit': {
                'criteria': [
                    'Permits issued correctly',
                    'Authorizations in place',
                    'Conditions met before work',
                    'Closure documentation complete'
                ],
                'status': ComplianceStatus.NEEDS_ATTENTION.value,
                'observations': ['2 permits found without proper ground hazard assessment'],
                'non_conformances': ['Ground hazard assessment missing on 2 permits'],
                'recommendations': [
                    'Retrain permit issuing officers on ground hazard assessment',
                    'Implement checklist validation in permit system'
                ],
                'regulatory_reference': 'OISD-STD-149'
            }
        }
        
        return checks.get(check_type, {
            'status': ComplianceStatus.SCHEDULED.value,
            'observations': ['Check type not configured']
        })
    
    def _identify_risk_areas(self, non_conformances: List[Dict]) -> List[Dict]:
        """Identify and categorize risk areas from audit findings."""
        risk_areas = []
        risk_categories = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': []
        }
        
        for finding in non_conformances:
            check_type = finding['check_type']
            
            # Risk categorization based on check type
            if check_type in ['gas_detector_calibration', 'confined_space_procedures']:
                category = 'CRITICAL'
            elif check_type in ['pressure_relief_testing', 'permit_to_work_audit']:
                category = 'HIGH'
            else:
                category = 'MEDIUM'
            
            risk_categories[category].append({
                'check_type': check_type,
                'non_conformance': finding.get('non_conformances', []),
                'potential_impact': self._assess_impact(check_type)
            })
        
        # Flatten and return
        for category in ['CRITICAL', 'HIGH', 'MEDIUM']:
            for risk in risk_categories[category]:
                risk['risk_level'] = category
                risk_areas.append(risk)
        
        return risk_areas
    
    def _assess_impact(self, check_type: str) -> str:
        """Assess potential impact of non-compliance."""
        impacts = {
            'gas_detector_calibration': 'Failure to detect hazardous gases leading to exposure',
            'pressure_relief_testing': 'Equipment over-pressure leading to explosion',
            'permit_to_work_audit': 'Unauthorized or unsafe work procedures',
            'confined_space_procedures': 'Asphyxiation or exposure in confined spaces',
            'fire_extinguisher_inspection': 'Inability to combat fires',
            'emergency_response_drill': 'Delayed emergency response'
        }
        return impacts.get(check_type, 'Potential safety or compliance impact')
    
    def _generate_corrective_action_plan(self, audit_id: str, 
                                        non_conformances: List[Dict],
                                        location: str) -> Dict:
        """Generate automated corrective action plan."""
        action_plan = {
            'plan_id': str(uuid.uuid4()),
            'audit_id': audit_id,
            'location': location,
            'created_at': datetime.now().isoformat(),
            'actions': [],
            'target_completion_date': (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        for finding in non_conformances:
            check_type = finding['check_type']
            recommendations = finding.get('recommendations', [])
            
            for i, recommendation in enumerate(recommendations, 1):
                action = {
                    'action_id': str(uuid.uuid4()),
                    'action_number': i,
                    'description': recommendation,
                    'check_type': check_type,
                    'assigned_to': 'Safety Officer',
                    'priority': 'HIGH' if check_type in ['gas_detector_calibration', 'confined_space_procedures'] else 'MEDIUM',
                    'status': 'OPEN',
                    'due_date': self._calculate_action_due_date(check_type),
                    'evidence_required': self._identify_evidence_requirements(check_type)
                }
                action_plan['actions'].append(action)
        
        # Store corrective action plan
        self.corrective_actions[action_plan['plan_id']] = action_plan
        
        return action_plan
    
    def _calculate_action_due_date(self, check_type: str) -> str:
        """Calculate due date for corrective action."""
        days_to_complete = {
            'gas_detector_calibration': 7,
            'pressure_relief_testing': 14,
            'confined_space_procedures': 3,
            'permit_to_work_audit': 7,
            'fire_extinguisher_inspection': 30,
            'emergency_response_drill': 14
        }
        
        days = days_to_complete.get(check_type, 30)
        due_date = datetime.now() + timedelta(days=days)
        return due_date.isoformat()
    
    def _identify_evidence_requirements(self, check_type: str) -> List[str]:
        """Identify what evidence is needed to verify corrective action."""
        evidence_map = {
            'gas_detector_calibration': [
                'Calibration certificate',
                'Calibration date stamp',
                'Equipment test report'
            ],
            'pressure_relief_testing': [
                'Pressure test report',
                'Test engineer signature',
                'Seal/tag placement photo'
            ],
            'confined_space_procedures': [
                'Updated procedure document',
                'Training attendance sheet',
                'Safety briefing video/photos'
            ],
            'permit_to_work_audit': [
                'Completed permits with assessments',
                'Officer training records',
                'System checklist screenshots'
            ]
        }
        
        return evidence_map.get(check_type, ['Documentation', 'Photographs', 'Inspector signature'])
    
    def get_compliance_dashboard(self, location: str) -> Dict:
        """Generate compliance dashboard for a location."""
        dashboard = {
            'location': location,
            'generated_at': datetime.now().isoformat(),
            'compliance_status': ComplianceStatus.COMPLIANT.value,
            'due_checks': [],
            'overdue_checks': [],
            'recent_audit_findings': [],
            'open_corrective_actions': [],
            'compliance_score': 100.0
        }
        
        # Analyze compliance records for this location
        location_checks = [
            c for c in self.compliance_records.values() 
            if c['location'] == location
        ]
        
        # Calculate due/overdue checks
        for check in location_checks:
            scheduled_date = datetime.fromisoformat(check['scheduled_date'])
            if scheduled_date < datetime.now():
                dashboard['overdue_checks'].append(check)
            elif scheduled_date < datetime.now() + timedelta(days=7):
                dashboard['due_checks'].append(check)
        
        # Get recent audit findings
        location_audits = [
            a for a in self.audit_findings
            if a['location'] == location
        ]
        
        if location_audits:
            latest_audit = max(location_audits, key=lambda x: x['started_at'])
            dashboard['recent_audit_findings'] = latest_audit['findings']
            dashboard['compliance_status'] = latest_audit['overall_status']
        
        # Get open corrective actions
        for plan in self.corrective_actions.values():
            if plan['location'] == location:
                open_actions = [a for a in plan['actions'] if a['status'] == 'OPEN']
                dashboard['open_corrective_actions'].extend(open_actions)
        
        # Calculate compliance score
        total_checks = len(location_checks)
        if total_checks > 0:
            compliant_checks = len([c for c in location_checks 
                                   if c['status'] == ComplianceStatus.COMPLIANT.value])
            dashboard['compliance_score'] = (compliant_checks / total_checks) * 100
        
        # Determine overall status
        if dashboard['overdue_checks']:
            dashboard['compliance_status'] = ComplianceStatus.NON_COMPLIANT.value
        elif dashboard['due_checks'] or dashboard['open_corrective_actions']:
            dashboard['compliance_status'] = ComplianceStatus.NEEDS_ATTENTION.value
        
        return dashboard
    
    def _calculate_next_check_date(self, check_type: str) -> str:
        """Calculate next check date based on check type."""
        interval_days = self.CHECK_INTERVALS.get(check_type, 90)
        next_date = datetime.now() + timedelta(days=interval_days)
        return next_date.isoformat()
    
    def generate_compliance_report(self, location: str, start_date: str = None, 
                                  end_date: str = None) -> str:
        """
        Generate comprehensive compliance report for regulatory submission.
        RAG-ready format for compliance documentation.
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).isoformat()
        if not end_date:
            end_date = datetime.now().isoformat()
        
        dashboard = self.get_compliance_dashboard(location)
        
        report = f"""
COMPLIANCE AUDIT REPORT
Location: {location}
Report Generated: {datetime.now().isoformat()}
Reporting Period: {start_date} to {end_date}

EXECUTIVE SUMMARY
=================
Compliance Status: {dashboard['compliance_status']}
Overall Compliance Score: {dashboard['compliance_score']:.1f}%

COMPLIANCE SUMMARY
==================
Due Checks: {len(dashboard['due_checks'])}
Overdue Checks: {len(dashboard['overdue_checks'])}
Open Corrective Actions: {len(dashboard['open_corrective_actions'])}

RECENT AUDIT FINDINGS
======================
"""
        
        for finding in dashboard['recent_audit_findings'][:10]:
            report += f"\n- {finding['check_type']}: {finding['status']}\n"
        
        report += f"""

OPEN CORRECTIVE ACTIONS
=======================
"""
        for action in dashboard['open_corrective_actions'][:10]:
            report += f"\n- {action['description']}\n"
            report += f"  Priority: {action['priority']}\n"
            report += f"  Due: {action['due_date']}\n"
        
        return report


class ComplianceAgent:
    """Correlates active permits with current hazards to detect compliance violations."""

    def __init__(self, permit_agent: PermitIntelligenceAgent = None):
        self.permit_agent = permit_agent or PermitIntelligenceAgent()
        self.regulations_dir = Path(__file__).resolve().parents[2] / 'data' / 'regulations'
        self.vector_store_dir = Path(__file__).resolve().parents[2] / 'data' / 'vectorstores' / 'compliance'
        self.collection_name = 'forge_sense_compliance_regulations'
        self._index_ready = False
        self._client = None
        self._collection = None
        self._documents: List[Document] = []
        self._fallback_index: List[Dict] = []
        self._vector_size = 256

    def evaluate_permit_compliance(
        self,
        active_permits: List[Dict] = None,
        detected_hazards: Dict = None,
        sensor_data: Dict = None,
        location: str = None,
    ) -> Dict:
        """Flag violations when hot work overlaps with detected gas hazards."""
        permit_state = self.permit_agent.validate_active_permits(sensor_data or {}, location)
        permits = active_permits if active_permits is not None else permit_state.get('active_permits', [])

        gas_detected = self._gas_detected(sensor_data, detected_hazards)
        violations = []
        warnings = []

        for permit in permits:
            if self._is_hot_work_permit(permit) and gas_detected and self._permit_is_in_hazard_zone(permit, detected_hazards, location):
                violations.append({
                    'event_type': 'COMPLIANCE_VIOLATION',
                    'severity': 'CRITICAL',
                    'permit_id': permit.get('permit_id'),
                    'permit_type': permit.get('permit_type'),
                    'location': permit.get('location', location),
                    'reason': 'Hot Work permit active while gas is detected in the same zone',
                })
            elif gas_detected and self._permit_is_in_hazard_zone(permit, detected_hazards, location):
                warnings.append({
                    'event_type': 'COMPLIANCE_WARNING',
                    'severity': 'HIGH',
                    'permit_id': permit.get('permit_id'),
                    'permit_type': permit.get('permit_type'),
                    'location': permit.get('location', location),
                    'reason': 'Detected gas hazard overlaps with an active permit area',
                })

        return {
            'event_type': 'COMPLIANCE_VIOLATION' if violations else 'COMPLIANCE_OK',
            'status': 'VIOLATION' if violations else 'COMPLIANT',
            'active_permits': permits,
            'permit_summary': permit_state,
            'violations': violations,
            'warnings': warnings,
            'gas_detected': gas_detected,
            'location': location,
        }

    def _is_hot_work_permit(self, permit: Dict) -> bool:
        permit_type = str(permit.get('permit_type', '')).replace(' ', '_').upper()
        return permit_type == 'HOT_WORK'

    def _gas_detected(self, sensor_data: Dict, detected_hazards: Dict) -> bool:
        if sensor_data:
            gas_level = sensor_data.get('gas', sensor_data.get('gas_level', 0))
            try:
                if float(gas_level) >= 0.5:
                    return True
            except (TypeError, ValueError):
                pass

        if not detected_hazards:
            return False

        if isinstance(detected_hazards, dict):
            return bool(detected_hazards.get('gas_detected') or detected_hazards.get('gas_hazard'))

        return any(str(hazard).upper() == 'GAS' for hazard in detected_hazards)

    def _permit_is_in_hazard_zone(self, permit: Dict, detected_hazards: Dict, location: str = None) -> bool:
        permit_location = permit.get('location') or location

        if not detected_hazards:
            return bool(permit_location)

        if isinstance(detected_hazards, dict):
            hazard_location = detected_hazards.get('location') or location
            if permit_location and hazard_location:
                return permit_location == hazard_location

            danger_zones = detected_hazards.get('danger_zones', [])
            return bool(danger_zones)

        return bool(detected_hazards)

    def answer_query(self, user_query: str, top_k: int = 3) -> str:
        """Return a concise compliance answer grounded in the ingested regulations."""
        query = (user_query or '').strip()
        if not query:
            return 'Please enter a compliance question.'

        snippets = self.retrieve_snippets(query, top_k=top_k)
        if not snippets:
            return 'No matching regulation was found in the current compliance corpus.'

        key_points = []
        references = []
        for snippet in snippets:
            text = snippet['text'].strip().replace('\n', ' ')
            key_points.extend(self._extract_compliance_sentences(text))

            metadata = snippet.get('metadata', {}) or {}
            source = metadata.get('source', 'regulation')
            page = metadata.get('page')
            references.append(f"{source}{f' p.{page}' if page is not None else ''}")

        unique_points = self._dedupe_sentences(key_points)[:3]
        if not unique_points:
            unique_points = [self._shorten_text(snippets[0]['text'])]

        response = ' '.join(unique_points)
        response += f" Source(s): {', '.join(dict.fromkeys(references))}."
        return response

    def retrieve_snippets(self, user_query: str, top_k: int = 3) -> List[Dict]:
        """Retrieve regulation snippets relevant to the user query."""
        self._ensure_index()
        query = (user_query or '').strip()
        if not query:
            return []

        if self._collection is not None:
            query_embedding = self._embed_text(query)
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances'],
            )

            documents = result.get('documents', [[]])[0] if result.get('documents') else []
            metadatas = result.get('metadatas', [[]])[0] if result.get('metadatas') else []
            distances = result.get('distances', [[]])[0] if result.get('distances') else []

            snippets = []
            for index, text in enumerate(documents):
                snippets.append({
                    'text': text,
                    'metadata': metadatas[index] if index < len(metadatas) else {},
                    'score': self._distance_to_score(distances[index] if index < len(distances) else None),
                })
            return snippets

        query_embedding = self._embed_text(query)
        scored_documents = []
        for entry in self._fallback_index:
            score = self._cosine_similarity(query_embedding, entry['embedding'])
            scored_documents.append((score, entry))

        scored_documents.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                'text': entry['document'].page_content,
                'metadata': entry['document'].metadata,
                'score': score,
            }
            for score, entry in scored_documents[:top_k]
        ]

    def _ensure_index(self):
        if self._index_ready:
            return

        self._documents = self._load_regulation_documents()

        if chromadb is not None:
            self.vector_store_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.vector_store_dir))
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={'hnsw:space': 'cosine'},
            )

            if self._collection.count() == 0 and self._documents:
                ids = []
                texts = []
                metadatas = []
                embeddings = []

                for index, document in enumerate(self._documents):
                    doc_id = document.metadata.get('doc_id') or f"reg-{index}"
                    ids.append(doc_id)
                    texts.append(document.page_content)
                    metadatas.append(document.metadata)
                    embeddings.append(self._embed_text(document.page_content))

                self._collection.add(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings,
                )
        else:
            self._fallback_index = [
                {
                    'document': document,
                    'embedding': self._embed_text(document.page_content),
                }
                for document in self._documents
            ]

        self._index_ready = True

    def _load_regulation_documents(self) -> List[Document]:
        documents = []
        pdf_files = sorted(self.regulations_dir.glob('*.pdf'))

        for pdf_file in pdf_files:
            documents.extend(self._load_pdf_documents(pdf_file))

        if documents:
            return documents

        fallback_text = self._fallback_regulation_text()
        return [
            Document(
                page_content=chunk,
                metadata={
                    'source': 'factory_act_sample.pdf',
                    'page': 1,
                    'doc_id': f'fallback-{index}',
                },
            )
            for index, chunk in enumerate(self._chunk_text(fallback_text))
        ]

    def _load_pdf_documents(self, pdf_path: Path) -> List[Document]:
        if PdfReader is None:
            return []

        reader = PdfReader(str(pdf_path))
        documents = []
        for page_index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or '').strip()
            if not text:
                continue

            for chunk_index, chunk in enumerate(self._chunk_text(text)):
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            'source': pdf_path.name,
                            'page': page_index,
                            'doc_id': f'{pdf_path.stem}-p{page_index}-c{chunk_index}',
                        },
                    )
                )

        return documents

    def _chunk_text(self, text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
        normalized = re.sub(r'\s+', ' ', text).strip()
        if not normalized:
            return []

        chunks = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + chunk_size)
            chunks.append(normalized[start:end])
            if end >= len(normalized):
                break
            start = max(end - overlap, start + 1)

        return chunks

    def _embed_text(self, text: str) -> List[float]:
        tokens = re.findall(r'[a-z0-9]+', text.lower())
        vector = [0.0] * self._vector_size

        for token in tokens:
            index = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16) % self._vector_size
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def _cosine_similarity(self, left: List[float], right: List[float]) -> float:
        return sum(a * b for a, b in zip(left, right))

    def _distance_to_score(self, distance) -> float:
        if distance is None:
            return 0.0

        try:
            return max(0.0, 1.0 - float(distance))
        except (TypeError, ValueError):
            return 0.0

    def _extract_compliance_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        compliance_keywords = (
            'shall', 'must', 'required', 'ensure', 'prohibit', 'prohibited',
            'calibration', 'inspection', 'permit', 'record', 'training', 'safety'
        )
        selected = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(keyword in lowered for keyword in compliance_keywords):
                selected.append(sentence.strip())

        return selected

    def _dedupe_sentences(self, sentences: List[str]) -> List[str]:
        seen = set()
        unique = []
        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            unique.append(cleaned)
        return unique

    def _shorten_text(self, text: str, limit: int = 240) -> str:
        compact = re.sub(r'\s+', ' ', text).strip()
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + '...'

    def _fallback_regulation_text(self) -> str:
        return (
            "Factory Act compliance summary. Hot work shall only proceed with a valid permit,"
            " documented gas testing, and verified fire-watch coverage. Work in restricted or"
            " high-voltage areas must be controlled, monitored, and approved by the responsible"
            " safety officer. Inspection records, calibration logs, and corrective action evidence"
            " shall be retained and made available for audit. Emergency equipment must remain"
            " accessible and training records should be current before hazardous work begins."
        )
