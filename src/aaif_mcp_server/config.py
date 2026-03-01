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
        WorkingGroup(
            wg_id="wg-governance-risk-regulatory", name="Governance, Risk & Regulatory Alignment",
            slug="governance-risk-regulatory", meeting_schedule="Thu 10am PT (biweekly)",
            mailing_list="wg-governance-risk-regulatory@lists.aaif.io",
            discord_channel="#wg-governance-risk-regulatory",
            github_repo="aaif/wg-governance-risk-and-regulatory",
            access_policy=WgAccessPolicy.any_member,
        ),
        WorkingGroup(
            wg_id="wg-security-privacy", name="Security & Privacy",
            slug="security-privacy", meeting_schedule="Tue 10am PT (biweekly)",
            mailing_list="wg-security-privacy@lists.aaif.io",
            discord_channel="#wg-security-privacy",
            github_repo="aaif/wg-security-and-privacy",
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


# ── Mock Calendar Events ──────────────────────────────────────────
MOCK_CALENDAR_EVENTS: dict[str, list[dict]] = {
    "C001": [  # Takeshi Yamada (Hitachi, Gold voting)
        {"event_id": "evt-001", "title": "AAIF Governing Board Meeting", "schedule": "1st Mon 10am PT", "zoom_link": "https://zoom.us/j/aaif-gb"},
        {"event_id": "evt-002", "title": "AAIF Members All-Hands", "schedule": "Last Fri 9am PT", "zoom_link": "https://zoom.us/j/aaif-allhands"},
    ],
    "C002": [  # Yuki Tanaka (Hitachi, Gold technical)
        {"event_id": "evt-002", "title": "AAIF Members All-Hands", "schedule": "Last Fri 9am PT", "zoom_link": "https://zoom.us/j/aaif-allhands"},
    ],
    "C003": [  # Sambhav Kothari (Bloomberg, Gold voting)
        {"event_id": "evt-001", "title": "AAIF Governing Board Meeting", "schedule": "1st Mon 10am PT", "zoom_link": "https://zoom.us/j/aaif-gb"},
        {"event_id": "evt-002", "title": "AAIF Members All-Hands", "schedule": "Last Fri 9am PT", "zoom_link": "https://zoom.us/j/aaif-allhands"},
    ],
}

MOCK_CALENDAR_RULES: dict[str, dict[str, list[str]]] = {
    "aaif": {
        "platinum_voting_contact": ["AAIF Governing Board Meeting", "AAIF Technical Committee", "AAIF Members All-Hands"],
        "gold_voting_contact": ["AAIF Governing Board Meeting", "AAIF Members All-Hands"],
        "gold_technical_contact": ["AAIF Members All-Hands"],
        "silver_primary_contact": ["AAIF Members All-Hands"],
    }
}


# ── Mock WG Enrollments ───────────────────────────────────────────
MOCK_WG_ENROLLMENTS: dict[str, list[str]] = {
    # contact_id → list of wg_ids
    "C001": ["wg-agentic-commerce"],
    "C002": ["wg-agentic-commerce", "wg-accuracy-reliability", "wg-governance-risk-regulatory"],
    "C003": ["wg-identity-trust"],
    "C005": [],  # Natoma not yet enrolled
    "C007": ["wg-agentic-commerce", "wg-identity-trust", "wg-observability", "wg-security-privacy"],
}


# ── Mock LF Staff ─────────────────────────────────────────────────
MOCK_LF_STAFF: dict[str, dict] = {
    "staff-001": {"name": "Jennifer Tarnate", "role": "Membership", "email": "jtarnate@linuxfoundation.org", "timezone": "America/Los_Angeles"},
    "staff-002": {"name": "Candy Tan", "role": "Onboarding Coordinator", "email": "ctan@linuxfoundation.org", "timezone": "America/Los_Angeles"},
    "staff-003": {"name": "Christina Harter", "role": "Operations/PM", "email": "chartner@linuxfoundation.org", "timezone": "America/New_York"},
}


# ── Mock Onboarding Calls ────────────────────────────────────────
MOCK_ONBOARDING_CALLS: dict[str, dict] = {
    "0017V00001HITACHI": {"meeting_id": "mtg-001", "status": "completed", "scheduled_at": "2026-01-10T10:00:00Z", "attendees": ["t.yamada@hitachi.com", "jtarnate@linuxfoundation.org"], "zoom_link": "https://zoom.us/j/onboard-hitachi"},
    "0017V00001BLOOMBERG": {"meeting_id": "mtg-002", "status": "scheduled", "scheduled_at": "2026-03-05T14:00:00Z", "attendees": ["skothari@bloomberg.net", "ctan@linuxfoundation.org"], "zoom_link": "https://zoom.us/j/onboard-bloomberg"},
    "0017V00001NATOMA": {"meeting_id": None, "status": "pending", "scheduled_at": None, "attendees": [], "zoom_link": None},
}


# ── Mock Elections ────────────────────────────────────────────────
MOCK_ELECTIONS: dict[str, dict] = {
    "elec-001": {
        "election_id": "elec-001",
        "wg_id": "wg-agentic-commerce",
        "wg_name": "Agentic Commerce",
        "position": "WG Chair",
        "state": "voting",  # nominations, voting, complete
        "nomination_end": "2026-02-15",
        "voting_start": "2026-02-16",
        "voting_end": "2026-03-15",
        "candidates": [
            {"contact_id": "C001", "name": "Takeshi Yamada", "org": "Hitachi, Ltd.", "tier": "gold", "eligible": True},
            {"contact_id": "C003", "name": "Sambhav Kothari", "org": "Bloomberg LP", "tier": "gold", "eligible": True},
        ],
        "total_eligible_voters": 4,
        "votes_cast": 2,
    },
    "elec-002": {
        "election_id": "elec-002",
        "wg_id": "wg-identity-trust",
        "wg_name": "Identity & Trust",
        "position": "WG Chair",
        "state": "complete",
        "nomination_end": "2026-01-10",
        "voting_start": "2026-01-11",
        "voting_end": "2026-01-25",
        "candidates": [
            {"contact_id": "C007", "name": "Sam Altman", "org": "OpenAI", "tier": "platinum", "eligible": True},
        ],
        "total_eligible_voters": 3,
        "votes_cast": 3,
        "winner": {"contact_id": "C007", "name": "Sam Altman"},
    },
}

# ── Mock Press Release Templates ──────────────────────────────────
MOCK_PR_TEMPLATES: dict[str, dict] = {
    "new-member-announcement": {
        "template_id": "new-member-announcement",
        "name": "New Member Announcement",
        "description": "Standard press release for announcing a new AAIF member",
        "fields": ["org_name", "tier", "quote_contact", "quote_text", "about_org"],
    },
    "project-milestone": {
        "template_id": "project-milestone",
        "name": "Project Milestone",
        "description": "Announce a project release or milestone",
        "fields": ["project_name", "milestone", "version", "highlights"],
    },
}

MOCK_PRESS_RELEASES: dict[str, dict] = {
    "pr-001": {
        "pr_id": "pr-001",
        "org_id": "0017V00001HITACHI",
        "template_id": "new-member-announcement",
        "state": "approved",
        "created_at": "2026-01-15",
        "stages": [
            {"stage": "draft", "status": "complete", "completed_at": "2026-01-15"},
            {"stage": "pmo_review", "status": "complete", "completed_at": "2026-01-16", "reviewer": "Jennifer Tarnate"},
            {"stage": "comms_review", "status": "complete", "completed_at": "2026-01-18", "reviewer": "Comms Team"},
            {"stage": "legal_review", "status": "complete", "completed_at": "2026-01-20", "reviewer": "Legal"},
        ],
    },
}

# ── Mock Brand Guidelines ─────────────────────────────────────────
MOCK_BRAND_GUIDELINES: dict[str, dict] = {
    "aaif": {
        "foundation": "AI & Agentic Infrastructure Foundation",
        "logo_requirements": {
            "format": "SVG preferred; PNG accepted as fallback",
            "min_dimensions": "1000x1000 pixels (for raster formats)",
            "color_space": "sRGB",
            "background": "Transparent background required",
            "file_size_max": "5MB",
        },
        "brand_colors": {
            "primary": "#0066CC",
            "secondary": "#00AA55",
            "accent": "#FF6600",
        },
        "usage_guidelines": "Logo must maintain clear space equal to the height of the 'A' in AAIF on all sides.",
        "website": "https://aaif.io",
    },
}

MOCK_LOGO_STATUS: dict[str, dict] = {
    "0017V00001HITACHI": {"status": "validated", "format": "SVG", "dimensions": "2000x2000", "issues": []},
    "0017V00001BLOOMBERG": {"status": "validated", "format": "SVG", "dimensions": "1500x1500", "issues": []},
    "0017V00001NATOMA": {"status": "pending", "format": None, "dimensions": None, "issues": ["Logo not yet submitted"]},
    "0017V00001OPENAI": {"status": "validated", "format": "SVG", "dimensions": "3000x3000", "issues": []},
}

# ── Mock Engagement Data ──────────────────────────────────────────
MOCK_ENGAGEMENT_DATA: dict[str, dict] = {
    "0017V00001HITACHI": {
        "meeting_attendance_rate": 0.85,
        "wg_participation_count": 2,
        "github_commits_30d": 15,
        "slack_messages_30d": 42,
        "last_activity": "2026-02-27",
    },
    "0017V00001BLOOMBERG": {
        "meeting_attendance_rate": 0.70,
        "wg_participation_count": 1,
        "github_commits_30d": 8,
        "slack_messages_30d": 25,
        "last_activity": "2026-02-25",
    },
    "0017V00001NATOMA": {
        "meeting_attendance_rate": 0.20,
        "wg_participation_count": 0,
        "github_commits_30d": 0,
        "slack_messages_30d": 3,
        "last_activity": "2026-02-01",
    },
    "0017V00001IPROOV": {
        "meeting_attendance_rate": 0.50,
        "wg_participation_count": 1,
        "github_commits_30d": 5,
        "slack_messages_30d": 12,
        "last_activity": "2026-02-20",
    },
    "0017V00001OPENAI": {
        "meeting_attendance_rate": 0.95,
        "wg_participation_count": 3,
        "github_commits_30d": 45,
        "slack_messages_30d": 120,
        "last_activity": "2026-02-28",
    },
}


# ── Config Validation ──────────────────────────────────────────────

def validate_config() -> list[str]:
    """Validate all config data at startup. Returns list of warnings.

    Checks:
    - MOCK_MEMBERS have required fields (org_name, contacts)
    - TIER_ENTITLEMENTS exist for all standard tiers (platinum, gold, silver)
    - PROVISIONING_RULES reference valid lists and have defined rules

    Returns:
        List of warning strings. Empty list if no issues found.
    """
    warnings = []

    # Check MOCK_MEMBERS have required fields
    for org_id, org in MOCK_MEMBERS.items():
        if not org.org_name:
            warnings.append(f"MOCK_MEMBERS[{org_id}]: missing org_name")
        if not org.contacts:
            warnings.append(f"MOCK_MEMBERS[{org_id}]: no contacts defined")

    # Check TIER_ENTITLEMENTS exist for all tiers
    for foundation_id, tiers in TIER_ENTITLEMENTS.items():
        for tier_name in ["platinum", "gold", "silver"]:
            if tier_name not in tiers:
                warnings.append(f"TIER_ENTITLEMENTS[{foundation_id}]: missing '{tier_name}' tier")

    # Check PROVISIONING_RULES reference valid lists
    for foundation_id, rules_config in PROVISIONING_RULES.items():
        if not rules_config.rules:
            warnings.append(f"PROVISIONING_RULES[{foundation_id}]: no rules defined")

    return warnings
