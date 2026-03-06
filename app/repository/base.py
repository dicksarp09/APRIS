from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class RepoFile:
    path: str
    name: str
    size: int
    is_binary: bool
    content: Optional[str] = None


@dataclass
class RepoMetadata:
    url: str
    name: str
    owner: str
    description: Optional[str] = None
    default_branch: str = "main"
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    size_kb: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class CommitInfo:
    sha: str
    message: str
    author: str
    date: str
    files_changed: int = 0


class RepositoryProvider(ABC):
    """Abstract interface for repository access layer.

    This abstraction allows APRIS to work with different repository sources
    (local git, GitHub MCP, etc.) without changing the analysis pipeline.
    """

    @abstractmethod
    def list_files(self, path: str = "") -> List[str]:
        """List all files in the repository.

        Args:
            path: Directory path to list from (empty = root)

        Returns:
            List of file paths relative to repository root
        """
        pass

    @abstractmethod
    def get_file(self, path: str) -> Optional[RepoFile]:
        """Get a single file's content and metadata.

        Args:
            path: Path to the file relative to repository root

        Returns:
            RepoFile object or None if not found
        """
        pass

    @abstractmethod
    def get_files(self, paths: List[str]) -> Dict[str, RepoFile]:
        """Get multiple files at once.

        Args:
            paths: List of file paths

        Returns:
            Dictionary mapping path to RepoFile
        """
        pass

    @abstractmethod
    def search_code(
        self, query: str, file_pattern: str = "*.py"
    ) -> List[Dict[str, Any]]:
        """Search for code in the repository.

        Args:
            query: Search query
            file_pattern: File pattern to search in

        Returns:
            List of search results with file path, line number, and content
        """
        pass

    @abstractmethod
    def get_git_history(self, max_commits: int = 10) -> List[CommitInfo]:
        """Get git commit history.

        Args:
            max_commits: Maximum number of commits to retrieve

        Returns:
            List of commit information
        """
        pass

    @abstractmethod
    def get_repo_metadata(self) -> RepoMetadata:
        """Get repository metadata.

        Returns:
            RepoMetadata object with repository information
        """
        pass

    @abstractmethod
    def exists(self) -> bool:
        """Check if the repository is accessible.

        Returns:
            True if repository exists and is accessible
        """
        pass

    @abstractmethod
    def get_local_path(self) -> Optional[str]:
        """Get local filesystem path if available.

        Returns:
            Local path if repository is cloned locally, None otherwise
        """
        pass


class ProviderFactory:
    """Factory for creating repository providers."""

    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a provider class.

        Args:
            name: Provider name (e.g., 'local', 'github_mcp')
            provider_class: Provider class implementation
        """
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, name: str, config: Dict[str, Any]) -> RepositoryProvider:
        """Create a provider instance.

        Args:
            name: Provider name
            config: Provider configuration

        Returns:
            RepositoryProvider instance

        Raises:
            ValueError: If provider name is not registered
        """
        if name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {name}. Available: {list(cls._providers.keys())}"
            )

        # Handle config object for GitHubMCPProvider
        provider_config = dict(config)
        if "config" in provider_config:
            provider_config["config"] = provider_config["config"]

        return cls._providers[name](**provider_config)

    @classmethod
    def available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        return list(cls._providers.keys())
