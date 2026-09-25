# AI-Orchestrated Java CVE Reachability Analyzer

An enterprise-grade Software Composition Analysis (SCA) and reachability assessment engine built with **LangChain**, **LangGraph**, and **Deterministic Java Static Analysis**.

---

## 1. Overview & Problem Definition

Standard SCA tools detect when a vulnerable third-party artifact (CVE) is present in an application's dependency graph. However, direct or transitive dependency presence does **not** imply that the vulnerable functionality is executed or reachable by the application.

This analyzer combines:
- **AI Orchestration & Reasoning (LangChain + LangGraph + OpenAI/Qwen)**: Interprets CVE vulnerability reports, structures ambiguous inputs, orchestrates multi-step workflows, manages human-in-the-loop interventions, and synthesizes evidence.
- **Deterministic Verification Tools (`mvn`, `gradle`, `jar`, `javap`, AST analysis)**: Establishes hard technical facts regarding dependency trees, JAR bytecode symbol existence, AST references, and static call paths.

---

## 2. Core Architectural Principle

```
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

### Controlled Assessment Statuses
The analyzer enforces controlled final states:
- `NOT_PRESENT`: Vulnerable artifact/version is not in the resolved dependency tree.
- `SYMBOL_NOT_FOUND`: Affected class or method could not be verified in the JAR.
- `STATICALLY_REACHABLE`: A supported static call path was proven from an entry point.
- `NO_STATIC_PATH_FOUND`: Dependency and symbols are present, but no application reference or supported static call path was found.
  > **Note**: `NO_STATIC_PATH_FOUND` does not prove runtime safety.
- `INSUFFICIENT_EVIDENCE`: Required bytecode, JAR, or repository files were inaccessible.
- `HUMAN_REVIEW`: Ambiguous symbols, multiple candidates, or conflict requires expert review.

---

## 3. Workflow Graph (LangGraph)

```
START 
  ↓
prepare_repository (Clones GitHub repo with optional PAT or loads local path)
  ↓
repository_validator (Checks directory and Java source tree)
  ↓
build_system_detector (Identifies Maven or Gradle)
  ↓
vulnerability_analyzer (Interprets CVE description & symbols)
  ↓ (If ambiguous: human_review interrupt)
dependency_analyzer (Resolves dependency tree, identifies direct vs transitive)
  ↓ (If absent: early exit to evidence_aggregator with NOT_PRESENT)
symbol_verifier (Inspects JAR / bytecode with jar and javap)
  ↓ (If missing: early exit with SYMBOL_NOT_FOUND)
source_analyzer (Scans Java AST for imports, instantiations, invocations)
  ↓ (If no references: early exit with NO_STATIC_PATH_FOUND)
reachability_analyzer (Constructs call graph and finds static path via BFS)
  ↓
evidence_aggregator (Aggregates facts into immutable evidence ledger)
  ↓
report_generator (Produces standardized evidence-based final report)
  ↓
END
```

---

## 4. Installation & Setup

### Prerequisites
- Python 3.10+
- JDK 17+ (`java`, `javac`, `jar`, `javap`)
- Maven 3.x (`mvn`) or Gradle wrapper (`gradlew`)
- Git

### Quickstart
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

### Configuration (`.env`)
Create a `.env` file (see `.env.example`):
```dotenv
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4o-mini
GITHUB_TOKEN=your_pat_for_private_repos  # Optional
```

---

## 5. Usage (Interactive Prompt)

Simply launch the application:
```bash
python3 -m cve_analyzer.cli
```

The application will prompt you for:
1. **Repository URL**: A remote GitHub repository (e.g. `https://github.com/owner/repo.git`) or a local directory path.
2. **Personal Access Token**: Enter your GitHub PAT for private repositories, or press **Enter** (leave blank) for public repositories.

```text
╭──────────────────────────────────────────────────────────────────────────────╮
│ AI-Orchestrated Java CVE Reachability Analyzer                               │
│ Enter your repository details below. All dependencies (including transitive) │
│ will be resolved and evaluated for vulnerability reachability.               │
╰──────────────────────────────────────────────────────────────────────────────╯
1. Enter Repository URL (GitHub URL or local path): https://github.com/my-org/my-app.git
2. Enter Personal Access Token (or press Enter if public): [hidden or entered]
```

### Automated Process:
1. **Clones Repository**: Authenticates and shallow-clones the repo using your PAT if private.
2. **Build System Detection**: Identifies Maven (`pom.xml`) or Gradle (`build.gradle`).
3. **Recursive Dependency Resolution**: Computes the complete direct and transitive dependency graph.
4. **Vulnerability Discovery**: Recursively scans all resolved dependencies for known CVEs via OSV and curated databases.
5. **LangGraph Reachability Analysis**: Verifies symbols in JARs, scans Java AST, and traverses static call graphs from application entry points.
6. **Summary & Reports**: Prints a summary table followed by detailed evidence-based reports matching Section 26.

### Interactive Human-in-the-Loop Review
When the CVE description is ambiguous (e.g. multiple candidate classes), LangGraph pauses at the `human_review` node and prompts the user to select the correct symbol before resuming.

---

## 6. Standardized Report Output (Section 26)

```
=========================================================
JAVA CVE REACHABILITY ANALYSIS
=========================================================
CVE: CVE-XXXX-YYYY
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

## 7. Evaluation & Test Suite (10 Scenarios from Section 28)

Run all unit and integration tests:
```bash
pytest tests/ -v
```

All 10 scenarios outlined in Section 28 of the specification are covered and verified:

| # | Test Scenario | Expected Result | Status |
|---|---|---|---|
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
