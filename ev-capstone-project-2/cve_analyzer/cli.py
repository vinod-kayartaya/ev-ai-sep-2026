import os
import sys
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from cve_analyzer.agent.graph import build_cve_analysis_graph
from cve_analyzer.models.state import CVEAnalysisState
from cve_analyzer.models.vulnerability import VulnerabilityInfo
from cve_analyzer.models.dependency import DependencyInfo
from cve_analyzer.models.report import AssessmentStatus, AnalysisReport
from cve_analyzer.tools.git_manager import GitManager
from cve_analyzer.tools.repo_analyzer import RepositoryAnalyzer
from cve_analyzer.tools.dependency_analyzer import DependencyAnalyzer
from cve_analyzer.tools.vulnerability_scanner import VulnerabilityScanner
from cve_analyzer.report_generator import ReportGenerator

console = Console()


def prompt_user_inputs() -> tuple[str, Optional[str]]:
    """
    Asks the user interactively for:
    1. Repository URL
    2. Personal Access Token (or blank for public repository)
    """
    console.print(Panel(
        "[bold cyan]AI-Orchestrated Java CVE Reachability Analyzer[/bold cyan]\n"
        "[dim]Enter your repository details below. All dependencies (including transitive)\n"
        "will be resolved and evaluated for vulnerability reachability.[/dim]",
        border_style="cyan"
    ))

    try:
        repo_url = console.input("[bold green]1. Enter Repository URL (GitHub URL or local path): [/bold green]").strip()
        while not repo_url:
            console.print("[red]Repository URL cannot be empty.[/red]")
            repo_url = console.input("[bold green]1. Enter Repository URL (GitHub URL or local path): [/bold green]").strip()

        token_input = console.input("[bold green]2. Enter Personal Access Token (or press Enter if public): [/bold green]").strip()
        token = token_input if token_input else None

        return repo_url, token
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)


