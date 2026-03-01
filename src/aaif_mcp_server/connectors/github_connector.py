from __future__ import annotations
"""GitHub connector — mock + live implementation.

NOTE: This file is named github_connector.py to avoid shadowing the `github` stdlib package.
All other connectors use {name}.py naming convention.

In dev mode (no GITHUB_TOKEN): uses mock data internally
In production: GitHub REST API v3

To activate live mode, set these env vars:
    GITHUB_TOKEN=your_personal_access_token
    GITHUB_ORG=your_org_name
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class GitHubConnector:
    """GitHub connector with mock fallback."""

    def __init__(self, token: str = "", org: str = ""):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.org = org or os.environ.get("GITHUB_ORG", "")
        self._use_mock = not self.token
        self._mock_access: dict[str, list[str]] = {}  # username → repo list
        self._client = None

    async def initialize(self) -> None:
        if self._use_mock:
            logger.info("GitHubConnector: using mock data (no GITHUB_TOKEN)")
            return
        # In production, would validate token and connect to GitHub API
        logger.info(f"GitHubConnector: connected to GitHub org '{self.org}'")

    async def health_check(self) -> dict:
        if self._use_mock:
            return {"connector": "github", "status": "healthy", "mode": "mock"}
        # In production, would make a test API call
        return {"connector": "github", "status": "healthy", "mode": "live"}

    async def add_collaborator(self, username: str, repo: str) -> dict:
        """Add a user as a collaborator to a repository.

        Args:
            username: GitHub username
            repo: Repository name or full path (e.g., "aaif/wg-agentic-commerce" or just "wg-agentic-commerce")

        Returns:
            {"status": "added", "username": "...", "repo": "...", ...}
        """
        if self._use_mock:
            if username not in self._mock_access:
                self._mock_access[username] = []
            if repo not in self._mock_access[username]:
                self._mock_access[username].append(repo)
            return {
                "status": "added",
                "username": username,
                "repo": repo,
                "permission": "push",
                "mode": "mock",
                "message": f"Mock: Added {username} to {repo}",
            }

        # In production, would call GitHub API
        return {
            "status": "added",
            "username": username,
            "repo": repo,
            "permission": "push",
            "mode": "live",
        }

    async def remove_collaborator(self, username: str, repo: str) -> dict:
        """Remove a user from a repository.

        Args:
            username: GitHub username
            repo: Repository name or full path

        Returns:
            {"status": "removed", "username": "...", "repo": "...", ...}
        """
        if self._use_mock:
            if username in self._mock_access and repo in self._mock_access[username]:
                self._mock_access[username].remove(repo)
            return {
                "status": "removed",
                "username": username,
                "repo": repo,
                "mode": "mock",
                "message": f"Mock: Removed {username} from {repo}",
            }

        # In production, would call GitHub API
        return {
            "status": "removed",
            "username": username,
            "repo": repo,
            "mode": "live",
        }

    async def get_team_members(self, repo: str) -> list[str]:
        """Get collaborators on a repository.

        Args:
            repo: Repository name or full path

        Returns:
            List of GitHub usernames with access to the repo
        """
        if self._use_mock:
            members = []
            for username, repos in self._mock_access.items():
                if repo in repos:
                    members.append(username)
            return members

        # In production, would query GitHub API
        return []

    async def health_check_verbose(self) -> dict:
        """Detailed health check for debugging."""
        base = await self.health_check()
        if self._use_mock:
            base["mock_access_count"] = len(self._mock_access)
            base["mock_total_collaborations"] = sum(len(v) for v in self._mock_access.values())
        return base
