import os
import shutil
import zipfile
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from cve_analyzer.models.evidence import Evidence


class JarAnalyzer:
    """
    Inspects Java JAR files and bytecode using `jar`, `javap`, or zipfile inspection
    to verify class and method existence.
    """

    def __init__(self, javap_cmd: Optional[str] = None):
        self.javap_cmd = javap_cmd or shutil.which("javap") or "javap"

    def locate_jar(
        self,
        group: str,
        artifact: str,
        version: str,
        repo_path: Optional[str] = None
    ) -> Optional[Path]:
        """
        Attempts to locate a dependency JAR in:
        1. Local repository lib/ or target/ folders
        2. Maven local cache (~/.m2/repository)
        3. Gradle caches
        """
        # 1. Search within the repo folder if provided
        if repo_path:
            repo = Path(repo_path)
            for cand in repo.glob(f"**/{artifact}*.jar"):
                if not cand.name.endswith("-sources.jar") and not cand.name.endswith("-javadoc.jar"):
                    return cand

        # 2. Search local Maven repository: ~/.m2/repository/group_path/artifact/version/*.jar
        m2_repo = Path.home() / ".m2" / "repository"
        if m2_repo.exists() and group and artifact and version:
            group_rel = group.replace(".", "/")
            jar_candidate = m2_repo / group_rel / artifact / version / f"{artifact}-{version}.jar"
            if jar_candidate.exists():
                return jar_candidate

        # 3. Search common mock/test directories in workspace
        ws = Path(__file__).resolve().parent.parent.parent
        for cand in ws.glob(f"**/{artifact}*.jar"):
            return cand

        return None

    def verify_symbols_in_jar(
        self,
        jar_path: Path,
        class_name: str,
        method_name: Optional[str] = None
    ) -> Tuple[bool, bool, List[Evidence]]:
        """
        Verifies whether class_name and method_name exist in the given JAR.
        Returns: (class_found: bool, method_found: bool, evidence_list: List[Evidence])
        """
        evidence_list: List[Evidence] = []
        if not jar_path.exists():
            evidence_list.append(Evidence(
                source="jar_analyzer",
                evidence_type="JAR_NOT_FOUND",
                description=f"JAR file does not exist at {jar_path}",
                file=str(jar_path),
                confidence="HIGH"
            ))
            return False, False, evidence_list

        class_resource = class_name.replace(".", "/") + ".class"
        class_found = False

        # 1. Verify class file presence in JAR via zipfile inspection
        try:
            with zipfile.ZipFile(str(jar_path), 'r') as z:
                all_files = set(z.namelist())
                class_found = class_resource in all_files

            evidence_list.append(Evidence(
                source="jar_zip_inspection",
                evidence_type="CLASS_EXISTS" if class_found else "CLASS_NOT_FOUND",
                description=f"Class {class_name} {'found' if class_found else 'NOT found'} in {jar_path.name}",
                file=str(jar_path),
                confidence="HIGH"
            ))
        except Exception as e:
            evidence_list.append(Evidence(
                source="jar_zip_inspection",
                evidence_type="JAR_READ_ERROR",
                description=f"Failed to read JAR archive {jar_path}: {e}",
                file=str(jar_path),
                confidence="LOW"
            ))
            return False, False, evidence_list

        if not class_found:
            return False, False, evidence_list

        if not method_name:
            # Only class verification requested
            return True, True, evidence_list

        # 2. Verify method existence using javap
        method_found = False
        cmd = [self.javap_cmd, "-classpath", str(jar_path), class_name]
        cmd_str = " ".join(cmd)

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                check=False
            )
            if res.returncode == 0:
                javap_output = res.stdout
                # Check method presence: match method name followed by parentheses or as identifier
                # e.g. "public void parseUnsafe(" or "parseUnsafe("
                clean_method = method_name.replace("()", "").strip()
                if f"{clean_method}(" in javap_output or f" {clean_method} " in javap_output:
                    method_found = True

                evidence_list.append(Evidence(
                    source="javap",
                    evidence_type="METHOD_EXISTS" if method_found else "METHOD_NOT_FOUND",
                    description=f"Method {method_name} {'found' if method_found else 'NOT found'} in {class_name}",
                    file=str(jar_path),
                    command=cmd_str,
                    confidence="HIGH"
                ))
            else:
                # Javap command failed, fallback to searching byte stream in class file
                method_found = self._check_method_in_class_bytes(jar_path, class_resource, method_name)
                evidence_list.append(Evidence(
                    source="bytecode_search",
                    evidence_type="METHOD_EXISTS" if method_found else "METHOD_NOT_FOUND",
                    description=f"Method {method_name} {'found' if method_found else 'NOT found'} via bytecode string table",
                    file=str(jar_path),
                    confidence="MEDIUM"
                ))
        except Exception as e:
            # Fallback
            method_found = self._check_method_in_class_bytes(jar_path, class_resource, method_name)
            evidence_list.append(Evidence(
                source="bytecode_fallback",
                evidence_type="METHOD_EXISTS" if method_found else "METHOD_NOT_FOUND",
                description=f"Javap error ({e}), bytecode search result: {method_found}",
                file=str(jar_path),
                confidence="MEDIUM"
            ))

        return class_found, method_found, evidence_list

    @staticmethod
    def _check_method_in_class_bytes(jar_path: Path, class_resource: str, method_name: str) -> bool:
        """Fallback check: inspect strings in class file constant pool."""
        try:
            clean_m = method_name.replace("()", "").encode("utf-8")
            with zipfile.ZipFile(str(jar_path), 'r') as z:
                content = z.read(class_resource)
                return clean_m in content
        except Exception:
            return False

    @staticmethod
    def create_mock_jar(jar_path: Path, class_name: str, methods: List[str]):
        """
        Creates a valid mock JAR with a compiled class containing specified methods.
        Used for reproducible testing and evaluation scenarios.
        """
        jar_path = jar_path.resolve()
        jar_path.parent.mkdir(parents=True, exist_ok=True)
        pkg_parts = class_name.split(".")
        simple_class_name = pkg_parts[-1]
        pkg_name = ".".join(pkg_parts[:-1])

        java_code = f"package {pkg_name};\npublic class {simple_class_name} {{\n"
        for m in methods:
            clean_m = m.replace("()", "")
            java_code += f"    public void {clean_m}() {{ System.out.println(\"{clean_m}\"); }}\n"
        java_code += "}\n"

        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            pkg_dir = tmp
            for p in pkg_parts[:-1]:
                pkg_dir = pkg_dir / p
            pkg_dir.mkdir(parents=True, exist_ok=True)

            java_file = pkg_dir / f"{simple_class_name}.java"
            java_file.write_text(java_code)

            # Compile with javac
            javac = shutil.which("javac") or "javac"
            subprocess.run([javac, str(java_file)], cwd=tmp_dir, check=True)

            # Package with jar
            jar_cmd = shutil.which("jar") or "jar"
            class_rel = java_file.with_suffix(".class").relative_to(tmp)
            subprocess.run([jar_cmd, "cf", str(jar_path), str(class_rel)], cwd=tmp_dir, check=True)
