from __future__ import annotations
"""Salesforce connector — mock + live implementation.

In dev mode (no instance_url): uses mock data from config.py
In production: OAuth 2.0 JWT bearer flow → SFDC REST API v59

To activate live mode, set these env vars:
    SFDC_INSTANCE_URL=https://yourorg.my.salesforce.com
    SFDC_CLIENT_ID=your_connected_app_client_id
    SFDC_CLIENT_SECRET=your_connected_app_secret
    SFDC_USERNAME=integration-user@linuxfoundation.org
"""

import logging
import os
from datetime import datetime
from typing import Optional

import httpx

from .base import BaseCRMConnector
from ..config import MOCK_MEMBERS
from ..models import Contact, ContactRole, MemberOrg, Tier

logger = logging.getLogger(__name__)

# ── Field mapping: SFDC custom field API names → our model fields ──
# Update these to match your actual SFDC schema
SFDC_FIELD_MAP = {
    "account": {
        "Id": "org_id",
        "Name": "org_name",
        "Membership_Tier__c": "tier",
        "Membership_Status__c": "status",
        "Contract_Signed_Date__c": "contract_signed",
        "Contract_Expiry_Date__c": "contract_expiry",
        "Employee_Count_Range__c": "headcount_tier",
        "Is_LF_Member__c": "is_lf_member",
        "BillingCountry": "country",
    },
    "contact": {
        "Id": "contact_id",
        "Name": "name",
        "Email": "email",
        "Membership_Role__c": "role",
        "LFID__c": "lfid",
        "LFID_Verified__c": "lfid_verified",
        "GitHub_Username__c": "github_username",
    },
}

# Tier name normalization (SFDC values → our enum)
TIER_MAP = {
    "platinum": Tier.platinum,
    "gold": Tier.gold,
    "silver": Tier.silver,
    "Platinum": Tier.platinum,
    "Gold": Tier.gold,
    "Silver": Tier.silver,
}

ROLE_MAP = {
    "Voting Contact": ContactRole.voting_contact,
    "Alternate Contact": ContactRole.alternate_contact,
    "Technical Contact": ContactRole.technical_contact,
    "Billing Contact": ContactRole.billing_contact,
    "Marketing Contact": ContactRole.marketing_contact,
    "Primary Contact": ContactRole.primary_contact,
    # lowercase variants
    "voting_contact": ContactRole.voting_contact,
    "alternate_contact": ContactRole.alternate_contact,
    "technical_contact": ContactRole.technical_contact,
    "billing_contact": ContactRole.billing_contact,
    "marketing_contact": ContactRole.marketing_contact,
    "primary_contact": ContactRole.primary_contact,
}


