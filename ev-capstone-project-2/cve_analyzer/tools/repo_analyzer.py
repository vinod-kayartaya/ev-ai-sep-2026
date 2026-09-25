import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from cve_analyzer.models.evidence import Evidence


class RepositoryAnalyzer:
    """
    Validates Java repositories and detects build systems (Maven / Gradle) deterministically.
    """

    @staticmethod
    def analyze(repo_path: str) -> Tuple[Dict[str, Any], List[Evidence]]:
        evidence_list = []
        path = Path(repo_path)

        if not path.exists() or not path.is_dir():
            evidence = Evidence(
                source="repo_analyzer",
                evidence_type="INVALID_REPOSITORY",
                description=f"Directory {repo_path} does not exist or is not a directory.",
                file=repo_path,
                confidence="HIGH"
            )
            return {
                "repository_valid": False,
                "build_system": "UNKNOWN",
                "source_directory": "",
                "test_directory": "",
                "java_files_count": 0
            }, [evidence]

        # Check build files
        has_pom = (path / "pom.xml").exists()
        has_gradle_groovy = (path / "build.gradle").exists()
        has_gradle_kotlin = (path / "build.gradle.kts").exists()
        has_gradle = has_gradle_groovy or has_gradle_kotlin

        build_system = "UNKNOWN"
        if has_pom:
            build_system = "MAVEN"
            evidence_list.append(Evidence(
                source="repo_analyzer",
                evidence_type="BUILD_SYSTEM_DETECTED",
                description="Found pom.xml indicating a Maven build system.",
                file=str(path / "pom.xml"),
                confidence="HIGH"
            ))
        elif has_gradle:
            build_system = "GRADLE"
            gradle_file = "build.gradle.kts" if has_gradle_kotlin else "build.gradle"
            evidence_list.append(Evidence(
                source="repo_analyzer",
                evidence_type="BUILD_SYSTEM_DETECTED",
                description=f"Found {gradle_file} indicating a Gradle build system.",
                file=str(path / gradle_file),
                confidence="HIGH"
            ))
        else:
            evidence_list.append(Evidence(
                source="repo_analyzer",
                evidence_type="BUILD_SYSTEM_UNKNOWN",
                description="No pom.xml or build.gradle found in repository root.",
                file=repo_path,
                confidence="HIGH"
            ))

        # Detect source directory
        source_candidates = [
            "src/main/java",
            "app/src/main/java",
            "src",
            "."
        ]
        source_dir = None
        for cand in source_candidates:
            cand_path = path / cand
            if cand_path.exists() and cand_path.is_dir():
                java_files = list(cand_path.glob("**/*.java"))
                if java_files:
                    source_dir = cand
                    break

        if not source_dir:
            # Fallback check any java files
            all_java = list(path.glob("**/*.java"))
            if all_java:
                source_dir = "."

        test_candidates = [
            "src/test/java",
            "app/src/test/java",
            "test"
        ]
        test_dir = None
        for cand in test_candidates:
            if (path / cand).exists() and (path / cand).is_dir():
                test_dir = cand
                break

        # Count java files in repository
        total_java_files = len(list(path.glob("**/*.java")))

        is_valid = (build_system != "UNKNOWN" or total_java_files > 0)

        summary_evidence = Evidence(
            source="repo_analyzer",
            evidence_type="REPOSITORY_STRUCTURE",
            description=f"Build System: {build_system}, Source Dir: {source_dir or 'None'}, Java Files: {total_java_files}",
            file=repo_path,
            confidence="HIGH"
        )
        evidence_list.append(summary_evidence)

        result = {
            "repository_valid": is_valid,
            "build_system": build_system,
            "source_directory": source_dir or "src/main/java",
            "test_directory": test_dir,
            "java_files_count": total_java_files
        }
        return result, evidence_list
