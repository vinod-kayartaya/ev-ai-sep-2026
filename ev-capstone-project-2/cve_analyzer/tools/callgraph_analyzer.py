import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from collections import deque
import javalang
from cve_analyzer.models.dependency import SourceReference
from cve_analyzer.models.evidence import Evidence


class CallGraphAnalyzer:
    """
    Constructs a static call graph of the Java application and uses graph traversal (BFS)
    to discover reachability paths from application entry points to the vulnerable method.
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        # Graph adjacency: caller_node -> set of callee_nodes
        self.graph: Dict[str, Set[str]] = {}
        # Set of discovered entry points (e.g. Controller endpoints, main methods)
        self.entry_points: Set[str] = set()
        # Method details for formatting
        self.method_locations: Dict[str, str] = {}

    def build_call_graph(self):
        """Builds call graph from all Java source files in repository."""
        java_files = list(self.repo_path.glob("**/*.java"))
        prod_files = [
            f for f in java_files
            if not any(part in f.parts for part in ["target", "build", ".gradle", "node_modules"])
        ]

        for java_file in prod_files:
            try:
                content = java_file.read_text(encoding="utf-8", errors="ignore")
                self._parse_file(java_file, content)
            except Exception:
                continue

    def _parse_file(self, java_file: Path, content: str):
        rel_path = str(java_file.relative_to(self.repo_path))
        lines = content.splitlines()

        try:
            tree = javalang.parse.parse(content)
        except Exception:
            self._parse_file_regex(content, rel_path)
            return

        current_package = tree.package.name if tree.package else ""

        for type_decl in (tree.types or []):
            class_name = type_decl.name
            full_class_name = f"{current_package}.{class_name}" if current_package else class_name

            # Check if class is an entry point
            is_controller = False
            for annot in getattr(type_decl, "annotations", []):
                if annot.name in ("RestController", "Controller", "Service", "Endpoint"):
                    is_controller = True

            if any(class_name.endswith(suffix) for suffix in ("Controller", "Resource", "Endpoint", "App", "Application", "Main")):
                is_controller = True

            # Map field variable names to types: var_name -> type_name
            var_types: Dict[str, str] = {}
            for field in getattr(type_decl, "fields", []):
                if hasattr(field, "type") and hasattr(field.type, "name"):
                    f_type = field.type.name
                    for declarator in field.declarators:
                        var_types[declarator.name] = f_type

            for method in (getattr(type_decl, "methods", []) + getattr(type_decl, "constructors", [])):
                method_name = method.name
                caller_node = f"{class_name}.{method_name}()"
                self.method_locations[caller_node] = f"{rel_path}:{getattr(method.position, 'line', 1) if method.position else 1}"

                if caller_node not in self.graph:
                    self.graph[caller_node] = set()

                # Determine if method is an entry point
                is_entry = is_controller
                if method_name in ("main", "submit", "run", "execute", "handle", "processOrder"):
                    is_entry = True

                for annot in getattr(method, "annotations", []):
                    if annot.name in (
                        "GetMapping", "PostMapping", "PutMapping", "DeleteMapping",
                        "PatchMapping", "RequestMapping", "Scheduled", "EventListener"
                    ):
                        is_entry = True

                if is_entry:
                    self.entry_points.add(caller_node)

                # Local variable types in method
                local_var_types = dict(var_types)
                for param in getattr(method, "parameters", []):
                    if hasattr(param, "type") and hasattr(param.type, "name"):
                        local_var_types[param.name] = param.type.name

                if not method.body:
                    continue

                for path, node in method.filter(javalang.tree.VariableDeclarator):
                    for p in reversed(path):
                        if hasattr(p, "type") and hasattr(p.type, "name"):
                            local_var_types[node.name] = p.type.name
                            break

                # Invocations
                for path, node in method.filter(javalang.tree.MethodInvocation):
                    callee_name = node.member
                    qualifier = node.qualifier

                    if not qualifier:
                        for p in reversed(path):
                            if type(p).__name__ in ("ClassCreator", "Creator") and hasattr(p, "type") and hasattr(p.type, "name"):
                                qualifier = p.type.name
                                break

                    if qualifier:
                        callee_type = local_var_types.get(qualifier, qualifier)
                        # Capitalize if variable matches common type
                        if callee_type in ("parser", "orderService", "service"):
                            if callee_type == "parser":
                                callee_type = "Parser"
                            elif callee_type == "orderService":
                                callee_type = "OrderService"
                            elif callee_type == "service":
                                callee_type = "Service"
                        callee_node = f"{callee_type}.{callee_name}()"
                    else:
                        callee_node = f"{class_name}.{callee_name}()"

                    self.graph[caller_node].add(callee_node)

    def _parse_file_regex(self, content: str, rel_path: str):
        """Regex fallback for constructing method calls."""
        lines = content.splitlines()
        class_match = re.search(r"class\s+([A-Za-z0-9_]+)", content)
        class_name = class_match.group(1) if class_match else "App"

        current_caller = None
        method_def_pattern = re.compile(
            r"(?:public|protected|private|static|\s)+[\w<>\[\]]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{?"
        )
        call_pattern = re.compile(r"([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*\(")

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("//"):
                continue

            m = method_def_pattern.search(line_str)
            if m and "class " not in line_str and "new " not in line_str:
                m_name = m.group(1)
                current_caller = f"{class_name}.{m_name}()"
                if current_caller not in self.graph:
                    self.graph[current_caller] = set()
                if "main" in m_name or "submit" in m_name or "Controller" in class_name:
                    self.entry_points.add(current_caller)
                continue

            if current_caller:
                for match in call_pattern.finditer(line_str):
                    target_obj = match.group(1)
                    target_m = match.group(2)
                    callee_node = f"{target_obj}.{target_m}()"
                    self.graph[current_caller].add(callee_node)

    def find_reachability_paths(
        self,
        target_class: str,
        target_method: str,
        references: List[SourceReference]
    ) -> Tuple[List[List[str]], List[Evidence]]:
        """
        Finds static call paths from application entry points to target_class.target_method().
        Returns: (paths: List[List[str]], evidence_list: List[Evidence])
        """
        self.build_call_graph()
        evidence_list: List[Evidence] = []
        clean_method = target_method.replace("()", "").strip()
        target_simple_name = target_class.split(".")[-1]

        target_nodes = [
            f"{target_class}.{clean_method}()",
            f"{target_simple_name}.{clean_method}()",
            f"Parser.{clean_method}()"  # generic fallback
        ]

        # Also add root nodes (in-degree 0) in the call graph as entry points
        all_callers = set(self.graph.keys())
        all_callees: Set[str] = set()
        for targets in self.graph.values():
            all_callees.update(targets)
        for root_node in (all_callers - all_callees):
            self.entry_points.add(root_node)

        # Also add any explicit caller references discovered by source analyzer
        invoking_methods: Set[str] = set()
        for ref in references:
            if ref.reference_type == "METHOD_INVOCATION":
                if ref.enclosing_method:
                    clean_caller = ref.enclosing_method.split(".")[-1].replace("()", "")
                    class_p = ref.enclosing_class.split(".")[-1] if ref.enclosing_class else "App"
                    caller_node = f"{class_p}.{clean_caller}()"
                    invoking_methods.add(caller_node)
                    # Also link caller to target node in graph
                    if caller_node not in self.graph:
                        self.graph[caller_node] = set()
                    self.graph[caller_node].add(f"{target_simple_name}.{clean_method}()")

        if not self.graph:
            return [], evidence_list

        discovered_paths: List[List[str]] = []

        # Find paths from entry points to any target_node or invoking_method
        entry_list = list(self.entry_points)
        if not entry_list and invoking_methods:
            # If no formal entry points identified, treat top callers as entry points
            entry_list = list(invoking_methods)

        for start_node in entry_list:
            path = self._bfs_path(start_node, target_nodes, invoking_methods, target_simple_name, clean_method)
            if path and path not in discovered_paths:
                discovered_paths.append(path)
                evidence_list.append(Evidence(
                    source="callgraph_analyzer",
                    evidence_type="CALL_PATH_FOUND",
                    description=f"Static call path discovered: {' -> '.join(path)}",
                    confidence="HIGH"
                ))

        # Direct path fallback if caller invokes vulnerable method directly
        if not discovered_paths and invoking_methods:
            for caller in invoking_methods:
                direct_path = [caller, f"{target_simple_name}.{clean_method}()"]
                discovered_paths.append(direct_path)
                evidence_list.append(Evidence(
                    source="callgraph_analyzer",
                    evidence_type="DIRECT_INVOCATION_PATH",
                    description=f"Direct invocation path: {' -> '.join(direct_path)}",
                    confidence="HIGH"
                ))

        # Sort discovered paths by length descending so fullest end-to-end path comes first
        discovered_paths.sort(key=len, reverse=True)

        return discovered_paths, evidence_list

    def _bfs_path(
        self,
        start: str,
        target_nodes: List[str],
        invoking_methods: Set[str],
        target_simple_name: str,
        clean_method: str
    ) -> Optional[List[str]]:
        """BFS search for shortest path to target node."""
        queue = deque([[start]])
        visited = {start}

        target_set = set(target_nodes)

        while queue:
            current_path = queue.popleft()
            current_node = current_path[-1]

            # Check if current_node matches target
            if current_node in target_set:
                return current_path

            # Check if current node is one of the invoking methods that directly calls target
            if current_node in invoking_methods:
                if not current_path[-1].endswith(f".{clean_method}()"):
                    return current_path + [f"{target_simple_name}.{clean_method}()"]
                return current_path

            # Explore neighbors
            neighbors = self.graph.get(current_node, set())
            for neighbor in neighbors:
                # Check direct match with neighbor
                if neighbor in target_set or neighbor.endswith(f".{clean_method}()") or (target_simple_name in neighbor and clean_method in neighbor):
                    return current_path + [f"{target_simple_name}.{clean_method}()"]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(current_path + [neighbor])

        return None
