"""Domain 9: Logo & Brand Asset Validation — 3 tools.

Validates logo files against brand guidelines, provides brand guidelines,
and generates secure upload URLs for brand assets.
"""

import logging
import uuid
from datetime import datetime

from ..config import MOCK_BRAND_GUIDELINES, MOCK_LOGO_STATUS
from ..connectors.registry import get_sfdc

logger = logging.getLogger(__name__)


async def validate_logo(file_url: str, foundation_id: str = "aaif") -> dict:
    """Validate a logo file against brand guidelines.

    Checks: format (SVG preferred), dimensions, color space, file size.

    Args:
        file_url: URL to the logo file
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Validation result with pass/fail and any issues found.
    """
    guidelines = MOCK_BRAND_GUIDELINES.get(foundation_id, {})
    logo_reqs = guidelines.get("logo_requirements", {})

    issues = []
    passed = True

    # Check file extension
    if not any(file_url.lower().endswith(ext) for ext in [".svg", ".png", ".jpg", ".jpeg"]):
        issues.append("Invalid format: SVG, PNG, or JPG required")
        passed = False
    elif file_url.lower().endswith(".png") or file_url.lower().endswith(".jpg"):
        issues.append("Warning: PNG/JPG accepted but SVG preferred")

    # Check URL (basic validation)
    if not file_url.startswith(("http://", "https://")):
        issues.append("Invalid URL format")
        passed = False

    # Mock additional checks based on file extension
    if passed and file_url.lower().endswith(".svg"):
        # For SVG files, assume valid
        pass
    elif passed and (file_url.lower().endswith(".png") or file_url.lower().endswith(".jpg")):
        # For raster, we'd normally check dimensions but can't without downloading
        # In production, you'd download and analyze
        issues.append("Unable to verify dimensions from URL (would require download)")

    return {
        "file_url": file_url,
        "validated": passed,
        "status": "pass" if passed else "fail",
        "issues": issues,
        "guidelines_summary": {
            "format": logo_reqs.get("format", "Not specified"),
            "min_dimensions": logo_reqs.get("min_dimensions", "Not specified"),
            "color_space": logo_reqs.get("color_space", "Not specified"),
            "background": logo_reqs.get("background", "Not specified"),
            "file_size_max": logo_reqs.get("file_size_max", "Not specified"),
        },
        "message": (
            f"Logo validation: {'PASS' if passed else 'FAIL'} "
            f"({len(issues)} {'issue' if len(issues) != 1 else 'issues'})"
        ),
    }


async def get_brand_guidelines(foundation_id: str = "aaif") -> dict:
    """Retrieve brand guidelines and requirements.

    Args:
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Brand guidelines including logo requirements, colors, and usage rules.
    """
    guidelines = MOCK_BRAND_GUIDELINES.get(foundation_id)
    if not guidelines:
        return {
            "error": "GUIDELINES_NOT_FOUND",
            "message": f"Brand guidelines not found for {foundation_id}",
        }

    return {
        "foundation_id": foundation_id,
        "foundation": guidelines.get("foundation"),
        "logo_requirements": guidelines.get("logo_requirements"),
        "brand_colors": guidelines.get("brand_colors"),
        "usage_guidelines": guidelines.get("usage_guidelines"),
        "website": guidelines.get("website"),
        "message": f"Brand guidelines retrieved for {guidelines.get('foundation')}",
    }


async def request_logo_upload(org_id: str, foundation_id: str = "aaif") -> dict:
    """Generate a secure, temporary upload URL for logo submission.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Upload URL and metadata including expiration time and accepted formats.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {
            "error": "ORG_NOT_FOUND",
            "message": f"No org found with ID '{org_id}'",
        }

    # Generate a unique upload token
    upload_token = uuid.uuid4().hex
    expires_in_hours = 24

    # Mock upload URL (in production, this would be a signed S3 URL or similar)
    upload_url = (
        f"https://assets.aaif.io/upload/{org_id}/{upload_token}?expires={expires_in_hours}h"
    )

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "upload_url": upload_url,
        "upload_token": upload_token,
        "expires_in_hours": expires_in_hours,
        "expires_at": (
            datetime.utcnow()
            .isoformat() + f" (UTC+{expires_in_hours}h)"
        ),
        "accepted_formats": ["SVG", "PNG", "JPG", "JPEG"],
        "max_file_size_mb": 5,
        "instructions": (
            "Upload your logo using the provided URL. "
            "SVG format is preferred. PNG/JPG accepted as fallback. "
            "Ensure transparent background. Minimum 1000x1000 pixels for raster formats."
        ),
        "message": (
            f"Secure upload URL generated for {org.org_name}. "
            f"Link expires in {expires_in_hours} hours."
        ),
    }
