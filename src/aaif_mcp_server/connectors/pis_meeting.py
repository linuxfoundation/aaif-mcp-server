from __future__ import annotations
"""LFX Meeting connector via PIS zoomV2 API.

Manages LFX Meetings (Zoom-backed) for AAIF projects — registrant
provisioning, meeting lookup, mailing-list sync, and engagement metrics.

Replaces mock GoogleCalendarConnector for calendar invite provisioning
when PIS credentials are configured.

Endpoints used (all under zoomV2 tag, same X-ACL auth):
    GET    /v2/zoom/meetings                         — list meetings by project
    GET    /v2/zoom/meetings/{id}                    — get meeting details
    POST   /v2/zoom/meetings                         — create meeting
    PUT    /v2/zoom/meetings/{id}                    — update meeting
    GET    /v2/zoom/meeting_count                    — count meetings
    GET    /v2/zoom/meetings/{id}/registrants        — list registrants
    POST   /v2/zoom/meetings/{id}/registrants        — add registrant
    GET    /v2/zoom/meetings/{id}/registrants/{rid}  — get registrant
    PUT    /v2/zoom/meetings/{id}/registrants/{rid}  — update registrant
    DELETE /v2/zoom/meetings/{id}/registrants/{rid}  — remove registrant
    POST   /v2/zoom/meetings/{id}/bulk_registrants   — bulk add registrants
    POST   /v2/zoom/meetings/{id}/mailinglists       — sync mailing list → meeting
    GET    /v2/zoom/meetings/{id}/join_link          — get join link
    GET    /v2/zoom/meetings/{id}/participants       — past meeting attendance
    GET    /v2/zoom/meetings/{id}/past               — past occurrences
"""

import logging
from typing import Optional

import httpx

from .pis_client import PISClient

logger = logging.getLogger(__name__)


