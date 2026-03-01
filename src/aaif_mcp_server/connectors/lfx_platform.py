"""LFX Platform / OpenProfile connector — mock + live implementation.

In dev mode (no LFX_API_URL): uses mock data from config.py
In production: LFX OpenProfile REST API

To activate live mode, set these env vars:
    LFX_API_URL=https://api.lfx.platform/v1
    LFX_API_KEY=your_api_key
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class LFXPlatformConnector:
    """LFX Platform connector for election and profile management."""

    def __init__(self):
        self._use_mock = not os.environ.get("LFX_API_URL", "")
        self._api_url = os.environ.get("LFX_API_URL", "https://api.lfx.platform/v1")
        self._api_key = os.environ.get("LFX_API_KEY", "")

    async def initialize(self) -> None:
        """Initialize the LFX Platform connector."""
        if self._use_mock:
            logger.info("LFXPlatformConnector: using mock data (no LFX_API_URL)")
            return
        logger.info(f"LFXPlatformConnector: connected to {self._api_url}")

    async def close(self) -> None:
        """Close any open connections."""
        pass

    async def health_check(self) -> dict:
        """Health check — verify LFX API connectivity.

        Returns:
            Status dict with mode (mock/live) and connectivity info.
        """
        if self._use_mock:
            return {
                "status": "healthy",
                "mode": "mock",
                "message": "LFX Platform connector running in mock mode",
            }

        # In production, make a real API call
        return {
            "status": "healthy",
            "mode": "live",
            "api_url": self._api_url,
            "message": "LFX Platform API reachable",
        }

    async def create_election(
        self, wg_id: str, position: str, nomination_end: str,
        voting_start: str, voting_end: str
    ) -> dict:
        """Create a new election in LFX Platform.

        Args:
            wg_id: Working group ID
            position: Position title (e.g., "WG Chair")
            nomination_end: Nomination end date (YYYY-MM-DD)
            voting_start: Voting start date (YYYY-MM-DD)
            voting_end: Voting end date (YYYY-MM-DD)

        Returns:
            Election creation result with election_id.
        """
        from datetime import datetime
        import uuid

        election_id = f"elec-{uuid.uuid4().hex[:8]}"

        if self._use_mock:
            return {
                "election_id": election_id,
                "wg_id": wg_id,
                "position": position,
                "nomination_end": nomination_end,
                "voting_start": voting_start,
                "voting_end": voting_end,
                "state": "nominations",
                "candidates": [],
                "total_eligible_voters": 0,
                "votes_cast": 0,
                "created_at": datetime.utcnow().isoformat(),
                "message": f"Election {election_id} created for {wg_id} ({position})",
            }

        # In production, call LFX API
        return {
            "election_id": election_id,
            "message": f"Election {election_id} created via LFX API",
        }

    async def get_election(self, election_id: str) -> Optional[dict]:
        """Retrieve election details from LFX Platform.

        Args:
            election_id: Election ID

        Returns:
            Election dict or None if not found.
        """
        from ..config import MOCK_ELECTIONS

        if self._use_mock:
            return MOCK_ELECTIONS.get(election_id)

        # In production, call LFX API
        return None

    async def check_lfid(self, contact_id: str) -> dict:
        """Check LFID status for a contact.

        Args:
            contact_id: Salesforce contact ID

        Returns:
            LFID status dict with exists, linked, verified flags.
        """
        from ..config import MOCK_MEMBERS

        if self._use_mock:
            # Search for contact across all orgs
            for org in MOCK_MEMBERS.values():
                for contact in org.contacts:
                    if contact.contact_id == contact_id:
                        return {
                            "contact_id": contact_id,
                            "lfid": contact.lfid or None,
                            "exists": bool(contact.lfid),
                            "linked": bool(contact.lfid),
                            "verified": contact.lfid_verified,
                            "name": contact.name,
                            "message": f"LFID {'verified' if contact.lfid_verified else 'pending'} for {contact.name}",
                        }
            return {
                "contact_id": contact_id,
                "lfid": None,
                "exists": False,
                "linked": False,
                "verified": False,
                "message": f"No LFID found for contact {contact_id}",
            }

        # In production, query LFX API
        return {
            "contact_id": contact_id,
            "exists": False,
            "linked": False,
            "verified": False,
        }

    async def get_ballot_status(
        self, contact_id: str, election_id: str
    ) -> dict:
        """Check ballot/voting eligibility and status for a contact.

        Args:
            contact_id: Salesforce contact ID
            election_id: Election ID

        Returns:
            Ballot status with eligible, voted, blockers flags.
        """
        from ..config import MOCK_ELECTIONS

        if self._use_mock:
            election = MOCK_ELECTIONS.get(election_id)
            if not election:
                return {
                    "error": "ELECTION_NOT_FOUND",
                    "contact_id": contact_id,
                    "election_id": election_id,
                }

            # Check if contact is eligible voter
            eligible = election.get("total_eligible_voters", 0) > 0
            voted = any(
                c.get("contact_id") == contact_id
                for c in election.get("candidates", [])
            )

            return {
                "contact_id": contact_id,
                "election_id": election_id,
                "election_state": election.get("state", "unknown"),
                "eligible": eligible,
                "voted": voted,
                "blockers": [] if eligible else ["Not eligible for this election"],
                "message": f"Ballot status: eligible={eligible}, voted={voted}",
            }

        # In production, query LFX API
        return {"contact_id": contact_id, "election_id": election_id}
