import shutil
from pathlib import Path
from cve_analyzer.tools.jar_analyzer import JarAnalyzer


class FixturesBuilder:
    """
    Constructs isolated Java mock repositories and JAR artifacts
    for testing all 10 evaluation scenarios from Section 28.
    """

    @staticmethod
    def ensure_mock_jars(fixtures_dir: Path):
        mock_jars_dir = fixtures_dir / "mock_jars"
        mock_jars_dir.mkdir(parents=True, exist_ok=True)

        # 1. Normal vulnerable library with Parser.parseUnsafe()
        p1 = mock_jars_dir / "vulnerable-library-1.2.3.jar"
        if not p1.exists():
            JarAnalyzer.create_mock_jar(p1, "com.vendor.Parser", ["parseUnsafe", "safeParse"])

        # 2. Library with missing class (only OtherClass)
        p2 = mock_jars_dir / "missing-class-library-1.2.3.jar"
        if not p2.exists():
            JarAnalyzer.create_mock_jar(p2, "com.vendor.OtherClass", ["someMethod"])

        # 3. Library with class present but method missing (only safeParse)
        p3 = mock_jars_dir / "missing-method-library-1.2.3.jar"
        if not p3.exists():
            JarAnalyzer.create_mock_jar(p3, "com.vendor.Parser", ["safeParse", "otherMethod"])

    @staticmethod
    def create_scenario_1_repo(base_path: Path) -> Path:
        """Scenario 1: Vulnerable dependency absent."""
        repo = base_path / "scenario_1_absent"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True, exist_ok=True)

        pom = repo / "pom.xml"
        pom.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>order-service</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>1.7.30</version>
        </dependency>
    </dependencies>
</project>""")
        src = repo / "src/main/java/com/example"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.java").write_text("""package com.example;
public class App {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}""")
        return repo

    @staticmethod
    def create_scenario_2_repo(base_path: Path, mock_jars_dir: Path) -> Path:
        """Scenario 2: Vulnerable dependency present but unused in application."""
        repo = base_path / "scenario_2_unused"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True, exist_ok=True)

        pom = repo / "pom.xml"
        pom.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>order-service</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.vendor</groupId>
            <artifactId>vulnerable-library</artifactId>
            <version>1.2.3</version>
        </dependency>
    </dependencies>
</project>""")
        # Copy jar into repo lib folder
        lib = repo / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        shutil.copy(mock_jars_dir / "vulnerable-library-1.2.3.jar", lib / "vulnerable-library-1.2.3.jar")

        src = repo / "src/main/java/com/example"
        src.mkdir(parents=True, exist_ok=True)
        (src / "OrderService.java").write_text("""package com.example;
public class OrderService {
    public void processOrder() {
        System.out.println("Processing order cleanly without calling vendor library");
    }
}""")
        return repo

    @staticmethod
    def create_scenario_3_repo(base_path: Path, mock_jars_dir: Path) -> Path:
        """Scenario 3: Vulnerable class absent in JAR."""
        repo = base_path / "scenario_3_class_absent"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True, exist_ok=True)

        pom = repo / "pom.xml"
        pom.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>app</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.vendor</groupId>
            <artifactId>missing-class-library</artifactId>
            <version>1.2.3</version>
        </dependency>
    </dependencies>
</project>""")
        lib = repo / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        shutil.copy(mock_jars_dir / "missing-class-library-1.2.3.jar", lib / "missing-class-library-1.2.3.jar")

        src = repo / "src/main/java/com/example"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.java").write_text("package com.example;\npublic class App {}")
        return repo

    @staticmethod
    def create_scenario_4_repo(base_path: Path, mock_jars_dir: Path) -> Path:
        """Scenario 4: Vulnerable method absent in JAR."""
        repo = base_path / "scenario_4_method_absent"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True, exist_ok=True)

        pom = repo / "pom.xml"
        pom.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>app</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.vendor</groupId>
            <artifactId>missing-method-library</artifactId>
            <version>1.2.3</version>
        </dependency>
    </dependencies>
</project>""")
        lib = repo / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        shutil.copy(mock_jars_dir / "missing-method-library-1.2.3.jar", lib / "missing-method-library-1.2.3.jar")

        src = repo / "src/main/java/com/example"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.java").write_text("package com.example;\npublic class App {}")
        return repo

    @staticmethod
    def create_scenario_5_repo(base_path: Path, mock_jars_dir: Path) -> Path:
        """Scenario 5: Method directly invoked."""
        repo = base_path / "scenario_5_direct_invocation"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True, exist_ok=True)

        pom = repo / "pom.xml"
        pom.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>order-service</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.vendor</groupId>
            <artifactId>vulnerable-library</artifactId>
            <version>1.2.3</version>
        </dependency>
    </dependencies>
</project>""")
        lib = repo / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        shutil.copy(mock_jars_dir / "vulnerable-library-1.2.3.jar", lib / "vulnerable-library-1.2.3.jar")

        src = repo / "src/main/java/com/example"
        src.mkdir(parents=True, exist_ok=True)
        (src / "OrderService.java").write_text("""package com.example;

import com.vendor.Parser;

public class OrderService {
    public void processOrder() {
        Parser parser = new Parser();
        parser.parseUnsafe("order-data");
    }
}""")
        return repo

    @staticmethod
    def create_scenario_6_repo(base_path: Path, mock_jars_dir: Path) -> Path:
        """Scenario 6: Transitive dependency + reachable call path from Controller."""
        repo = base_path / "scenario_6_transitive_reachable"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True, exist_ok=True)

        # Pre-computed maven dependency tree representing transitive dependency
        (repo / "dependency-tree.txt").write_text(r"""[INFO] com.example:order-app:jar:1.0.0
[INFO] +- com.vendor:framework-a:jar:2.1.0:compile
[INFO] |  \- com.vendor:library-b:jar:1.0.0:compile
[INFO] |     \- com.vendor:vulnerable-library:jar:1.2.3:compile
[INFO] \- org.slf4j:slf4j-api:jar:1.7.30:compile
""")

        pom = repo / "pom.xml"
        pom.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>order-app</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.vendor</groupId>
            <artifactId>framework-a</artifactId>
            <version>2.1.0</version>
        </dependency>
    </dependencies>
</project>""")
        lib = repo / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        shutil.copy(mock_jars_dir / "vulnerable-library-1.2.3.jar", lib / "vulnerable-library-1.2.3.jar")

        src = repo / "src/main/java/com/example"
        src.mkdir(parents=True, exist_ok=True)

        # OrderController -> OrderService -> Parser.parseUnsafe()
        (src / "OrderController.java").write_text("""package com.example;

public class OrderController {
    private OrderService orderService = new OrderService();

    public void submit() {
        orderService.process();
    }
}""")

        (src / "OrderService.java").write_text("""package com.example;

import com.vendor.Parser;

public class OrderService {
    public void process() {
        Parser parser = new Parser();
        parser.parseUnsafe("order-data");
    }
}""")
        return repo

    @staticmethod
    def create_scenario_8_repo(base_path: Path) -> Path:
        """Scenario 8: Source/bytecode unavailable (JAR missing)."""
        repo = base_path / "scenario_8_bytecode_unavailable"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True, exist_ok=True)

        pom = repo / "pom.xml"
        pom.write_text("""<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>app</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.vendor</groupId>
            <artifactId>unknown-remote-library</artifactId>
            <version>9.9.9</version>
        </dependency>
    </dependencies>
</project>""")
        src = repo / "src/main/java/com/example"
        src.mkdir(parents=True, exist_ok=True)
        (src / "App.java").write_text("package com.example;\npublic class App {}")
        return repo
