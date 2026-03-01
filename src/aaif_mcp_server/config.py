from __future__ import annotations
"""Foundation configuration — tier rules, entitlement matrices, mailing list mappings, WG definitions.

This is the single source of truth for AAIF-specific provisioning rules.
When extending to other foundations (PyTorch, CNCF, OpenSSF), add new entries here.
"""

from .models import (
    ChecklistItem, ChecklistTemplate, Contact, ContactRole,
    DeliverableId, MemberOrg, ProvisioningRule, RulesConfig,
    Tier, TierEntitlements, WorkingGroup, WgAccessPolicy,
)
from datetime import datetime


# ── Tier Entitlements ──────────────────────────────────────────────

TIER_ENTITLEMENTS: dict[str, dict[str, TierEntitlements]] = {
    "aaif": {
        "platinum": TierEntitlements(
            tier=Tier.platinum, foundation_id="aaif",
            gb_seats=2, voting_rights=True, wg_chair_eligible=True,
            wg_participation=True, tc_eligible=True,
            event_member_pricing=True, max_contacts=10,
            mailing_lists=["governing-board@lists.aaif.io", "technical-committee@lists.aaif.io",
                           "members-all@lists.aaif.io"],
            pricing="Contact for pricing",
        ),
        "gold": TierEntitlements(
            tier=Tier.gold, foundation_id="aaif",
            gb_seats=1, voting_rights=True, wg_chair_eligible=True,
            wg_participation=True, tc_eligible=True,
            event_member_pricing=True, max_contacts=8,
            mailing_lists=["governing-board@lists.aaif.io", "members-all@lists.aaif.io"],
            pricing="$205,000/year ($200,000 for existing LF members)",
        ),
        "silver": TierEntitlements(
            tier=Tier.silver, foundation_id="aaif",
            gb_seats=0, voting_rights=False, wg_chair_eligible=False,
            wg_participation=True, tc_eligible=False,
            event_member_pricing=True, max_contacts=5,
            mailing_lists=["members-all@lists.aaif.io"],
            pricing="$10,000-$75,000/year (scaled by headcount)",
        ),
    }
}


# ── Working Groups ─────────────────────────────────────────────────

WORKING_GROUPS: dict[str, list[WorkingGroup]] = {
    "aaif": [
        WorkingGroup(
            wg_id="wg-agentic-commerce", name="Agentic Commerce",
            slug="agentic-commerce", meeting_schedule="Wed 9am PT",
            mailing_list="wg-agentic-commerce@lists.aaif.io",
            discord_channel="#wg-agentic-commerce",
            github_repo="aaif/wg-agentic-commerce",
            access_policy=WgAccessPolicy.any_member,
        ),
        WorkingGroup(
            wg_id="wg-accuracy-reliability", name="Accuracy & Reliability",
            slug="accuracy-reliability", meeting_schedule="Tue 9am PT",
            mailing_list="wg-accuracy-reliability@lists.aaif.io",
            discord_channel="#wg-accuracy-reliability",
            github_repo="aaif/wg-accuracy-reliability",
            access_policy=WgAccessPolicy.any_member,
        ),
        WorkingGroup(
            wg_id="wg-identity-trust", name="Identity & Trust",
            slug="identity-trust", meeting_schedule="Thu 9am PT",
            mailing_list="wg-identity-trust@lists.aaif.io",
            discord_channel="#wg-identity-trust",
            github_repo="aaif/wg-identity-trust",
            access_policy=WgAccessPolicy.any_member,
        ),
        WorkingGroup(
            wg_id="wg-observability", name="Observability & Traceability",
            slug="observability", meeting_schedule="Wed 10am PT",
            mailing_list="wg-observability@lists.aaif.io",
            discord_channel="#wg-observability",
            github_repo="aaif/wg-observability",
            access_policy=WgAccessPolicy.any_member,
        ),
        WorkingGroup(
            wg_id="wg-workflows", name="Workflows & Process Integration",
            slug="workflows", meeting_schedule="Thu 8am PT",
            mailing_list="wg-workflows@lists.aaif.io",
            discord_channel="#wg-workflows",
            github_repo="aaif/wg-workflows",
            access_policy=WgAccessPolicy.any_member,
        ),
    ]
}


# ── Provisioning Rules ─────────────────────────────────────────────

