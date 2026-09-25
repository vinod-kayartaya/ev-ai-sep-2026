from typing import Dict, Any, List, Optional
from cve_analyzer.models.report import AnalysisReport, AssessmentStatus, ConfidenceLevel
from cve_analyzer.models.dependency import SourceReference
from cve_analyzer.models.evidence import Evidence


class ReportGenerator:
    """
    Generates human-readable evidence-based reports matching Section 26
    of the AI-Orchestrated Java CVE Reachability Analyzer specification.
    """

    @staticmethod
    def generate_text_report(report: AnalysisReport) -> str:
        sep_double = "=" * 57
        sep_single = "-" * 57

        lines = [
            sep_double,
            "JAVA CVE REACHABILITY ANALYSIS",
            sep_double,
            f"CVE: {report.cve_id}",
            f"Affected Artifact: {report.affected_artifact}",
            f"Detected Version: {report.detected_version or 'NOT FOUND'}",
            f"Dependency Type: {report.dependency_type or 'NOT_PRESENT'}",
        ]

        if report.dependency_path:
            lines.append("Dependency Path:")
            if len(report.dependency_path) == 1:
                lines.append(f"  {report.dependency_path[0]}")
            else:
                lines.append(f"  {report.dependency_path[0]}")
                for step in report.dependency_path[1:]:
                    lines.append(f"  -> {step}")

        lines.extend([
            sep_single,
            "AFFECTED SYMBOL",
            sep_single,
            f"Class: {report.affected_class or 'N/A'}",
            f"Method: {report.affected_method or 'N/A'}",
            f"Class Present: {'YES' if report.class_present else ('NO' if report.class_present is False else 'UNKNOWN')}",
            f"Method Present: {'YES' if report.method_present else ('NO' if report.method_present is False else 'UNKNOWN')}",
        ])

        lines.extend([
            sep_single,
            "APPLICATION USAGE",
            sep_single,
        ])

        if report.application_references:
            # Show first key reference
            primary_ref = report.application_references[0]
            lines.append(f"Reference: {primary_ref.file}:{primary_ref.line}")
            inv = primary_ref.code_snippet or f"{report.affected_class}.{report.affected_method}()"
            lines.append(f"Invocation: {inv.strip()}")
            if len(report.application_references) > 1:
                lines.append(f"Total References: {len(report.application_references)}")
        else:
            lines.append("Application Reference: NOT FOUND")

        lines.extend([
            sep_single,
            "STATIC CALL PATH",
            sep_single,
        ])

        if report.static_call_paths:
            path = report.static_call_paths[0]
            for idx, node in enumerate(path):
                lines.append(node)
                if idx < len(path) - 1:
                    lines.append("    |")
                    lines.append("    v")
        else:
            lines.append("NO STATIC PATH DISCOVERED")

        lines.extend([
            sep_single,
            "ASSESSMENT",
            sep_single,
            str(report.assessment.value if hasattr(report.assessment, 'value') else report.assessment),
            f"Confidence: {report.confidence.value if hasattr(report.confidence, 'value') else report.confidence}",
            sep_single,
            "IMPORTANT LIMITATION",
            sep_single,
        ])

        if report.assessment == AssessmentStatus.STATICALLY_REACHABLE:
            lines.extend([
                "Static reachability does not establish runtime",
                "exploitability. The analysis establishes that a",
                "supported static path to the affected functionality",
                "was identified."
            ])
        elif report.assessment == AssessmentStatus.NO_STATIC_PATH_FOUND:
            lines.extend([
                "The absence of a statically discovered path does not",
                "constitute proof of safety. Dynamic invocations, reflection,",
                "or runtime dependency injection might still reach the code."
            ])
        else:
            lines.extend([
                "Analysis concluded with status: " + str(report.assessment),
                "Review evidence log for specific factual findings."
            ])

        lines.append(sep_double)
        return "\n".join(lines)

    @staticmethod
    def build_report_from_state(state: Dict[str, Any]) -> AnalysisReport:
        """Constructs an AnalysisReport object from the LangGraph state."""
        vuln = state.get("vulnerability") or {}
        aff_artifact = vuln.get("artifact", "unknown")
        cve_id = state.get("cve_id", "CVE-UNKNOWN")

        v_dep = state.get("vulnerable_dependency") or {}
        det_version = v_dep.get("version")
        dep_type = None
        if v_dep:
            dep_type = "DIRECT" if v_dep.get("direct") else "TRANSITIVE"
        elif state.get("assessment") == AssessmentStatus.NOT_PRESENT.value:
            dep_type = "NOT_PRESENT"

        dep_path = []
        if state.get("dependency_paths"):
            dep_path = state.get("dependency_paths")[0]
        elif v_dep.get("dependency_path"):
            dep_path = v_dep.get("dependency_path")

        aff_classes = state.get("affected_classes") or vuln.get("affected_classes", [])
        aff_class = aff_classes[0] if aff_classes else None

        aff_methods = state.get("affected_methods") or vuln.get("affected_methods", [])
        aff_method = aff_methods[0] if aff_methods else None
        if aff_method and not aff_method.endswith("()"):
            aff_method = f"{aff_method}()"

        # JAR evidence inspection
        class_present = None
        method_present = None
        for ev in state.get("jar_evidence", []):
            etype = ev.get("evidence_type")
            if etype == "CLASS_EXISTS":
                class_present = True
            elif etype == "CLASS_NOT_FOUND":
                class_present = False
            elif etype == "METHOD_EXISTS":
                method_present = True
            elif etype == "METHOD_NOT_FOUND":
                method_present = False

        # References
        refs_raw = state.get("references", [])
        refs: List[SourceReference] = []
        for r in refs_raw:
            if isinstance(r, SourceReference):
                refs.append(r)
            elif isinstance(r, dict):
                refs.append(SourceReference(**r))

        call_paths = state.get("call_paths", [])

        # Assessment
        assessment_str = state.get("assessment", AssessmentStatus.INSUFFICIENT_EVIDENCE.value)
        try:
            assessment = AssessmentStatus(assessment_str)
        except Exception:
            assessment = AssessmentStatus.INSUFFICIENT_EVIDENCE

        confidence_str = state.get("confidence", ConfidenceLevel.HIGH.value)
        try:
            confidence = ConfidenceLevel(confidence_str)
        except Exception:
            confidence = ConfidenceLevel.HIGH

        # Evidence
        evidence_list: List[Evidence] = []
        for ev in state.get("evidence", []):
            if isinstance(ev, Evidence):
                evidence_list.append(ev)
            elif isinstance(ev, dict):
                evidence_list.append(Evidence(**ev))

        report = AnalysisReport(
            cve_id=cve_id,
            affected_artifact=aff_artifact,
            detected_version=det_version,
            dependency_type=dep_type,
            dependency_path=dep_path,
            affected_class=aff_class,
            affected_method=aff_method,
            class_present=class_present,
            method_present=method_present,
            application_references=refs,
            static_call_paths=call_paths,
            assessment=assessment,
            confidence=confidence,
            evidence_list=evidence_list
        )
        report.raw_report = ReportGenerator.generate_text_report(report)
        return report
