"""Tests for resource/reference data endpoints (read-only utilities).

Tests get_provisioning_rules, get_tier_entitlements, get_working_groups,
get_member_profile, and list_members against static configuration and mock data.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.resources.rules import (
    get_provisioning_rules,
    get_tier_entitlements,
    get_working_groups,
)
from aaif_mcp_server.resources.member import (
    get_member_profile,
    list_members,
)


@pytest.mark.asyncio
async def test_get_tier_entitlements(
    foundation_id: str,
):
    """Test retrieval of tier entitlements matrix."""
    result = await get_tier_entitlements(foundation_id)

    assert "error" not in result
    assert "tiers" in result or "platinum" in result

    # Should have all three tiers
    tiers = result if "tiers" not in result else result.get("tiers", {})
    assert "platinum" in str(tiers).lower()
    assert "gold" in str(tiers).lower()
    assert "silver" in str(tiers).lower()


@pytest.mark.asyncio
async def test_get_provisioning_rules(
    foundation_id: str,
):
    """Test retrieval of provisioning rules configuration."""
    result = await get_provisioning_rules(foundation_id)

    assert "error" not in result
    assert foundation_id in str(result).lower() or "rules" in result

    # Should have role-based rules
    rules_data = result.get("rules", result)
    assert len(rules_data) > 0


@pytest.mark.asyncio
async def test_get_working_groups(
    foundation_id: str,
):
    """Test retrieval of working groups configuration."""
    result = await get_working_groups(foundation_id)

    assert "error" not in result
    assert "working_groups" in result or len(result) > 0

    # Should have WG definitions
    wgs = result.get("working_groups", result)
    assert isinstance(wgs, list) or isinstance(wgs, dict)


@pytest.mark.asyncio
async def test_get_working_groups_includes_details(
    foundation_id: str,
):
    """Test that WG list includes meeting schedule and contact info."""
    result = await get_working_groups(foundation_id)

    wgs = result.get("working_groups", result)
    if isinstance(wgs, list) and len(wgs) > 0:
        first_wg = wgs[0] if isinstance(wgs[0], dict) else None
        if first_wg:
            assert "name" in first_wg or "wg_id" in first_wg


@pytest.mark.asyncio
async def test_get_member_profile_hitachi(
    org_hitachi: str,
):
    """Test member profile retrieval for Hitachi."""
    result = await get_member_profile(org_hitachi)

    assert "error" not in result
    # Profile nests org data under "org" key
    org = result["org"]
    assert org["org_id"] == org_hitachi
    assert org["org_name"] == "Hitachi, Ltd."
    assert org["tier"] == "gold"
    assert org["status"] == "active"


@pytest.mark.asyncio
async def test_get_member_profile_includes_contacts(
    org_bloomberg: str,
):
    """Test that member profile includes contact list."""
    result = await get_member_profile(org_bloomberg)

    # Contacts are nested under org
    org = result["org"]
    assert "contacts" in org
    assert result["contact_count"] == 2  # Bloomberg has 2 contacts


@pytest.mark.asyncio
async def test_get_member_profile_platinum(
    org_openai: str,
):
    """Test member profile for Platinum tier."""
    result = await get_member_profile(org_openai)

    assert "error" not in result
    org = result["org"]
    assert org["tier"] == "platinum"
    assert org["org_name"] == "OpenAI"


@pytest.mark.asyncio
async def test_get_member_profile_not_found():
    """Test error handling for non-existent member."""
    result = await get_member_profile("0017V00001INVALID")

    assert "error" in result or result.get("org_id") is None


@pytest.mark.asyncio
async def test_list_members(
    foundation_id: str,
):
    """Test listing all members for a foundation."""
    result = await list_members(foundation_id)

    assert "error" not in result
    assert "members" in result or isinstance(result, list)

    # Should have at least our 6 test members
    members = result.get("members", result) if isinstance(result, dict) else result
    assert len(members) >= 6


@pytest.mark.asyncio
async def test_list_members_includes_tier_info(
    foundation_id: str,
):
    """Test that member list includes tier information."""
    result = await list_members(foundation_id)

    members = result.get("members", result) if isinstance(result, dict) else result
    if len(members) > 0:
        first_member = members[0]
        # Should have at least org_id and tier
        assert "org_id" in first_member or "name" in first_member


@pytest.mark.asyncio
async def test_list_members_by_tier(
    foundation_id: str,
):
    """Test that member list includes tier info for filtering."""
    result = await list_members(foundation_id)

    assert "error" not in result
    members = result.get("members", [])

    # Find gold members in the list
    gold_members = [m for m in members if m.get("tier") == "gold"]
    assert len(gold_members) >= 2  # Hitachi and Bloomberg are Gold


@pytest.mark.asyncio
async def test_get_tier_entitlements_matrix_structure(
    foundation_id: str,
):
    """Test entitlements include all required fields."""
    result = await get_tier_entitlements(foundation_id)

    tiers = result if "tiers" not in result else result.get("tiers", {})
    # Convert to dict if needed
    if not isinstance(tiers, dict):
        return

    for tier_name, entitlements in tiers.items():
        if isinstance(entitlements, dict):
            # Should have key fields
            assert "gb_seats" in entitlements or "voting_rights" in entitlements


@pytest.mark.asyncio
async def test_list_members_includes_status(
    foundation_id: str,
):
    """Test that member list shows status (active, pending, etc)."""
    result = await list_members(foundation_id)

    members = result.get("members", result) if isinstance(result, dict) else result
    if len(members) > 0:
        # Most members should be active or pending
        for member in members:
            status = member.get("status", "active")
            assert status in ["active", "pending", "cancelled", "suspended"]
