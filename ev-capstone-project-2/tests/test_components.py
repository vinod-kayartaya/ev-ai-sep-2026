import pytest
from pathlib import Path
from cve_analyzer.tools.git_manager import GitManager
from cve_analyzer.tools.repo_analyzer import RepositoryAnalyzer
from cve_analyzer.tools.dependency_analyzer import DependencyAnalyzer
from cve_analyzer.tools.callgraph_analyzer import CallGraphAnalyzer
from cve_analyzer.models.dependency import SourceReference
from cve_analyzer.report_generator import ReportGenerator
from cve_analyzer.models.report import AnalysisReport, AssessmentStatus, ConfidenceLevel


def test_git_manager_is_git_url():
    assert GitManager.is_git_url("https://github.com/owner/repo.git") is True
    assert GitManager.is_git_url("git@github.com:owner/repo.git") is True
    assert GitManager.is_git_url("https://github.com/owner/repo") is True
    assert GitManager.is_git_url("/local/path/to/repo") is False


def test_git_manager_local_repo(tmp_path):
    repo_dir = tmp_path / "my_java_repo"
    repo_dir.mkdir()
    (repo_dir / "pom.xml").write_text("<project></project>")

    git_mgr = GitManager()
    path, ev = git_mgr.prepare_repository(str(repo_dir))
    assert path == str(repo_dir.resolve())
    assert ev.evidence_type == "LOCAL_REPO_VALIDATED"


def test_repo_analyzer(tmp_path):
    repo_dir = tmp_path / "maven_repo"
    repo_dir.mkdir()
    (repo_dir / "pom.xml").write_text("<project></project>")
    src_dir = repo_dir / "src/main/java"
    src_dir.mkdir(parents=True)
    (src_dir / "Main.java").write_text("public class Main {}")

    info, evs = RepositoryAnalyzer.analyze(str(repo_dir))
    assert info["repository_valid"] is True
    assert info["build_system"] == "MAVEN"
    assert info["source_directory"] == "src/main/java"
    assert info["java_files_count"] == 1


def test_dependency_analyzer_tree_parser():
    tree_text = r"""[INFO] com.example:app:jar:1.0.0
[INFO] +- com.vendor:framework:jar:2.0.0:compile
[INFO] |  \- com.vendor:transitive-lib:jar:1.5.0:compile
[INFO] \- org.slf4j:slf4j-api:jar:1.7.30:compile
"""
    deps = DependencyAnalyzer.parse_maven_dependency_tree(tree_text)
    assert len(deps) == 3

    transitive = [d for d in deps if d.artifact == "transitive-lib"][0]
    assert transitive.direct is False
    assert len(transitive.dependency_path) == 3
    assert transitive.dependency_path[0] == "com.example:app:1.0.0"
    assert transitive.dependency_path[1] == "com.vendor:framework:2.0.0"
    assert transitive.dependency_path[2] == "com.vendor:transitive-lib:1.5.0"

    direct = [d for d in deps if d.artifact == "framework"][0]
    assert direct.direct is True


def test_callgraph_analyzer_bfs(tmp_path):
    src = tmp_path / "src/main/java/com/example"
    src.mkdir(parents=True)

    (src / "Controller.java").write_text("""package com.example;
public class Controller {
    public void submit() {
        new Service().process();
    }
}""")

    (src / "Service.java").write_text("""package com.example;
import com.vendor.Parser;
public class Service {
    public void process() {
        new Parser().parseUnsafe();
    }
}""")

    analyzer = CallGraphAnalyzer(str(tmp_path))
    refs = [
        SourceReference(
            file="src/main/java/com/example/Service.java",
            line=5,
            target_class="com.vendor.Parser",
            target_method="parseUnsafe",
            reference_type="METHOD_INVOCATION",
            enclosing_class="com.example.Service",
            enclosing_method="Service.process()"
        )
    ]

    paths, evs = analyzer.find_reachability_paths("com.vendor.Parser", "parseUnsafe", refs)
    assert len(paths) >= 1
    # Verify path connects submit() to parseUnsafe()
    path = paths[0]
    assert "Controller.submit()" in path[0]
    assert "parseUnsafe()" in path[-1]


def test_report_generator_formatting():
    report = AnalysisReport(
        cve_id="CVE-2024-TEST",
        affected_artifact="com.vendor:vulnerable-library",
        detected_version="1.2.3",
        dependency_type="TRANSITIVE",
        dependency_path=["app", "framework-a", "library-b", "vulnerable-library:1.2.3"],
        affected_class="com.vendor.Parser",
        affected_method="parseUnsafe()",
        class_present=True,
        method_present=True,
        application_references=[
            SourceReference(
                file="OrderService.java",
                line=42,
                target_class="com.vendor.Parser",
                target_method="parseUnsafe",
                reference_type="METHOD_INVOCATION",
                code_snippet="Parser.parseUnsafe(data)"
            )
        ],
        static_call_paths=[
            ["OrderController.submit()", "OrderService.process()", "Parser.parseUnsafe()"]
        ],
        assessment=AssessmentStatus.STATICALLY_REACHABLE,
        confidence=ConfidenceLevel.HIGH
    )

    text = ReportGenerator.generate_text_report(report)
    assert "JAVA CVE REACHABILITY ANALYSIS" in text
    assert "CVE: CVE-2024-TEST" in text
    assert "Affected Artifact: com.vendor:vulnerable-library" in text
    assert "Detected Version: 1.2.3" in text
    assert "Dependency Type: TRANSITIVE" in text
    assert "Class: com.vendor.Parser" in text
    assert "Method: parseUnsafe()" in text
    assert "Class Present: YES" in text
    assert "Method Present: YES" in text
    assert "Reference: OrderService.java:42" in text
    assert "Invocation: Parser.parseUnsafe(data)" in text
    assert "OrderController.submit()" in text
    assert "OrderService.process()" in text
    assert "Parser.parseUnsafe()" in text
    assert "STATICALLY_REACHABLE" in text
    assert "Confidence: HIGH" in text
    assert "Static reachability does not establish runtime" in text
