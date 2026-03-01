from __future__ import annotations
"""Domain 5: Contact Role Management — 5 tools.

Maps to: Deliverable D2 (Membership Record & Contact Info)
PRD Requirements: CR-1 through CR-5

These tools manage contact roles within member organizations, including adding,
updating, removing contacts, and transferring voting rights. All operations track
downstream effects (e.g., mailing list provisioning changes).
"""

from ..connectors.registry import get_sfdc
from ..config import PROVISIONING_RULES
from ..models import ContactRole, Tier

# In-memory store for tracking contact mutations within a session (mock mode)
_contact_mutations: dict[str, list[dict]] = {}


async def list_contacts(org_id: str, foundation_id: str = "aaif") -> dict:
    """List all contacts for an organization with their roles and downstream effects.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of contacts with roles and provisioning details.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    rules_config = PROVISIONING_RULES.get(foundation_id)
    if not rules_config:
        return {"error": "NO_RULES", "message": f"No provisioning rules for '{foundation_id}'"}

    contacts_info = []
    for contact in org.contacts:
        # Find expected provisioning for this contact
        expected_lists = set()
        for rule in rules_config.rules:
            if rule.tier == org.tier and rule.role == contact.role:
                expected_lists.update(rule.resources)

        contacts_info.append({
            "contact_id": contact.contact_id,
            "name": contact.name,
            "email": contact.email,
            "role": contact.role.value,
            "lfid": contact.lfid,
            "lfid_verified": contact.lfid_verified,
            "github_username": contact.github_username,
            "discord_handle": contact.discord_handle,
            "expected_provisioning": sorted(expected_lists),
        })

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "tier": org.tier.value,
        "total_contacts": len(org.contacts),
        "contacts": contacts_info,
        "message": f"Listed {len(org.contacts)} contact(s) for {org.org_name}",
    }


async def add_contact(
    org_id: str, name: str, email: str, role: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Add a new contact to an organization.

    Args:
        org_id: Salesforce organization ID
        name: Contact full name
        email: Contact email address
        role: Contact role (voting_contact, technical_contact, primary_contact, etc.)
        dry_run: If True, report what would change without making changes
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Confirmation of contact added with downstream effects.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    # Validate role
    try:
        contact_role = ContactRole(role)
    except ValueError:
        return {
            "error": "INVALID_ROLE",
            "message": f"Invalid role '{role}'. Valid roles: {[r.value for r in ContactRole]}",
        }

    # Check if contact already exists
    for c in org.contacts:
        if c.email.lower() == email.lower():
            return {
                "error": "CONTACT_EXISTS",
                "message": f"Contact with email '{email}' already exists in {org.org_name}",
                "existing_contact": {"id": c.contact_id, "name": c.name, "role": c.role.value},
            }

    # Generate mock contact ID
    new_contact_id = f"C{len(org.contacts) + 1000}"

    # Determine downstream effects (mailing lists)
    rules_config = PROVISIONING_RULES.get(foundation_id)
    expected_lists = set()
    if rules_config:
        for rule in rules_config.rules:
            if rule.tier == org.tier and rule.role == contact_role:
                expected_lists.update(rule.resources)

    # Track mutation
    if org_id not in _contact_mutations:
        _contact_mutations[org_id] = []

    mutation = {
        "action": "add",
        "contact_id": new_contact_id,
        "name": name,
        "email": email,
        "role": role,
        "expected_lists": sorted(expected_lists),
    }

    if dry_run:
        return {
            "org_id": org_id,
            "org_name": org.org_name,
            "tier": org.tier.value,
            "dry_run": True,
            "contact_id": new_contact_id,
            "name": name,
            "email": email,
            "role": role,
            "downstream_effects": {
                "mailing_lists_to_provision": sorted(expected_lists),
                "calendar_invites": ["AAIF Members All-Hands"] if org.tier != Tier.silver else [],
            },
            "message": f"DRY RUN: Would add contact {name} ({email}) as {role} to {org.org_name}. Would provision to {len(expected_lists)} list(s).",
        }

    _contact_mutations[org_id].append(mutation)

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "tier": org.tier.value,
        "dry_run": False,
        "contact_id": new_contact_id,
        "name": name,
        "email": email,
        "role": role,
        "downstream_effects": {
            "mailing_lists_provisioned": sorted(expected_lists),
            "calendar_invites": ["AAIF Members All-Hands"] if org.tier != Tier.silver else [],
        },
        "message": f"Contact {name} ({email}) added as {role} to {org.org_name}. Provisioned to {len(expected_lists)} list(s).",
    }


async def update_contact_role(
    org_id: str, contact_id: str, new_role: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Update a contact's role, listing downstream effects.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to update
        new_role: New role (voting_contact, technical_contact, etc.)
        dry_run: If True, report changes without making them
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Role change confirmation with downstream effects.
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

    # Validate new role
    try:
        new_contact_role = ContactRole(new_role)
    except ValueError:
        return {
            "error": "INVALID_ROLE",
            "message": f"Invalid role '{new_role}'. Valid roles: {[r.value for r in ContactRole]}",
        }

    # Get old and new expected lists
    rules_config = PROVISIONING_RULES.get(foundation_id)
    old_lists = set()
    new_lists = set()

    if rules_config:
        for rule in rules_config.rules:
            if rule.tier == org.tier:
                if rule.role == contact.role:
                    old_lists.update(rule.resources)
                if rule.role == new_contact_role:
                    new_lists.update(rule.resources)

    lists_to_add = new_lists - old_lists
    lists_to_remove = old_lists - new_lists

    # Track mutation
    if org_id not in _contact_mutations:
        _contact_mutations[org_id] = []

    mutation = {
        "action": "update_role",
        "contact_id": contact_id,
        "old_role": contact.role.value,
        "new_role": new_role,
        "lists_to_add": sorted(lists_to_add),
        "lists_to_remove": sorted(lists_to_remove),
    }

    if dry_run:
        return {
            "org_id": org_id,
            "org_name": org.org_name,
            "contact_id": contact_id,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "old_role": contact.role.value,
            "new_role": new_role,
            "dry_run": True,
            "downstream_effects": {
                "mailing_lists_to_add": sorted(lists_to_add),
                "mailing_lists_to_remove": sorted(lists_to_remove),
            },
            "message": f"DRY RUN: Would change {contact.name} role from {contact.role.value} to {new_role}. {len(lists_to_add)} list(s) to add, {len(lists_to_remove)} to remove.",
        }

    _contact_mutations[org_id].append(mutation)

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "old_role": contact.role.value,
        "new_role": new_role,
        "dry_run": False,
        "downstream_effects": {
            "mailing_lists_added": sorted(lists_to_add),
            "mailing_lists_removed": sorted(lists_to_remove),
        },
        "message": f"Contact {contact.name} role changed from {contact.role.value} to {new_role}. Updated {len(lists_to_add) + len(lists_to_remove)} list memberships.",
    }


async def remove_contact(
    org_id: str, contact_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Remove a contact from an organization, triggering offboarding actions.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to remove
        dry_run: If True, report changes without making them
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Removal confirmation with offboarding actions.
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

    # Get lists this contact is subscribed to
    rules_config = PROVISIONING_RULES.get(foundation_id)
    subscribed_lists = set()
    if rules_config:
        for rule in rules_config.rules:
            if rule.tier == org.tier and rule.role == contact.role:
                subscribed_lists.update(rule.resources)

    # Track mutation
    if org_id not in _contact_mutations:
        _contact_mutations[org_id] = []

    mutation = {
        "action": "remove",
        "contact_id": contact_id,
        "name": contact.name,
        "email": contact.email,
        "role": contact.role.value,
        "lists_to_remove": sorted(subscribed_lists),
    }

    if dry_run:
        return {
            "org_id": org_id,
            "org_name": org.org_name,
            "contact_id": contact_id,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "role": contact.role.value,
            "dry_run": True,
            "offboarding_actions": {
                "mailing_lists_to_remove": sorted(subscribed_lists),
                "discord_channels_to_remove": ["#wg-agentic-commerce"] if contact.discord_handle else [],
                "github_repos_to_revoke": ["aaif/wg-agentic-commerce"] if contact.github_username else [],
                "calendar_invites_to_cancel": ["AAIF Members All-Hands"],
            },
            "message": f"DRY RUN: Would remove {contact.name} ({contact.email}) from {org.org_name}. Offboarding {len(subscribed_lists)} list(s), revoke Discord/GitHub access.",
        }

    _contact_mutations[org_id].append(mutation)

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "role": contact.role.value,
        "dry_run": False,
        "offboarding_actions": {
            "mailing_lists_removed": sorted(subscribed_lists),
            "discord_channels_removed": ["#wg-agentic-commerce"] if contact.discord_handle else [],
            "github_repos_revoked": ["aaif/wg-agentic-commerce"] if contact.github_username else [],
            "calendar_invites_cancelled": ["AAIF Members All-Hands"],
        },
        "message": f"Contact {contact.name} ({contact.email}) removed from {org.org_name}. Offboarded from {len(subscribed_lists)} list(s) and revoked system access.",
    }


async def transfer_voting_rights(
    org_id: str, from_contact_id: str, to_contact_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Transfer voting rights from one contact to another.

    Args:
        org_id: Salesforce organization ID
        from_contact_id: Current voting contact ID
        to_contact_id: New voting contact ID
        dry_run: If True, report changes without making them
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Voting rights transfer confirmation.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    from_contact = None
    to_contact = None

    for c in org.contacts:
        if c.contact_id == from_contact_id:
            from_contact = c
        if c.contact_id == to_contact_id:
            to_contact = c

    if not from_contact:
        return {
            "error": "FROM_CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{from_contact_id}'",
        }

    if not to_contact:
        return {
            "error": "TO_CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{to_contact_id}'",
        }

    if from_contact.role != ContactRole.voting_contact:
        return {
            "error": "NOT_VOTING_CONTACT",
            "message": f"{from_contact.name} is not a voting_contact (role: {from_contact.role.value})",
        }

    # Check org tier supports voting
    if org.tier == Tier.silver:
        return {
            "error": "TIER_NO_VOTING",
            "message": f"{org.tier.value.upper()} tier members cannot have voting rights",
        }

    rules_config = PROVISIONING_RULES.get(foundation_id)
    voting_lists = set()
    if rules_config:
        for rule in rules_config.rules:
            if rule.tier == org.tier and rule.role == ContactRole.voting_contact:
                voting_lists.update(rule.resources)

    # Track mutation
    if org_id not in _contact_mutations:
        _contact_mutations[org_id] = []

    mutation = {
        "action": "transfer_voting",
        "from_contact_id": from_contact_id,
        "to_contact_id": to_contact_id,
        "lists_involved": sorted(voting_lists),
    }

    if dry_run:
        return {
            "org_id": org_id,
            "org_name": org.org_name,
            "from_contact": {
                "id": from_contact.contact_id,
                "name": from_contact.name,
                "email": from_contact.email,
            },
            "to_contact": {
                "id": to_contact.contact_id,
                "name": to_contact.name,
                "email": to_contact.email,
            },
            "dry_run": True,
            "voting_lists": sorted(voting_lists),
            "message": f"DRY RUN: Would transfer voting rights from {from_contact.name} to {to_contact.name}. Affects {len(voting_lists)} list(s).",
        }

    _contact_mutations[org_id].append(mutation)

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "from_contact": {
            "id": from_contact.contact_id,
            "name": from_contact.name,
            "email": from_contact.email,
        },
        "to_contact": {
            "id": to_contact.contact_id,
            "name": to_contact.name,
            "email": to_contact.email,
        },
        "dry_run": False,
        "voting_lists": sorted(voting_lists),
        "message": f"Voting rights transferred from {from_contact.name} to {to_contact.name}. Updated {len(voting_lists)} list membership(s).",
    }
