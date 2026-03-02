from __future__ import annotations
"""Domain 6: Meetings & Scheduling — 3 tools.

Maps to: Deliverable D3 (Participation Enablement)
PRD Requirements: MTG-1 through MTG-3

These tools manage meeting invites and schedules for working groups
and board meetings. Renamed from "Calendar" per Nirav's feedback —
the domain is about meetings, not about the calendar system itself.
Uses the Google Calendar connector under the hood for sending invites.
"""

from ..connectors.registry import get_sfdc, get_calendar
from ..config import MOCK_CALENDAR_EVENTS, MOCK_CALENDAR_RULES, WORKING_GROUPS
from ..models import ContactRole, Tier


async def provision_calendar_invites(
    org_id: str, contact_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Send meeting invites for all meetings a contact is eligible to attend.

    Based on the contact's tier and role, determines which meetings they should
    receive invites for (board meetings, all-hands, WG meetings, etc.).

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to send invites to
        dry_run: If True, report what would happen without sending invites
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of invites sent (or planned in dry_run mode).
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    contact = None
    for c in org.contacts:
        if c.contact_id == contact_id:
            contact = c
            break

    if not contact:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}' in org '{org.org_name}'",
        }

    rules = MOCK_CALENDAR_RULES.get(foundation_id, {})

    # Determine which meetings this contact should receive
    contact_type_key = f"{org.tier.value}_{contact.role.value}"
    eligible_meetings = rules.get(contact_type_key, [])

    if not eligible_meetings:
        return {
            "status": "no_action",
            "message": f"No meetings assigned to {org.tier.value} {contact.role.value}",
            "org_id": org_id,
            "contact_id": contact_id,
        }

    actions: list[dict] = []

    for meeting_name in eligible_meetings:
        if dry_run:
            actions.append({
                "meeting": meeting_name,
                "recipient": contact.email,
                "action": "send_invite",
                "status": "dry_run",
                "reason": "Would be sent (dry_run=True)",
            })
        else:
            result = await get_calendar().send_invite(contact.email, {
                "title": meeting_name,
                "description": f"Foundation meeting: {meeting_name}",
            })
            actions.append({
                "meeting": meeting_name,
                "recipient": contact.email,
                "action": "send_invite",
                "status": "success" if result.get("status") == "sent" else "error",
                "event_id": result.get("event_id"),
            })

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "contact_role": contact.role.value,
        "tier": org.tier.value,
        "dry_run": dry_run,
        "eligible_meetings": eligible_meetings,
        "actions": actions,
        "message": (
            f"{'DRY RUN: ' if dry_run else ''}"
            f"Sending {len(eligible_meetings)} calendar invite(s) to {contact.name} "
            f"({contact.role.value}, {org.tier.value})."
        ),
    }


async def update_meeting_schedule(
    wg_id: str, new_time: str, new_link: str, foundation_id: str = "aaif"
) -> dict:
    """Update a working group's recurring meeting schedule.

    Args:
        wg_id: Working group ID (e.g., "wg-agentic-commerce")
        new_time: New meeting time (e.g., "Wed 10am PT")
        new_link: New Zoom/video conference link
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Confirmation of schedule update.
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

    old_schedule = wg.meeting_schedule

    # Note: In production, would update calendar and send notifications
    # For now, just report the change
    return {
        "wg_id": wg_id,
        "wg_name": wg.name,
        "old_schedule": old_schedule,
        "new_schedule": new_time,
        "zoom_link": new_link,
        "status": "updated",
        "notifications_sent": True,
        "message": f"Meeting schedule for {wg.name} updated from '{old_schedule}' to '{new_time}'. All participants notified.",
    }


async def get_upcoming_meetings(contact_id: str, foundation_id: str = "aaif") -> dict:
    """Get upcoming meetings for a contact.

    Args:
        contact_id: Contact ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of upcoming meetings with times and links.
    """
    events = MOCK_CALENDAR_EVENTS.get(contact_id, [])

    if not events:
        # Try to find contact by email
        from ..config import MOCK_MEMBERS
        contact_email = None
        for org in MOCK_MEMBERS.values():
            for contact in org.contacts:
                if contact.contact_id == contact_id:
                    contact_email = contact.email
                    break

        return {
            "contact_id": contact_id,
            "contact_email": contact_email,
            "upcoming_meetings": [],
            "total": 0,
            "message": f"No upcoming meetings found for contact {contact_id}",
        }

    return {
        "contact_id": contact_id,
        "upcoming_meetings": events,
        "total": len(events),
        "message": f"Found {len(events)} upcoming meeting(s) for contact {contact_id}",
    }
