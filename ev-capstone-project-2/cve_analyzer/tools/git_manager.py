import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse
from cve_analyzer.config import DEFAULT_CLONE_DIR
from cve_analyzer.models.evidence import Evidence


class GitManager:
    """
    Manages GitHub repository operations: cloning public & private repos with PAT,
    validating local paths, and caching clones.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or DEFAULT_CLONE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_git_url(repo_target: str) -> bool:
        """Check if target string looks like a Git URL."""
        if not repo_target:
            return False
        clean = repo_target.strip().lower()
        return (
            clean.startswith("http://")
            or clean.startswith("https://")
            or clean.startswith("git@")
            or clean.endswith(".git")
            or "github.com" in clean
        )

    def prepare_repository(
        self,
        repo_target: str,
        github_token: Optional[str] = None
    ) -> Tuple[str, Evidence]:
        """
        Prepares a repository for analysis:
        - If repo_target is an existing local directory, returns it directly.
        - If repo_target is a GitHub URL, clones it to a managed local directory.
        """
        target_path = Path(repo_target)
        if target_path.exists() and target_path.is_dir():
            evidence = Evidence(
                source="git_manager",
                evidence_type="LOCAL_REPO_VALIDATED",
                description=f"Using local repository directory at {target_path}",
                file=str(target_path),
                confidence="HIGH"
            )
            return str(target_path.resolve()), evidence

        if not self.is_git_url(repo_target):
            raise ValueError(f"Target '{repo_target}' is neither a local directory nor a valid Git URL.")

        # Clone repository
        clone_url = repo_target.strip()
        auth_clone_url = clone_url
        sanitized_url = clone_url

        if github_token:
            parsed = urlparse(clone_url)
            if parsed.scheme in ("http", "https"):
                # Embed token safely for git clone command
                auth_clone_url = f"{parsed.scheme}://x-access-token:{github_token}@{parsed.netloc}{parsed.path}"
                sanitized_url = f"{parsed.scheme}://x-access-token:***@{parsed.netloc}{parsed.path}"

        # Extract repo name for directory naming
        repo_name = (
            Path(urlparse(clone_url).path).stem.replace(".git", "")
            or "repo"
        )
        dest_dir = tempfile.mkdtemp(prefix=f"cve_reach_{repo_name}_", dir=str(self.base_dir))

        cmd = ["git", "clone", "--depth", "1", auth_clone_url, dest_dir]
        sanitized_cmd = ["git", "clone", "--depth", "1", sanitized_url, dest_dir]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                # Cleanup on failure
                shutil.rmtree(dest_dir, ignore_errors=True)
                raise RuntimeError(
                    f"Failed to clone repository: {result.stderr.strip() or result.stdout.strip()}"
                )

            evidence = Evidence(
                source="git_manager",
                evidence_type="GIT_CLONED",
                description=f"Successfully cloned repository {sanitized_url} into local workspace",
                file=dest_dir,
                command=" ".join(sanitized_cmd),
                confidence="HIGH"
            )
            return dest_dir, evidence

        except Exception as e:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise RuntimeError(f"Error while cloning {sanitized_url}: {e}")

    @staticmethod
    def cleanup_clone(clone_path: str):
        """Clean up cloned repository if it is in the temporary directory."""
        p = Path(clone_path)
        if p.exists() and "cve_reach_" in p.name:
            shutil.rmtree(p, ignore_errors=True)
