"""Tests for MCP tool-level PIS Meeting integration.

Verifies that calendar.py, orchestrator.py, and wg_enrollment.py
correctly route to PISMeetingConnector when PIS is configured,
and fall back to mock/GoogleCalendar when not.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_sfdc():
    """Mock SFDC connector returning a Gold org with one contact."""
    connector = AsyncMock()

    # Build mock org
    contact = MagicMock()
    contact.contact_id = "C001"
    contact.name = "Kenji Tanaka"
    contact.email = "kenji@hitachi.test"
    contact.role = MagicMock()
    contact.role.value = "voting_contact"
    contact.discord_handle = "kenji#1234"
    contact.github_username = "kenji-tanaka"

    org = MagicMock()
    org.org_id = "ORG001"
    org.org_name = "Hitachi"
    org.tier = MagicMock()
    org.tier.value = "gold"
    org.status = "active"
    org.contacts = [contact]

    connector.get_org.return_value = org
    connector.list_orgs.return_value = [org]
    return connector


@pytest.fixture
def mock_pis_meeting():
    """Mock PISMeetingConnector for tool-level tests."""
    connector = AsyncMock()

    # provision_calendar_invites returns list of results
    connector.provision_calendar_invites.return_value = [
        {"meeting_id": "111", "topic": "AAIF All-Hands", "status": "registered"},
        {"meeting_id": "222", "topic": "WG Agentic Commerce", "status": "registered"},
    ]

    # get_contact_meetings returns meetings where contact is registered
    connector.get_contact_meetings.return_value = {
        "email": "kenji@hitachi.test",
        "meetings": [
            {"meeting_id": "111", "topic": "AAIF All-Hands", "status": "registered"},
        ],
    }

    # remove_from_all_meetings returns removal results
    connector.remove_from_all_meetings.return_value = [
        {"meeting_id": "111", "topic": "AAIF All-Hands", "status": "removed"},
    ]

    # list_meetings returns project meetings
    connector.list_meetings.return_value = [
        {"meeting_id": "111", "topic": "AAIF All-Hands", "committee_id": ""},
        {"meeting_id": "222", "topic": "WG Agentic Commerce", "committee_id": "wg-agentic-commerce"},
    ]

    # get_join_link returns a URL
    connector.get_join_link.return_value = {"join_url": "https://zoom.us/j/111"}

    # update_meeting returns success
    connector.update_meeting.return_value = {"id": "222", "status": "updated"}

    return connector


@pytest.fixture
def mock_calendar():
    """Mock GoogleCalendar connector."""
    connector = AsyncMock()
    connector.send_invite.return_value = {"status": "sent", "event_id": "evt-mock-001"}
    return connector


# ── Tests: provision_calendar_invites ─────────────────────────────

@pytest.mark.asyncio
async def test_provision_uses_pis_when_configured(mock_sfdc, mock_pis_meeting):
    """When PIS is configured, provision uses PISMeetingConnector."""
    with patch("aaif_mcp_server.tools.calendar.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.calendar.get_pis_meeting", return_value=mock_pis_meeting), \
         patch("aaif_mcp_server.config.MOCK_WG_ENROLLMENTS", {"C001": ["wg-agentic-commerce"]}):
        from aaif_mcp_server.tools.calendar import provision_calendar_invites
        result = await provision_calendar_invites("ORG001", "C001", dry_run=False)

    assert result["source"] == "pis_meeting_v2"
    assert len(result["actions"]) == 2
    mock_pis_meeting.provision_calendar_invites.assert_called_once()


@pytest.mark.asyncio
async def test_provision_dry_run_pis(mock_sfdc, mock_pis_meeting):
    """Dry run with PIS queries meetings without adding registrants."""
    with patch("aaif_mcp_server.tools.calendar.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.calendar.get_pis_meeting", return_value=mock_pis_meeting), \
         patch("aaif_mcp_server.config.MOCK_WG_ENROLLMENTS", {"C001": ["wg-agentic-commerce"]}):
        from aaif_mcp_server.tools.calendar import provision_calendar_invites
        result = await provision_calendar_invites("ORG001", "C001", dry_run=True)

    assert result["dry_run"] is True
    assert result["source"] == "pis_meeting_v2"
    # Should NOT have called the actual provision method
    mock_pis_meeting.provision_calendar_invites.assert_not_called()
    # Should have queried for existing registrations
    mock_pis_meeting.get_contact_meetings.assert_called_once()


@pytest.mark.asyncio
async def test_provision_falls_back_to_mock(mock_sfdc, mock_calendar):
    """When PIS is not configured, falls back to mock calendar rules."""
    mock_rules = {"aaif": {"gold_voting_contact": ["AAIF All-Hands", "Board Meeting"]}}

    with patch("aaif_mcp_server.tools.calendar.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.calendar.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.calendar.get_calendar", return_value=mock_calendar), \
         patch("aaif_mcp_server.tools.calendar.MOCK_CALENDAR_RULES", mock_rules):
        from aaif_mcp_server.tools.calendar import provision_calendar_invites
        result = await provision_calendar_invites("ORG001", "C001", dry_run=False)

    assert result["source"] == "mock_calendar"
    assert len(result["actions"]) == 2
    assert mock_calendar.send_invite.call_count == 2


@pytest.mark.asyncio
async def test_provision_contact_not_found(mock_sfdc, mock_pis_meeting):
    """Returns error when contact not found."""
    with patch("aaif_mcp_server.tools.calendar.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.calendar.get_pis_meeting", return_value=mock_pis_meeting):
        from aaif_mcp_server.tools.calendar import provision_calendar_invites
        result = await provision_calendar_invites("ORG001", "C999", dry_run=True)

    assert result["error"] == "CONTACT_NOT_FOUND"


# ── Tests: get_upcoming_meetings ──────────────────────────────────

@pytest.mark.asyncio
async def test_upcoming_meetings_uses_pis(mock_sfdc, mock_pis_meeting):
    """When PIS is configured, queries LFX Meeting V2 for registrant status."""
    mock_members = {"ORG001": mock_sfdc.get_org.return_value}

    with patch("aaif_mcp_server.tools.calendar.get_pis_meeting", return_value=mock_pis_meeting), \
         patch("aaif_mcp_server.config.MOCK_MEMBERS", mock_members):
        from aaif_mcp_server.tools.calendar import get_upcoming_meetings
        result = await get_upcoming_meetings("C001")

    assert result["source"] == "pis_meeting_v2"
    assert result["total"] == 1
    assert result["upcoming_meetings"][0]["join_link"] == "https://zoom.us/j/111"


@pytest.mark.asyncio
async def test_upcoming_meetings_falls_back_to_mock(mock_sfdc):
    """When PIS is not configured, uses mock calendar events."""
    mock_events = {"C001": [
        {"title": "AAIF All-Hands", "time": "2026-03-10T14:00:00Z"},
    ]}

    with patch("aaif_mcp_server.tools.calendar.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.calendar.MOCK_CALENDAR_EVENTS", mock_events):
        from aaif_mcp_server.tools.calendar import get_upcoming_meetings
        result = await get_upcoming_meetings("C001")

    assert result["source"] == "mock_calendar"
    assert result["total"] == 1


# ── Tests: update_meeting_schedule ────────────────────────────────

@pytest.mark.asyncio
async def test_update_schedule_uses_pis(mock_pis_meeting):
    """When PIS is configured, updates meetings via LFX Meeting V2 API."""
    from aaif_mcp_server.config import WorkingGroup, WgAccessPolicy
    mock_wgs = {"aaif": [WorkingGroup(
        wg_id="wg-agentic-commerce",
        name="Agentic Commerce",
        slug="agentic-commerce",
        meeting_schedule="Wed 10am PT",
        mailing_list="wg-agentic-commerce@lists.aaif.io",
        discord_channel="#wg-agentic-commerce",
        github_repo="aaif/wg-agentic-commerce",
        access_policy=WgAccessPolicy.any_member,
    )]}

    # list_meetings by committee_id
    mock_pis_meeting.list_meetings.return_value = [
        {"meeting_id": "222", "topic": "WG Agentic Commerce"},
    ]

    with patch("aaif_mcp_server.tools.calendar.get_pis_meeting", return_value=mock_pis_meeting), \
         patch("aaif_mcp_server.tools.calendar.WORKING_GROUPS", mock_wgs):
        from aaif_mcp_server.tools.calendar import update_meeting_schedule
        result = await update_meeting_schedule("wg-agentic-commerce", "Thu 11am PT", "https://zoom.us/new")

    assert result["source"] == "pis_meeting_v2"
    assert result["status"] == "updated"
    mock_pis_meeting.update_meeting.assert_called_once()


@pytest.mark.asyncio
async def test_update_schedule_falls_back(mock_calendar):
    """When PIS is not configured, returns config-only update."""
    from aaif_mcp_server.config import WorkingGroup, WgAccessPolicy
    mock_wgs = {"aaif": [WorkingGroup(
        wg_id="wg-agentic-commerce",
        name="Agentic Commerce",
        slug="agentic-commerce",
        meeting_schedule="Wed 10am PT",
        mailing_list="wg-agentic-commerce@lists.aaif.io",
        discord_channel="#wg-agentic-commerce",
        github_repo="aaif/wg-agentic-commerce",
        access_policy=WgAccessPolicy.any_member,
    )]}

    with patch("aaif_mcp_server.tools.calendar.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.calendar.WORKING_GROUPS", mock_wgs):
        from aaif_mcp_server.tools.calendar import update_meeting_schedule
        result = await update_meeting_schedule("wg-agentic-commerce", "Thu 11am PT", "https://zoom.us/new")

    assert result["source"] == "mock_calendar"


# ── Tests: offboarding with PIS Meeting ───────────────────────────

@pytest.mark.asyncio
async def test_offboarding_uses_pis_meeting(mock_sfdc, mock_pis_meeting):
    """Offboarding removes meeting registrants via PIS when configured."""
    mock_groupsio = AsyncMock()
    mock_groupsio.get_lists.return_value = ["general@lists.aaif.io"]
    mock_groupsio.is_member.return_value = True
    mock_groupsio.remove_member.return_value = {"status": "removed"}

    mock_github_conn = AsyncMock()
    mock_github_conn.remove_collaborator.return_value = {"status": "removed"}

    with patch("aaif_mcp_server.tools.orchestrator.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.orchestrator.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_meeting", return_value=mock_pis_meeting), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_github", return_value=mock_github_conn):
        from aaif_mcp_server.tools.orchestrator import run_offboarding_checklist
        result = await run_offboarding_checklist("ORG001", "kenji@hitachi.test", dry_run=False)

    # Should have meeting removal actions
    meeting_actions = [a for a in result["actions"] if a["step"] == "remove_meeting_registrant"]
    assert len(meeting_actions) == 1
    assert meeting_actions[0]["source"] == "pis_meeting_v2"
    assert meeting_actions[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_offboarding_dry_run_pis_meeting(mock_sfdc, mock_pis_meeting):
    """Offboarding dry run shows meeting removal actions via PIS."""
    mock_groupsio = AsyncMock()
    mock_groupsio.get_lists.return_value = ["general@lists.aaif.io"]
    mock_groupsio.is_member.return_value = True

    mock_github_conn = AsyncMock()

    with patch("aaif_mcp_server.tools.orchestrator.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.orchestrator.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_meeting", return_value=mock_pis_meeting), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_github", return_value=mock_github_conn):
        from aaif_mcp_server.tools.orchestrator import run_offboarding_checklist
        result = await run_offboarding_checklist("ORG001", "kenji@hitachi.test", dry_run=True)

    meeting_actions = [a for a in result["actions"] if a["step"] == "remove_meeting_registrant"]
    assert len(meeting_actions) == 1
    assert meeting_actions[0]["status"] == "dry_run"


@pytest.mark.asyncio
async def test_offboarding_manual_without_pis(mock_sfdc):
    """Without PIS, offboarding flags calendar removal as manual."""
    mock_groupsio = AsyncMock()
    mock_groupsio.get_lists.return_value = []

    mock_github_conn = AsyncMock()

    with patch("aaif_mcp_server.tools.orchestrator.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.orchestrator.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_github", return_value=mock_github_conn):
        from aaif_mcp_server.tools.orchestrator import run_offboarding_checklist
        result = await run_offboarding_checklist("ORG001", "kenji@hitachi.test", dry_run=True)

    manual_cal = [a for a in result["actions"] if a["step"] == "remove_calendar_invites"]
    assert len(manual_cal) == 1
    assert manual_cal[0]["status"] == "manual_required"


# ── Tests: WG enrollment with PIS Meeting ─────────────────────────

@pytest.mark.asyncio
async def test_wg_enroll_uses_pis_meeting(mock_sfdc, mock_pis_meeting):
    """WG enrollment uses PIS Meeting for calendar invites when configured."""
    from aaif_mcp_server.config import WorkingGroup, WgAccessPolicy
    mock_wgs = {"aaif": [WorkingGroup(
        wg_id="wg-agentic-commerce",
        name="Agentic Commerce",
        slug="agentic-commerce",
        meeting_schedule="Wed 10am PT",
        mailing_list="wg-agentic-commerce@lists.aaif.io",
        discord_channel="#wg-agentic-commerce",
        github_repo="aaif/wg-agentic-commerce",
        access_policy=WgAccessPolicy.any_member,
    )]}

    mock_groupsio = AsyncMock()
    mock_groupsio.add_member.return_value = {"status": "added"}
    mock_discord = AsyncMock()
    mock_discord.add_role.return_value = {"status": "added"}
    mock_github = AsyncMock()
    mock_github.add_collaborator.return_value = {"status": "added"}

    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_discord", return_value=mock_discord), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_github", return_value=mock_github), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=mock_pis_meeting), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs), \
         patch("aaif_mcp_server.tools.wg_enrollment.MOCK_WG_ENROLLMENTS", {}):
        from aaif_mcp_server.tools.wg_enrollment import enroll_in_working_group
        result = await enroll_in_working_group("C001", "wg-agentic-commerce", dry_run=False)

    assert result["meeting_source"] == "pis_meeting_v2"
    assert result["enrollment_results"]["meeting"]["source"] == "pis_meeting_v2"
    mock_pis_meeting.provision_calendar_invites.assert_called_once()


@pytest.mark.asyncio
async def test_wg_enroll_dry_run_pis(mock_sfdc, mock_pis_meeting):
    """WG enrollment dry run shows PIS meeting source."""
    from aaif_mcp_server.config import WorkingGroup, WgAccessPolicy
    mock_wgs = {"aaif": [WorkingGroup(
        wg_id="wg-agentic-commerce",
        name="Agentic Commerce",
        slug="agentic-commerce",
        meeting_schedule="Wed 10am PT",
        mailing_list="wg-agentic-commerce@lists.aaif.io",
        discord_channel="#wg-agentic-commerce",
        github_repo="aaif/wg-agentic-commerce",
        access_policy=WgAccessPolicy.any_member,
    )]}

    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=mock_pis_meeting), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs):
        from aaif_mcp_server.tools.wg_enrollment import enroll_in_working_group
        result = await enroll_in_working_group("C001", "wg-agentic-commerce", dry_run=True)

    assert result["meeting_source"] == "pis_meeting_v2"
    assert "LFX Meeting V2 API" in result["enrollment_actions"]["meeting"]