PROVISIONING_RULES: dict[str, RulesConfig] = {
    "aaif": RulesConfig(
        foundation_id="aaif",
        rules=[
            # Gold voting contacts → GB + all-members + WG lists
            ProvisioningRule(tier=Tier.gold, role=ContactRole.voting_contact,
                            resources=["governing-board@lists.aaif.io", "members-all@lists.aaif.io"]),
            ProvisioningRule(tier=Tier.gold, role=ContactRole.alternate_contact,
                            resources=["governing-board@lists.aaif.io", "members-all@lists.aaif.io"]),
            ProvisioningRule(tier=Tier.gold, role=ContactRole.technical_contact,
                            resources=["members-all@lists.aaif.io"]),
            ProvisioningRule(tier=Tier.gold, role=ContactRole.marketing_contact,
                            resources=["outreach-committee@lists.aaif.io", "members-all@lists.aaif.io"]),
            # Silver contacts → all-members list only
            ProvisioningRule(tier=Tier.silver, role=ContactRole.primary_contact,
                            resources=["members-all@lists.aaif.io"]),
            ProvisioningRule(tier=Tier.silver, role=ContactRole.technical_contact,
                            resources=["members-all@lists.aaif.io"]),
            # Platinum → everything Gold gets + TC
            ProvisioningRule(tier=Tier.platinum, role=ContactRole.voting_contact,
                            resources=["governing-board@lists.aaif.io", "technical-committee@lists.aaif.io",
                                       "members-all@lists.aaif.io"]),
            ProvisioningRule(tier=Tier.platinum, role=ContactRole.technical_contact,
                            resources=["technical-committee@lists.aaif.io", "members-all@lists.aaif.io"]),
        ],
    )
}


# ── Onboarding Checklist Template ──────────────────────────────────

CHECKLIST_TEMPLATES: dict[str, ChecklistTemplate] = {
    "aaif": ChecklistTemplate(
        foundation_id="aaif",
        deliverables=[
            {
                "id": "D1", "name": "Agreement & Membership Activation",
                "effort": "1-2", "target": "1-5 days (member signature dependent)",
                "items": [
                    ChecklistItem(id="D1-1", deliverable=DeliverableId.D1,
                                  text="Membership tier validated", effort="<1",
                                  automated=True, tool="validate_membership_tier").model_dump(),
                    ChecklistItem(id="D1-2", deliverable=DeliverableId.D1,
                                  text="Sanctions/compliance screening clear", effort="<1",
                                  automated=True, tool="check_sanctions").model_dump(),
                    ChecklistItem(id="D1-3", deliverable=DeliverableId.D1,
                                  text="Tax-exempt status verified (if applicable)", effort="<1",
                                  automated=True, tool="check_tax_exempt_status").model_dump(),
                ],
            },
            {
                "id": "D2", "name": "Membership Record & Contact Info",
                "effort": "1-2 (CRM), 3-4 (tracker sync)", "target": "2-5 business days",
                "items": [
                    ChecklistItem(id="D2-1", deliverable=DeliverableId.D2,
                                  text="CRM record validated", effort="<1",
                                  automated=True, tool="validate_membership_tier").model_dump(),
                    ChecklistItem(id="D2-2", deliverable=DeliverableId.D2,
                                  text="Contacts collected by role", effort="2-3",
                                  automated=False, tool=None).model_dump(),
                    ChecklistItem(id="D2-3", deliverable=DeliverableId.D2,
                                  text="Member tracker synced", effort="3-4",
                                  automated=True, tool="reconcile_silos").model_dump(),
                ],
            },
            {
                "id": "D3", "name": "Participation Enablement",
                "effort": "3-4", "target": "1-3 business days",
                "items": [
                    ChecklistItem(id="D3-1", deliverable=DeliverableId.D3,
                                  text="Mailing lists provisioned", effort="<1",
                                  automated=True, tool="provision_mailing_lists").model_dump(),
                    ChecklistItem(id="D3-2", deliverable=DeliverableId.D3,
                                  text="Calendar invites sent", effort="<1",
                                  automated=True, tool="provision_calendar_invites").model_dump(),
                    ChecklistItem(id="D3-3", deliverable=DeliverableId.D3,
                                  text="Working group enrollment complete", effort="<1",
                                  automated=True, tool="enroll_in_working_group").model_dump(),
                    ChecklistItem(id="D3-4", deliverable=DeliverableId.D3,
                                  text="Discord access provisioned", effort="1-2",
                                  automated=False, tool=None).model_dump(),
                    ChecklistItem(id="D3-5", deliverable=DeliverableId.D3,
                                  text="GitHub repo access granted", effort="1-2",
                                  automated=False, tool=None).model_dump(),
                ],
            },
            {
                "id": "D4", "name": "Orientation & Initial Outreach",
                "effort": "1", "target": "1-2 business days",
                "items": [
                    ChecklistItem(id="D4-1", deliverable=DeliverableId.D4,
                                  text="Welcome email sent", effort="<1",
                                  automated=True, tool=None).model_dump(),
                    ChecklistItem(id="D4-2", deliverable=DeliverableId.D4,
                                  text="Onboarding call scheduled", effort="<1",
                                  automated=True, tool="schedule_onboarding_call").model_dump(),
                ],
            },
            {
                "id": "D5", "name": "Visibility & Public Recognition",
                "effort": "3-4", "target": "1-2 weeks",
                "items": [
                    ChecklistItem(id="D5-1", deliverable=DeliverableId.D5,
                                  text="Logo collected and validated", effort="<1",
                                  automated=True, tool="validate_logo").model_dump(),
                    ChecklistItem(id="D5-2", deliverable=DeliverableId.D5,
                                  text="Press release drafted", effort="<1",
                                  automated=True, tool="draft_press_release").model_dump(),
                    ChecklistItem(id="D5-3", deliverable=DeliverableId.D5,
                                  text="Website/landscape updated", effort="2-3",
                                  automated=False, tool=None).model_dump(),
                ],
            },
        ],
    )
}


