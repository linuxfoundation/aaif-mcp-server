from __future__ import annotations
"""LFX PIS (Project Infrastructure Service) base HTTP client.

Shared by all PIS-backed connectors (Groups.io, GitHub, etc.).
Handles X-ACL authentication, request signing, and pagination.

To activate PIS mode, set these env vars:
    PIS_ACL_TOKEN=your_acl_token
    PIS_USERNAME=your_lfid_username
    PIS_BASE_URL=https://api-gw.dev.platform.linuxfoundation.org/project-infrastructure-service  (optional)
"""

import logging
import os
from typing import Any, Optional
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

PIS_DEFAULT_BASE_URL = (
    "https://api-gw.dev.platform.linuxfoundation.org"
    "/project-infrastructure-service"
)


class PISClient:
    """Shared HTTP client for LFX Project Infrastructure Service API.

    Handles:
    - X-ACL / X-USERNAME / X-REQUEST-ID header injection
    - Pagination via page_token
    - Configurable base URL for dev/staging/prod
    """

    def __init__(
        self,
        acl_token: str = "",
        username: str = "",
        base_url: str = "",
    ):
        self.acl_token = acl_token or os.environ.get("PIS_ACL_TOKEN", "")
        self.username = username or os.environ.get("PIS_USERNAME", "")
        self.base_url = (
            base_url
            or os.environ.get("PIS_BASE_URL", "")
            or PIS_DEFAULT_BASE_URL
        )
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_configured(self) -> bool:
        """Return True if PIS credentials are available."""
        return bool(self.acl_token and self.username)

    async def initialize(self) -> None:
        """Set up the async HTTP client."""
        if self._client:
            return
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
        )
        logger.info(
            "PISClient initialized: base_url=%s, username=%s",
            self.base_url,
            self.username,
        )

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build PIS request headers with auth + unique request ID."""
        headers = {
            "X-ACL": self.acl_token,
            "X-USERNAME": self.username,
            "X-REQUEST-ID": str(uuid4()),
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict:
        """Authenticated GET request."""
        if not self._client:
            await self.initialize()
        resp = await self._client.get(path, params=params, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def post(
        self,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict:
        """Authenticated POST request."""
        if not self._client:
            await self.initialize()
        resp = await self._client.post(path, json=json_body, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def put(
        self,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict:
        """Authenticated PUT request."""
        if not self._client:
            await self.initialize()
        resp = await self._client.put(path, json=json_body, headers=self._headers())
        resp.raise_for_status()
        # PUT may return 204 No Content
        if resp.status_code == 204:
            return {"status": "updated"}
        return resp.json()

    async def delete(self, path: str) -> dict:
        """Authenticated DELETE request."""
        if not self._client:
            await self.initialize()
        resp = await self._client.delete(path, headers=self._headers())
        resp.raise_for_status()
        if resp.status_code == 204:
            return {"status": "deleted"}
        return resp.json()

    async def get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        page_size: int = 100,
    ) -> list[dict]:
        """GET with automatic pagination. Returns all items across pages."""
        all_items: list[dict] = []
        params = dict(params or {})
        params["page_size"] = page_size
        page_token: Optional[str] = None

        while True:
            if page_token:
                params["page_token"] = page_token
            elif "page_token" in params:
                del params["page_token"]

            data = await self.get(path, params=params)

            # PIS returns {"data": [...], "meta": {"page_token": "..."}}
            items = data.get("data", [])
            all_items.extend(items)

            meta = data.get("meta", {})
            page_token = meta.get("page_token")
            if not page_token or not items:
                break

        return all_items

    async def close(self) -> None:
        """Shut down the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> dict:
        """Basic connectivity check — try listing services."""
        try:
            await self.get("/v2/groupsio_service", params={"page_size": 1})
            return {"connector": "pis", "status": "healthy", "mode": "live"}
        except Exception as e:
            return {
                "connector": "pis",
                "status": "unhealthy",
                "mode": "live",
                "error": str(e),
            }
