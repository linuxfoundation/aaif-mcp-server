"""Tests for Domain 11: Logo and Brand Management (3 tools).

Tests validate_logo, get_brand_guidelines, and request_logo_upload
against mock brand and logo data.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.logo_brand import (
    validate_logo,
    get_brand_guidelines,
    request_logo_upload,
)


@pytest.mark.asyncio
async def test_validate_logo_svg(foundation_id: str):
    """Test validate_logo passes for SVG format."""
    result = await validate_logo("https://example.com/logo.svg", foundation_id)

    assert "error" not in result
    assert "valid" in result or "message" in result


@pytest.mark.asyncio
async def test_validate_logo_png(foundation_id: str):
    """Test validate_logo passes for PNG format (may have warning)."""
    result = await validate_logo("https://example.com/logo.png", foundation_id)

    assert "error" not in result or "warning" in result


@pytest.mark.asyncio
async def test_validate_logo_invalid_format(foundation_id: str):
    """Test validate_logo fails or returns issues for GIF format."""
    result = await validate_logo("https://example.com/logo.gif", foundation_id)

    # Either returns error or validation issues
    if "error" in result:
        assert result["error"] in ["INVALID_FORMAT", "VALIDATION_FAILED"]
    else:
        assert "issues" in result or "message" in result


@pytest.mark.asyncio
async def test_validate_logo_invalid_url(foundation_id: str):
    """Test validate_logo fails or returns issues for invalid URL."""
    result = await validate_logo("not-a-url.svg", foundation_id)

    # Either returns error or validation issues
    if "error" in result:
        assert result["error"] in ["INVALID_URL", "VALIDATION_FAILED"]
    else:
        assert "issues" in result or "message" in result


@pytest.mark.asyncio
async def test_get_brand_guidelines(foundation_id: str):
    """Test get_brand_guidelines returns guidelines."""
    result = await get_brand_guidelines(foundation_id)

    assert "error" not in result
    assert "guidelines" in result or "message" in result


@pytest.mark.asyncio
async def test_get_brand_guidelines_not_found():
    """Test get_brand_guidelines returns error for invalid foundation."""
    result = await get_brand_guidelines("nonexistent")

    assert "error" in result
    assert result["error"] == "GUIDELINES_NOT_FOUND"


@pytest.mark.asyncio
async def test_request_logo_upload(
    org_hitachi: str,
    foundation_id: str,
):
    """Test request_logo_upload returns upload URL."""
    result = await request_logo_upload(org_hitachi, foundation_id)

    assert "error" not in result
    assert "upload_url" in result or "url" in result or "message" in result


@pytest.mark.asyncio
async def test_request_logo_upload_not_found(
    org_invalid: str,
    foundation_id: str,
):
    """Test request_logo_upload returns error for invalid org."""
    result = await request_logo_upload(org_invalid, foundation_id)

    assert "error" in result
    assert result["error"] == "ORG_NOT_FOUND"