# ── Mock Member Data (realistic AAIF members) ─────────────────────

MOCK_MEMBERS: dict[str, MemberOrg] = {
    "0017V00001HITACHI": MemberOrg(
        org_id="0017V00001HITACHI", org_name="Hitachi, Ltd.", tier=Tier.gold,
        status="active", contract_signed=datetime(2025, 12, 15),
        contract_expiry=datetime(2026, 12, 14), is_lf_member=True, country="JP",
        contacts=[
            Contact(contact_id="C001", name="Takeshi Yamada", email="t.yamada@hitachi.com",
                    role=ContactRole.voting_contact, lfid="tyamada-hitachi", lfid_verified=True),
            Contact(contact_id="C002", name="Yuki Tanaka", email="y.tanaka@hitachi.com",
                    role=ContactRole.technical_contact, lfid="ytanaka", lfid_verified=True),
        ],
    ),
    "0017V00001BLOOMBERG": MemberOrg(
        org_id="0017V00001BLOOMBERG", org_name="Bloomberg LP", tier=Tier.gold,
        status="active", contract_signed=datetime(2025, 11, 1),
        contract_expiry=datetime(2026, 10, 31), is_lf_member=True, country="US",
        contacts=[
            Contact(contact_id="C003", name="Sambhav Kothari", email="skothari@bloomberg.net",
                    role=ContactRole.voting_contact, lfid="skothari-bb", lfid_verified=True),
            Contact(contact_id="C004", name="Ania Musial", email="amusial@bloomberg.net",
                    role=ContactRole.alternate_contact, lfid="amusial-bb", lfid_verified=True),
        ],
    ),
    "0017V00001NATOMA": MemberOrg(
        org_id="0017V00001NATOMA", org_name="Natoma", tier=Tier.silver,
        status="active", contract_signed=datetime(2026, 2, 10),
        contract_expiry=datetime(2027, 2, 9), is_lf_member=False, country="US",
        headcount_tier="1-99",
        contacts=[
            Contact(contact_id="C005", name="Paresh Bhaya", email="paresh@natoma.com",
                    role=ContactRole.primary_contact, lfid="pbhaya", lfid_verified=False),
        ],
    ),
    "0017V00001IPROOV": MemberOrg(
        org_id="0017V00001IPROOV", org_name="iProov", tier=Tier.silver,
        status="active", contract_signed=datetime(2026, 1, 20),
        contract_expiry=datetime(2027, 1, 19), is_lf_member=False, country="GB",
        headcount_tier="100-499",
        contacts=[
            Contact(contact_id="C006", name="Andrew Bud", email="abud@iproov.com",
                    role=ContactRole.primary_contact, lfid="abud-iproov", lfid_verified=True),
        ],
    ),
    "0017V00001OPENAI": MemberOrg(
        org_id="0017V00001OPENAI", org_name="OpenAI", tier=Tier.platinum,
        status="active", contract_signed=datetime(2025, 10, 1),
        contract_expiry=datetime(2026, 9, 30), is_lf_member=True, country="US",
        contacts=[
            Contact(contact_id="C007", name="Sam Altman", email="sam@openai.com",
                    role=ContactRole.voting_contact, lfid="saltman-oai", lfid_verified=True),
        ],
    ),
    "0017V00001SANCTIONED": MemberOrg(
        org_id="0017V00001SANCTIONED", org_name="TestCorp Sanctioned LLC", tier=Tier.silver,
        status="pending", country="RU",
        contacts=[
            Contact(contact_id="C099", name="Test Person", email="test@sanctioned.example",
                    role=ContactRole.primary_contact),
        ],
    ),
}


# ── Mock Mailing List Subscriptions ────────────────────────────────

MOCK_LIST_SUBSCRIPTIONS: dict[str, list[str]] = {
    # email → list of mailing lists they're subscribed to
    "t.yamada@hitachi.com": ["governing-board@lists.aaif.io", "members-all@lists.aaif.io"],
    "y.tanaka@hitachi.com": ["members-all@lists.aaif.io"],
    "skothari@bloomberg.net": ["governing-board@lists.aaif.io", "members-all@lists.aaif.io"],
    "amusial@bloomberg.net": ["governing-board@lists.aaif.io", "members-all@lists.aaif.io"],
    "paresh@natoma.com": [],  # Not yet provisioned
    "abud@iproov.com": ["members-all@lists.aaif.io"],
}


# ── Sanctioned Entities (mock) ─────────────────────────────────────

MOCK_SANCTIONS_LIST: list[dict] = [
    {"name": "TestCorp Sanctioned LLC", "list": "OFAC SDN", "country": "RU",
     "reason": "Executive Order 14024"},
    {"name": "Restricted Entity GmbH", "list": "EU Sanctions", "country": "BY",
     "reason": "Council Regulation (EU) 2025/XXX"},
]
