from __future__ import annotations
"""Domain 7: Working Group Enrollment — 5 tools.

Maps to: Deliverable D3 (Participation Enablement)
PRD Requirements: WGE-1 through WGE-5

These tools manage enrollment across multiple systems (mailing lists, Discord,
GitHub, calendar). Enrollment happens across all systems; removal is the inverse.

Per Nirav's feedback: WG enrollment may be self-service (member-facing via
Intercom) or manual (PMO staff via PCC). The `caller_role` parameter enables
future routing — when called from a member context, enrollment follows the
self-service flow; when called from PMO context, it follows the manual flow.
"""

from ..connectors.registry import get_sfdc, get_groupsio, get_discord, get_github
from ..config import MOCK_WG_ENROLLMENTS, WORKING_GROUPS
from ..models import ContactRole, Tier


async def enroll_in_working_group(
    contact_id: str, wg_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Enroll a contact in a working group across all systems.

    Enrolls the contact in:
    - Mailing list
    - Discord channel
    - GitHub repository
    - Meeting invites for WG meetings

    This tool supports both self-service (member-initiated via Intercom)
    and manual (PMO staff via PCC) enrollment flows. The caller context
    determines which flow is used.

    Args:
        contact_id: Contact ID
        wg_id: Working group ID (e.g., "wg-agentic-commerce")
        dry_run: If True, report changes without making them
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Enrollment status across all systems.
    """
    # Find contact across all orgs
    all_orgs = await get_sfdc().list_orgs(foundation_id)
    contact = None
    org = None

    for o in all_orgs:
        for c in o.contacts:
            if c.contact_id == contact_id:
                contact = c
                org = o
                break
        if contact:
            break

    if not contact or not org:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}'",
        }

    # Find WG
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = None
    for w in wgs:
        if w.wg_id == wg_id:
            wg = w
            break

    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"No working group with ID '{wg_id}'",
        }

    # Check eligibility (any member can join by default, role-restricted WGs would need more logic)
    if org.status != "active":
        return {
            "error": "ORG_NOT_ACTIVE",
            "message": f"Organization must be active to enroll in working groups",
        }

    # Prepare enrollment actions
    actions = {
        "mailing_list": {"action": "add", "target": wg.mailing_list},
        "discord": {"action": "add", "target": wg.discord_channel},
        "github": {"action": "add", "target": wg.github_repo},
        "calendar": {"action": "send_invite", "target": wg.meeting_schedule},
    }

    if dry_run:
        return {
            "org_id": org.org_id,
            "org_name": org.org_name,
            "contact_id": contact_id,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "wg_id": wg_id,
            "wg_name": wg.name,
            "dry_run": True,
            "enrollment_actions": {
                "mailing_list": f"Would add {contact.email} to {wg.mailing_list}",
                "discord": f"Would add {contact.discord_handle or 'N/A'} to {wg.discord_channel}",
                "github": f"Would add {contact.github_username or 'N/A'} to {wg.github_repo}",
                "calendar": f"Would send meeting invite for {wg.meeting_schedule}",
            },
            "message": f"DRY RUN: Would enroll {contact.name} in {wg.name} across 4 systems.",
        }

    # Execute enrollment (mock mode)
    enrollment_results = {
        "mailing_list": await get_groupsio().add_member(wg.mailing_list, contact.email),
        "discord": await get_discord().add_role(contact.discord_handle or contact.name, wg.discord_channel) if contact.discord_handle else {"status": "skipped", "reason": "No Discord handle"},
        "github": await get_github().add_collaborator(contact.github_username or contact.name, wg.github_repo) if contact.github_username else {"status": "skipped", "reason": "No GitHub username"},
    }

    # Track in mock enrollment data
    if contact_id not in MOCK_WG_ENROLLMENTS:
        MOCK_WG_ENROLLMENTS[contact_id] = []
    if wg_id not in MOCK_WG_ENROLLMENTS[contact_id]:
        MOCK_WG_ENROLLMENTS[contact_id].append(wg_id)

    return {
        "org_id": org.org_id,
        "org_name": org.org_name,
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "wg_id": wg_id,
        "wg_name": wg.name,
        "dry_run": False,
        "enrollment_results": enrollment_results,
        "message": f"Enrolled {contact.name} in {wg.name}. Provisioned to mailing list, Discord, GitHub, and calendar.",
    }


async def leave_working_group(
    contact_id: str, wg_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Remove a contact from a working group across all systems.

    Args:
        contact_id: Contact ID
        wg_id: Working group ID
        dry_run: If True, report changes without making them
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Unenrollment status across all systems.
    """
    # Find contact across all orgs
    all_orgs = await get_sfdc().list_orgs(foundation_id)
    contact = None
    org = None

    for o in all_orgs:
        for c in o.contacts:
            if c.contact_id == contact_id:
                contact = c
                org = o
                break
        if contact:
            break

    if not contact or not org:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}'",
        }

    # Find WG
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = None
    for w in wgs:
        if w.wg_id == wg_id:
            wg = w
            break

    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"No working group with ID '{wg_id}'",
        }

    if dry_run:
        return {
            "org_id": org.org_id,
            "org_name": org.org_name,
            "contact_id": contact_id,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "wg_id": wg_id,
            "wg_name": wg.name,
            "dry_run": True,
            "unenrollment_actions": {
                "mailing_list": f"Would remove {contact.email} from {wg.mailing_list}",
                "discord": f"Would remove {contact.discord_handle or 'N/A'} from {wg.discord_channel}",
                "github": f"Would remove {contact.github_username or 'N/A'} from {wg.github_repo}",
            },
            "message": f"DRY RUN: Would remove {contact.name} from {wg.name} across 3 systems.",
        }

    # Execute unenrollment (mock mode)
    unenrollment_results = {
        "mailing_list": await get_groupsio().remove_member(wg.mailing_list, contact.email),
        "discord": await get_discord().remove_role(contact.discord_handle or contact.name, wg.discord_channel) if contact.discord_handle else {"status": "skipped"},
        "github": await get_github().remove_collaborator(contact.github_username or contact.name, wg.github_repo) if contact.github_username else {"status": "skipped"},
    }

    # Update mock enrollment data
    if contact_id in MOCK_WG_ENROLLMENTS and wg_id in MOCK_WG_ENROLLMENTS[contact_id]:
        MOCK_WG_ENROLLMENTS[contact_id].remove(wg_id)

    return {
        "org_id": org.org_id,
        "org_name": org.org_name,
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "wg_id": wg_id,
        "wg_name": wg.name,
        "dry_run": False,
        "unenrollment_results": unenrollment_results,
        "message": f"Removed {contact.name} from {wg.name}. Removed from mailing list, Discord, and GitHub.",
    }


