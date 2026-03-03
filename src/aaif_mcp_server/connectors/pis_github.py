from __future__ import annotations
"""GitHub connector via LFX PIS API (ITX passthrough).

Uses the V2 github_v2-tagged endpoints from PIS to manage GitHub
organizations and repositories tracked by the Linux Foundation.

Note: PIS manages *tracking* of GitHub orgs/repos — it doesn't directly
manage collaborator access. For collaborator management, we still need
the direct GitHub API. PIS is useful for:
- Listing orgs and repos associated with a project
- Creating new repos under an LF-managed org
- Getting repo metadata (DCO status, shared status, etc.)

Endpoints used:
    GET    /v2/github                     — list all GitHub orgs
    GET    /v2/github/{org}               — get org details
    GET    /v2/github/{org}/repos         — list repos for an org
    GET    /v2/github/{org}/repos/{repo}  — get repo details
    POST   /v2/github/{org}/repos         — create a repo
    PUT    /v2/github/{org}               — update org details
    DELETE /v2/github/{org}               — untrack org
"""

import logging
from typing import Optional

from .pis_client import PISClient

logger = logging.getLogger(__name__)


class PISGitHubConnector:
    """GitHub org/repo management via LFX PIS API.

    This supplements (not replaces) the direct GitHubConnector.
    PIS handles org-level tracking; direct GitHub API handles
    collaborator-level access management.
    """

    def __init__(self, pis_client: PISClient, project_id: str = ""):
        self._pis = pis_client
        self._project_id = project_id
        # Cache: org_name → org_id
        self._org_cache: dict[str, str] = {}
        # Cache: (org_name, repo_name) → repo_info
        self._repo_cache: dict[tuple[str, str], dict] = {}

    async def initialize(self) -> None:
        """Initialize PIS client and build org cache."""
        await self._pis.initialize()
        if self._project_id:
            await self._build_org_cache()
        logger.info(
            "PISGitHubConnector initialized: %d orgs cached",
            len(self._org_cache),
        )

    async def _build_org_cache(self) -> None:
        """Fetch all GitHub orgs for the AAIF project."""
        try:
            orgs = await self._pis.get_paginated(
                "/v2/github",
                params={"project_id": self._project_id},
            )
            for org in orgs:
                org_name = org.get("organization", "")
                org_id = org.get("id", "")
                if org_name:
                    self._org_cache[org_name] = org_id
            logger.info("GitHub org cache: %d orgs", len(self._org_cache))
        except Exception as e:
            logger.error("Failed to build GitHub org cache: %s", e)

    # ── Read operations ──────────────────────────────────────────

    async def list_orgs(self) -> list[dict]:
        """List all GitHub orgs tracked for this project."""
        return await self._pis.get_paginated(
            "/v2/github",
            params={"project_id": self._project_id} if self._project_id else {},
        )

    async def get_org(self, org_name: str) -> Optional[dict]:
        """Get details for a specific GitHub org."""
        try:
            return await self._pis.get(f"/v2/github/{org_name}")
        except Exception as e:
            logger.error("get_org(%s) failed: %s", org_name, e)
            return None

    async def list_repos(
        self, org_name: str, search: str = ""
    ) -> list[dict]:
        """List repos for a GitHub org, optionally filtered by search term."""
        params: dict = {}
        if self._project_id:
            params["project_id"] = self._project_id
        if search:
            params["search"] = search
        return await self._pis.get_paginated(
            f"/v2/github/{org_name}/repos",
            params=params,
        )

    async def get_repo(self, org_name: str, repo_name: str) -> Optional[dict]:
        """Get details for a specific repo."""
        try:
            return await self._pis.get(
                f"/v2/github/{org_name}/repos/{repo_name}"
            )
        except Exception as e:
            logger.error("get_repo(%s/%s) failed: %s", org_name, repo_name, e)
            return None

    # ── Write operations ─────────────────────────────────────────

    async def create_repo(
        self,
        org_name: str,
        repo_name: str,
        description: str = "",
        dco_enabled: bool = True,
        has_issues: bool = True,
    ) -> dict:
        """Create a new GitHub repo under an LF-managed org via PIS."""
        body = {
            "name": repo_name,
            "description": description,
            "has_issues": has_issues,
            "has_projects": True,
            "has_wiki": False,
            "archived": False,
            "dco_enabled": dco_enabled,
            "homepage": "",
        }
        try:
            result = await self._pis.post(
                f"/v2/github/{org_name}/repos",
                json_body=body,
            )
            logger.info("PIS: created repo %s/%s", org_name, repo_name)
            return {
                "status": "created",
                "org": org_name,
                "repo": repo_name,
                "details": result,
                "mode": "pis_live",
            }
        except Exception as e:
            logger.error("create_repo failed: %s", e)
            return {
                "status": "error",
                "org": org_name,
                "repo": repo_name,
                "error": str(e),
            }

    async def track_org(self, org_name: str) -> dict:
        """Start tracking a GitHub org in PIS for this project."""
        body = {
            "organization": org_name,
            "project": self._project_id,
        }
        try:
            result = await self._pis.post("/v2/github", json_body=body)
            self._org_cache[org_name] = result.get("id", "")
            logger.info("PIS: tracking GitHub org %s", org_name)
            return {"status": "tracked", "org": org_name, "details": result}
        except Exception as e:
            logger.error("track_org(%s) failed: %s", org_name, e)
            return {"status": "error", "org": org_name, "error": str(e)}

    # ── Health check ─────────────────────────────────────────────

    async def health_check(self) -> dict:
        """Check connectivity by listing orgs."""
        try:
            orgs = await self.list_orgs()
            return {
                "connector": "pis_github",
                "status": "healthy",
                "mode": "live",
                "tracked_orgs": len(orgs),
            }
        except Exception as e:
            return {
                "connector": "pis_github",
                "status": "unhealthy",
                "mode": "live",
                "error": str(e),
            }

    async def close(self) -> None:
        """Close is handled by shared PIS client."""
        pass  # PIS client lifecycle managed by registry
