"""Tests for Domain 5: Contact Role Management (5 tools).

Tests list_contacts, add_contact, update_contact_role, remove_contact,
and transfer_voting_rights against mock member data.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.contact_roles import (
    list_contacts,
    add_contact,
    update_contact_role,
    remove_contact,
    transfer_voting_rights,
)


@pytest.mark.asyncio
async def test_list_contacts_hitachi(
    org_hitachi: str,
    foundation_id: str,
):
    """Test list_contacts returns contacts with roles for valid org."""
    result = await list_contacts(org_hitachi, foundation_id)

    assert "error" not in result
    assert result["org_id"] == org_hitachi
    assert result["org_name"] == "Hitachi, Ltd."
    assert result["tier"] == "gold"
    assert "contacts" in result
    assert result["total_contacts"] > 0

    # Check structure of contacts
    for contact in result["contacts"]:
        assert "contact_id" in contact
        assert "name" in contact
        assert "email" in contact
        assert "role" in contact


@pytest.mark.asyncio
async def test_list_contacts_not_found(
    org_invalid: str,
    foundation_id: str,
):
    """Test list_contacts returns error for invalid org."""
    result = await list_contacts(org_invalid, foundation_id)

    assert "error" in result
    assert result["error"] == "ORG_NOT_FOUND"


@pytest.mark.asyncio
async def test_add_contact_dry_run(
    org_hitachi: str,
    foundation_id: str,
):
    """Test add_contact with dry_run=True does not persist."""
    result = await add_contact(
        org_hitachi,
        "Test User",
        "testuser@example.com",
        "technical_contact",
        dry_run=True,
        foundation_id=foundation_id,
    )

    assert "error" not in result
    assert "dry_run" in result or "message" in result


@pytest.mark.asyncio
async def test_add_contact_invalid_role(
    org_hitachi: str,
    foundation_id: str,
):
    """Test add_contact returns error for invalid role."""
    result = await add_contact(
        org_hitachi,
        "Test",
        "test@example.com",
        "invalid_role",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "INVALID_ROLE"


@pytest.mark.asyncio
async def test_add_contact_duplicate(
    org_hitachi: str,
    email_hitachi_yamada: str,
    foundation_id: str,
):
    """Test add_contact returns error when contact email already exists."""
    result = await add_contact(
        org_hitachi,
        "Duplicate",
        email_hitachi_yamada,
        "voting_contact",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "CONTACT_EXISTS"


@pytest.mark.asyncio
async def test_update_contact_role_dry_run(
    org_hitachi: str,
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test update_contact_role with dry_run=True."""
    result = await update_contact_role(
        org_hitachi,
        contact_hitachi_c001,
        "technical_contact",
        dry_run=True,
        foundation_id=foundation_id,
    )

    assert "error" not in result


@pytest.mark.asyncio
async def test_update_contact_role_not_found(
    org_hitachi: str,
    foundation_id: str,
):
    """Test update_contact_role returns error for non-existent contact."""
    result = await update_contact_role(
        org_hitachi,
        "C999",
        "technical_contact",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "CONTACT_NOT_FOUND"


@pytest.mark.asyncio
async def test_remove_contact_dry_run(
    org_hitachi: str,
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test remove_contact with dry_run=True."""
    result = await remove_contact(
        org_hitachi,
        contact_hitachi_c001,
        dry_run=True,
        foundation_id=foundation_id,
    )

    assert "error" not in result


@pytest.mark.asyncio
async def test_transfer_voting_rights_dry_run(
    org_hitachi: str,
    contact_hitachi_c001: str,
    contact_hitachi_c002: str,
    foundation_id: str,
):
    """Test transfer_voting_rights with dry_run=True."""
    result = await transfer_voting_rights(
        org_hitachi,
        contact_hitachi_c001,
        contact_hitachi_c002,
        dry_run=True,
        foundation_id=foundation_id,
    )

    assert "error" not in result


@pytest.mark.asyncio
async def test_transfer_voting_rights_not_voting(
    org_hitachi: str,
    contact_hitachi_c002: str,
    foundation_id: str,
):
    """Test transfer_voting_rights returns error when source contact is not voting."""
    result = await transfer_voting_rights(
        org_hitachi,
        contact_hitachi_c002,
        contact_hitachi_c002,
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "NOT_VOTING_CONTACT"


@pytest.mark.asyncio
async def test_transfer_voting_rights_silver_tier(
    org_natoma: str,
    contact_natoma_c005: str,
    foundation_id: str,
):
    """Test transfer_voting_rights fails for Silver tier (no voting rights)."""
    result = await transfer_voting_rights(
        org_natoma,
        contact_natoma_c005,
        contact_natoma_c005,
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "NOT_VOTING_CONTACT"
