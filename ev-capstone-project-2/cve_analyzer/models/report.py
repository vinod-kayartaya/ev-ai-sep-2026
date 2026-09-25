from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from cve_analyzer.models.evidence import Evidence
from cve_analyzer.models.dependency import DependencyInfo, SourceReference
from cve_analyzer.models.vulnerability import VulnerabilityInfo


class AssessmentStatus(str, Enum):
    NOT_PRESENT = "NOT_PRESENT"
    SYMBOL_NOT_FOUND = "SYMBOL_NOT_FOUND"
    STATICALLY_REACHABLE = "STATICALLY_REACHABLE"
    NO_STATIC_PATH_FOUND = "NO_STATIC_PATH_FOUND"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AnalysisReport(BaseModel):
    """
    Evidence-based report model matching the project specification.
    """
    cve_id: str
    affected_artifact: str
    detected_version: Optional[str] = None
    dependency_type: Optional[str] = None  # DIRECT or TRANSITIVE or NOT_PRESENT
    dependency_path: List[str] = Field(default_factory=list)
    affected_class: Optional[str] = None
    affected_method: Optional[str] = None
    class_present: Optional[bool] = None
    method_present: Optional[bool] = None
    application_references: List[SourceReference] = Field(default_factory=list)
    static_call_paths: List[List[str]] = Field(default_factory=list)
    assessment: AssessmentStatus
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    evidence_list: List[Evidence] = Field(default_factory=list)
    limitations: List[str] = Field(
        default_factory=lambda: [
            "Static reachability does not establish runtime exploitability.",
            "The analysis establishes whether a supported static path to the affected functionality was identified.",
            "Dynamic reflection, dependency injection, and native calls may not be fully resolved statically."
        ]
    )
    raw_report: Optional[str] = None