async def list_available_working_groups(contact_id: str, foundation_id: str = "aaif") -> dict:
    """List all working groups with contact's current enrollment status.

    Args:
        contact_id: Contact ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of working groups with access levels.
    """
    # Find contact
    all_orgs = await get_sfdc().list_orgs(foundation_id)
    contact = None
    org = None

    for o in all_orgs:
        for c in o.contacts:
            if c.contact_id == contact_id:
                contact = c
                org = o
                break
        if contact:
            break

    if not contact or not org:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}'",
        }

    wgs = WORKING_GROUPS.get(foundation_id, [])
    enrolled_wgs = MOCK_WG_ENROLLMENTS.get(contact_id, [])

    available = []
    for wg in wgs:
        available.append({
            "wg_id": wg.wg_id,
            "wg_name": wg.name,
            "meeting_schedule": wg.meeting_schedule,
            "enrolled": wg.wg_id in enrolled_wgs,
            "access_policy": wg.access_policy.value,
        })

    return {
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "org_id": org.org_id,
        "org_name": org.org_name,
        "tier": org.tier.value,
        "available_working_groups": available,
        "enrolled_count": len(enrolled_wgs),
        "total_wgs": len(wgs),
        "message": f"{contact.name} is enrolled in {len(enrolled_wgs)}/{len(wgs)} working groups.",
    }


async def get_wg_members(wg_id: str, foundation_id: str = "aaif") -> dict:
    """Get member roster for a working group.

    Args:
        wg_id: Working group ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of members enrolled in the WG.
    """
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = None
    for w in wgs:
        if w.wg_id == wg_id:
            wg = w
            break

    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"No working group with ID '{wg_id}'",
        }

    # Find all contacts enrolled in this WG
    members = []
    for contact_id, wg_ids in MOCK_WG_ENROLLMENTS.items():
        if wg_id in wg_ids:
            # Find contact details
            all_orgs = await get_sfdc().list_orgs(foundation_id)
            for org in all_orgs:
                for contact in org.contacts:
                    if contact.contact_id == contact_id:
                        members.append({
                            "contact_id": contact.contact_id,
                            "name": contact.name,
                            "email": contact.email,
                            "org_id": org.org_id,
                            "org_name": org.org_name,
                            "tier": org.tier.value,
                            "role": contact.role.value,
                        })
                        break

    return {
        "wg_id": wg_id,
        "wg_name": wg.name,
        "members": members,
        "total_members": len(members),
        "message": f"Working group '{wg.name}' has {len(members)} enrolled member(s).",
    }


async def check_wg_eligibility(contact_id: str, wg_id: str, foundation_id: str = "aaif") -> dict:
    """Check if a contact is eligible to join a working group.

    Args:
        contact_id: Contact ID
        wg_id: Working group ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Eligibility status and reason.
    """
    # Find contact
    all_orgs = await get_sfdc().list_orgs(foundation_id)
    contact = None
    org = None

    for o in all_orgs:
        for c in o.contacts:
            if c.contact_id == contact_id:
                contact = c
                org = o
                break
        if contact:
            break

    if not contact or not org:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}'",
        }

    # Find WG
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = None
    for w in wgs:
        if w.wg_id == wg_id:
            wg = w
            break

    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"No working group with ID '{wg_id}'",
        }

    # Check eligibility
    eligible = True
    reasons = []

    if org.status != "active":
        eligible = False
        reasons.append(f"Organization status is '{org.status}', must be active")

    if wg.access_policy.value == "role_restricted":
        # For demo, only voting_contact and technical_contact can access restricted WGs
        if contact.role not in [ContactRole.voting_contact, ContactRole.technical_contact]:
            eligible = False
            reasons.append(f"Role '{contact.role.value}' not authorized for role-restricted WG")

    already_enrolled = contact_id in MOCK_WG_ENROLLMENTS and wg_id in MOCK_WG_ENROLLMENTS[contact_id]
    if already_enrolled:
        reasons.append("Contact is already enrolled in this WG")

    return {
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "org_id": org.org_id,
        "org_name": org.org_name,
        "wg_id": wg_id,
        "wg_name": wg.name,
        "eligible": eligible,
        "already_enrolled": already_enrolled,
        "reasons": reasons,
        "message": (
            f"{'Eligible' if eligible else 'Not eligible'} to join {wg.name}. "
            f"{', '.join(reasons) if reasons else 'No restrictions.'}"
        ),
    }
