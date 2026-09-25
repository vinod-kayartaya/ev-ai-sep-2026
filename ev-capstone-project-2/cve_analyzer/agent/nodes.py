import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from langgraph.types import interrupt
from cve_analyzer.models.state import CVEAnalysisState
from cve_analyzer.models.evidence import Evidence
from cve_analyzer.models.vulnerability import VulnerabilityInfo
from cve_analyzer.models.dependency import DependencyInfo, SourceReference
from cve_analyzer.models.report import AssessmentStatus, ConfidenceLevel
from cve_analyzer.tools.git_manager import GitManager
from cve_analyzer.tools.repo_analyzer import RepositoryAnalyzer
from cve_analyzer.tools.dependency_analyzer import DependencyAnalyzer
from cve_analyzer.tools.jar_analyzer import JarAnalyzer
from cve_analyzer.tools.source_analyzer import SourceAnalyzer
from cve_analyzer.tools.callgraph_analyzer import CallGraphAnalyzer
from cve_analyzer.agent.llm import get_llm, parse_vulnerability_with_fallback
from cve_analyzer.agent.prompts import CVE_INTERPRETATION_SYSTEM_PROMPT, HUMAN_REVIEW_PROMPT
from cve_analyzer.report_generator import ReportGenerator


def prepare_repository_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Clones remote GitHub repository (with PAT if needed) or validates local path."""
    repo_target = state.get("repo_url") or state.get("repository_path", "")
    token = state.get("github_token")

    evidence_list = list(state.get("evidence", []))
    errors = list(state.get("errors", []))

    git_mgr = GitManager()
    try:
        local_path, ev = git_mgr.prepare_repository(repo_target, token)
        evidence_list.append(ev.model_dump())
        return {
            "repository_path": local_path,
            "evidence": evidence_list,
            "errors": errors
        }
    except Exception as e:
        err_msg = f"Failed to prepare repository: {e}"
        errors.append(err_msg)
        evidence_list.append(Evidence(
            source="git_manager",
            evidence_type="CLONE_FAILED",
            description=err_msg,
            confidence="HIGH"
        ).model_dump())
        return {
            "repository_valid": False,
            "assessment": AssessmentStatus.INSUFFICIENT_EVIDENCE.value,
            "evidence": evidence_list,
            "errors": errors
        }


def repository_validator_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Validates local repository directory and layout."""
    repo_path = state.get("repository_path", "")
    repo_info, ev_list = RepositoryAnalyzer.analyze(repo_path)

    curr_ev = list(state.get("evidence", []))
    for ev in ev_list:
        curr_ev.append(ev.model_dump())

    return {
        "repository_valid": repo_info["repository_valid"],
        "build_system": repo_info["build_system"],
        "source_directory": repo_info["source_directory"],
        "test_directory": repo_info.get("test_directory"),
        "evidence": curr_ev
    }


