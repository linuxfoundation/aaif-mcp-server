"""Tests for Domain 7: Working Group Enrollment (5 tools).

Tests enroll_in_working_group, leave_working_group, list_available_working_groups,
get_wg_members, and check_wg_eligibility against mock WG data.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.wg_enrollment import (
    enroll_in_working_group,
    leave_working_group,
    list_available_working_groups,
    get_wg_members,
    check_wg_eligibility,
)


@pytest.mark.asyncio
async def test_enroll_in_wg_dry_run(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test enroll_in_working_group with dry_run=True."""
    result = await enroll_in_working_group(
        contact_hitachi_c001,
        "wg-agentic-commerce",
        dry_run=True,
        foundation_id=foundation_id,
    )

    assert "error" not in result


@pytest.mark.asyncio
async def test_enroll_in_wg_contact_not_found(foundation_id: str):
    """Test enroll_in_working_group returns error for invalid contact."""
    result = await enroll_in_working_group(
        "C999",
        "wg-agentic-commerce",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "CONTACT_NOT_FOUND"


@pytest.mark.asyncio
async def test_enroll_in_wg_wg_not_found(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test enroll_in_working_group returns error for invalid WG."""
    result = await enroll_in_working_group(
        contact_hitachi_c001,
        "wg-nonexistent",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "WG_NOT_FOUND"


@pytest.mark.asyncio
async def test_leave_wg_dry_run(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test leave_working_group with dry_run=True."""
    result = await leave_working_group(
        contact_hitachi_c001,
        "wg-agentic-commerce",
        dry_run=True,
        foundation_id=foundation_id,
    )

    assert "error" not in result


@pytest.mark.asyncio
async def test_list_available_wgs(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test list_available_working_groups returns list of WGs."""
    result = await list_available_working_groups(contact_hitachi_c001, foundation_id)

    assert "error" not in result
    assert isinstance(result.get("available_working_groups"), list) or "available_working_groups" in result


@pytest.mark.asyncio
async def test_list_available_wgs_not_found(foundation_id: str):
    """Test list_available_working_groups returns error for invalid contact."""
    result = await list_available_working_groups("C999", foundation_id)

    assert "error" in result
    assert result["error"] == "CONTACT_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_wg_members(foundation_id: str):
    """Test get_wg_members returns member list."""
    result = await get_wg_members("wg-agentic-commerce", foundation_id)

    assert "error" not in result
    assert isinstance(result.get("members"), list) or "members" in result


@pytest.mark.asyncio
async def test_get_wg_members_not_found(foundation_id: str):
    """Test get_wg_members returns error for non-existent WG."""
    result = await get_wg_members("wg-nonexistent", foundation_id)

    assert "error" in result
    assert result["error"] == "WG_NOT_FOUND"


@pytest.mark.asyncio
async def test_check_wg_eligibility(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test check_wg_eligibility for valid contact and WG."""
    result = await check_wg_eligibility(
        contact_hitachi_c001,
        "wg-agentic-commerce",
        foundation_id,
    )

    assert "error" not in result
    assert "eligible" in result or "eligibility" in result


@pytest.mark.asyncio
async def test_check_wg_eligibility_contact_not_found(foundation_id: str):
    """Test check_wg_eligibility returns error for invalid contact."""
    result = await check_wg_eligibility(
        "C999",
        "wg-agentic-commerce",
        foundation_id,
    )

    assert "error" in result
    assert result["error"] == "CONTACT_NOT_FOUND"
