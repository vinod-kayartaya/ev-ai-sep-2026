from typing import Optional
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """
    Formal evidence model for auditability and explainability.
    Every important conclusion is associated with an Evidence item.
    """
    source: str = Field(description="Authoritative source or tool, e.g. maven, javap, source_analyzer")
    evidence_type: str = Field(description="Type of evidence, e.g. DEPENDENCY_FOUND, METHOD_EXISTS, METHOD_INVOCATION")
    description: str = Field(description="Human-readable explanation of the factual finding")
    file: Optional[str] = Field(default=None, description="Related file or JAR path")
    line: Optional[int] = Field(default=None, description="Line number if applicable")
    command: Optional[str] = Field(default=None, description="Command executed if applicable")
    confidence: str = Field(default="HIGH", description="Confidence level: HIGH, MEDIUM, LOW")

    def to_dict(self) -> dict:
        return self.model_dump()
