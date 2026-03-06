from app.repository.base import (
    RepositoryProvider,
    RepoFile,
    RepoMetadata,
    CommitInfo,
    ProviderFactory,
)
from app.repository.local_provider import LocalGitProvider
from app.repository.github_mcp_provider import GitHubMCPProvider, GitHubMCPConfig


__all__ = [
    "RepositoryProvider",
    "RepoFile",
    "RepoMetadata",
    "CommitInfo",
    "ProviderFactory",
    "LocalGitProvider",
    "GitHubMCPProvider",
    "GitHubMCPConfig",
]


def get_repository_provider(
    provider_type: str, repo_url: str, config=None, **kwargs
) -> RepositoryProvider:
    """Get a repository provider instance.

    Args:
        provider_type: Type of provider ('local' or 'github_mcp')
        repo_url: Repository URL
        config: Optional config object for the provider
        **kwargs: Additional configuration for the provider (used if config not provided)

    Returns:
        RepositoryProvider instance
    """
    provider_config = {"repo_url": repo_url}
    if config:
        provider_config["config"] = config
    else:
        provider_config.update(kwargs)
    return ProviderFactory.create(provider_type, provider_config)