class PISMeetingConnector:
    """LFX Meeting management via PIS zoomV2 API.

    Key concepts:
    - Meetings are scoped to a project_id (e.g. AAIF)
    - Each meeting has a numeric Zoom meeting ID
    - Contacts are added as "registrants" (not "attendees")
    - Registrants auto-receive calendar invites via Zoom
    - Mailing list sync can bulk-add Groups.io list members to a meeting
    - Meetings can be tied to committees (WGs) via committee_id
    """

    def __init__(self, pis_client: PISClient, project_id: str = ""):
        self._pis = pis_client
        self._project_id = project_id
        # Cache: meeting_id → meeting summary (topic, committee_id, etc.)
        self._meeting_cache: dict[int, dict] = {}
        # Cache: committee_id → list of meeting_ids
        self._committee_meetings: dict[str, list[int]] = {}
        self._cache_built = False

    async def initialize(self) -> None:
        """Initialize and build meeting cache for the project."""
        if self._project_id:
            await self._build_meeting_cache()
        logger.info(
            "PISMeetingConnector initialized: %d meetings cached",
            len(self._meeting_cache),
        )

    # ── Cache management ─────────────────────────────────────────

    async def _build_meeting_cache(self) -> None:
        """Fetch all meetings for the project and cache by ID and committee."""
        try:
            meetings = await self._pis.get_paginated(
                "/v2/zoom/meetings",
                params={"project_id": self._project_id},
            )
            for m in meetings:
                meeting_id = m.get("id")
                if not meeting_id:
                    continue

                self._meeting_cache[meeting_id] = {
                    "id": meeting_id,
                    "topic": m.get("topic", ""),
                    "committee_id": m.get("committee_id", ""),
                    "start_time": m.get("start_time", ""),
                    "duration": m.get("duration", 0),
                    "timezone": m.get("timezone", ""),
                    "join_url": m.get("join_url", ""),
                    "type": m.get("type", 0),
                    "project_id": m.get("project_id", self._project_id),
                }

                # Index by committee
                committee = m.get("committee_id", "")
                if committee:
                    if committee not in self._committee_meetings:
                        self._committee_meetings[committee] = []
                    self._committee_meetings[committee].append(meeting_id)

            self._cache_built = True
            logger.info(
                "Meeting cache built: %d meetings across %d committees for project %s",
                len(self._meeting_cache),
                len(self._committee_meetings),
                self._project_id,
            )
        except Exception as e:
            logger.error("Failed to build meeting cache: %s", e)

    # ── Meeting CRUD ─────────────────────────────────────────────

    async def list_meetings(
        self,
        committee_id: str = "",
        include_past: bool = False,
    ) -> list[dict]:
        """List all meetings for the project, optionally filtered by committee.

        Test with: GET /v2/zoom/meetings?project_id={AAIF_PID}
        """
        params: dict = {"project_id": self._project_id}
        if committee_id:
            params["committee"] = committee_id
        if include_past:
            params["show_previous_meetings"] = "true"

        return await self._pis.get_paginated("/v2/zoom/meetings", params=params)

    async def get_meeting(self, meeting_id: int) -> dict:
        """Get details for a specific meeting.

        Test with: GET /v2/zoom/meetings/{id}
        """
        return await self._pis.get(f"/v2/zoom/meetings/{meeting_id}")

    async def create_meeting(self, meeting_data: dict) -> dict:
        """Create a new LFX meeting.

        Test with: POST /v2/zoom/meetings
        Body: ZoomMeetingV2Post (topic, start_time, duration, timezone, etc.)
        """
        return await self._pis.post("/v2/zoom/meetings", json_body=meeting_data)

    async def update_meeting(self, meeting_id: int, updates: dict) -> dict:
        """Update an existing meeting (time, topic, settings).

        Test with: PUT /v2/zoom/meetings/{id}
        """
        return await self._pis.put(f"/v2/zoom/meetings/{meeting_id}", json_body=updates)

    async def get_meeting_count(self) -> int:
        """Get total meeting count for the project.

        Test with: GET /v2/zoom/meeting_count?project_id={AAIF_PID}
        """
        try:
            data = await self._pis.get(
                "/v2/zoom/meeting_count",
                params={"project_id": self._project_id},
            )
            return data.get("count", 0)
        except Exception:
            return 0

    # ── Registrant management (calendar invite provisioning) ─────

    async def list_registrants(self, meeting_id: int) -> list[dict]:
        """List all registrants for a meeting.

        Test with: GET /v2/zoom/meetings/{id}/registrants
        """
        return await self._pis.get_paginated(
            f"/v2/zoom/meetings/{meeting_id}/registrants",
        )

    async def add_registrant(
        self,
        meeting_id: int,
        email: str,
        first_name: str = "",
        last_name: str = "",
        occurrence_ids: list[str] | None = None,
    ) -> dict:
        """Add a contact as a meeting registrant (sends calendar invite).

        This is the primary method for onboarding — when a contact is added
        as a registrant, Zoom automatically sends them a calendar invite.

        Test with: POST /v2/zoom/meetings/{id}/registrants
        """
        body: dict = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "host": False,
        }
        if occurrence_ids:
            body["occurrence_ids"] = occurrence_ids
        # else: empty = add to whole series

        try:
            result = await self._pis.post(
                f"/v2/zoom/meetings/{meeting_id}/registrants",
                json_body=body,
            )
            logger.info(
                "PIS Meeting: added registrant %s to meeting %d", email, meeting_id
            )
            return {
                "status": "added",
                "meeting_id": meeting_id,
                "email": email,
                "registrant_id": result.get("id", ""),
                "join_url": result.get("join_url", ""),
                "mode": "pis_live",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                return {
                    "status": "already_registered",
                    "meeting_id": meeting_id,
                    "email": email,
                }
            logger.error("PIS add_registrant failed: %s", e)
            return {
                "status": "error",
                "meeting_id": meeting_id,
                "email": email,
                "error": str(e),
            }

    async def get_registrant(self, meeting_id: int, registrant_id: str) -> dict:
        """Get details for a specific registrant.

        Test with: GET /v2/zoom/meetings/{id}/registrants/{rid}
        """
        return await self._pis.get(
            f"/v2/zoom/meetings/{meeting_id}/registrants/{registrant_id}"
        )

    async def remove_registrant(
        self, meeting_id: int, registrant_id: str
    ) -> dict:
        """Remove a registrant from a meeting (offboarding).

        Test with: DELETE /v2/zoom/meetings/{id}/registrants/{rid}
        """
        try:
            await self._pis.delete(
                f"/v2/zoom/meetings/{meeting_id}/registrants/{registrant_id}"
            )
            logger.info(
                "PIS Meeting: removed registrant %s from meeting %d",
                registrant_id, meeting_id,
            )
            return {
                "status": "removed",
                "meeting_id": meeting_id,
                "registrant_id": registrant_id,
                "mode": "pis_live",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "status": "not_registered",
                    "meeting_id": meeting_id,
                    "registrant_id": registrant_id,
                }
            return {
                "status": "error",
                "meeting_id": meeting_id,
                "registrant_id": registrant_id,
                "error": str(e),
            }

    async def find_registrant_by_email(
        self, meeting_id: int, email: str
    ) -> Optional[dict]:
        """Find a registrant by email within a meeting.

        PIS doesn't support lookup by email — list all and filter.
        """
        registrants = await self.list_registrants(meeting_id)
        for r in registrants:
            if r.get("email", "").lower() == email.lower():
                return r
        return None

    async def remove_registrant_by_email(
        self, meeting_id: int, email: str
    ) -> dict:
        """Remove a registrant by email (two-step: find → delete).

        Convenience method for offboarding where we have email, not registrant ID.
        """
        registrant = await self.find_registrant_by_email(meeting_id, email)
        if not registrant:
            return {
                "status": "not_registered",
                "meeting_id": meeting_id,
                "email": email,
            }

        rid = registrant.get("id", "")
        result = await self.remove_registrant(meeting_id, rid)
        result["email"] = email
        return result

    # ── Bulk operations ──────────────────────────────────────────

    async def bulk_add_registrants(
        self, meeting_id: int, registrants: list[dict]
    ) -> dict:
        """Bulk add registrants to a meeting.

        Test with: POST /v2/zoom/meetings/{id}/bulk_registrants
        Body: Array of ZoomMeetingRegistrantPost objects
        """
        try:
            result = await self._pis.post(
                f"/v2/zoom/meetings/{meeting_id}/bulk_registrants",
                json_body=registrants,
            )
            logger.info(
                "PIS Meeting: bulk added %d registrants to meeting %d",
                len(registrants), meeting_id,
            )
            return {
                "status": "accepted",
                "meeting_id": meeting_id,
                "count": len(registrants),
                "report": result,
                "mode": "pis_live",
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "meeting_id": meeting_id,
                "count": len(registrants),
                "error": str(e),
            }

    async def sync_mailing_list(
        self, meeting_id: int, subgroup_ids: list[int]
    ) -> dict:
        """Sync Groups.io mailing list members to meeting registrants.

        This is a powerful endpoint — auto-adds all list members as registrants.
        Great for WG meetings that should mirror WG mailing list membership.

        Test with: POST /v2/zoom/meetings/{id}/mailinglists
        """
        body = {"subgroup_ids": subgroup_ids}
        try:
            result = await self._pis.post(
                f"/v2/zoom/meetings/{meeting_id}/mailinglists",
                json_body=body,
            )
            logger.info(
                "PIS Meeting: synced mailing lists %s to meeting %d",
                subgroup_ids, meeting_id,
            )
            return {
                "status": "accepted",
                "meeting_id": meeting_id,
                "subgroup_ids": subgroup_ids,
                "report": result,
                "mode": "pis_live",
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "error",
                "meeting_id": meeting_id,
                "subgroup_ids": subgroup_ids,
                "error": str(e),
            }

    # ── Meeting links & attendance ───────────────────────────────

    async def get_join_link(
        self,
        meeting_id: int,
        email: str = "",
        name: str = "",
    ) -> dict:
        """Get meeting join link (optionally personalized).

        Test with: GET /v2/zoom/meetings/{id}/join_link
        """
        params: dict = {}
        if email:
            params["email"] = email
        if name:
            params["name"] = name

        try:
            return await self._pis.get(
                f"/v2/zoom/meetings/{meeting_id}/join_link",
                params=params or None,
            )
        except Exception as e:
            return {"error": str(e), "meeting_id": meeting_id}

    async def get_registrant_by_lfx_user(
        self, meeting_id: int, user_id: str
    ) -> dict:
        """Look up registrant by LFX user ID.

        Test with: GET /v2/zoom/meetings/{id}/lfxuser/{user_id}
        """
        try:
            return await self._pis.get(
                f"/v2/zoom/meetings/{meeting_id}/lfxuser/{user_id}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "not_registered", "user_id": user_id}
            return {"error": str(e)}

    async def get_past_participants(self, meeting_id: int) -> dict:
        """Get participant count from past meeting (for engagement scoring).

        Test with: GET /v2/zoom/meetings/{id}/participants
        """
        try:
            return await self._pis.get(
                f"/v2/zoom/meetings/{meeting_id}/participants"
            )
        except Exception as e:
            return {"error": str(e), "meeting_id": meeting_id}

    async def get_past_occurrences(self, meeting_id: int) -> list[dict]:
        """Get past occurrences of a meeting.

        Test with: GET /v2/zoom/meetings/{id}/past
        """
        try:
            data = await self._pis.get(f"/v2/zoom/meetings/{meeting_id}/past")
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as e:
            logger.error("get_past_occurrences failed: %s", e)
            return []

    # ── Occurrence management ────────────────────────────────────

    async def cancel_occurrence(
        self, meeting_id: int, occurrence_id: str
    ) -> dict:
        """Cancel a specific meeting occurrence.

        Test with: DELETE /v2/zoom/meetings/{id}/occurrences/{occurrence}
        """
        try:
            return await self._pis.delete(
                f"/v2/zoom/meetings/{meeting_id}/occurrences/{occurrence_id}"
            )
        except httpx.HTTPStatusError as e:
            return {"status": "error", "error": str(e)}

    # ── High-level operations for MCP tools ──────────────────────

    async def provision_calendar_invites(
        self,
        contact_email: str,
        contact_first_name: str = "",
        contact_last_name: str = "",
        committee_ids: list[str] | None = None,
    ) -> list[dict]:
        """Provision calendar invites for a contact across relevant meetings.

        This is the main method called by tool_provision_calendar_invites.
        Adds the contact as a registrant to all meetings matching the
        specified committees (or all project meetings if none specified).

        Returns a list of results, one per meeting.
        """
        results = []

        if committee_ids:
            # Add to meetings for specific committees
            meeting_ids = []
            for cid in committee_ids:
                meeting_ids.extend(self._committee_meetings.get(cid, []))
        else:
            # Add to all project meetings
            meeting_ids = list(self._meeting_cache.keys())

        if not meeting_ids:
            # Cache may be empty — try fetching live
            meetings = await self.list_meetings()
            meeting_ids = [m.get("id") for m in meetings if m.get("id")]

        for mid in meeting_ids:
            result = await self.add_registrant(
                meeting_id=mid,
                email=contact_email,
                first_name=contact_first_name,
                last_name=contact_last_name,
            )
            # Enrich with meeting topic from cache
            meeting_info = self._meeting_cache.get(mid, {})
            result["meeting_topic"] = meeting_info.get("topic", "")
            result["committee_id"] = meeting_info.get("committee_id", "")
            results.append(result)

        return results

    async def remove_from_all_meetings(
        self, contact_email: str, committee_ids: list[str] | None = None
    ) -> list[dict]:
        """Remove a contact from project meetings (offboarding or WG leave).

        Two-step per meeting: find registrant by email, then delete.

        Args:
            contact_email: Email of the registrant to remove.
            committee_ids: If provided, only remove from meetings whose
                committee_id matches one of these values. Used for
                WG-scoped removal (leave_working_group).
                If None, removes from ALL project meetings (full offboarding).
        """
        results = []
        meeting_ids = list(self._meeting_cache.keys())

        if not meeting_ids:
            meetings = await self.list_meetings()
            meeting_ids = [m.get("id") for m in meetings if m.get("id")]

        for mid in meeting_ids:
            # If committee filtering is active, skip meetings that don't match
            if committee_ids is not None:
                meeting_info = self._meeting_cache.get(mid, {})
                mtg_committee = meeting_info.get("committee_id", "")
                if mtg_committee not in committee_ids:
                    continue

            result = await self.remove_registrant_by_email(mid, contact_email)
            meeting_info = self._meeting_cache.get(mid, {})
            result["meeting_topic"] = meeting_info.get("topic", "")
            results.append(result)

        return results

    async def get_contact_meetings(self, contact_email: str) -> list[dict]:
        """Get all meetings a contact is registered for.

        Checks each project meeting for the contact's registration.
        """
        registered_meetings = []
        meeting_ids = list(self._meeting_cache.keys())

        if not meeting_ids:
            meetings = await self.list_meetings()
            meeting_ids = [m.get("id") for m in meetings if m.get("id")]

        for mid in meeting_ids:
            registrant = await self.find_registrant_by_email(mid, contact_email)
            if registrant:
                meeting_info = self._meeting_cache.get(mid, {})
                registered_meetings.append({
                    "meeting_id": mid,
                    "topic": meeting_info.get("topic", ""),
                    "committee_id": meeting_info.get("committee_id", ""),
                    "start_time": meeting_info.get("start_time", ""),
                    "join_url": registrant.get("join_url", ""),
                    "registration_status": registrant.get("status", ""),
                })

        return registered_meetings

    # ── Health check ─────────────────────────────────────────────

    async def health_check(self) -> dict:
        """Check connectivity to LFX Meeting API."""
        base = await self._pis.health_check()
        base["connector"] = "pis_meeting"
        base["cached_meetings"] = len(self._meeting_cache)
        base["cached_committees"] = len(self._committee_meetings)
        return base

    async def close(self) -> None:
        """Close underlying PIS client (shared — may be used by others)."""
        # PIS client is shared; don't close it here — registry handles that
        pass
