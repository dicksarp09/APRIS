import os
import subprocess
import tempfile
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.repository.base import RepositoryProvider, RepoFile, RepoMetadata, CommitInfo


class LocalGitProvider(RepositoryProvider):
    """Repository provider using local git clone.

    This is the default provider that clones repositories locally
    and analyzes them from the filesystem.
    """

    def __init__(
        self,
        repo_url: str,
        base_dir: str = None,
        depth: int = 1,
        max_file_size_kb: int = 200,
    ):
        self.repo_url = repo_url
        self.base_dir = base_dir or os.path.join(
            os.path.expanduser("~"), ".apris", "repos"
        )
        self.depth = depth
        self.max_file_size_kb = max_file_size_kb
        self.repo_path: Optional[str] = None
        self._repo_metadata: Optional[RepoMetadata] = None

    def _ensure_cloned(self) -> bool:
        """Ensure repository is cloned. Returns success status."""
        if self.repo_path and os.path.exists(self.repo_path):
            return True

        try:
            os.makedirs(self.base_dir, exist_ok=True)

            repo_name = self.repo_url.rstrip("/").split("/")[-1]
            import uuid

            unique_id = uuid.uuid4().hex[:8]
            self.repo_path = os.path.join(self.base_dir, f"{repo_name}_{unique_id}")

            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    str(self.depth),
                    self.repo_url,
                    self.repo_path,
                ],
                capture_output=True,
                timeout=180,
            )

            if result.returncode != 0:
                return False

            return True
        except Exception:
            return False

    def list_files(self, path: str = "") -> List[str]:
        if not self._ensure_cloned():
            return []

        search_path = self.repo_path if not path else os.path.join(self.repo_path, path)
        if not os.path.exists(search_path):
            return []

        files = []
        for root, _, filenames in os.walk(search_path):
            for f in filenames:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, self.repo_path)
                if not rel_path.startswith(".git"):
                    files.append(rel_path)

        return sorted(files)

    def get_file(self, path: str) -> Optional[RepoFile]:
        if not self._ensure_cloned():
            return None

        full_path = os.path.join(self.repo_path, path)
        if not os.path.exists(full_path):
            return None

        try:
            stat = os.stat(full_path)
            size_kb = stat.st_size // 1024

            if size_kb > self.max_file_size_kb:
                return RepoFile(
                    path=path,
                    name=os.path.basename(path),
                    size=stat.st_size,
                    is_binary=self._is_binary(full_path),
                    content=None,
                )

            with open(full_path, "rb") as f:
                content = f.read()

            is_binary = self._is_binary(full_path)

            return RepoFile(
                path=path,
                name=os.path.basename(path),
                size=stat.st_size,
                is_binary=is_binary,
                content=content.decode("utf-8", errors="ignore")
                if not is_binary
                else None,
            )
        except Exception:
            return None

    def get_files(self, paths: List[str]) -> Dict[str, RepoFile]:
        result = {}
        for path in paths:
            file = self.get_file(path)
            if file:
                result[path] = file
        return result

    def _is_binary(self, filepath: str) -> bool:
        try:
            with open(filepath, "rb") as f:
                chunk = f.read(8192)
                return b"\x00" in chunk
        except Exception:
            return True

    def search_code(
        self, query: str, file_pattern: str = "*.py"
    ) -> List[Dict[str, Any]]:
        if not self._ensure_cloned():
            return []

        results = []
        try:
            result = subprocess.run(
                ["grep", "-rn", "--include=" + file_pattern, query, self.repo_path],
                capture_output=True,
                timeout=30,
            )

            for line in result.stdout.decode().splitlines():
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        filepath = os.path.relpath(parts[0], self.repo_path)
                        results.append(
                            {
                                "file": filepath,
                                "line": parts[1],
                                "content": parts[2],
                            }
                        )
        except Exception:
            pass

        return results

    def get_git_history(self, max_commits: int = 10) -> List[CommitInfo]:
        if not self._ensure_cloned():
            return []

        commits = []
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    self.repo_path,
                    "log",
                    f"-{max_commits}",
                    "--pretty=format:%H|%s|%an|%ad|%p",
                    "--date=iso",
                ],
                capture_output=True,
                timeout=30,
            )

            for line in result.stdout.decode().splitlines():
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        commits.append(
                            CommitInfo(
                                sha=parts[0],
                                message=parts[1],
                                author=parts[2],
                                date=parts[3],
                            )
                        )
        except Exception:
            pass

        return commits

    def get_repo_metadata(self) -> RepoMetadata:
        if self._repo_metadata:
            return self._repo_metadata

        repo_name = self.repo_url.rstrip("/").split("/")[-1]
        owner = self.repo_url.rstrip("/").split("/")[-2]

        self._repo_metadata = RepoMetadata(
            url=self.repo_url,
            name=repo_name,
            owner=owner,
            default_branch="main",
        )

        if self.repo_path and os.path.exists(self.repo_path):
            try:
                result = subprocess.run(
                    ["git", "-C", self.repo_path, "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    self._repo_metadata.default_branch = result.stdout.decode().strip()
            except Exception:
                pass

        return self._repo_metadata

    def exists(self) -> bool:
        return self._ensure_cloned()

    def get_local_path(self) -> Optional[str]:
        if self._ensure_cloned():
            return self.repo_path
        return None

    def cleanup(self):
        """Clean up cloned repository."""
        if self.repo_path and os.path.exists(self.repo_path):
            try:
                shutil.rmtree(self.repo_path)
            except Exception:
                pass