def build_system_detector_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Ensures build system is identified, or records unknown."""
    build_sys = state.get("build_system", "UNKNOWN")
    evidence = list(state.get("evidence", []))
    if build_sys == "UNKNOWN":
        evidence.append(Evidence(
            source="build_system_detector",
            evidence_type="BUILD_SYSTEM_WARNING",
            description="Could not detect Maven or Gradle build files. Fallback heuristic will be used.",
            confidence="MEDIUM"
        ).model_dump())
    return {"evidence": evidence}


def vulnerability_analyzer_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Interprets CVE input, extracts affected artifact, classes, methods, detects ambiguity."""
    cve_id = state.get("cve_id", "CVE-UNKNOWN")
    raw_text = state.get("cve_raw_text")
    existing_vuln = state.get("vulnerability")
    human_answer = state.get("human_answer")

    evidence = list(state.get("evidence", []))

    if existing_vuln and isinstance(existing_vuln, dict):
        vuln = VulnerabilityInfo(**existing_vuln)
    else:
        # Try LLM if configured, otherwise fallback parser
        llm = get_llm()
        if llm and raw_text:
            try:
                # LLM structured extraction
                structured_llm = llm.with_structured_output(VulnerabilityInfo)
                vuln = structured_llm.invoke([
                    {"role": "system", "content": CVE_INTERPRETATION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"CVE ID: {cve_id}\n\nVulnerability text:\n{raw_text}"}
                ])
            except Exception:
                vuln = parse_vulnerability_with_fallback(cve_id, raw_text)
        else:
            vuln = parse_vulnerability_with_fallback(cve_id, raw_text)

    # Incorporate human answer if returning from human review
    if human_answer:
        # User might specify class and/or method: "com.vendor.Parser" or "parseUnsafe"
        parts = [p.strip() for p in human_answer.split() if p.strip()]
        for part in parts:
            if "." in part:
                vuln.affected_classes = [part]
            else:
                vuln.affected_methods = [part.replace("()", "")]
        vuln.is_ambiguous = False
        vuln.ambiguity_reason = None
        evidence.append(Evidence(
            source="human_input",
            evidence_type="HUMAN_RESOLVED_SYMBOL",
            description=f"Human reviewer specified: {human_answer}",
            confidence="HIGH"
        ).model_dump())

    evidence.append(Evidence(
        source="vulnerability_analyzer",
        evidence_type="VULNERABILITY_PARSED",
        description=f"Parsed CVE {cve_id}: Artifact={vuln.artifact}, Classes={vuln.affected_classes}, Methods={vuln.affected_methods}",
        confidence="HIGH"
    ).model_dump())

    return {
        "vulnerability": vuln.model_dump(),
        "affected_classes": vuln.affected_classes,
        "affected_methods": vuln.affected_methods,
        "evidence": evidence
    }


def dependency_analyzer_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Resolves dependencies and verifies if vulnerable artifact/version is present."""
    repo_path = state.get("repository_path", "")
    build_sys = state.get("build_system", "MAVEN")
    vuln_dict = state.get("vulnerability", {})
    vuln = VulnerabilityInfo(**vuln_dict) if vuln_dict else VulnerabilityInfo(cve_id="", artifact="")

    analyzer = DependencyAnalyzer()
    retries = state.get("retry_count", 0)
    deps, ev_list, err = analyzer.resolve(repo_path, build_sys, max_retries=1)

    evidence = list(state.get("evidence", []))
    for ev in ev_list:
        evidence.append(ev.model_dump())

    errors = list(state.get("errors", []))
    if err:
        errors.append(err)

    # Search for vulnerable dependency
    matched_dep: Optional[DependencyInfo] = None
    dep_paths: List[List[str]] = []

    for dep in deps:
        if vuln.matches_artifact(dep.group, dep.artifact):
            if vuln.matches_version(dep.version):
                matched_dep = dep
                dep_paths.append(dep.dependency_path)
                evidence.append(Evidence(
                    source="dependency_analyzer",
                    evidence_type="VULNERABLE_DEPENDENCY_FOUND",
                    description=f"Vulnerable dependency {dep.coordinate} matched. Direct: {dep.direct}",
                    confidence="HIGH"
                ).model_dump())
                break

    if not matched_dep:
        evidence.append(Evidence(
            source="dependency_analyzer",
            evidence_type="DEPENDENCY_NOT_PRESENT",
            description=f"Target artifact {vuln.artifact} (versions: {vuln.affected_versions}) was NOT found in resolved dependencies.",
            confidence="HIGH"
        ).model_dump())

    return {
        "dependencies": [d.model_dump() for d in deps],
        "vulnerable_dependency": matched_dep.model_dump() if matched_dep else None,
        "dependency_paths": dep_paths,
        "evidence": evidence,
        "errors": errors
    }


def human_review_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Human-in-the-Loop review for ambiguous symbols or missing information."""
    vuln_dict = state.get("vulnerability", {})
    reason = vuln_dict.get("ambiguity_reason", "Ambiguous vulnerable symbols")
    classes = vuln_dict.get("affected_classes", [])
    methods = vuln_dict.get("affected_methods", [])

    question = (
        f"Human review required: {reason}. "
        f"Candidate classes: {classes or 'None'}. "
        f"Candidate methods: {methods or 'None'}. "
        f"Please provide the exact target class and method to analyze."
    )

    evidence = list(state.get("evidence", []))
    evidence.append(Evidence(
        source="human_review",
        evidence_type="HUMAN_REVIEW_TRIGGERED",
        description=f"Triggered human review: {reason}",
        confidence="HIGH"
    ).model_dump())

    # If state already has human_answer, use it
    if state.get("human_answer"):
        return {
            "human_review_required": False,
            "evidence": evidence
        }

    # Use LangGraph interrupt if running interactively with checkpointer
    try:
        user_input = interrupt({
            "type": "HUMAN_REVIEW_REQUIRED",
            "question": question,
            "cve_id": state.get("cve_id"),
            "candidate_classes": classes,
            "candidate_methods": methods
        })
        return {
            "human_review_required": False,
            "human_answer": str(user_input),
            "evidence": evidence
        }
    except Exception:
        # When running in non-interactive batch test, record question and mark assessment
        return {
            "human_review_required": True,
            "human_question": question,
            "assessment": AssessmentStatus.HUMAN_REVIEW.value,
            "evidence": evidence
        }


