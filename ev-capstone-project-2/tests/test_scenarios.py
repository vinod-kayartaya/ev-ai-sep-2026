import pytest
from pathlib import Path
from cve_analyzer.agent.graph import build_cve_analysis_graph
from cve_analyzer.models.state import CVEAnalysisState
from cve_analyzer.models.report import AssessmentStatus
from tests.fixtures_builder import FixturesBuilder


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("cve_test_fixtures")
    FixturesBuilder.ensure_mock_jars(base)
    return base


def run_graph(state: CVEAnalysisState) -> dict:
    graph = build_cve_analysis_graph(checkpointer=False)
    final_output = {}
    for event in graph.stream(state):
        for _, node_output in event.items():
            final_output.update(node_output)
    return final_output


def test_scenario_1_dependency_absent(fixtures_dir):
    """Scenario 1: Vulnerable dependency absent -> NOT_PRESENT"""
    repo_path = FixturesBuilder.create_scenario_1_repo(fixtures_dir)
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0001",
        "cve_raw_text": "artifact: com.vendor:vulnerable-library affected_class: com.vendor.Parser affected_method: parseUnsafe",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.NOT_PRESENT.value
    # Verify report contains NOT_PRESENT
    assert "NOT_PRESENT" in result.get("final_report", "")


def test_scenario_2_dependency_unused(fixtures_dir):
    """Scenario 2: Vulnerable dependency present but unused -> NO_STATIC_PATH_FOUND"""
    repo_path = FixturesBuilder.create_scenario_2_repo(fixtures_dir, fixtures_dir / "mock_jars")
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0002",
        "cve_raw_text": "artifact: com.vendor:vulnerable-library affected_class: com.vendor.Parser affected_method: parseUnsafe",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.NO_STATIC_PATH_FOUND.value
    assert "NO_STATIC_PATH_FOUND" in result.get("final_report", "")
    assert "Application Reference: NOT FOUND" in result.get("final_report", "")


def test_scenario_3_vulnerable_class_absent(fixtures_dir):
    """Scenario 3: Vulnerable class absent in JAR -> SYMBOL_NOT_FOUND"""
    repo_path = FixturesBuilder.create_scenario_3_repo(fixtures_dir, fixtures_dir / "mock_jars")
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0003",
        "cve_raw_text": "artifact: com.vendor:missing-class-library affected_class: com.vendor.Parser affected_method: parseUnsafe",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.SYMBOL_NOT_FOUND.value
    assert "Class Present: NO" in result.get("final_report", "")


def test_scenario_4_vulnerable_method_absent(fixtures_dir):
    """Scenario 4: Vulnerable method absent in JAR -> SYMBOL_NOT_FOUND"""
    repo_path = FixturesBuilder.create_scenario_4_repo(fixtures_dir, fixtures_dir / "mock_jars")
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0004",
        "cve_raw_text": "artifact: com.vendor:missing-method-library affected_class: com.vendor.Parser affected_method: parseUnsafe",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.SYMBOL_NOT_FOUND.value
    assert "Method Present: NO" in result.get("final_report", "")


def test_scenario_5_method_directly_invoked(fixtures_dir):
    """Scenario 5: Method directly invoked -> STATICALLY_REACHABLE"""
    repo_path = FixturesBuilder.create_scenario_5_repo(fixtures_dir, fixtures_dir / "mock_jars")
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0005",
        "cve_raw_text": "artifact: com.vendor:vulnerable-library affected_class: com.vendor.Parser affected_method: parseUnsafe",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.STATICALLY_REACHABLE.value
    assert len(result["call_paths"]) > 0
    assert "STATICALLY_REACHABLE" in result.get("final_report", "")
    assert "Parser.parseUnsafe" in result.get("final_report", "")


def test_scenario_6_transitive_dependency_reachable(fixtures_dir):
    """Scenario 6: Transitive dependency + reachable method -> STATICALLY_REACHABLE"""
    repo_path = FixturesBuilder.create_scenario_6_repo(fixtures_dir, fixtures_dir / "mock_jars")
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0006",
        "cve_raw_text": "artifact: com.vendor:vulnerable-library affected_class: com.vendor.Parser affected_method: parseUnsafe",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.STATICALLY_REACHABLE.value
    # Verify dependency is classified as TRANSITIVE
    assert result["vulnerable_dependency"]["direct"] is False
    assert len(result["vulnerable_dependency"]["dependency_path"]) > 2
    # Verify call path discovered: OrderController.submit() -> OrderService.process() -> Parser.parseUnsafe()
    report = result.get("final_report", "")
    assert "Dependency Type: TRANSITIVE" in report
    assert "OrderController.submit" in report
    assert "OrderService.process" in report
    assert "Parser.parseUnsafe" in report


def test_scenario_7_cve_symbol_ambiguous(fixtures_dir):
    """Scenario 7: CVE symbol ambiguous -> HUMAN_REVIEW"""
    repo_path = FixturesBuilder.create_scenario_1_repo(fixtures_dir)
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0007",
        "cve_raw_text": "Vulnerability reported in com.vendor:vulnerable-library. The specific vulnerable class or method is not identified.",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.HUMAN_REVIEW.value
    assert result["human_review_required"] is True


def test_scenario_8_source_bytecode_unavailable(fixtures_dir):
    """Scenario 8: Source/bytecode unavailable -> INSUFFICIENT_EVIDENCE"""
    repo_path = FixturesBuilder.create_scenario_8_repo(fixtures_dir)
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0008",
        "cve_raw_text": "artifact: com.vendor:unknown-remote-library affected_class: com.vendor.RemoteParser affected_method: execute",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.INSUFFICIENT_EVIDENCE.value
    assert "INSUFFICIENT_EVIDENCE" in result.get("final_report", "")


def test_scenario_9_dependency_command_fails(fixtures_dir):
    """Scenario 9: Dependency command fails -> Retry / error handling"""
    from cve_analyzer.tools.dependency_analyzer import DependencyAnalyzer
    # Point to invalid maven binary to simulate command failure
    analyzer = DependencyAnalyzer(maven_cmd="/invalid/path/to/mvn")
    repo_path = FixturesBuilder.create_scenario_1_repo(fixtures_dir)
    deps, ev_list, err = analyzer.resolve(str(repo_path), "MAVEN", max_retries=1)
    # The analyzer should handle the failure and fall back to POM.xml parser
    assert len(deps) >= 1
    assert any(ev.evidence_type == "DEPENDENCY_FALLBACK" for ev in ev_list)


def test_scenario_10_multiple_possible_symbols(fixtures_dir):
    """Scenario 10: Multiple possible symbols -> HUMAN_REVIEW"""
    repo_path = FixturesBuilder.create_scenario_1_repo(fixtures_dir)
    state: CVEAnalysisState = {
        "repository_path": str(repo_path),
        "cve_id": "CVE-2024-0010",
        "cve_raw_text": "Vulnerability in com.vendor:vulnerable-library affecting either com.vendor.XmlParser or com.vendor.JsonParser via parseXml() or parseJson()",
        "retry_count": 0,
    }
    result = run_graph(state)
    assert result["assessment"] == AssessmentStatus.HUMAN_REVIEW.value
    assert result["human_review_required"] is True
