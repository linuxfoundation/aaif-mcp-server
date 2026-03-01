from __future__ import annotations
"""Domain 1: Mailing List Provisioning — 4 tools.

Maps to: Deliverable D3 (Participation Enablement)
PRD Requirements: ML-1 through ML-6

These tools provision, remove, check, and remediate mailing list memberships
based on tier + role provisioning rules. All operations use the Groups.io
connector and reference the PROVISIONING_RULES config.
"""

from ..connectors.registry import get_sfdc, get_groupsio
from ..config import PROVISIONING_RULES
from ..models import MailingListAction, MailingListGap, MailingListMembership


async def provision_mailing_lists(
    org_id: str, contact_email: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Provision a contact onto the correct mailing lists based on their org's
    tier and their role. Uses the PROVISIONING_RULES engine.

    IMPORTANT: Defaults to dry_run=True. Set dry_run=False to actually
    mutate mailing list membership. The LLM orchestrator should confirm
    with the human before running with dry_run=False.

    Args:
        org_id: Salesforce organization ID
        contact_email: Email address of the contact to provision
        dry_run: If True, report what would change without making changes
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of actions taken (or planned in dry_run mode).
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    # Find the contact
    contact = None
    for c in org.contacts:
        if c.email.lower() == contact_email.lower():
            contact = c
            break

    if not contact:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with email '{contact_email}' in org '{org.org_name}'",
            "org_id": org_id,
            "available_contacts": [c.email for c in org.contacts],
        }

    # Resolve expected lists from provisioning rules
    rules_config = PROVISIONING_RULES.get(foundation_id)
    if not rules_config:
        return {"error": "NO_RULES", "message": f"No provisioning rules for '{foundation_id}'"}

    expected_lists = set()
    for rule in rules_config.rules:
        if rule.tier == org.tier and rule.role == contact.role:
            expected_lists.update(rule.resources)

    if not expected_lists:
        return {
            "status": "no_action",
            "message": f"No provisioning rules match tier={org.tier.value}, role={contact.role.value}",
            "org_id": org_id,
            "contact_email": contact_email,
        }

    actions: list[dict] = []
    for list_name in sorted(expected_lists):
        already_member = await get_groupsio().is_member(list_name, contact.email)

        if already_member:
            actions.append(MailingListAction(
                list_name=list_name, email=contact.email,
                action="skip_duplicate", status="skipped",
                reason="Already a member",
            ).model_dump())
            continue

        if dry_run:
            actions.append(MailingListAction(
                list_name=list_name, email=contact.email,
                action="add", status="dry_run",
                reason="Would be added (dry_run=True)",
            ).model_dump())
        else:
            result = await get_groupsio().add_member(list_name, contact.email)
            actions.append(MailingListAction(
                list_name=list_name, email=contact.email,
                action="add", status="success" if result.get("status") == "added" else "error",
                reason=result.get("status", "unknown"),
            ).model_dump())

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "contact_email": contact.email,
        "contact_role": contact.role.value,
        "tier": org.tier.value,
        "dry_run": dry_run,
        "actions": actions,
        "message": (
            f"{'DRY RUN: ' if dry_run else ''}"
            f"Provisioning {contact.email} ({contact.role.value}) for {org.org_name} ({org.tier.value}). "
            f"{len(actions)} list(s) processed."
        ),
    }


async def remove_from_mailing_lists(
    org_id: str, contact_email: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Remove a contact from all mailing lists they're subscribed to.
    Used during offboarding, contact changes, or tier downgrades.

    Args:
        org_id: Salesforce organization ID
        contact_email: Email address of the contact to remove
        dry_run: If True, report what would change without making changes
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of removal actions taken (or planned in dry_run mode).
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    # Get all foundation lists
    all_lists = await get_groupsio().get_lists(foundation_id)
    actions: list[dict] = []

    for list_name in all_lists:
        is_member = await get_groupsio().is_member(list_name, contact_email)
        if not is_member:
            continue

        if dry_run:
            actions.append(MailingListAction(
                list_name=list_name, email=contact_email,
                action="remove", status="dry_run",
                reason="Would be removed (dry_run=True)",
            ).model_dump())
        else:
            result = await get_groupsio().remove_member(list_name, contact_email)
            actions.append(MailingListAction(
                list_name=list_name, email=contact_email,
                action="remove",
                status="success" if result.get("status") == "removed" else "error",
                reason=result.get("status", "unknown"),
            ).model_dump())

    if not actions:
        return {
            "status": "no_action",
            "message": f"{contact_email} is not subscribed to any lists in '{foundation_id}'",
            "org_id": org_id,
            "contact_email": contact_email,
        }

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "contact_email": contact_email,
        "dry_run": dry_run,
        "actions": actions,
        "message": (
            f"{'DRY RUN: ' if dry_run else ''}"
            f"Removing {contact_email} from {len(actions)} list(s)."
        ),
    }


