from typing import TypedDict, List, Dict, Any, Optional
from cve_analyzer.models.evidence import Evidence
from cve_analyzer.models.vulnerability import VulnerabilityInfo
from cve_analyzer.models.dependency import DependencyInfo, SourceReference
from cve_analyzer.models.report import AssessmentStatus, ConfidenceLevel


class CVEAnalysisState(TypedDict, total=False):
    """
    LangGraph Workflow State for CVE Reachability Analysis.
    Maintains all intermediate technical facts, reasoning state, and evidence.
    """
    # Repository information
    repository_path: str
    repo_url: Optional[str]
    github_token: Optional[str]
    source_directory: str
    test_directory: Optional[str]
    repository_valid: bool
    build_system: str  # MAVEN, GRADLE, UNKNOWN

    # CVE and Vulnerability inputs
    cve_id: str
    cve_raw_text: Optional[str]
    vulnerability: Optional[Dict[str, Any]]  # Serialized VulnerabilityInfo
    
    # Resolved dependencies
    dependencies: List[Dict[str, Any]]
    vulnerable_dependency: Optional[Dict[str, Any]]
    dependency_paths: List[List[str]]

    # Affected symbols to verify
    affected_classes: List[str]
    affected_methods: List[str]

    # Verification evidence
    jar_evidence: List[Dict[str, Any]]
    source_evidence: List[Dict[str, Any]]
    bytecode_evidence: List[Dict[str, Any]]

    # References and Call Paths
    references: List[Dict[str, Any]]
    call_paths: List[List[str]]

    # Global evidence list
    evidence: List[Dict[str, Any]]

    # Assessment & Decision
    assessment: str
    confidence: str
    
    # Human-in-the-loop and Error Handling
    human_review_required: bool
    human_question: Optional[str]
    human_answer: Optional[str]
    errors: List[str]
    retry_count: int

    # Final outputs
    final_report: Optional[str]
    report_dict: Optional[Dict[str, Any]]
