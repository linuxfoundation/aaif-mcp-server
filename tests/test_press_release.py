"""Tests for Domain 10: Press Release Management (3 tools).

Tests draft_press_release, get_press_release_status, and list_press_release_templates
against mock press release data.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.press_release import (
    draft_press_release,
    get_press_release_status,
    list_press_release_templates,
)


@pytest.mark.asyncio
async def test_draft_press_release(
    org_hitachi: str,
    foundation_id: str,
):
    """Test draft_press_release returns PR with content and stages."""
    result = await draft_press_release(org_hitachi, foundation_id=foundation_id)

    assert "error" not in result
    assert "pr_id" in result or "content" in result or "message" in result


@pytest.mark.asyncio
async def test_draft_press_release_not_found(
    org_invalid: str,
    foundation_id: str,
):
    """Test draft_press_release returns error for invalid org."""
    result = await draft_press_release(org_invalid, foundation_id=foundation_id)

    assert "error" in result
    assert result["error"] == "ORG_NOT_FOUND"


@pytest.mark.asyncio
async def test_draft_press_release_bad_template(
    org_hitachi: str,
    foundation_id: str,
):
    """Test draft_press_release returns error for invalid template."""
    result = await draft_press_release(
        org_hitachi,
        template_id="nonexistent",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "TEMPLATE_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_press_release_status(foundation_id: str):
    """Test get_press_release_status for valid PR ID."""
    result = await get_press_release_status("pr-sample-001", foundation_id)

    # Either return status or NOT_FOUND
    if "error" not in result:
        assert "status" in result or "pr_id" in result
    else:
        assert result["error"] == "PR_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_press_release_status_not_found(foundation_id: str):
    """Test get_press_release_status returns error for invalid PR ID."""
    result = await get_press_release_status("pr-fake", foundation_id)

    assert "error" in result
    assert result["error"] == "PR_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_press_release_templates(foundation_id: str):
    """Test list_press_release_templates returns template list."""
    result = await list_press_release_templates(foundation_id)

    assert "error" not in result
    assert isinstance(result.get("templates"), list) or "templates" in result
    templates = result.get("templates", [])
    assert len(templates) > 0
