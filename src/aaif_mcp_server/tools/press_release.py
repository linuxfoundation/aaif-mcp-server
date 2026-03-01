"""Domain 8: Press Release Drafting — 3 tools.

Generates press release drafts from templates, tracks approval workflow,
and provides template catalog.
"""

import logging
import uuid
from datetime import datetime

from ..config import MOCK_MEMBERS, MOCK_PR_TEMPLATES, MOCK_PRESS_RELEASES
from ..connectors.registry import get_sfdc, get_hubspot

logger = logging.getLogger(__name__)


async def draft_press_release(
    org_id: str, template_id: str = "new-member-announcement", foundation_id: str = "aaif"
) -> dict:
    """Generate a press release draft from a template using org data.

    Args:
        org_id: Salesforce organization ID
        template_id: Press release template ID (default: new-member-announcement)
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Press release draft with markdown content and metadata.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {
            "error": "ORG_NOT_FOUND",
            "message": f"No org found with ID '{org_id}'",
        }

    template = MOCK_PR_TEMPLATES.get(template_id)
    if not template:
        return {
            "error": "TEMPLATE_NOT_FOUND",
            "message": f"Template '{template_id}' not found",
        }

    # Generate press release ID
    pr_id = f"pr-{uuid.uuid4().hex[:8]}"

    # Find first voting contact for quote (if available)
    quote_contact = None
    quote_text = None
    for contact in org.contacts:
        if contact.name:
            quote_contact = contact.name
            quote_text = (
                f"We are excited to join AAIF and contribute to advancing "
                f"responsible AI development. This collaboration aligns with "
                f"our commitment to building trustworthy AI systems."
            )
            break

    # Generate markdown content
    content = f"""# {org.org_name} Joins AAIF as {org.tier.value.title()} Member

SAN FRANCISCO — {datetime.utcnow().strftime('%B %d, %Y')} — The Linux Foundation today announced that {org.org_name} has joined the AI & Agentic Infrastructure Foundation (AAIF) as a {org.tier.value.title()} member, joining a growing ecosystem of organizations committed to advancing responsible AI development.

## About the Partnership

{org.org_name}'s membership underscores the growing importance of open, collaborative standards for AI infrastructure. As a {org.tier.value.title()} member, the organization will participate in AAIF's working groups on Agentic Commerce, Accuracy & Reliability, Identity & Trust, Observability & Traceability, and Workflows & Process Integration.

## Member Perspective

{f'"{quote_text}"' if quote_text else ""} — {quote_contact if quote_contact else "Member Representative"}, {org.org_name}

## About the AI & Agentic Infrastructure Foundation

The AI & Agentic Infrastructure Foundation (AAIF), hosted by the Linux Foundation, is dedicated to accelerating the adoption of safe, open, and interoperable AI systems and agents. The foundation brings together technology leaders, academics, and policy experts to develop best practices, standards, and governance models for responsible AI development.

For more information about membership and participation, visit [aaif.io](https://aaif.io).

### Foundation Contact
The Linux Foundation
press@linuxfoundation.org
"""

    result = {
        "pr_id": pr_id,
        "org_id": org_id,
        "org_name": org.org_name,
        "tier": org.tier.value,
        "template_id": template_id,
        "state": "draft",
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
        "stages": [
            {"stage": "draft", "status": "complete", "completed_at": datetime.utcnow().isoformat()},
            {"stage": "pmo_review", "status": "pending"},
            {"stage": "comms_review", "status": "pending"},
            {"stage": "legal_review", "status": "pending"},
        ],
        "message": f"Press release {pr_id} drafted for {org.org_name} ({org.tier.value} membership announcement)",
    }

    return result


async def get_press_release_status(
    pr_id: str, foundation_id: str = "aaif"
) -> dict:
    """Retrieve press release status and approval workflow progress.

    Returns workflow stages (draft → PMO review → Comms review → Legal review → approved).

    Args:
        pr_id: Press release ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Press release status with workflow progression.
    """
    pr = MOCK_PRESS_RELEASES.get(pr_id)
    if not pr:
        return {
            "error": "PR_NOT_FOUND",
            "message": f"Press release '{pr_id}' not found",
        }

    # Calculate overall status
    all_complete = all(s["status"] == "complete" for s in pr.get("stages", []))
    overall_state = "approved" if all_complete else "in_progress"

    completed_stages = sum(
        1 for s in pr.get("stages", []) if s["status"] == "complete"
    )
    total_stages = len(pr.get("stages", []))

    return {
        "pr_id": pr_id,
        "org_id": pr.get("org_id"),
        "state": pr.get("state", overall_state),
        "template_id": pr.get("template_id"),
        "created_at": pr.get("created_at"),
        "stages": pr.get("stages", []),
        "workflow_progress": f"{completed_stages}/{total_stages} stages complete",
        "message": (
            f"Press release status: {overall_state} "
            f"({completed_stages}/{total_stages} approvals complete)"
        ),
    }


async def list_press_release_templates(foundation_id: str = "aaif") -> dict:
    """List all available press release templates.

    Args:
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Template catalog with details and required fields.
    """
    templates = list(MOCK_PR_TEMPLATES.values())

    return {
        "foundation_id": foundation_id,
        "templates": templates,
        "count": len(templates),
        "message": f"Found {len(templates)} press release templates for {foundation_id}",
    }