class SalesforceConnector(BaseCRMConnector):
    """Salesforce CRM connector. Uses mock data in dev; real API in production."""

    def __init__(
        self,
        instance_url: str = "",
        client_id: str = "",
        client_secret: str = "",
        username: str = "",
    ):
        self.instance_url = instance_url or os.environ.get("SFDC_INSTANCE_URL", "")
        self.client_id = client_id or os.environ.get("SFDC_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("SFDC_CLIENT_SECRET", "")
        self.username = username or os.environ.get("SFDC_USERNAME", "")
        self._use_mock = not self.instance_url
        self._token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        if self._use_mock:
            logger.info("SalesforceConnector: using mock data (no SFDC_INSTANCE_URL)")
            return
        await self._authenticate()
        logger.info(f"SalesforceConnector: connected to {self.instance_url}")

    async def _authenticate(self) -> None:
        """OAuth 2.0 username-password flow (swap to JWT bearer for production)."""
        self._client = httpx.AsyncClient(timeout=30.0)
        token_url = f"{self.instance_url}/services/oauth2/token"

        resp = await self._client.post(token_url, data={
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
        })
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        # Update instance_url in case SFDC returns a different one
        if "instance_url" in data:
            self.instance_url = data["instance_url"]
        logger.info("SFDC: authenticated successfully")

    async def _query(self, soql: str) -> list[dict]:
        """Execute a SOQL query and return all records (handles pagination)."""
        if not self._client or not self._token:
            await self._authenticate()

        headers = {"Authorization": f"Bearer {self._token}"}
        url = f"{self.instance_url}/services/data/v59.0/query"
        all_records = []

        resp = await self._client.get(url, params={"q": soql}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        all_records.extend(data.get("records", []))

        # Handle pagination
        while not data.get("done", True) and data.get("nextRecordsUrl"):
            next_url = f"{self.instance_url}{data['nextRecordsUrl']}"
            resp = await self._client.get(next_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            all_records.extend(data.get("records", []))

        return all_records

    def _parse_org(self, record: dict, contacts: list[Contact] = None) -> MemberOrg:
        """Convert a SFDC Account record → MemberOrg model."""
        fm = SFDC_FIELD_MAP["account"]
        tier_raw = record.get(fm.get("Membership_Tier__c", "Membership_Tier__c"), "silver")
        tier = TIER_MAP.get(tier_raw, Tier.silver)

        def parse_date(val):
            if not val:
                return None
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return None

        return MemberOrg(
            org_id=record.get("Id", ""),
            org_name=record.get("Name", ""),
            tier=tier,
            foundation_id="aaif",
            status=record.get("Membership_Status__c", "active"),
            contract_signed=parse_date(record.get("Contract_Signed_Date__c")),
            contract_expiry=parse_date(record.get("Contract_Expiry_Date__c")),
            headcount_tier=record.get("Employee_Count_Range__c"),
            is_lf_member=bool(record.get("Is_LF_Member__c", False)),
            country=record.get("BillingCountry", "US"),
            contacts=contacts or [],
        )

    def _parse_contact(self, record: dict) -> Contact:
        """Convert a SFDC Contact record → Contact model."""
        role_raw = record.get("Membership_Role__c", "primary_contact")
        role = ROLE_MAP.get(role_raw, ContactRole.primary_contact)

        return Contact(
            contact_id=record.get("Id", ""),
            name=record.get("Name", ""),
            email=record.get("Email", ""),
            role=role,
            lfid=record.get("LFID__c"),
            lfid_verified=bool(record.get("LFID_Verified__c", False)),
            github_username=record.get("GitHub_Username__c"),
        )

    # ── Public API ────────────────────────────────────────────────────

    async def health_check(self) -> dict:
        if self._use_mock:
            return {"connector": "salesforce", "status": "healthy", "mode": "mock"}
        try:
            await self._query("SELECT Id FROM Account LIMIT 1")
            return {"connector": "salesforce", "status": "healthy", "mode": "live",
                    "instance_url": self.instance_url}
        except Exception as e:
            return {"connector": "salesforce", "status": "unhealthy", "mode": "live",
                    "error": str(e)}

    async def get_org(self, org_id: str) -> Optional[MemberOrg]:
        if self._use_mock:
            return MOCK_MEMBERS.get(org_id)

        # Query account
        account_fields = ", ".join(SFDC_FIELD_MAP["account"].keys())
        records = await self._query(
            f"SELECT {account_fields} FROM Account WHERE Id = '{org_id}'"
        )
        if not records:
            return None

        # Query associated contacts
        contact_fields = ", ".join(SFDC_FIELD_MAP["contact"].keys())
        contact_records = await self._query(
            f"SELECT {contact_fields} FROM Contact WHERE AccountId = '{org_id}'"
        )
        contacts = [self._parse_contact(r) for r in contact_records]

        return self._parse_org(records[0], contacts)

    async def get_org_by_name(self, org_name: str) -> Optional[MemberOrg]:
        if self._use_mock:
            for m in MOCK_MEMBERS.values():
                if m.org_name.lower() == org_name.lower():
                    return m
            return None

        account_fields = ", ".join(SFDC_FIELD_MAP["account"].keys())
        # Escape single quotes in name
        safe_name = org_name.replace("'", "\\'")
        records = await self._query(
            f"SELECT {account_fields} FROM Account WHERE Name = '{safe_name}'"
        )
        if not records:
            return None

        org = self._parse_org(records[0])
        # Load contacts
        org.contacts = await self.get_contacts(org.org_id)
        return org

    async def get_contacts(self, org_id: str) -> list[Contact]:
        if self._use_mock:
            org = MOCK_MEMBERS.get(org_id)
            return org.contacts if org else []

        contact_fields = ", ".join(SFDC_FIELD_MAP["contact"].keys())
        records = await self._query(
            f"SELECT {contact_fields} FROM Contact WHERE AccountId = '{org_id}'"
        )
        return [self._parse_contact(r) for r in records]

    async def list_orgs(self, foundation_id: str = "aaif") -> list[MemberOrg]:
        if self._use_mock:
            return [m for m in MOCK_MEMBERS.values() if m.foundation_id == foundation_id]

        account_fields = ", ".join(SFDC_FIELD_MAP["account"].keys())
        records = await self._query(
            f"SELECT {account_fields} FROM Account "
            f"WHERE Foundation__c = '{foundation_id}' "
            f"ORDER BY Name ASC"
        )
        orgs = []
        for r in records:
            org = self._parse_org(r)
            org.contacts = await self.get_contacts(org.org_id)
            orgs.append(org)
        return orgs

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
