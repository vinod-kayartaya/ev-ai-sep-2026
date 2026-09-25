from typing import List, Optional
from pydantic import BaseModel, Field


class DependencyInfo(BaseModel):
    """
    Structured representation of a dependency in the project dependency tree.
    """
    group: str = Field(default="", description="Maven groupId / Gradle group")
    artifact: str = Field(description="Maven artifactId / Gradle module name")
    version: str = Field(default="", description="Resolved dependency version")
    scope: str = Field(default="compile", description="Dependency scope (compile, runtime, test, provided)")
    direct: bool = Field(default=True, description="True if direct dependency, False if transitive")
    dependency_path: List[str] = Field(default_factory=list, description="Chain of dependencies from root application")
    jar_path: Optional[str] = Field(default=None, description="Local path to the dependency JAR file if available")

    @property
    def coordinate(self) -> str:
        if self.group:
            return f"{self.group}:{self.artifact}:{self.version}"
        return f"{self.artifact}:{self.version}"


class SourceReference(BaseModel):
    """
    Representation of an application reference to a class or method.
    """
    file: str = Field(description="Relative or absolute path to the Java file")
    line: int = Field(description="Line number in the source file")
    target_class: str = Field(description="Referenced class name")
    target_method: Optional[str] = Field(default=None, description="Referenced method name")
    reference_type: str = Field(description="Type: METHOD_INVOCATION, IMPORT, INSTANTIATION, FIELD_DECLARATION, INHERITANCE")
    code_snippet: Optional[str] = Field(default=None, description="Source line containing the reference")
    enclosing_class: Optional[str] = Field(default=None, description="Enclosing Java class name")
    enclosing_method: Optional[str] = Field(default=None, description="Enclosing method signature, e.g. OrderService.processOrder()")
