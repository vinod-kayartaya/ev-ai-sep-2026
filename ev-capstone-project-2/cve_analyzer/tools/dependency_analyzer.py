import re
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from cve_analyzer.models.dependency import DependencyInfo
from cve_analyzer.models.evidence import Evidence


class DependencyAnalyzer:
    """
    Resolves Maven and Gradle dependencies, parses dependency trees,
    and extracts direct/transitive dependency relationships and paths.
    """

    def __init__(self, maven_cmd: Optional[str] = None, gradle_cmd: Optional[str] = None):
        # Auto-detect or search standard paths for mvn
        self.maven_cmd = maven_cmd or self._find_maven()
        self.gradle_cmd = gradle_cmd or self._find_gradle()

    @staticmethod
    def _find_maven() -> Optional[str]:
        if shutil.which("mvn"):
            return "mvn"
        # Check standard user locations
        for cand in [
            "/Users/vinod/apache-maven-3.9.2/bin/mvn",
            "/usr/local/bin/mvn",
            "/opt/homebrew/bin/mvn",
        ]:
            if Path(cand).exists():
                return cand
        return None

    @staticmethod
    def _find_gradle() -> Optional[str]:
        if shutil.which("gradle"):
            return "gradle"
        for cand in ["/usr/local/bin/gradle", "/opt/homebrew/bin/gradle"]:
            if Path(cand).exists():
                return cand
        return None

    def resolve(
        self,
        repo_path: str,
        build_system: str,
        max_retries: int = 2
    ) -> Tuple[List[DependencyInfo], List[Evidence], Optional[str]]:
        """
        Resolves dependencies for the repository using the detected build system.
        Returns: (dependencies, evidence_list, error_message)
        """
        path = Path(repo_path)
        evidence_list: List[Evidence] = []
        dependencies: List[DependencyInfo] = []
        error: Optional[str] = None

        if build_system == "MAVEN":
            dependencies, evidence_list, error = self._resolve_maven(path, max_retries)
        elif build_system == "GRADLE":
            dependencies, evidence_list, error = self._resolve_gradle(path, max_retries)
        else:
            # Fallback: try pom.xml first, then build.gradle
            if (path / "pom.xml").exists():
                dependencies, evidence_list, error = self._resolve_maven(path, max_retries)
            elif (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
                dependencies, evidence_list, error = self._resolve_gradle(path, max_retries)
            else:
                error = "Cannot resolve dependencies: Unknown build system."
                evidence_list.append(Evidence(
                    source="dependency_analyzer",
                    evidence_type="DEPENDENCY_ERROR",
                    description=error,
                    file=repo_path,
                    confidence="HIGH"
                ))

        return dependencies, evidence_list, error

    def _resolve_maven(
        self,
        path: Path,
        max_retries: int
    ) -> Tuple[List[DependencyInfo], List[Evidence], Optional[str]]:
        evidence_list: List[Evidence] = []
        cmd_output = None
        cmd_executed = None

        # Check if pom.xml has pre-generated dependency tree file (e.g. dependency-tree.txt for tests)
        pre_tree = path / "dependency-tree.txt"
        if pre_tree.exists():
            cmd_output = pre_tree.read_text()
            cmd_executed = "cat dependency-tree.txt"

        # Attempt to run mvn dependency:tree if command is available
        if not cmd_output and self.maven_cmd:
            cmd = [self.maven_cmd, "dependency:tree", "-DoutputType=text", "-B"]
            cmd_executed = " ".join(cmd)
            for attempt in range(max_retries + 1):
                try:
                    res = subprocess.run(
                        cmd,
                        cwd=str(path),
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=False
                    )
                    if res.returncode == 0:
                        cmd_output = res.stdout
                        break
                    else:
                        if attempt == max_retries:
                            evidence_list.append(Evidence(
                                source="mvn",
                                evidence_type="COMMAND_FAILED",
                                description=f"mvn dependency:tree failed (exit code {res.returncode}): {res.stderr[:200]}",
                                command=cmd_executed,
                                confidence="HIGH"
                            ))
                except Exception as e:
                    if attempt == max_retries:
                        evidence_list.append(Evidence(
                            source="mvn",
                            evidence_type="COMMAND_EXCEPTION",
                            description=f"Exception running mvn dependency:tree: {e}",
                            command=cmd_executed,
                            confidence="HIGH"
                        ))

        # Parse output if obtained from mvn
        if cmd_output:
            deps = self.parse_maven_dependency_tree(cmd_output)
            if deps:
                evidence_list.append(Evidence(
                    source="mvn_dependency_tree",
                    evidence_type="DEPENDENCY_TREE_RESOLVED",
                    description=f"Resolved {len(deps)} dependencies via Maven dependency:tree",
                    command=cmd_executed,
                    confidence="HIGH"
                ))
                return deps, evidence_list, None

        # Fallback to direct POM.xml parsing
        pom_path = path / "pom.xml"
        if pom_path.exists():
            deps, pom_evidence = self.parse_pom_xml(pom_path)
            evidence_list.extend(pom_evidence)
            evidence_list.append(Evidence(
                source="pom_xml_parser",
                evidence_type="DEPENDENCY_FALLBACK",
                description=f"Resolved {len(deps)} dependencies directly from pom.xml",
                file=str(pom_path),
                confidence="MEDIUM"
            ))
            return deps, evidence_list, None

        return [], evidence_list, "Failed to resolve Maven dependencies."

    def _resolve_gradle(
        self,
        path: Path,
        max_retries: int
    ) -> Tuple[List[DependencyInfo], List[Evidence], Optional[str]]:
        evidence_list: List[Evidence] = []
        cmd_output = None
        cmd_executed = None

        gradlew = path / "gradlew"
        use_wrapper = gradlew.exists() and os.access(str(gradlew), os.X_OK)

        cmd = [str(gradlew) if use_wrapper else (self.gradle_cmd or "gradle"), "dependencies", "--configuration", "compileClasspath"]
        cmd_executed = " ".join(cmd)

        try:
            res = subprocess.run(
                cmd,
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=60,
                check=False
            )
            if res.returncode == 0:
                cmd_output = res.stdout
        except Exception:
            pass

        if cmd_output:
            deps = self.parse_gradle_dependencies(cmd_output)
            if deps:
                evidence_list.append(Evidence(
                    source="gradle_dependencies",
                    evidence_type="DEPENDENCY_TREE_RESOLVED",
                    description=f"Resolved {len(deps)} dependencies via Gradle",
                    command=cmd_executed,
                    confidence="HIGH"
                ))
                return deps, evidence_list, None

        # Fallback to build.gradle regex/text parsing
        build_gradle = path / "build.gradle"
        if not build_gradle.exists():
            build_gradle = path / "build.gradle.kts"

        if build_gradle.exists():
            deps = self.parse_build_gradle(build_gradle)
            evidence_list.append(Evidence(
                source="build_gradle_parser",
                evidence_type="DEPENDENCY_FALLBACK",
                description=f"Resolved {len(deps)} dependencies from {build_gradle.name}",
                file=str(build_gradle),
                confidence="MEDIUM"
            ))
            return deps, evidence_list, None

        return [], evidence_list, "Failed to resolve Gradle dependencies."

    @staticmethod
    def parse_maven_dependency_tree(tree_text: str) -> List[DependencyInfo]:
        """
        Parses `mvn dependency:tree` output into structured DependencyInfo list.
        Maintains parent stack to establish complete dependency paths.
        """
        dependencies: List[DependencyInfo] = []
        lines = tree_text.strip().splitlines()

        # Regular expressions for maven dependency lines:
        # e.g.: [INFO] +- com.vendor:library-b:jar:1.0.0:compile
        # or:   +- com.vendor:library-b:jar:1.0.0:compile
        tree_pattern = re.compile(
            r"^(?:\[INFO\]\s*)?([+|\\|\s|-]+)?\s*([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+):(?:([a-zA-Z0-9_.-]+):)?([a-zA-Z0-9_.-]+)(?:\s*\((.*)\))?"
        )
        # Also simple 4/5 part coordinate: group:artifact:type:version:scope
        simple_pattern = re.compile(
            r"^(?:\[INFO\]\s*)?([+|\\|\s|-]+)?\s*([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+)$"
        )

        # Root project name
        root_name = "application"
        # Stack entries: (depth, coordinate_str)
        stack: List[Tuple[int, str]] = [(0, root_name)]

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("[INFO] ---") or line_str.startswith("[INFO] Building"):
                continue

            # Check root project line
            # e.g. [INFO] com.example:order-service:jar:1.0-SNAPSHOT
            if not re.search(r"(\+-|\\-)", line):
                root_match = re.search(r"([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+)", line)
                if root_match:
                    root_name = f"{root_match.group(1)}:{root_match.group(2)}:{root_match.group(4)}"
                    stack = [(0, root_name)]
                    continue

            # Determine tree indentation/depth
            tree_prefix_match = re.search(r"^(?:\[INFO\]\s*)?([+|\\|\s|-]+)", line)
            if not tree_prefix_match:
                continue

            prefix = tree_prefix_match.group(1)
            # Count tree levels: each level is typically 3 spaces/chars ("+- ", "|  ", "\- ")
            depth = max(1, len(prefix) // 3)

            # Match coordinates
            m = tree_pattern.search(line)
            group, artifact, version, scope = "", "", "", "compile"

            if m:
                group = m.group(2)
                artifact = m.group(3)
                # m.group(4) is usually packaging/type (jar/war)
                # m.group(5) is version or classifier
                # m.group(6) is scope
                if m.group(5):
                    version = m.group(5)
                    scope = m.group(6) or "compile"
                else:
                    version = m.group(4)
                    scope = m.group(6) or "compile"
            else:
                m_simple = simple_pattern.search(line)
                if m_simple:
                    group = m_simple.group(2)
                    artifact = m_simple.group(3)
                    version = m_simple.group(4)
                    scope = m_simple.group(5)
                else:
                    continue

            coord = f"{group}:{artifact}:{version}"
            direct = (depth <= 1)

            # Adjust stack to current depth
            while len(stack) > 1 and stack[-1][0] >= depth:
                stack.pop()

            dep_path = [item[1] for item in stack] + [coord]
            stack.append((depth, coord))

            dep_info = DependencyInfo(
                group=group,
                artifact=artifact,
                version=version,
                scope=scope,
                direct=direct,
                dependency_path=dep_path
            )
            dependencies.append(dep_info)

        return dependencies

    @staticmethod
    def parse_gradle_dependencies(tree_text: str) -> List[DependencyInfo]:
        """
        Parses `./gradlew dependencies` output into DependencyInfo objects.
        """
        dependencies: List[DependencyInfo] = []
        stack: List[Tuple[int, str]] = [(0, "application")]

        # e.g.: \--- com.vendor:library-b:1.0.0
        # or:   +--- com.vendor:vulnerable-library:1.2.0 -> 1.2.3
        pattern = re.compile(
            r"([+|\\|\s|-]+)\s*([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+)(?:\s*->\s*([a-zA-Z0-9_.-]+))?"
        )

        for line in tree_text.splitlines():
            m = pattern.search(line)
            if not m:
                continue

            prefix = m.group(1)
            group = m.group(2)
            artifact = m.group(3)
            # If version was bumped with -> X.Y.Z, use target version
            version = m.group(5) if m.group(5) else m.group(4)

            depth = max(1, len(prefix) // 4)
            coord = f"{group}:{artifact}:{version}"
            direct = (depth <= 1)

            while len(stack) > 1 and stack[-1][0] >= depth:
                stack.pop()

            dep_path = [item[1] for item in stack] + [coord]
            stack.append((depth, coord))

            dependencies.append(DependencyInfo(
                group=group,
                artifact=artifact,
                version=version,
                scope="compile",
                direct=direct,
                dependency_path=dep_path
            ))

        return dependencies

    @staticmethod
    def parse_pom_xml(pom_file: Path) -> Tuple[List[DependencyInfo], List[Evidence]]:
        """
        Deterministic XML fallback parser for pom.xml. Resolves properties and dependencies.
        """
        dependencies: List[DependencyInfo] = []
        evidence: List[Evidence] = []

        try:
            tree = ET.parse(str(pom_file))
            root = tree.getroot()

            # Handle XML namespace
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            # Properties map
            properties: Dict[str, str] = {}
            props_elem = root.find(f"{ns}properties")
            if props_elem is not None:
                for child in props_elem:
                    prop_name = child.tag.replace(ns, "")
                    properties[prop_name] = child.text.strip() if child.text else ""

            # Root artifact coords
            root_group = root.find(f"{ns}groupId")
            if root_group is None:
                root_group = root.find(f"{ns}parent/{ns}groupId")
            root_art = root.find(f"{ns}artifactId")
            root_ver = root.find(f"{ns}version")
            if root_ver is None:
                root_ver = root.find(f"{ns}parent/{ns}version")

            root_coord = "application"
            if root_art is not None and root_art.text:
                g = root_group.text.strip() if (root_group is not None and root_group.text) else "com.example"
                v = root_ver.text.strip() if (root_ver is not None and root_ver.text) else "1.0.0"
                root_coord = f"{g}:{root_art.text.strip()}:{v}"

            # Function to resolve ${property}
            def resolve_str(s: Optional[str]) -> str:
                if not s:
                    return ""
                res = s.strip()
                for k, v in properties.items():
                    res = res.replace(f"${{{k}}}", v)
                return res

            # Parse direct dependencies
            deps_elem = root.find(f"{ns}dependencies")
            if deps_elem is not None:
                for dep in deps_elem.findall(f"{ns}dependency"):
                    g_elem = dep.find(f"{ns}groupId")
                    a_elem = dep.find(f"{ns}artifactId")
                    v_elem = dep.find(f"{ns}version")
                    s_elem = dep.find(f"{ns}scope")

                    group = resolve_str(g_elem.text if g_elem is not None else "")
                    artifact = resolve_str(a_elem.text if a_elem is not None else "")
                    version = resolve_str(v_elem.text if v_elem is not None else "")
                    scope = resolve_str(s_elem.text if s_elem is not None else "compile")

                    if artifact:
                        coord = f"{group}:{artifact}:{version}" if group else f"{artifact}:{version}"
                        dependencies.append(DependencyInfo(
                            group=group,
                            artifact=artifact,
                            version=version,
                            scope=scope,
                            direct=True,
                            dependency_path=[root_coord, coord]
                        ))

            # Look for sub-modules if a multi-module POM
            modules_elem = root.find(f"{ns}modules")
            if modules_elem is not None:
                for mod in modules_elem.findall(f"{ns}module"):
                    if mod.text:
                        sub_pom = pom_file.parent / mod.text.strip() / "pom.xml"
                        if sub_pom.exists():
                            sub_deps, _ = DependencyAnalyzer.parse_pom_xml(sub_pom)
                            dependencies.extend(sub_deps)

        except Exception as e:
            evidence.append(Evidence(
                source="pom_xml_parser",
                evidence_type="XML_PARSE_ERROR",
                description=f"Error parsing pom.xml: {e}",
                file=str(pom_file),
                confidence="LOW"
            ))

        return dependencies, evidence

    @staticmethod
    def parse_build_gradle(gradle_file: Path) -> List[DependencyInfo]:
        """
        Regex-based parser for build.gradle dependencies.
        """
        dependencies: List[DependencyInfo] = []
        text = gradle_file.read_text(errors="ignore")

        # e.g.: implementation 'com.vendor:library-b:1.0.0'
        # or:   implementation("com.vendor:library-b:1.0.0")
        pattern = re.compile(
            r"""(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s*\(?['"]([a-zA-Z0-9_.-]+):([a-zA-Z0-9_.-]+)(?::([a-zA-Z0-9_.-]+))?['"]\)?"""
        )

        for match in pattern.finditer(text):
            group = match.group(1)
            artifact = match.group(2)
            version = match.group(3) or ""
            coord = f"{group}:{artifact}:{version}" if version else f"{group}:{artifact}"

            dependencies.append(DependencyInfo(
                group=group,
                artifact=artifact,
                version=version,
                scope="compile",
                direct=True,
                dependency_path=["application", coord]
            ))

        return dependencies