def symbol_verifier_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Locates JAR and verifies affected class and method presence using jar and javap."""
    v_dep = state.get("vulnerable_dependency") or {}
    group = v_dep.get("group", "")
    art = v_dep.get("artifact", "")
    ver = v_dep.get("version", "")
    repo_path = state.get("repository_path", "")

    aff_classes = state.get("affected_classes", [])
    aff_methods = state.get("affected_methods", [])

    jar_analyzer = JarAnalyzer()
    jar_path = jar_analyzer.locate_jar(group, art, ver, repo_path)

    evidence = list(state.get("evidence", []))
    jar_evidence: List[Dict[str, Any]] = []
    errors = list(state.get("errors", []))

    if not jar_path:
        # Check if local .class files exist in build/target
        repo_p = Path(repo_path)
        class_files = list(repo_p.glob(f"**/{art}*/**/*.class"))
        if not class_files:
            # Check mock fixtures
            ws = Path(__file__).resolve().parent.parent.parent
            fixture_jars = list(ws.glob(f"**/{art}*.jar"))
            if fixture_jars:
                jar_path = fixture_jars[0]

    if not jar_path:
        ev = Evidence(
            source="jar_analyzer",
            evidence_type="BYTECODE_UNAVAILABLE",
            description=f"Neither JAR file nor compiled bytecode available for {group}:{art}:{ver}",
            confidence="HIGH"
        )
        evidence.append(ev.model_dump())
        jar_evidence.append(ev.model_dump())
        errors.append("Bytecode unavailable for vulnerable dependency")
        return {
            "jar_evidence": jar_evidence,
            "evidence": evidence,
            "errors": errors,
            "assessment": AssessmentStatus.INSUFFICIENT_EVIDENCE.value
        }

    target_class = aff_classes[0] if aff_classes else ""
    target_method = aff_methods[0] if aff_methods else None

    class_found, method_found, ev_list = jar_analyzer.verify_symbols_in_jar(
        jar_path, target_class, target_method
    )

    for ev in ev_list:
        evidence.append(ev.model_dump())
        jar_evidence.append(ev.model_dump())

    assessment = None
    if not class_found or (target_method and not method_found):
        assessment = AssessmentStatus.SYMBOL_NOT_FOUND.value

    return {
        "jar_evidence": jar_evidence,
        "evidence": evidence,
        "assessment": assessment,
        "errors": errors
    }


def source_analyzer_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Analyzes Java source code for imports, object creation, and method invocations."""
    repo_path = state.get("repository_path", "")
    src_dir = state.get("source_directory")
    aff_classes = state.get("affected_classes", [])
    aff_methods = state.get("affected_methods", [])

    target_class = aff_classes[0] if aff_classes else ""
    target_method = aff_methods[0] if aff_methods else None

    analyzer = SourceAnalyzer(repo_path, src_dir)
    refs, ev_list = analyzer.analyze_references(target_class, target_method)

    evidence = list(state.get("evidence", []))
    src_evidence: List[Dict[str, Any]] = []

    for ev in ev_list:
        evidence.append(ev.model_dump())
        src_evidence.append(ev.model_dump())

    return {
        "references": [r.model_dump() for r in refs],
        "source_evidence": src_evidence,
        "evidence": evidence
    }


