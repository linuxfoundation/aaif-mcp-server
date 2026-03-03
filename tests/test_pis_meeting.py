"""Tests for PIS LFX Meeting connector (zoomV2 endpoints).

Tests PISMeetingConnector with mocked HTTP responses to validate
meeting CRUD, registrant management, mailing list sync, and high-level
provisioning methods — without needing real PIS credentials.

Each test maps to a specific endpoint for incremental testing
when live credentials become available.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from aaif_mcp_server.connectors.pis_client import PISClient
from aaif_mcp_server.connectors.pis_meeting import PISMeetingConnector


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def pis_client():
    """PIS client with test credentials."""
    return PISClient(
        acl_token="test-acl-token",
        username="test-user",
        base_url="https://pis-test.example.com",
    )


@pytest.fixture
def mock_meetings():
    """Mock PIS meeting list response (AAIF meetings)."""
    return [
        {
            "id": 91309581319,
            "topic": "AAIF Governing Board Monthly",
            "type": 8,
            "start_time": "2026-03-15T17:00:00Z",
            "duration": 60,
            "timezone": "America/New_York",
            "join_url": "https://zoom.us/j/91309581319",
            "project_id": "aaif-project-123",
            "committee_id": "governing-board",
        },
        {
            "id": 92222333444,
            "topic": "AAIF All-Hands",
            "type": 8,
            "start_time": "2026-03-20T15:00:00Z",
            "duration": 90,
            "timezone": "America/New_York",
            "join_url": "https://zoom.us/j/92222333444",
            "project_id": "aaif-project-123",
            "committee_id": "",
        },
        {
            "id": 93333444555,
            "topic": "Agentic Commerce WG Weekly",
            "type": 8,
            "start_time": "2026-03-12T10:00:00Z",
            "duration": 60,
            "timezone": "America/Los_Angeles",
            "join_url": "https://zoom.us/j/93333444555",
            "project_id": "aaif-project-123",
            "committee_id": "wg-agentic-commerce",
        },
    ]


@pytest.fixture
def mock_registrants():
    """Mock registrants for a meeting."""
    return [
        {
            "id": "reg-001",
            "email": "t.yamada@hitachi.com",
            "first_name": "Taro",
            "last_name": "Yamada",
            "status": "approved",
            "create_time": "2026-01-15T10:30:00Z",
            "join_url": "https://zoom.us/j/91309581319?tk=token-001",
        },
        {
            "id": "reg-002",
            "email": "j.smith@acme.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "status": "approved",
            "create_time": "2026-01-20T14:00:00Z",
            "join_url": "https://zoom.us/j/91309581319?tk=token-002",
        },
    ]


# ── TestPISMeetingConnector ──────────────────────────────────────


class TestMeetingCache:
    """Tests for meeting cache building on initialize.

    Maps to: GET /v2/zoom/meetings?project_id={AAIF_PID}
    """

    @pytest.mark.asyncio
    async def test_build_meeting_cache(self, pis_client, mock_meetings):
        """Cache should index meetings by ID and committee."""
        pis_client.get_paginated = AsyncMock(return_value=mock_meetings)
        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")
        await connector.initialize()

        assert len(connector._meeting_cache) == 3
        assert 91309581319 in connector._meeting_cache
        assert connector._meeting_cache[91309581319]["topic"] == "AAIF Governing Board Monthly"

        # Committee index
        assert "governing-board" in connector._committee_meetings
        assert 91309581319 in connector._committee_meetings["governing-board"]
        assert "wg-agentic-commerce" in connector._committee_meetings
        assert 93333444555 in connector._committee_meetings["wg-agentic-commerce"]

    @pytest.mark.asyncio
    async def test_cache_handles_error(self, pis_client):
        """Cache build failure should not raise — graceful degradation."""
        pis_client.get_paginated = AsyncMock(side_effect=Exception("network error"))
        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")
        await connector.initialize()

        assert len(connector._meeting_cache) == 0
        assert not connector._cache_built

    @pytest.mark.asyncio
    async def test_no_project_id_skips_cache(self, pis_client):
        """No project_id should skip cache building."""
        pis_client.get_paginated = AsyncMock()
        connector = PISMeetingConnector(pis_client, project_id="")
        await connector.initialize()

        pis_client.get_paginated.assert_not_called()


class TestMeetingCRUD:
    """Tests for meeting list/get/create/update.

    Maps to:
        GET  /v2/zoom/meetings?project_id={PID}
        GET  /v2/zoom/meetings/{id}
        POST /v2/zoom/meetings
        PUT  /v2/zoom/meetings/{id}
        GET  /v2/zoom/meeting_count
    """

    @pytest.mark.asyncio
    async def test_list_meetings(self, pis_client, mock_meetings):
        """list_meetings → GET /v2/zoom/meetings?project_id=..."""
        pis_client.get_paginated = AsyncMock(return_value=mock_meetings)
        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")

        result = await connector.list_meetings()
        assert len(result) == 3
        pis_client.get_paginated.assert_called_with(
            "/v2/zoom/meetings", params={"project_id": "aaif-project-123"}
        )

    @pytest.mark.asyncio
    async def test_list_meetings_by_committee(self, pis_client):
        """list_meetings with committee filter."""
        pis_client.get_paginated = AsyncMock(return_value=[])
        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")

        await connector.list_meetings(committee_id="governing-board")
        call_params = pis_client.get_paginated.call_args[1]["params"]
        assert call_params["committee"] == "governing-board"

    @pytest.mark.asyncio
    async def test_get_meeting(self, pis_client):
        """get_meeting → GET /v2/zoom/meetings/{id}"""
        meeting_data = {"id": 91309581319, "topic": "Test Meeting"}
        pis_client.get = AsyncMock(return_value=meeting_data)
        connector = PISMeetingConnector(pis_client)

        result = await connector.get_meeting(91309581319)
        assert result["topic"] == "Test Meeting"
        pis_client.get.assert_called_with("/v2/zoom/meetings/91309581319")

    @pytest.mark.asyncio
    async def test_create_meeting(self, pis_client):
        """create_meeting → POST /v2/zoom/meetings"""
        pis_client.post = AsyncMock(return_value={"id": 99999, "topic": "New Meeting"})
        connector = PISMeetingConnector(pis_client)

        meeting_data = {
            "topic": "New Meeting",
            "start_time": "2026-04-01T10:00:00Z",
            "duration": 60,
            "project_id": "aaif-project-123",
        }
        result = await connector.create_meeting(meeting_data)
        assert result["id"] == 99999
        pis_client.post.assert_called_with("/v2/zoom/meetings", json_body=meeting_data)

    @pytest.mark.asyncio
    async def test_update_meeting(self, pis_client):
        """update_meeting → PUT /v2/zoom/meetings/{id}"""
        pis_client.put = AsyncMock(return_value={"status": "updated"})
        connector = PISMeetingConnector(pis_client)

        result = await connector.update_meeting(91309581319, {"duration": 90})
        assert result["status"] == "updated"

    @pytest.mark.asyncio
    async def test_get_meeting_count(self, pis_client):
        """get_meeting_count → GET /v2/zoom/meeting_count"""
        pis_client.get = AsyncMock(return_value={"count": 15})
        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")

        count = await connector.get_meeting_count()
        assert count == 15


class TestRegistrantManagement:
    """Tests for registrant CRUD (calendar invite provisioning).

    Maps to:
        GET    /v2/zoom/meetings/{id}/registrants
        POST   /v2/zoom/meetings/{id}/registrants
        GET    /v2/zoom/meetings/{id}/registrants/{rid}
        DELETE /v2/zoom/meetings/{id}/registrants/{rid}
    """

    @pytest.mark.asyncio
    async def test_list_registrants(self, pis_client, mock_registrants):
        """list_registrants → GET /v2/zoom/meetings/{id}/registrants"""
        pis_client.get_paginated = AsyncMock(return_value=mock_registrants)
        connector = PISMeetingConnector(pis_client)

        result = await connector.list_registrants(91309581319)
        assert len(result) == 2
        assert result[0]["email"] == "t.yamada@hitachi.com"

    @pytest.mark.asyncio
    async def test_add_registrant(self, pis_client):
        """add_registrant → POST /v2/zoom/meetings/{id}/registrants"""
        pis_client.post = AsyncMock(return_value={
            "id": "reg-new",
            "join_url": "https://zoom.us/j/test?tk=new-token",
        })
        connector = PISMeetingConnector(pis_client)

        result = await connector.add_registrant(
            meeting_id=91309581319,
            email="new.user@example.com",
            first_name="New",
            last_name="User",
        )
        assert result["status"] == "added"
        assert result["registrant_id"] == "reg-new"
        assert result["mode"] == "pis_live"

        # Verify request body
        call_body = pis_client.post.call_args[1]["json_body"]
        assert call_body["email"] == "new.user@example.com"
        assert call_body["first_name"] == "New"
        assert call_body["host"] is False

    @pytest.mark.asyncio
    async def test_add_registrant_already_registered(self, pis_client):
        """409 Conflict → already_registered."""
        response = httpx.Response(409, request=httpx.Request("POST", "http://test"))
        pis_client.post = AsyncMock(side_effect=httpx.HTTPStatusError("", request=response.request, response=response))
        connector = PISMeetingConnector(pis_client)

        result = await connector.add_registrant(91309581319, "existing@test.com")
        assert result["status"] == "already_registered"

    @pytest.mark.asyncio
    async def test_add_registrant_with_occurrences(self, pis_client):
        """Adding to specific occurrences only."""
        pis_client.post = AsyncMock(return_value={"id": "reg-occ"})
        connector = PISMeetingConnector(pis_client)

        await connector.add_registrant(
            meeting_id=91309581319,
            email="occ@test.com",
            occurrence_ids=["17105220000", "17108130000"],
        )
        call_body = pis_client.post.call_args[1]["json_body"]
        assert call_body["occurrence_ids"] == ["17105220000", "17108130000"]

    @pytest.mark.asyncio
    async def test_get_registrant(self, pis_client):
        """get_registrant → GET /v2/zoom/meetings/{id}/registrants/{rid}"""
        pis_client.get = AsyncMock(return_value={"id": "reg-001", "email": "t.yamada@hitachi.com"})
        connector = PISMeetingConnector(pis_client)

        result = await connector.get_registrant(91309581319, "reg-001")
        assert result["email"] == "t.yamada@hitachi.com"

    @pytest.mark.asyncio
    async def test_remove_registrant(self, pis_client):
        """remove_registrant → DELETE /v2/zoom/meetings/{id}/registrants/{rid}"""
        pis_client.delete = AsyncMock(return_value={"status": "deleted"})
        connector = PISMeetingConnector(pis_client)

        result = await connector.remove_registrant(91309581319, "reg-001")
        assert result["status"] == "removed"
        assert result["mode"] == "pis_live"

    @pytest.mark.asyncio
    async def test_remove_registrant_not_found(self, pis_client):
        """404 on remove → not_registered."""
        response = httpx.Response(404, request=httpx.Request("DELETE", "http://test"))
        pis_client.delete = AsyncMock(side_effect=httpx.HTTPStatusError("", request=response.request, response=response))
        connector = PISMeetingConnector(pis_client)

        result = await connector.remove_registrant(91309581319, "reg-gone")
        assert result["status"] == "not_registered"

    @pytest.mark.asyncio
    async def test_find_registrant_by_email(self, pis_client, mock_registrants):
        """find_registrant_by_email — list then filter."""
        pis_client.get_paginated = AsyncMock(return_value=mock_registrants)
        connector = PISMeetingConnector(pis_client)

        result = await connector.find_registrant_by_email(91309581319, "j.smith@acme.com")
        assert result is not None
        assert result["id"] == "reg-002"

    @pytest.mark.asyncio
    async def test_find_registrant_by_email_not_found(self, pis_client, mock_registrants):
        """Email not in registrant list → None."""
        pis_client.get_paginated = AsyncMock(return_value=mock_registrants)
        connector = PISMeetingConnector(pis_client)

        result = await connector.find_registrant_by_email(91309581319, "nobody@test.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_registrant_by_email(self, pis_client, mock_registrants):
        """Two-step: find by email → delete by registrant ID."""
        pis_client.get_paginated = AsyncMock(return_value=mock_registrants)
        pis_client.delete = AsyncMock(return_value={"status": "deleted"})
        connector = PISMeetingConnector(pis_client)

        result = await connector.remove_registrant_by_email(91309581319, "t.yamada@hitachi.com")
        assert result["status"] == "removed"
        pis_client.delete.assert_called_with("/v2/zoom/meetings/91309581319/registrants/reg-001")


class TestBulkAndSync:
    """Tests for bulk registrant operations and mailing list sync.

    Maps to:
        POST /v2/zoom/meetings/{id}/bulk_registrants
        POST /v2/zoom/meetings/{id}/mailinglists
    """

    @pytest.mark.asyncio
    async def test_bulk_add_registrants(self, pis_client):
        """bulk_add_registrants → POST /v2/zoom/meetings/{id}/bulk_registrants"""
        pis_client.post = AsyncMock(return_value={"imported": 3, "errors": 0})
        connector = PISMeetingConnector(pis_client)

        registrants = [
            {"email": "a@test.com", "first_name": "A", "last_name": "Test"},
            {"email": "b@test.com", "first_name": "B", "last_name": "Test"},
            {"email": "c@test.com", "first_name": "C", "last_name": "Test"},
        ]
        result = await connector.bulk_add_registrants(91309581319, registrants)
        assert result["status"] == "accepted"
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_sync_mailing_list(self, pis_client):
        """sync_mailing_list → POST /v2/zoom/meetings/{id}/mailinglists"""
        pis_client.post = AsyncMock(return_value={"synced": 15})
        connector = PISMeetingConnector(pis_client)

        result = await connector.sync_mailing_list(91309581319, [101, 102])
        assert result["status"] == "accepted"
        assert result["subgroup_ids"] == [101, 102]

        call_body = pis_client.post.call_args[1]["json_body"]
        assert call_body["subgroup_ids"] == [101, 102]


class TestMeetingLinks:
    """Tests for join links, LFX user lookup, and attendance.

    Maps to:
        GET /v2/zoom/meetings/{id}/join_link
        GET /v2/zoom/meetings/{id}/lfxuser/{user_id}
        GET /v2/zoom/meetings/{id}/participants
        GET /v2/zoom/meetings/{id}/past
    """

    @pytest.mark.asyncio
    async def test_get_join_link(self, pis_client):
        """get_join_link → GET /v2/zoom/meetings/{id}/join_link"""
        pis_client.get = AsyncMock(return_value={"join_url": "https://zoom.us/j/test?tk=abc"})
        connector = PISMeetingConnector(pis_client)

        result = await connector.get_join_link(91309581319, email="t.yamada@hitachi.com")
        assert "join_url" in result

    @pytest.mark.asyncio
    async def test_get_registrant_by_lfx_user(self, pis_client):
        """get_registrant_by_lfx_user → GET /v2/zoom/meetings/{id}/lfxuser/{uid}"""
        pis_client.get = AsyncMock(return_value={"id": "reg-001", "email": "t.yamada@hitachi.com"})
        connector = PISMeetingConnector(pis_client)

        result = await connector.get_registrant_by_lfx_user(91309581319, "uid-yamada")
        assert result["email"] == "t.yamada@hitachi.com"

    @pytest.mark.asyncio
    async def test_get_registrant_by_lfx_user_not_found(self, pis_client):
        """LFX user not registered → 404."""
        response = httpx.Response(404, request=httpx.Request("GET", "http://test"))
        pis_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("", request=response.request, response=response))
        connector = PISMeetingConnector(pis_client)

        result = await connector.get_registrant_by_lfx_user(91309581319, "uid-nobody")
        assert result["status"] == "not_registered"

    @pytest.mark.asyncio
    async def test_get_past_participants(self, pis_client):
        """get_past_participants → GET /v2/zoom/meetings/{id}/participants"""
        pis_client.get = AsyncMock(return_value={"total_records": 25, "participants": []})
        connector = PISMeetingConnector(pis_client)

        result = await connector.get_past_participants(91309581319)
        assert result["total_records"] == 25

    @pytest.mark.asyncio
    async def test_get_past_occurrences(self, pis_client):
        """get_past_occurrences → GET /v2/zoom/meetings/{id}/past"""
        pis_client.get = AsyncMock(return_value=[
            {"occurrence_id": "occ-1", "start_time": "2026-02-15T17:00:00Z"},
            {"occurrence_id": "occ-2", "start_time": "2026-01-15T17:00:00Z"},
        ])
        connector = PISMeetingConnector(pis_client)

        result = await connector.get_past_occurrences(91309581319)
        assert len(result) == 2


class TestHighLevelOperations:
    """Tests for MCP-tool-facing methods.

    These test the orchestration methods that map to our MCP tools:
    - provision_calendar_invites → tool_provision_calendar_invites
    - remove_from_all_meetings → offboarding
    - get_contact_meetings → tool_get_upcoming_meetings
    """

    @pytest.mark.asyncio
    async def test_provision_calendar_invites_all(self, pis_client, mock_meetings):
        """Provision to all project meetings when no committee filter."""
        pis_client.get_paginated = AsyncMock(return_value=mock_meetings)
        pis_client.post = AsyncMock(return_value={"id": "reg-new", "join_url": "https://zoom.us/test"})

        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")
        await connector.initialize()

        results = await connector.provision_calendar_invites(
            contact_email="new@example.com",
            contact_first_name="New",
            contact_last_name="User",
        )
        # Should add to all 3 meetings
        assert len(results) == 3
        assert all(r["status"] == "added" for r in results)

    @pytest.mark.asyncio
    async def test_provision_calendar_invites_by_committee(self, pis_client, mock_meetings):
        """Provision only to meetings matching specified committees."""
        pis_client.get_paginated = AsyncMock(return_value=mock_meetings)
        pis_client.post = AsyncMock(return_value={"id": "reg-new", "join_url": "https://zoom.us/test"})

        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")
        await connector.initialize()

        results = await connector.provision_calendar_invites(
            contact_email="wg-member@example.com",
            committee_ids=["wg-agentic-commerce"],
        )
        # Only 1 meeting for this WG
        assert len(results) == 1
        assert results[0]["committee_id"] == "wg-agentic-commerce"

    @pytest.mark.asyncio
    async def test_remove_from_all_meetings(self, pis_client, mock_meetings, mock_registrants):
        """Offboarding: remove contact from all project meetings."""
        pis_client.get_paginated = AsyncMock(side_effect=[
            mock_meetings,  # initialize cache
            mock_registrants,  # find registrant in meeting 1
            [],  # no registrant in meeting 2
            [],  # no registrant in meeting 3
        ])
        pis_client.delete = AsyncMock(return_value={"status": "deleted"})

        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")
        await connector.initialize()

        results = await connector.remove_from_all_meetings("t.yamada@hitachi.com")
        assert len(results) == 3
        # First meeting should have removed
        assert results[0]["status"] == "removed"
        # Others should be not_registered
        assert results[1]["status"] == "not_registered"

    @pytest.mark.asyncio
    async def test_get_contact_meetings(self, pis_client, mock_meetings, mock_registrants):
        """Get all meetings a contact is registered for."""
        pis_client.get_paginated = AsyncMock(side_effect=[
            mock_meetings,  # initialize cache
            mock_registrants,  # meeting 1 — yamada is there
            [],  # meeting 2 — not there
            mock_registrants,  # meeting 3 — yamada is there
        ])

        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")
        await connector.initialize()

        result = await connector.get_contact_meetings("t.yamada@hitachi.com")
        assert len(result) == 2
        assert all("meeting_id" in m for m in result)


class TestHealthCheck:
    """Tests for meeting connector health check."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, pis_client, mock_meetings):
        """Health check reports connector details."""
        pis_client.health_check = AsyncMock(return_value={
            "connector": "pis", "status": "healthy", "mode": "live",
        })
        pis_client.get_paginated = AsyncMock(return_value=mock_meetings)

        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")
        await connector.initialize()

        result = await connector.health_check()
        assert result["connector"] == "pis_meeting"
        assert result["cached_meetings"] == 3
        assert result["cached_committees"] == 2


class TestRegistryIntegration:
    """Tests for registry wiring of PIS Meeting connector."""

    @pytest.mark.asyncio
    async def test_pis_meeting_none_when_not_configured(self):
        """get_pis_meeting() returns None when PIS not configured."""
        with patch.dict("os.environ", {}, clear=True):
            from aaif_mcp_server.connectors import registry
            registry._initialized = True
            registry._pis_meeting = None
            result = registry.get_pis_meeting()
            assert result is None
            registry._initialized = False

    @pytest.mark.asyncio
    async def test_pis_meeting_available_when_configured(self, pis_client, mock_meetings):
        """get_pis_meeting() returns connector when PIS configured."""
        pis_client.get_paginated = AsyncMock(return_value=mock_meetings)
        connector = PISMeetingConnector(pis_client, project_id="aaif-project-123")
        await connector.initialize()

        from aaif_mcp_server.connectors import registry
        registry._initialized = True
        registry._pis_meeting = connector
        result = registry.get_pis_meeting()
        assert result is not None
        assert isinstance(result, PISMeetingConnector)
        registry._initialized = False
        registry._pis_meeting = None
