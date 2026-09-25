import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from cve_analyzer.tools.dependency_analyzer import DependencyAnalyzer
from cve_analyzer.tools.jar_analyzer import JarAnalyzer
from cve_analyzer.tools.source_analyzer import SourceAnalyzer
from cve_analyzer.tools.callgraph_analyzer import CallGraphAnalyzer
from cve_analyzer.tools.repo_analyzer import RepositoryAnalyzer


@tool
def resolve_dependencies(repository_path: str, build_system: Optional[str] = None) -> str:
    """
    Resolve Maven or Gradle dependencies and return the dependency tree.
    Args:
        repository_path: Path to the local Java project repository.
        build_system: MAVEN or GRADLE (auto-detected if None).
    """
    if not build_system:
        repo_res, _ = RepositoryAnalyzer.analyze(repository_path)
        build_system = repo_res.get("build_system", "MAVEN")

    analyzer = DependencyAnalyzer()
    deps, evidence, err = analyzer.resolve(repository_path, build_system)
    return json.dumps({
        "success": err is None,
        "error": err,
        "dependency_count": len(deps),
        "dependencies": [d.model_dump() for d in deps],
        "evidence": [e.model_dump() for e in evidence]
    }, indent=2)


@tool
def inspect_jar(jar_path: str, class_name: str, method_name: Optional[str] = None) -> str:
    """
    Verify class and method existence in a Java JAR file using jar and javap.
    Args:
        jar_path: Path to the .jar file.
        class_name: Fully qualified class name (e.g. com.vendor.Parser).
        method_name: Method name (e.g. parseUnsafe).
    """
    analyzer = JarAnalyzer()
    class_found, method_found, evidence = analyzer.verify_symbols_in_jar(
        Path(jar_path), class_name, method_name
    )
    return json.dumps({
        "class_found": class_found,
        "method_found": method_found,
        "evidence": [e.model_dump() for e in evidence]
    }, indent=2)


@tool
def find_method_references(repository_path: str, class_name: str, method_name: Optional[str] = None) -> str:
    """
    Find application references (imports, instantiations, method invocations) to a Java class or method.
    Args:
        repository_path: Path to the local repository.
        class_name: Target class name.
        method_name: Target method name.
    """
    analyzer = SourceAnalyzer(repository_path)
    refs, evidence = analyzer.analyze_references(class_name, method_name)
    return json.dumps({
        "reference_count": len(refs),
        "references": [r.model_dump() for r in refs],
        "evidence": [e.model_dump() for e in evidence]
    }, indent=2)


@tool
def find_call_paths(repository_path: str, target_class: str, target_method: str) -> str:
    """
    Constructs a static call graph and finds reachable call paths from application entry points
    to the target method.
    """
    source_analyzer = SourceAnalyzer(repository_path)
    refs, _ = source_analyzer.analyze_references(target_class, target_method)

    cg_analyzer = CallGraphAnalyzer(repository_path)
    paths, evidence = cg_analyzer.find_reachability_paths(target_class, target_method, refs)
    return json.dumps({
        "paths_found": len(paths) > 0,
        "paths": paths,
        "evidence": [e.model_dump() for e in evidence]
    }, indent=2)