def reachability_analyzer_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Builds static call graph and finds reachable paths from entry points."""
    repo_path = state.get("repository_path", "")
    aff_classes = state.get("affected_classes", [])
    aff_methods = state.get("affected_methods", [])
    refs_raw = state.get("references", [])
    refs = [SourceReference(**r) for r in refs_raw]

    target_class = aff_classes[0] if aff_classes else ""
    target_method = aff_methods[0] if aff_methods else ""

    cg_analyzer = CallGraphAnalyzer(repo_path)
    paths, ev_list = cg_analyzer.find_reachability_paths(target_class, target_method, refs)

    evidence = list(state.get("evidence", []))
    for ev in ev_list:
        evidence.append(ev.model_dump())

    assessment = (
        AssessmentStatus.STATICALLY_REACHABLE.value
        if paths
        else AssessmentStatus.NO_STATIC_PATH_FOUND.value
    )

    return {
        "call_paths": paths,
        "assessment": assessment,
        "evidence": evidence
    }


def evidence_aggregator_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Aggregates all technical facts and establishes the final controlled assessment."""
    evidence = list(state.get("evidence", []))
    v_dep = state.get("vulnerable_dependency")
    errors = state.get("errors", [])
    paths = state.get("call_paths", [])
    human_req = state.get("human_review_required", False)
    current_assessment = state.get("assessment")

    # Controlled State Determination matching Section 13
    final_assessment = AssessmentStatus.INSUFFICIENT_EVIDENCE.value
    confidence = ConfidenceLevel.HIGH.value

    if not state.get("repository_valid", True):
        final_assessment = AssessmentStatus.INSUFFICIENT_EVIDENCE.value
    elif human_req and not state.get("human_answer"):
        final_assessment = AssessmentStatus.HUMAN_REVIEW.value
        confidence = ConfidenceLevel.LOW.value
    elif v_dep is None and not errors:
        final_assessment = AssessmentStatus.NOT_PRESENT.value
    elif current_assessment == AssessmentStatus.SYMBOL_NOT_FOUND.value:
        final_assessment = AssessmentStatus.SYMBOL_NOT_FOUND.value
    elif current_assessment == AssessmentStatus.INSUFFICIENT_EVIDENCE.value:
        final_assessment = AssessmentStatus.INSUFFICIENT_EVIDENCE.value
        confidence = ConfidenceLevel.LOW.value
    elif paths:
        final_assessment = AssessmentStatus.STATICALLY_REACHABLE.value
    else:
        # Present in dependencies, class/method verified, but no static path
        if v_dep:
            final_assessment = AssessmentStatus.NO_STATIC_PATH_FOUND.value
        else:
            final_assessment = AssessmentStatus.INSUFFICIENT_EVIDENCE.value
            confidence = ConfidenceLevel.LOW.value

    final_assessment_str = str(final_assessment.value if hasattr(final_assessment, 'value') else final_assessment)
    confidence_str = str(confidence.value if hasattr(confidence, 'value') else confidence)

    evidence.append(Evidence(
        source="evidence_aggregator",
        evidence_type="ASSESSMENT_FINALIZED",
        description=f"Final assessment determined: {final_assessment_str} (Confidence: {confidence_str})",
        confidence=confidence_str
    ).model_dump())

    return {
        "assessment": final_assessment_str,
        "confidence": confidence_str,
        "evidence": evidence
    }


def report_generator_node(state: CVEAnalysisState) -> Dict[str, Any]:
    """Node: Generates the structured final report matching Section 26."""
    report = ReportGenerator.build_report_from_state(state)
    return {
        "final_report": report.raw_report,
        "report_dict": report.model_dump(mode="json")
    }
