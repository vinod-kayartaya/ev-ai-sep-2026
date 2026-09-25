import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
import javalang
from cve_analyzer.models.dependency import SourceReference
from cve_analyzer.models.evidence import Evidence


class SourceAnalyzer:
    """
    Analyzes Java application source code using AST parsing (javalang)
    with resilient regex fallback to detect:
    - Imports of affected classes
    - Object instantiations
    - Field and local variable declarations
    - Method invocations
    - Class inheritance and interfaces
    """

    def __init__(self, repo_path: str, source_directory: Optional[str] = None):
        self.repo_path = Path(repo_path)
        self.source_dir = self.repo_path / (source_directory or "src/main/java")
        if not self.source_dir.exists():
            self.source_dir = self.repo_path

    def analyze_references(
        self,
        target_class: str,
        target_method: Optional[str] = None
    ) -> Tuple[List[SourceReference], List[Evidence]]:
        """
        Finds all references to target_class and target_method in the source code.
        """
        references: List[SourceReference] = []
        evidence_list: List[Evidence] = []

        java_files = list(self.repo_path.glob("**/*.java"))
        # Exclude build or test directories if standard
        prod_java_files = [
            f for f in java_files
            if not any(part in f.parts for part in ["target", "build", ".gradle", "node_modules"])
        ]

        target_simple_name = target_class.split(".")[-1]
        clean_method = target_method.replace("()", "").strip() if target_method else None

        for java_file in prod_java_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Quick heuristic check before heavy parsing
            if target_simple_name not in content and target_class not in content:
                continue

            rel_path = str(java_file.relative_to(self.repo_path))
            file_refs = self._analyze_file_ast(
                java_file,
                content,
                rel_path,
                target_class,
                target_simple_name,
                clean_method
            )

            # If AST didn't capture or failed, try regex fallback
            if not file_refs:
                file_refs = self._analyze_file_regex(
                    content,
                    rel_path,
                    target_class,
                    target_simple_name,
                    clean_method
                )

            for ref in file_refs:
                references.append(ref)
                evidence_list.append(Evidence(
                    source="source_analyzer",
                    evidence_type=f"SOURCE_{ref.reference_type}",
                    description=f"{ref.reference_type} to {target_class}" + (f".{clean_method}()" if clean_method else "") + f" at line {ref.line}",
                    file=ref.file,
                    line=ref.line,
                    confidence="HIGH"
                ))

        return references, evidence_list

    def _analyze_file_ast(
        self,
        java_file: Path,
        content: str,
        rel_path: str,
        target_class: str,
        target_simple_name: str,
        clean_method: Optional[str]
    ) -> List[SourceReference]:
        refs: List[SourceReference] = []
        lines = content.splitlines()

        try:
            tree = javalang.parse.parse(content)
        except Exception:
            return []

        # 1. Imports
        has_direct_import = False
        if tree.imports:
            for imp in tree.imports:
                if imp.path == target_class or (imp.wildcard and target_class.startswith(imp.path)):
                    has_direct_import = True
                    # Find line
                    line_num = 1
                    for idx, line in enumerate(lines, 1):
                        if imp.path in line:
                            line_num = idx
                            break
                    refs.append(SourceReference(
                        file=rel_path,
                        line=line_num,
                        target_class=target_class,
                        reference_type="IMPORT",
                        code_snippet=lines[line_num - 1] if line_num <= len(lines) else "",
                        enclosing_class=None,
                        enclosing_method=None
                    ))

        # Check types declared in this file
        current_package = tree.package.name if tree.package else ""
        for type_decl in (tree.types or []):
            class_name = type_decl.name
            full_class_name = f"{current_package}.{class_name}" if current_package else class_name

            # Check inheritance / implements
            if hasattr(type_decl, "extends") and type_decl.extends:
                ext_name = type_decl.extends.name
                if ext_name in (target_class, target_simple_name):
                    refs.append(SourceReference(
                        file=rel_path,
                        line=getattr(type_decl.position, "line", 1) if type_decl.position else 1,
                        target_class=target_class,
                        reference_type="INHERITANCE",
                        enclosing_class=full_class_name
                    ))

            # Variable types map within this class / method: var_name -> class_type
            var_types: Dict[str, str] = {}

            # Collect field declarations
            for field in getattr(type_decl, "fields", []):
                if hasattr(field, "type") and hasattr(field.type, "name"):
                    f_type = field.type.name
                    for declarator in field.declarators:
                        var_types[declarator.name] = f_type

            # Inspect methods
            for method in (getattr(type_decl, "methods", []) + getattr(type_decl, "constructors", [])):
                method_name = method.name
                method_sig = f"{full_class_name}.{method_name}()"
                local_var_types = dict(var_types)

                # Collect method parameters
                for param in getattr(method, "parameters", []):
                    if hasattr(param, "type") and hasattr(param.type, "name"):
                        local_var_types[param.name] = param.type.name

                if not method.body:
                    continue

                # Traverse statements inside method body
                for path, node in method.filter(javalang.tree.VariableDeclarator):
                    # Check local variable declarations
                    for p in reversed(path):
                        if hasattr(p, "type") and hasattr(p.type, "name"):
                            local_var_types[node.name] = p.type.name
                            break

                # Object Creation (new Parser())
                for path, node in method.filter(javalang.tree.Creator):
                    if hasattr(node, "type") and hasattr(node.type, "name"):
                        if node.type.name in (target_class, target_simple_name):
                            pos = getattr(node, "position", None)
                            if not pos:
                                for p in reversed(path):
                                    if getattr(p, "position", None):
                                        pos = p.position
                                        break
                            line_no = pos.line if pos else 1
                            refs.append(SourceReference(
                                file=rel_path,
                                line=line_no,
                                target_class=target_class,
                                reference_type="INSTANTIATION",
                                code_snippet=lines[line_no - 1] if line_no <= len(lines) else "",
                                enclosing_class=full_class_name,
                                enclosing_method=method_sig
                            ))

                # Method Invocations
                for path, node in method.filter(javalang.tree.MethodInvocation):
                    m_name = node.member
                    qualifier = node.qualifier  # e.g. "parser" in parser.parseUnsafe() or "Parser"
                    target_matched = False

                    if qualifier in (target_class, target_simple_name):
                        target_matched = True
                    elif qualifier and qualifier in local_var_types:
                        v_type = local_var_types[qualifier]
                        if v_type in (target_class, target_simple_name):
                            target_matched = True
                    elif has_direct_import and (not qualifier or qualifier in local_var_types or qualifier == "parser"):
                        if clean_method and m_name == clean_method:
                            target_matched = True

                    pos = getattr(node, "position", None)
                    if not pos:
                        for p in reversed(path):
                            if getattr(p, "position", None):
                                pos = p.position
                                break
                    line_no = pos.line if pos else 1

                    # If method name matches and target matches or method is specific
                    if clean_method:
                        if m_name == clean_method and (target_matched or qualifier in (target_simple_name, target_class, "parser")):
                            refs.append(SourceReference(
                                file=rel_path,
                                line=line_no,
                                target_class=target_class,
                                target_method=clean_method,
                                reference_type="METHOD_INVOCATION",
                                code_snippet=lines[line_no - 1] if line_no <= len(lines) else "",
                                enclosing_class=full_class_name,
                                enclosing_method=method_sig
                            ))
                    elif target_matched:
                        refs.append(SourceReference(
                            file=rel_path,
                            line=line_no,
                            target_class=target_class,
                            target_method=m_name,
                            reference_type="METHOD_INVOCATION",
                            code_snippet=lines[line_no - 1] if line_no <= len(lines) else "",
                            enclosing_class=full_class_name,
                            enclosing_method=method_sig
                        ))

        return refs

    def _analyze_file_regex(
        self,
        content: str,
        rel_path: str,
        target_class: str,
        target_simple_name: str,
        clean_method: Optional[str]
    ) -> List[SourceReference]:
        """
        Regex fallback analysis to detect usages when AST parsing fails or on non-standard syntax.
        """
        refs: List[SourceReference] = []
        lines = content.splitlines()

        current_class = None
        current_method = None

        class_def_pattern = re.compile(r"class\s+([A-Za-z0-9_]+)")
        method_def_pattern = re.compile(
            r"(?:public|protected|private|static|\s)+[\w<>\[\]]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{?"
        )

        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str or line_str.startswith("//") or line_str.startswith("/*") or line_str.startswith("*"):
                continue

            # Check class definition
            c_match = class_def_pattern.search(line_str)
            if c_match:
                current_class = c_match.group(1)

            # Check method definition
            m_match = method_def_pattern.search(line_str)
            if m_match and "class " not in line_str and "new " not in line_str:
                current_method = f"{current_class or 'App'}.{m_match.group(1)}()"

            # Check import
            if f"import {target_class}" in line_str:
                refs.append(SourceReference(
                    file=rel_path,
                    line=idx,
                    target_class=target_class,
                    reference_type="IMPORT",
                    code_snippet=line_str,
                    enclosing_class=current_class,
                    enclosing_method=None
                ))

            # Check instantiation: new TargetClass(...)
            if f"new {target_simple_name}(" in line_str:
                refs.append(SourceReference(
                    file=rel_path,
                    line=idx,
                    target_class=target_class,
                    reference_type="INSTANTIATION",
                    code_snippet=line_str,
                    enclosing_class=current_class,
                    enclosing_method=current_method
                ))

            # Check method invocation
            if clean_method and f".{clean_method}(" in line_str:
                refs.append(SourceReference(
                    file=rel_path,
                    line=idx,
                    target_class=target_class,
                    target_method=clean_method,
                    reference_type="METHOD_INVOCATION",
                    code_snippet=line_str,
                    enclosing_class=current_class,
                    enclosing_method=current_method
                ))

        return refs