async def check_mailing_list_membership(
    contact_email: str, foundation_id: str = "aaif"
) -> dict:
    """Check which mailing lists a contact is subscribed to.

    Args:
        contact_email: Email address to check
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Membership status across all foundation mailing lists.
    """
    all_lists = await get_groupsio().get_lists(foundation_id)
    membership: dict[str, bool] = {}

    for list_name in sorted(all_lists):
        membership[list_name] = await get_groupsio().is_member(list_name, contact_email)

    subscribed = [k for k, v in membership.items() if v]
    not_subscribed = [k for k, v in membership.items() if not v]

    result = MailingListMembership(email=contact_email, lists=membership)

    return {
        **result.model_dump(),
        "summary": {
            "total_lists": len(all_lists),
            "subscribed_count": len(subscribed),
            "subscribed": subscribed,
            "not_subscribed": not_subscribed,
        },
        "message": f"{contact_email} is subscribed to {len(subscribed)}/{len(all_lists)} lists.",
    }


async def remediate_mailing_lists(
    foundation_id: str = "aaif", dry_run: bool = True
) -> dict:
    """Scan all members and fix mailing list gaps — add missing subscriptions
    and flag excess subscriptions based on tier + role provisioning rules.

    This is the "drift remediation" tool — it ensures actual list membership
    matches what the rules say it should be.

    Args:
        foundation_id: Foundation identifier (default: aaif)
        dry_run: If True, report gaps without making changes

    Returns:
        List of gaps found and remediation actions taken/planned.
    """
    rules_config = PROVISIONING_RULES.get(foundation_id)
    if not rules_config:
        return {"error": "NO_RULES", "message": f"No provisioning rules for '{foundation_id}'"}

    orgs = await get_sfdc().list_orgs(foundation_id)
    gaps: list[dict] = []
    actions: list[dict] = []

    for org in orgs:
        if org.status != "active":
            continue

        for contact in org.contacts:
            # Determine expected lists
            expected = set()
            for rule in rules_config.rules:
                if rule.tier == org.tier and rule.role == contact.role:
                    expected.update(rule.resources)

            if not expected:
                continue

            # Check actual
            actual = set()
            for list_name in expected:
                if await get_groupsio().is_member(list_name, contact.email):
                    actual.add(list_name)

            missing = expected - actual
            # Also check for extra lists the contact shouldn't have
            all_foundation_lists = await get_groupsio().get_lists(foundation_id)
            actual_all = set()
            for list_name in all_foundation_lists:
                if await get_groupsio().is_member(list_name, contact.email):
                    actual_all.add(list_name)
            extra = actual_all - expected

            if missing or extra:
                gaps.append(MailingListGap(
                    org_id=org.org_id, org_name=org.org_name,
                    contact_email=contact.email,
                    expected_lists=sorted(expected),
                    actual_lists=sorted(actual_all),
                    missing=sorted(missing),
                    extra=sorted(extra),
                ).model_dump())

                # Remediate missing
                for list_name in missing:
                    if dry_run:
                        actions.append(MailingListAction(
                            list_name=list_name, email=contact.email,
                            action="add", status="dry_run",
                            reason=f"Missing per rules (tier={org.tier.value}, role={contact.role.value})",
                        ).model_dump())
                    else:
                        await get_groupsio().add_member(list_name, contact.email)
                        actions.append(MailingListAction(
                            list_name=list_name, email=contact.email,
                            action="add", status="success",
                            reason=f"Added per rules (tier={org.tier.value}, role={contact.role.value})",
                        ).model_dump())

    return {
        "foundation_id": foundation_id,
        "dry_run": dry_run,
        "total_members_scanned": len(orgs),
        "gaps_found": len(gaps),
        "gaps": gaps,
        "actions_taken": len(actions),
        "actions": actions,
        "message": (
            f"{'DRY RUN: ' if dry_run else ''}"
            f"Scanned {len(orgs)} members. Found {len(gaps)} gap(s), "
            f"{len(actions)} remediation action(s) {'planned' if dry_run else 'applied'}."
        ),
    }
