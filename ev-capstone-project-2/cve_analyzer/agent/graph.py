from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from cve_analyzer.models.state import CVEAnalysisState
from cve_analyzer.models.report import AssessmentStatus
from cve_analyzer.agent.nodes import (
    prepare_repository_node,
    repository_validator_node,
    build_system_detector_node,
    vulnerability_analyzer_node,
    dependency_analyzer_node,
    human_review_node,
    symbol_verifier_node,
    source_analyzer_node,
    reachability_analyzer_node,
    evidence_aggregator_node,
    report_generator_node,
)


# Conditional routing functions
def route_after_prepare(state: CVEAnalysisState) -> Literal["repository_validator", "evidence_aggregator"]:
    if not state.get("repository_valid", True) or state.get("assessment") == AssessmentStatus.INSUFFICIENT_EVIDENCE.value:
        return "evidence_aggregator"
    return "repository_validator"


def route_after_vulnerability(state: CVEAnalysisState) -> Literal["human_review", "dependency_analyzer"]:
    vuln = state.get("vulnerability", {})
    if vuln.get("is_ambiguous", False) and not state.get("human_answer"):
        return "human_review"
    return "dependency_analyzer"


def route_after_human_review(state: CVEAnalysisState) -> Literal["vulnerability_analyzer", "evidence_aggregator"]:
    if state.get("human_review_required") and not state.get("human_answer"):
        return "evidence_aggregator"
    return "vulnerability_analyzer"


def route_after_dependency(state: CVEAnalysisState) -> Literal["symbol_verifier", "evidence_aggregator"]:
    # Early termination if vulnerable dependency absent
    if not state.get("vulnerable_dependency"):
        return "evidence_aggregator"
    return "symbol_verifier"


def route_after_symbol_verifier(state: CVEAnalysisState) -> Literal["source_analyzer", "evidence_aggregator"]:
    assessment = state.get("assessment")
    if assessment in (AssessmentStatus.SYMBOL_NOT_FOUND.value, AssessmentStatus.INSUFFICIENT_EVIDENCE.value):
        return "evidence_aggregator"
    return "source_analyzer"


def route_after_source(state: CVEAnalysisState) -> Literal["reachability_analyzer", "evidence_aggregator"]:
    refs = state.get("references", [])
    if not refs:
        return "evidence_aggregator"
    return "reachability_analyzer"


def build_cve_analysis_graph(checkpointer: bool = True):
    """
    Constructs the compiled LangGraph workflow for Java CVE Reachability Analysis.
    """
    workflow = StateGraph(CVEAnalysisState)

    # Add Nodes
    workflow.add_node("prepare_repository", prepare_repository_node)
    workflow.add_node("repository_validator", repository_validator_node)
    workflow.add_node("build_system_detector", build_system_detector_node)
    workflow.add_node("vulnerability_analyzer", vulnerability_analyzer_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("dependency_analyzer", dependency_analyzer_node)
    workflow.add_node("symbol_verifier", symbol_verifier_node)
    workflow.add_node("source_analyzer", source_analyzer_node)
    workflow.add_node("reachability_analyzer", reachability_analyzer_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)
    workflow.add_node("report_generator", report_generator_node)

    # Add Edges and Conditional Edges
    workflow.add_edge(START, "prepare_repository")

    workflow.add_conditional_edges(
        "prepare_repository",
        route_after_prepare,
        {
            "repository_validator": "repository_validator",
            "evidence_aggregator": "evidence_aggregator"
        }
    )

    workflow.add_edge("repository_validator", "build_system_detector")
    workflow.add_edge("build_system_detector", "vulnerability_analyzer")

    workflow.add_conditional_edges(
        "vulnerability_analyzer",
        route_after_vulnerability,
        {
            "human_review": "human_review",
            "dependency_analyzer": "dependency_analyzer"
        }
    )

    workflow.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "vulnerability_analyzer": "vulnerability_analyzer",
            "evidence_aggregator": "evidence_aggregator"
        }
    )

    workflow.add_conditional_edges(
        "dependency_analyzer",
        route_after_dependency,
        {
            "symbol_verifier": "symbol_verifier",
            "evidence_aggregator": "evidence_aggregator"
        }
    )

    workflow.add_conditional_edges(
        "symbol_verifier",
        route_after_symbol_verifier,
        {
            "source_analyzer": "source_analyzer",
            "evidence_aggregator": "evidence_aggregator"
        }
    )

    workflow.add_conditional_edges(
        "source_analyzer",
        route_after_source,
        {
            "reachability_analyzer": "reachability_analyzer",
            "evidence_aggregator": "evidence_aggregator"
        }
    )

    workflow.add_edge("reachability_analyzer", "evidence_aggregator")
    workflow.add_edge("evidence_aggregator", "report_generator")
    workflow.add_edge("report_generator", END)

    memory = MemorySaver() if checkpointer else None
    return workflow.compile(checkpointer=memory)