def scan_and_analyze_repository(
    repo_url: str,
    github_token: Optional[str] = None
) -> List[AnalysisReport]:
    """
    End-to-end repository reachability analysis:
    1. Clones/validates the repository with PAT if provided
    2. Identifies build system (Maven / Gradle)
    3. Resolves all dependencies (direct and transitive) recursively
    4. Automatically scans all dependencies for known vulnerabilities (OSV + offline database)
    5. Runs the LangGraph reachability workflow for each discovered vulnerability
    6. Produces rich executive summaries and individual evidence-based reports
    """
    console.print(f"\n[bold blue]Step 1: Preparing repository...[/bold blue]")
    git_mgr = GitManager()
    local_path, clone_ev = git_mgr.prepare_repository(repo_url, github_token)
    console.print(f"  [green]✓[/green] Repository ready at: [dim]{local_path}[/dim]")

    console.print(f"\n[bold blue]Step 2: Detecting build system and source layout...[/bold blue]")
    repo_info, _ = RepositoryAnalyzer.analyze(local_path)
    build_sys = repo_info["build_system"]
    src_dir = repo_info["source_directory"]
    console.print(f"  [green]✓[/green] Build system: [bold]{build_sys}[/bold]")
    console.print(f"  [green]✓[/green] Source directory: [dim]{src_dir}[/dim] (Java files: {repo_info['java_files_count']})")

    console.print(f"\n[bold blue]Step 3: Resolving dependencies recursively (direct and transitive)...[/bold blue]")
    dep_analyzer = DependencyAnalyzer()
    dependencies, dep_ev, dep_err = dep_analyzer.resolve(local_path, build_sys)

    if dep_err:
        console.print(f"  [yellow]Notice during dependency resolution: {dep_err}[/yellow]")

    direct_count = sum(1 for d in dependencies if d.direct)
    transitive_count = sum(1 for d in dependencies if not d.direct)
    console.print(f"  [green]✓[/green] Resolved [bold]{len(dependencies)}[/bold] total dependencies "
                  f"([bold]{direct_count}[/bold] direct, [bold]{transitive_count}[/bold] transitive)")

    console.print(f"\n[bold blue]Step 4: Scanning all dependencies for vulnerabilities...[/bold blue]")
    vuln_scanner = VulnerabilityScanner()
    discovered_vulns = vuln_scanner.scan_dependencies(dependencies)

    if not discovered_vulns:
        console.print("[bold green]✓ No known vulnerabilities detected in any direct or transitive dependencies.[/bold green]")
        return []

    console.print(f"  [bold red]![/bold red] Found [bold red]{len(discovered_vulns)}[/bold red] potential vulnerability match(es):")
    for v in discovered_vulns:
        console.print(f"    - [yellow]{v.cve_id}[/yellow] in [bold]{v.artifact}[/bold] (classes: {v.affected_classes or 'N/A'}, methods: {v.affected_methods or 'N/A'})")

    console.print(f"\n[bold blue]Step 5: Executing AI-orchestrated LangGraph reachability analysis for each vulnerability...[/bold blue]")
    graph = build_cve_analysis_graph(checkpointer=True)
    reports: List[AnalysisReport] = []

    for idx, vuln in enumerate(discovered_vulns, 1):
        console.print(f"\n[cyan]Analyzing [{idx}/{len(discovered_vulns)}]: {vuln.cve_id} on {vuln.artifact}...[/cyan]")

        initial_state: CVEAnalysisState = {
            "repository_path": local_path,
            "repo_url": repo_url if (repo_url.startswith("http") or repo_url.startswith("git@")) else None,
            "github_token": github_token,
            "cve_id": vuln.cve_id,
            "cve_raw_text": vuln.description or f"Vulnerability {vuln.cve_id} in {vuln.artifact}",
            "vulnerability": vuln.model_dump(),
            "build_system": build_sys,
            "source_directory": src_dir,
            "dependencies": [d.model_dump() for d in dependencies],
            "dependency_paths": [],
            "affected_classes": vuln.affected_classes,
            "affected_methods": vuln.affected_methods,
            "jar_evidence": [],
            "source_evidence": [],
            "bytecode_evidence": [],
            "references": [],
            "call_paths": [],
            "evidence": [],
            "errors": [],
            "retry_count": 0,
            "repository_valid": True,
        }

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        for event in graph.stream(initial_state, config=config):
            pass  # Execute graph nodes

        final_state = graph.get_state(config).values
        report = ReportGenerator.build_report_from_state(final_state)
        reports.append(report)

    # Step 6: Render Summary Table
    table = Table(
        title="Java CVE Reachability Analysis - Summary",
        box=box.ROUNDED,
        header_style="bold cyan"
    )
    table.add_column("CVE ID", style="bold yellow")
    table.add_column("Affected Artifact", style="white")
    table.add_column("Version", style="dim")
    table.add_column("Dep Type", style="magenta")
    table.add_column("Reachability Assessment", style="bold")
    table.add_column("Confidence", style="cyan")

    for rep in reports:
        status_color = "red" if rep.assessment == AssessmentStatus.STATICALLY_REACHABLE else (
            "green" if rep.assessment in (AssessmentStatus.NOT_PRESENT, AssessmentStatus.NO_STATIC_PATH_FOUND) else "yellow"
        )
        table.add_row(
            rep.cve_id,
            rep.affected_artifact,
            rep.detected_version or "N/A",
            rep.dependency_type or "N/A",
            f"[{status_color}]{rep.assessment.value}[/{status_color}]",
            rep.confidence.value
        )

    console.print("\n")
    console.print(table)

    # Step 7: Render Individual Evidence-Based Reports
    console.print("\n[bold]Detailed Evidence-Based Reports:[/bold]")
    for rep in reports:
        console.print(rep.raw_report)
        console.print("\n")

    return reports


def main():
    """
    Entrypoint: prompts user directly for Repository URL and PAT.
    """
    # If arguments are passed on command line, use them, otherwise prompt interactively
    if len(sys.argv) > 1 and sys.argv[1].startswith("--repo"):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--repo", required=True)
        parser.add_argument("--token", default=None)
        args, _ = parser.parse_known_args()
        repo_url = args.repo
        token = args.token
    else:
        repo_url, token = prompt_user_inputs()

    scan_and_analyze_repository(repo_url, token)


if __name__ == "__main__":
    main()
