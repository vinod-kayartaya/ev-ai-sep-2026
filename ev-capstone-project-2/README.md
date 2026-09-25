# AI-Orchestrated Java CVE Reachability Analyzer

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Java 17](https://img.shields.io/badge/java-17+-orange.svg)](https://www.oracle.com/java/)
[![LangGraph](https://img.shields.io/badge/orchestrator-LangGraph-purple.svg)](https://github.com/langchain-ai/langgraph)
[![LangChain](https://img.shields.io/badge/framework-LangChain-green.svg)](https://github.com/langchain-ai/langchain)
[![Tests Passing](https://img.shields.io/badge/tests-18%20passed-brightgreen.svg)]()

An enterprise-grade Software Composition Analysis (SCA) and reachability assessment engine built with **LangChain**, **LangGraph**, and **Deterministic Java Static Analysis**.

---

## 1. Overview & Problem Definition

Modern Java enterprise applications rely on dozens of direct and hundreds of transitive third-party libraries. When a CVE is disclosed against a library, conventional Software Composition Analysis (SCA) scanners flag alerts simply based on package presence in `pom.xml` or `build.gradle`.

However, **presence does not equal exploitability or reachability**. In most real-world codebases:
- The vulnerable class may never be imported or instantiated.
- The vulnerable method is never invoked.
- No execution path exists from any application entry point (e.g. REST Controller, HTTP endpoint, or `main()` method) to the vulnerable code.

```text
Java Application
       |
       +-- Framework A (Direct)
              |
              +-- Library B (Transitive)
                     |
                     +-- Vulnerable Library 1.2.3 (Transitive)
```

The **AI-Orchestrated Java CVE Reachability Analyzer** solves this by establishing whether functionality associated with the vulnerability is **statically reachable** from the application, producing an auditable, evidence-backed report.

---

## 2. Core Architectural Principle

The system enforces a strict separation between **AI reasoning/orchestration** and **deterministic verification of technical facts**:

```text
                LLM / LangGraph
                       |          Reasoning + Orchestration
                       v
              Deterministic Tools
                       |          Verification of Technical Facts
                       v
                    Evidence
                       |
                       v
               Assessment + Report
```

- **LLM / LangGraph**: Orchestrates the multi-stage workflow, interprets unstructured CVE advisories, identifies potential candidate symbols, handles ambiguity through human-in-the-loop interactions, and correlates evidence into explainable security reports.
- **Deterministic Tools**: Authoritative sources for ground truth facts:
  - Repository Analyzer $\rightarrow$ Build system (`pom.xml`, `build.gradle`)
  - Maven / Gradle Analyzer $\rightarrow$ Complete recursive dependency trees & transitive paths
  - JAR Analyzer (`jar`, `javap`) $\rightarrow$ Physical existence of classes and methods in bytecode
  - Java AST Analyzer (`javalang`) $\rightarrow$ Real source references, instantiations, and method invocations
  - Call Graph Analyzer $\rightarrow$ Graph traversal (BFS) from application entry points to the vulnerable invocation

---

## 3. Controlled Reachability Statuses

The assessment engine produces strictly controlled states to prevent misleading security claims:

| Status | Meaning & Criteria |
|---|---|
| **`STATICALLY_REACHABLE`** | A verified static call path exists from an application entry point to the vulnerable method. |
| **`NO_STATIC_PATH_FOUND`** | Dependency and symbols are present, but no application reference or supported static call path was identified. *(Note: Does not constitute proof of runtime safety).* |
| **`NOT_PRESENT`** | The vulnerable artifact or affected version is not present in the resolved dependency tree. |
| **`SYMBOL_NOT_FOUND`** | The affected class or method could not be found in the dependency JAR bytecode. |
| **`INSUFFICIENT_EVIDENCE`** | Available technical evidence was insufficient (e.g. JAR bytecode or source unavailable). |
| **`HUMAN_REVIEW`** | Ambiguity detected (e.g. multiple candidate classes/methods, ambiguous CVE description) requiring engineer intervention. |

---

## 4. End-to-End Workflow (LangGraph)

```text
                         +-----------------------------+
                         |         User Input          |
                         |  (Repo URL + Optional PAT)  |
                         +--------------+--------------+
                                        |
                                        v
                         +-----------------------------+
                         |     prepare_repository      |
                         | (Git clone / Local validate)|
                         +--------------+--------------+
                                        |
                                        v
                         +-----------------------------+
                         |    repository_validator     |
                         |  & build_system_detector    |
                         +--------------+--------------+
                                        |
                                        v
                         +-----------------------------+
                         |     dependency_analyzer     |
                         |   (Direct & Transitive)     |
                         +--------------+--------------+
                                        |
                                        v
                         +-----------------------------+
                         |    vulnerability_scanner    |
                         |    (OSV API + Offline DB)   |
                         +--------------+--------------+
                                        |
                                        v
                         +-----------------------------+
                         |  symbol_verifier (in JAR)   |
                         |     (via jar and javap)     |
                         +--------------+--------------+
                                        |
                       +----------------+----------------+
                       |                                 |
              [Class/Method Found]             [Symbol Absent / Ambiguous]
                       |                                 |
                       v                                 v
         +---------------------------+     +---------------------------+
         |      source_analyzer      |     |     human_review or       |
         |    (Java AST references)  |     |     SYMBOL_NOT_FOUND      |
         +-------------+-------------+     +-------------+-------------+
                       |                                 |
                       v                                 |
         +---------------------------+                   |
         |   reachability_analyzer   |                   |
         |  (Call Graph BFS Traversal|                   |
         +-------------+-------------+                   |
                       |                                 |
                       +----------------+----------------+
                                        |
                                        v
                         +-----------------------------+
                         |     evidence_aggregator     |
                         | (Immutable Evidence Ledger) |
                         +--------------+--------------+
                                        |
                                        v
                         +-----------------------------+
                         |      report_generator       |
                         |  (Summary Table + Reports)  |
                         +-----------------------------+
```

---

## 5. Installation & Prerequisites

### Prerequisites
- **Python**: 3.10 or higher
- **Java Development Kit**: JDK 17+ (`java`, `javac`, `jar`, `javap` accessible in system PATH)
- **Build Tools**: Maven 3.x (`mvn`) or Gradle wrapper (`gradlew`)
- **Version Control**: Git

### Quick Setup

```bash
# 1. Clone or navigate to the project directory
cd /path/to/ev-capstone-project-2

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Configuration (`.env`)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

```dotenv
# LLM Configuration (OpenAI or local OpenAI-compatible endpoint, e.g. Qwen / vLLM / Ollama)
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
OPENAI_API_BASE=

# GitHub Authentication (Optional: can also be entered during interactive prompt)
GITHUB_TOKEN=your_github_pat_for_private_repos

# Observability (Optional: Langfuse / LangSmith)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
LANGCHAIN_TRACING_V2=false
```

---

## 6. How to Run (Interactive Prompt)

The application takes **only two inputs**, requested interactively from the user:
1. **Repository URL**: A public or private GitHub repository URL (or a local directory path).
2. **Personal Access Token**: Enter your GitHub PAT for private repositories, or press **Enter** (leave blank) for public repositories.

Run the application:
```bash
python3 -m cve_analyzer.cli
```

### What Happens Automatically:
1. **Authentication & Clone**: Authenticates using your PAT if private, performs a shallow clone into a sandboxed directory (or uses the local path).
2. **Build System Detection**: Identifies whether the project uses Maven (`pom.xml`) or Gradle (`build.gradle`, `build.gradle.kts`), discovering source directories (`src/main/java`).
3. **Recursive Dependency Resolution**: Executes dependency tree resolution (`mvn dependency:tree` or Gradle dependencies) with resilient XML POM parsing fallbacks.
4. **Automated Vulnerability Discovery**: Scans all resolved direct and transitive dependencies recursively against known CVEs (using live OSV API with an embedded offline database for airgapped/sandboxed environments).
5. **AI Reachability Orchestration**: For every vulnerability found:
   - Inspects the dependency JAR bytecode using `jar` and `javap`.
   - Analyzes application Java source code using AST parsing (`javalang`) to detect imports, object creation (`new Parser()`), field types, and method invocations (`parser.parseUnsafe()`).
   - Builds a static call graph, identifies entry points (e.g. `@RestController`, `@GetMapping`, `@PostMapping`, `main()`, and root entry points), and traverses paths via BFS.
6. **Executive Summary & Evidence-Based Reports**: Prints an executive summary table of all scanned dependencies followed by detailed Section 26 reports.

---

## 7. Example Output

### Interactive Terminal Session
```text
╭──────────────────────────────────────────────────────────────────────────────╮
│ AI-Orchestrated Java CVE Reachability Analyzer                               │
│ Enter your repository details below. All dependencies (including transitive) │
│ will be resolved and evaluated for vulnerability reachability.               │
╰──────────────────────────────────────────────────────────────────────────────╯
1. Enter Repository URL (GitHub URL or local path): https://github.com/my-org/order-service.git
2. Enter Personal Access Token (or press Enter if public): ghp_examplePersonalAccessToken

Step 1: Preparing repository...
  ✓ Repository ready at: /path/to/workspace_clones/cve_reach_order-service_xyz

Step 2: Detecting build system and source layout...
  ✓ Build system: MAVEN
  ✓ Source directory: src/main/java (Java files: 12)

Step 3: Resolving dependencies recursively (direct and transitive)...
  ✓ Resolved 28 total dependencies (6 direct, 22 transitive)

Step 4: Scanning all dependencies for vulnerabilities...
  ! Found 2 potential vulnerability match(es):
    - CVE-2024-TEST in com.vendor:vulnerable-library (classes: ['com.vendor.Parser'], methods: ['parseUnsafe'])
    - CVE-2021-44228 in org.apache.logging.log4j:log4j-core (classes: ['org.apache.logging.log4j.core.lookup.JndiLookup'], methods: ['lookup'])

Step 5: Executing AI-orchestrated LangGraph reachability analysis for each vulnerability...

Analyzing [1/2]: CVE-2024-TEST on com.vendor:vulnerable-library...
Analyzing [2/2]: CVE-2021-44228 on org.apache.logging.log4j:log4j-core...

                    Java CVE Reachability Analysis - Summary                    
╭─────────────┬──────────────────────────┬─────────┬────────────┬──────────────────────┬────────────╮
│ CVE ID      │ Affected Artifact        │ Version │ Dep Type   │ Reachability Assess  │ Confidence │
├─────────────┼──────────────────────────┼─────────┼────────────┼──────────────────────┼────────────┤
│ CVE-2024-T… │ com.vendor:vulnerable-…  │ 1.2.3   │ TRANSITIVE │ STATICALLY_REACHABLE │ HIGH       │
│ CVE-2021-4… │ org.apache.logging.log4… │ 2.14.1  │ DIRECT     │ NO_STATIC_PATH_FOUND │ HIGH       │
╰─────────────┴──────────────────────────┴─────────┴────────────┴──────────────────────┴────────────╯
```

### Standardized Evidence-Based Final Report (Section 26 Format)
```text
=========================================================
JAVA CVE REACHABILITY ANALYSIS
=========================================================
CVE: CVE-2024-TEST
Affected Artifact: com.vendor:vulnerable-library
Detected Version: 1.2.3
Dependency Type: TRANSITIVE
Dependency Path:
  com.example:order-app:1.0.0
  -> com.vendor:framework-a:2.1.0
  -> com.vendor:library-b:1.0.0
  -> com.vendor:vulnerable-library:1.2.3
---------------------------------------------------------
AFFECTED SYMBOL
---------------------------------------------------------
Class: com.vendor.Parser
Method: parseUnsafe()
Class Present: YES
Method Present: YES
---------------------------------------------------------
APPLICATION USAGE
---------------------------------------------------------
Reference: src/main/java/com/example/OrderService.java:3
Invocation: import com.vendor.Parser;
Total References: 3
---------------------------------------------------------
STATIC CALL PATH
---------------------------------------------------------
OrderController.submit()
    |
    v
OrderService.process()
    |
    v
Parser.parseUnsafe()
---------------------------------------------------------
ASSESSMENT
---------------------------------------------------------
STATICALLY_REACHABLE
Confidence: HIGH
---------------------------------------------------------
IMPORTANT LIMITATION
---------------------------------------------------------
Static reachability does not establish runtime
exploitability. The analysis establishes that a
supported static path to the affected functionality
was identified.
=========================================================
```

---

## 8. Comprehensive Test Suite (All 10 Scenarios from Section 28)

Run the full pytest suite:
```bash
pytest tests/ -v
```

All 10 evaluation scenarios specified in Section 28 of the specification are fully tested:

| # | Evaluation Scenario | Expected Assessment | Result |
|---|---|---|:---:|
| 1 | Vulnerable dependency absent | `NOT_PRESENT` | **PASSED** |
| 2 | Vulnerable dependency present but unused | `NO_STATIC_PATH_FOUND` | **PASSED** |
| 3 | Vulnerable class absent in JAR | `SYMBOL_NOT_FOUND` | **PASSED** |
| 4 | Vulnerable method absent in JAR | `SYMBOL_NOT_FOUND` | **PASSED** |
| 5 | Method directly invoked | `STATICALLY_REACHABLE` | **PASSED** |
| 6 | Transitive dependency + reachable method | `STATICALLY_REACHABLE` | **PASSED** |
| 7 | CVE symbol ambiguous | `HUMAN_REVIEW` | **PASSED** |
| 8 | Source / bytecode unavailable | `INSUFFICIENT_EVIDENCE` | **PASSED** |
| 9 | Dependency command fails | Retry / fallback handling | **PASSED** |
| 10 | Multiple possible symbols | `HUMAN_REVIEW` | **PASSED** |

```bash
============================== 18 passed in 7.47s ==============================
```

---

## 9. Project Directory Structure

```text
ev-capstone-project-2/
├── .env.example                    # Template for environment variables
├── .gitignore                      # Git ignore patterns
├── README.md                       # Comprehensive documentation
├── pyproject.toml                  # Project metadata and test configuration
├── requirements.txt                # Python package dependencies
├── cve_analyzer/                   # Core application package
│   ├── __init__.py
│   ├── cli.py                      # Interactive terminal prompt interface
│   ├── config.py                   # Environment & path configuration
│   ├── report_generator.py         # Formats Section 26 reports & summary tables
│   ├── models/                     # Pydantic & TypedDict data models
│   │   ├── dependency.py           # DependencyInfo & SourceReference
│   │   ├── evidence.py             # Immutable Evidence model
│   │   ├── report.py               # AnalysisReport & AssessmentStatus enums
│   │   ├── state.py                # CVEAnalysisState for LangGraph
│   │   └── vulnerability.py        # VulnerabilityInfo model
│   ├── tools/                      # Deterministic Java static analysis tools
│   │   ├── git_manager.py          # GitHub cloning (with PAT) & caching
│   │   ├── repo_analyzer.py        # Maven & Gradle layout detection
│   │   ├── dependency_analyzer.py  # Dependency tree resolver & XML fallback
│   │   ├── jar_analyzer.py         # JAR extraction & javap symbol verification
│   │   ├── source_analyzer.py      # Java AST parser (javalang)
│   │   ├── callgraph_analyzer.py   # Call graph construction & BFS reachability
│   │   └── vulnerability_scanner.py# OSV API + Offline vulnerability database
│   └── agent/                      # LangChain & LangGraph Orchestration
│       ├── graph.py                # LangGraph StateGraph & conditional routing
│       ├── nodes.py                # Workflow node implementations
│       ├── llm.py                  # LLM setup (OpenAI/Qwen) & fallback parser
│       ├── prompts.py              # Prompt templates
│       └── tools.py                # @tool definitions for LangChain
└── tests/                          # Automated test suites
    ├── fixtures_builder.py         # Mock Java repos & real JAR compiler
    ├── test_components.py          # Unit tests for individual analyzers
    ├── test_scenarios.py           # Verification of all 10 spec scenarios
    └── test_vulnerability_scanner.py# Tests for vulnerability scanning & scan pipeline
```

---

## 10. Observability & Tracing

The application natively supports **Langfuse** and **LangSmith** for full execution tracing of LangGraph nodes, LLM calls, tool executions, and routing decisions. 

To enable tracing, populate your keys in `.env`:
```dotenv
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```
When enabled, every graph run logs a trace containing:
- Repository cloning and validation events
- Build system and dependency tree resolution
- JAR bytecode inspection results (`javap` output)
- AST references and static call paths
- State transitions and final evidence aggregation
