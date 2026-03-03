from __future__ import annotations
"""Groups.io connector via LFX PIS API (ITX passthrough).

Uses the V2 groupV2-tagged endpoints from PIS to manage Groups.io
mailing lists, subgroups, and member subscriptions.

This replaces direct Groups.io API calls with the LFX-managed gateway,
which handles auth, rate limiting, and audit logging.

Endpoints used:
    GET  /v2/groupsio_service          — list Groups.io services
    GET  /v2/groupsio_subgroup         — list subgroups (mailing lists)
    GET  /v2/groupsio_subgroup/{id}/members     — list members
    GET  /v2/groupsio_subgroup/{id}/member_count — count members
    POST /v2/groupsio_subgroup/{id}/members     — subscribe member
    DELETE /v2/groupsio_subgroup/{id}/members/{mid} — unsubscribe member
"""

import logging
from typing import Optional

import httpx

from .base import BaseMailingListConnector
from .pis_client import PISClient

logger = logging.getLogger(__name__)


class PISGroupsIOConnector(BaseMailingListConnector):
    """Groups.io management via LFX PIS API.

    Key difference from direct GroupsIOConnector:
    - PIS uses numeric subgroup IDs, not list email addresses
    - We maintain a name→ID cache built from GET /v2/groupsio_subgroup
    - Subscribe requires richer payload (full_name, org, delivery_mode)
    - Remove requires member_id lookup (no "delete by email")
    """

    def __init__(self, pis_client: PISClient, project_id: str = ""):
        self._pis = pis_client
        self._project_id = project_id
        # Cache: list_name → subgroup_id  (e.g. "governing-board@lists.aaif.io" → 12345)
        self._subgroup_cache: dict[str, int] = {}
        # Cache: list_name → subgroup full URL
        self._subgroup_urls: dict[str, str] = {}
        # Reverse cache: subgroup_id → list_name
        self._id_to_name: dict[int, str] = {}
        self._cache_built = False

    async def initialize(self) -> None:
        """Initialize PIS client and build subgroup cache."""
        await self._pis.initialize()
        if self._project_id:
            await self._build_subgroup_cache()
        logger.info(
            "PISGroupsIOConnector initialized: %d subgroups cached",
            len(self._subgroup_cache),
        )

    async def _build_subgroup_cache(self) -> None:
        """Fetch all subgroups for the project and build name→ID lookup."""
        try:
            subgroups = await self._pis.get_paginated(
                "/v2/groupsio_subgroup",
                params={"project_id": self._project_id},
            )
            for sg in subgroups:
                sg_id = sg.get("id") or sg.get("group_id")
                title = sg.get("title", "")
                group_name = sg.get("group_name", "")
                url = sg.get("url", "")

                if not sg_id or not title:
                    continue

                # Build the full email-style list name: "governing-board@lists.aaif.io"
                # PIS may return title="governing-board" and group_name="aaif"
                # or the full email in the url field
                if "@" in title:
                    list_name = title
                elif url and "lists." in url:
                    # Extract domain from URL: "https://lists.aaif.io/g/governing-board"
                    domain = url.split("//")[1].split("/")[0] if "//" in url else ""
                    list_name = f"{title}@{domain}" if domain else title
                elif group_name:
                    list_name = f"{title}@lists.{group_name}.io"
                else:
                    list_name = title

                self._subgroup_cache[list_name] = int(sg_id)
                self._subgroup_urls[list_name] = url
                self._id_to_name[int(sg_id)] = list_name

            self._cache_built = True
            logger.info(
                "Subgroup cache built: %d lists for project %s",
                len(self._subgroup_cache),
                self._project_id,
            )
        except Exception as e:
            logger.error("Failed to build subgroup cache: %s", e)
            # Don't raise — allow graceful degradation to mock

    def _resolve_subgroup_id(self, list_name: str) -> Optional[int]:
        """Resolve a list name to its PIS subgroup ID.

        Tries exact match first, then prefix match (e.g. "governing-board"
        matches "governing-board@lists.aaif.io").
        """
        if list_name in self._subgroup_cache:
            return self._subgroup_cache[list_name]

        # Try prefix match: "governing-board" → "governing-board@lists.aaif.io"
        prefix = list_name.split("@")[0] if "@" in list_name else list_name
        for cached_name, sg_id in self._subgroup_cache.items():
            if cached_name.startswith(prefix + "@") or cached_name == prefix:
                return sg_id

        logger.warning("Subgroup not found in cache: %s", list_name)
        return None

    async def _find_member_id(
        self, subgroup_id: int, email: str
    ) -> Optional[int]:
        """Find a member's ID by email within a subgroup.

        PIS doesn't support lookup by email directly — we must list
        members and filter. Uses pagination to handle large lists.
        """
        members = await self._pis.get_paginated(
            f"/v2/groupsio_subgroup/{subgroup_id}/members",
        )
        for m in members:
            if m.get("email", "").lower() == email.lower():
                return m.get("member_id") or m.get("id")
        return None

    # ── BaseMailingListConnector interface ────────────────────────

    async def health_check(self) -> dict:
        base = await self._pis.health_check()
        base["connector"] = "pis_groupsio"
        base["cached_subgroups"] = len(self._subgroup_cache)
        return base

    async def add_member(self, list_name: str, email: str) -> dict:
        """Subscribe a member to a mailing list via PIS."""
        sg_id = self._resolve_subgroup_id(list_name)
        if sg_id is None:
            return {
                "status": "error",
                "list": list_name,
                "email": email,
                "error": f"Subgroup not found: {list_name}",
            }

        body = {
            "email": email,
            "delivery_mode": "email_delivery_single",
            "member_type": "direct",
            "mod_status": "none",
        }

        try:
            result = await self._pis.post(
                f"/v2/groupsio_subgroup/{sg_id}/members",
                json_body=body,
            )
            logger.info("PIS: subscribed %s to %s (subgroup %d)", email, list_name, sg_id)
            return {
                "status": "added",
                "list": list_name,
                "email": email,
                "member_id": result.get("member_id") or result.get("id"),
                "mode": "pis_live",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                return {"status": "already_member", "list": list_name, "email": email}
            logger.error("PIS add_member failed: %s", e)
            return {
                "status": "error",
                "list": list_name,
                "email": email,
                "error": str(e),
            }

    async def add_member_enriched(
        self,
        list_name: str,
        email: str,
        full_name: str = "",
        organization: str = "",
        job_title: str = "",
    ) -> dict:
        """Subscribe a member with full profile info (PIS-specific).

        The PIS V2 API accepts richer payloads than the direct Groups.io API.
        Use this when contact details are available from SFDC.
        """
        sg_id = self._resolve_subgroup_id(list_name)
        if sg_id is None:
            return {
                "status": "error",
                "list": list_name,
                "email": email,
                "error": f"Subgroup not found: {list_name}",
            }

        body = {
            "email": email,
            "full_name": full_name,
            "organization": organization,
            "job_title": job_title,
            "delivery_mode": "email_delivery_single",
            "member_type": "direct",
            "mod_status": "none",
        }
        # Strip empty values
        body = {k: v for k, v in body.items() if v}
        body.setdefault("delivery_mode", "email_delivery_single")
        body.setdefault("member_type", "direct")

        try:
            result = await self._pis.post(
                f"/v2/groupsio_subgroup/{sg_id}/members",
                json_body=body,
            )
            return {
                "status": "added",
                "list": list_name,
                "email": email,
                "member_id": result.get("member_id") or result.get("id"),
                "mode": "pis_live",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                return {"status": "already_member", "list": list_name, "email": email}
            return {"status": "error", "list": list_name, "email": email, "error": str(e)}

    async def remove_member(self, list_name: str, email: str) -> dict:
        """Remove a member from a mailing list via PIS.

        Two-step: find member_id by email, then DELETE.
        """
        sg_id = self._resolve_subgroup_id(list_name)
        if sg_id is None:
            return {
                "status": "error",
                "list": list_name,
                "email": email,
                "error": f"Subgroup not found: {list_name}",
            }

        member_id = await self._find_member_id(sg_id, email)
        if member_id is None:
            return {"status": "not_member", "list": list_name, "email": email}

        try:
            await self._pis.delete(
                f"/v2/groupsio_subgroup/{sg_id}/members/{member_id}"
            )
            logger.info(
                "PIS: removed %s from %s (subgroup %d, member %d)",
                email, list_name, sg_id, member_id,
            )
            return {
                "status": "removed",
                "list": list_name,
                "email": email,
                "mode": "pis_live",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "not_member", "list": list_name, "email": email}
            logger.error("PIS remove_member failed: %s", e)
            return {"status": "error", "list": list_name, "email": email, "error": str(e)}

    async def get_members(self, list_name: str) -> list[str]:
        """Get all member emails for a mailing list."""
        sg_id = self._resolve_subgroup_id(list_name)
        if sg_id is None:
            logger.warning("get_members: subgroup not found: %s", list_name)
            return []

        members = await self._pis.get_paginated(
            f"/v2/groupsio_subgroup/{sg_id}/members",
        )
        return [m.get("email", "") for m in members if m.get("email")]

    async def get_members_detailed(self, list_name: str) -> list[dict]:
        """Get full member records (PIS-specific — includes name, org, role)."""
        sg_id = self._resolve_subgroup_id(list_name)
        if sg_id is None:
            return []
        return await self._pis.get_paginated(
            f"/v2/groupsio_subgroup/{sg_id}/members",
        )

    async def is_member(self, list_name: str, email: str) -> bool:
        """Check if an email is subscribed to a mailing list."""
        sg_id = self._resolve_subgroup_id(list_name)
        if sg_id is None:
            return False

        member_id = await self._find_member_id(sg_id, email)
        return member_id is not None

    async def get_lists(self, foundation_id: str) -> list[str]:
        """Get all mailing list addresses for the foundation."""
        if not self._cache_built:
            await self._build_subgroup_cache()
        return sorted(self._subgroup_cache.keys())

    async def get_member_count(self, list_name: str) -> int:
        """Get subscriber count without fetching all members (PIS-specific)."""
        sg_id = self._resolve_subgroup_id(list_name)
        if sg_id is None:
            return 0
        try:
            data = await self._pis.get(
                f"/v2/groupsio_subgroup/{sg_id}/member_count"
            )
            return data.get("count", 0)
        except Exception:
            return 0

    async def get_service_info(self) -> dict:
        """Get the Groups.io service config for this project (PIS-specific)."""
        try:
            services = await self._pis.get_paginated(
                "/v2/groupsio_service",
                params={"project_id": self._project_id},
            )
            return services[0] if services else {}
        except Exception as e:
            logger.error("get_service_info failed: %s", e)
            return {}

    async def close(self) -> None:
        """Close underlying PIS client."""
        await self._pis.close()
