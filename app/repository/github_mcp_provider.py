import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import threading

from app.repository.base import RepositoryProvider, RepoFile, RepoMetadata, CommitInfo


@dataclass
class GitHubMCPConfig:
    """Configuration for GitHub MCP provider."""

    github_token: Optional[str] = None
    mcp_server_url: str = "https://api.githubcopilot.com/mcp/"
    max_files: int = 200
    max_file_size_kb: int = 200
    timeout_seconds: int = 300


class GitHubMCPProvider(RepositoryProvider):
    """Repository provider using GitHub MCP (Model Context Protocol).

    This provider fetches repository data through the GitHub MCP server,
    providing an abstraction layer between the agent and GitHub API.
    """

    def __init__(self, repo_url: str, config: GitHubMCPConfig = None):
        self.repo_url = repo_url
        self.config = config or GitHubMCPConfig()

        parts = repo_url.rstrip("/").replace("https://github.com/", "").split("/")
        self.owner = parts[0] if len(parts) > 0 else ""
        self.repo_name = parts[1] if len(parts) > 1 else ""

        self._file_list: Optional[List[str]] = None
        self._file_urls: Dict[str, str] = {}
        self._metadata: Optional[RepoMetadata] = None

    def _get_token(self) -> str:
        """Get GitHub token."""
        token = self.config.github_token or os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise ValueError(
                "GitHub token required for MCP provider. Set GITHUB_TOKEN environment variable."
            )
        return token

    def _call_mcp(self, method: str, params: Dict[str, Any] = None) -> Any:
        """Call MCP tool using JSON-RPC over SSE."""
        import httpx

        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        request_id = 1
        request_body = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                with client.stream(
                    "POST",
                    self.config.mcp_server_url,
                    headers=headers,
                    json=request_body,
                ) as response:
                    if response.status_code != 200:
                        return None

                    # Parse SSE response
                    buffer = ""
                    for line in response.iter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            try:
                                result = json.loads(data)
                                if result.get("id") == request_id:
                                    if "result" in result:
                                        return result["result"]
                                    if "error" in result:
                                        print(f"MCP error: {result['error']}")
                                        return None
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            print(f"MCP call failed: {e}")

        return None

    def list_files(self, path: str = "") -> List[str]:
        """Get repository file tree via MCP."""
        if self._file_list is not None:
            if not path:
                return self._file_list
            return [f for f in self._file_list if f.startswith(path + "/")]

        result = self._call_mcp(
            "tools/call",
            {
                "name": "get_file_contents",
                "arguments": {
                    "owner": self.owner,
                    "repo": self.repo_name,
                    "path": path,
                },
            },
        )

        files = []
        if result and isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            text = item["text"]
                            data = json.loads(text)

                            if isinstance(data, list):
                                for entry in data:
                                    if entry.get("type") == "file":
                                        files.append(entry.get("path", ""))
                                        self._file_urls[entry.get("path", "")] = (
                                            entry.get("download_url", "")
                                        )
                            elif isinstance(data, dict) and data.get("type") == "file":
                                files.append(data.get("path", ""))
                                self._file_urls[data.get("path", "")] = data.get(
                                    "download_url", ""
                                )
                        except Exception as e:
                            print(f"Parse error: {e}")

        if len(files) > self.config.max_files:
            files = files[: self.config.max_files]

        self._file_list = files
        return files

    def get_file(self, path: str) -> Optional[RepoFile]:
        """Get a single file from GitHub via MCP (uses direct URL as fallback)."""
        # First try MCP tool
        result = self._call_mcp(
            "tools/call",
            {
                "name": "get_file_contents",
                "arguments": {
                    "owner": self.owner,
                    "repo": self.repo_name,
                    "path": path,
                },
            },
        )

        if result and isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            data = json.loads(item["text"])
                            if isinstance(data, dict) and "content" in data:
                                file_content = data.get("content", "")
                                size = len(file_content.encode("utf-8"))

                                if size // 1024 > self.config.max_file_size_kb:
                                    return RepoFile(
                                        path=path,
                                        name=os.path.basename(path),
                                        size=size,
                                        is_binary=False,
                                        content=None,
                                    )

                                return RepoFile(
                                    path=path,
                                    name=os.path.basename(path),
                                    size=size,
                                    is_binary=False,
                                    content=file_content,
                                )
                        except:
                            pass

        # Fallback: use download URL from cached file list
        download_url = self._file_urls.get(path, "")
        if download_url:
            try:
                import httpx

                token = self._get_token()
                headers = {"Authorization": f"token {token}"}
                response = httpx.get(download_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    content = response.text
                    size = len(content.encode("utf-8"))
                    return RepoFile(
                        path=path,
                        name=os.path.basename(path),
                        size=size,
                        is_binary=False,
                        content=content,
                    )
            except Exception as e:
                print(f"Fallback file fetch failed: {e}")

        return None

    def get_files(self, paths: List[str]) -> Dict[str, RepoFile]:
        """Get multiple files via MCP."""
        result = {}
        for path in paths:
            file = self.get_file(path)
            if file:
                result[path] = file
        return result

    def search_code(
        self, query: str, file_pattern: str = "*.py"
    ) -> List[Dict[str, Any]]:
        """Search code via MCP."""
        result = self._call_mcp(
            "tools/call",
            {
                "name": "search_code",
                "arguments": {
                    "query": f"{query} repo:{self.owner}/{self.repo_name}",
                },
            },
        )

        search_results = []
        if result and isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            data = json.loads(item["text"])
                            if isinstance(data, list):
                                for entry in data[:20]:
                                    search_results.append(
                                        {
                                            "file": entry.get("path", ""),
                                            "name": entry.get("name", ""),
                                            "url": entry.get("html_url", ""),
                                        }
                                    )
                        except:
                            pass

        return search_results

    def get_git_history(self, max_commits: int = 10) -> List[CommitInfo]:
        """Get commit history via MCP."""
        result = self._call_mcp(
            "tools/call",
            {
                "name": "list_commits",
                "arguments": {
                    "owner": self.owner,
                    "repo": self.repo_name,
                    "per_page": max_commits,
                },
            },
        )

        commits = []
        if result and isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            data = json.loads(item["text"])
                            if isinstance(data, list):
                                for commit_data in data:
                                    commit = commit_data.get("commit", {})
                                    commits.append(
                                        CommitInfo(
                                            sha=commit_data.get("sha", ""),
                                            message=commit.get("message", ""),
                                            author=commit.get("author", {}).get(
                                                "name", "Unknown"
                                            ),
                                            date=commit.get("author", {}).get(
                                                "date", ""
                                            ),
                                        )
                                    )
                        except:
                            pass

        return commits

    def get_repo_metadata(self) -> RepoMetadata:
        """Get repository metadata via MCP."""
        if self._metadata:
            return self._metadata

        result = self._call_mcp(
            "tools/call",
            {
                "name": "get_repository",
                "arguments": {
                    "owner": self.owner,
                    "repo": self.repo_name,
                },
            },
        )

        if result and isinstance(result, dict):
            content = result.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        try:
                            data = json.loads(item["text"])
                            if isinstance(data, dict):
                                owner_data = data.get("owner", {})
                                owner_login = (
                                    owner_data.get("login", self.owner)
                                    if isinstance(owner_data, dict)
                                    else self.owner
                                )
                                self._metadata = RepoMetadata(
                                    url=self.repo_url,
                                    name=data.get("name", self.repo_name),
                                    owner=owner_login,
                                    description=data.get("description"),
                                    default_branch=data.get("default_branch", "main"),
                                    language=data.get("language"),
                                    stars=data.get("stargazers_count", 0),
                                    forks=data.get("forks_count", 0),
                                    size_kb=data.get("size", 0) * 1024,
                                    created_at=data.get("created_at"),
                                    updated_at=data.get("updated_at"),
                                )
                                return self._metadata
                        except:
                            pass

        return RepoMetadata(
            url=self.repo_url,
            name=self.repo_name,
            owner=self.owner,
        )

    def exists(self) -> bool:
        """Check if repository exists via MCP."""
        try:
            metadata = self.get_repo_metadata()
            return metadata.name is not None
        except Exception:
            return False

    def get_local_path(self) -> Optional[str]:
        """GitHub MCP doesn't provide local path."""
        return None

    def get_file_tree_cached(self) -> Optional[List[str]]:
        """Get cached file tree."""
        return self._file_list


from app.repository.base import ProviderFactory
from app.repository.local_provider import LocalGitProvider

ProviderFactory.register("local", LocalGitProvider)
ProviderFactory.register("github_mcp", GitHubMCPProvider)
