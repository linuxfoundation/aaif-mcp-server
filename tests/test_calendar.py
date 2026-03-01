"""Tests for Domain 6: Calendar Management (3 tools).

Tests provision_calendar_invites, update_meeting_schedule, and get_upcoming_meetings
against mock calendar data.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.calendar import (
    provision_calendar_invites,
    update_meeting_schedule,
    get_upcoming_meetings,
)


@pytest.mark.asyncio
async def test_provision_calendar_invites_dry_run(
    org_hitachi: str,
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test provision_calendar_invites with dry_run=True."""
    result = await provision_calendar_invites(
        org_hitachi,
        contact_hitachi_c001,
        dry_run=True,
        foundation_id=foundation_id,
    )

    assert "error" not in result


@pytest.mark.asyncio
async def test_provision_calendar_invites_not_found(
    org_invalid: str,
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test provision_calendar_invites returns error for invalid org."""
    result = await provision_calendar_invites(
        org_invalid,
        contact_hitachi_c001,
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "ORG_NOT_FOUND"


@pytest.mark.asyncio
async def test_provision_calendar_invites_contact_not_found(
    org_hitachi: str,
    foundation_id: str,
):
    """Test provision_calendar_invites returns error for invalid contact."""
    result = await provision_calendar_invites(
        org_hitachi,
        "C999",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "CONTACT_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_meeting_schedule(foundation_id: str):
    """Test update_meeting_schedule for existing working group."""
    result = await update_meeting_schedule(
        "wg-agentic-commerce",
        "Thu 2pm PT",
        "https://zoom.us/new",
        foundation_id=foundation_id,
    )

    assert "error" not in result
    assert "wg_id" in result or "message" in result


@pytest.mark.asyncio
async def test_update_meeting_schedule_not_found(foundation_id: str):
    """Test update_meeting_schedule returns error for non-existent WG."""
    result = await update_meeting_schedule(
        "wg-nonexistent",
        "Thu 2pm PT",
        "https://zoom.us/new",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "WG_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_upcoming_meetings(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test get_upcoming_meetings returns list structure."""
    result = await get_upcoming_meetings(contact_hitachi_c001, foundation_id)

    assert "error" not in result
    assert isinstance(result.get("upcoming_meetings"), list) or "upcoming_meetings" in result
