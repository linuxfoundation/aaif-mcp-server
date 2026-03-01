from __future__ import annotations
"""Groups.io connector — mock + live implementation.

In dev mode (no api_token): uses in-memory mock data
In production: Groups.io REST API v1

To activate live mode, set:
    GROUPSIO_API_TOKEN=your_api_token
    GROUPSIO_ORG_ID=your_org_id (optional, for org-level operations)

API docs: https://groups.io/api
"""

import logging
import os
from typing import Optional

import httpx

from .base import BaseMailingListConnector
from ..config import MOCK_LIST_SUBSCRIPTIONS

logger = logging.getLogger(__name__)

GROUPSIO_BASE_URL = "https://groups.io/api/v1"

# In-memory store for mock mode (so mutations persist within a session)
_mock_subscriptions: dict[str, list[str]] = {}
_initialized = False


def _init_mock():
    global _mock_subscriptions, _initialized
    if not _initialized:
        _mock_subscriptions = {k: list(v) for k, v in MOCK_LIST_SUBSCRIPTIONS.items()}
        _initialized = True


class GroupsIOConnector(BaseMailingListConnector):
    """Groups.io mailing list connector. Mock data in dev; real API in production."""

    def __init__(self, api_token: str = "", org_id: str = ""):
        self.api_token = api_token or os.environ.get("GROUPSIO_API_TOKEN", "")
        self.org_id = org_id or os.environ.get("GROUPSIO_ORG_ID", "")
        self._use_mock = not self.api_token
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        if self._use_mock:
            _init_mock()
            logger.info("GroupsIOConnector: using mock data (no GROUPSIO_API_TOKEN)")
            return
        self._client = httpx.AsyncClient(
            base_url=GROUPSIO_BASE_URL,
            headers={"Authorization": f"Bearer {self.api_token}"},
            timeout=30.0,
        )
        logger.info("GroupsIOConnector: connected to Groups.io API")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an authenticated API request to Groups.io."""
        if not self._client:
            await self.initialize()
        resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _group_name_to_id(self, list_name: str) -> str:
        """Convert mailing list address to Groups.io group name.
        e.g., 'governing-board@lists.aaif.io' → 'governing-board'
        """
        return list_name.split("@")[0] if "@" in list_name else list_name

    # ── Public API ────────────────────────────────────────────────────

    async def health_check(self) -> dict:
        if self._use_mock:
            return {"connector": "groupsio", "status": "healthy", "mode": "mock"}
        try:
            data = await self._request("GET", "/getuser")
            return {"connector": "groupsio", "status": "healthy", "mode": "live",
                    "user": data.get("email", "unknown")}
        except Exception as e:
            return {"connector": "groupsio", "status": "unhealthy", "mode": "live",
                    "error": str(e)}

    async def add_member(self, list_name: str, email: str) -> dict:
        if self._use_mock:
            _init_mock()
            subs = _mock_subscriptions.setdefault(email, [])
            if list_name in subs:
                return {"status": "already_member", "list": list_name, "email": email}
            subs.append(list_name)
            logger.info(f"Mock: added {email} to {list_name}")
            return {"status": "added", "list": list_name, "email": email}

        # Live: POST /directadd
        group_name = self._group_name_to_id(list_name)
        try:
            data = await self._request("POST", "/directadd", data={
                "group_name": group_name,
                "emails": email,
            })
            added = data.get("added", [])
            if email.lower() in [e.lower() for e in added]:
                return {"status": "added", "list": list_name, "email": email}
            return {"status": "already_member", "list": list_name, "email": email}
        except httpx.HTTPStatusError as e:
            logger.error(f"Groups.io add_member failed: {e}")
            return {"status": "error", "list": list_name, "email": email,
                    "error": str(e)}

    async def remove_member(self, list_name: str, email: str) -> dict:
        if self._use_mock:
            _init_mock()
            subs = _mock_subscriptions.get(email, [])
            if list_name not in subs:
                return {"status": "not_member", "list": list_name, "email": email}
            subs.remove(list_name)
            logger.info(f"Mock: removed {email} from {list_name}")
            return {"status": "removed", "list": list_name, "email": email}

        # Live: POST /removemember
        group_name = self._group_name_to_id(list_name)
        try:
            await self._request("POST", "/removemember", data={
                "group_name": group_name,
                "email": email,
            })
            return {"status": "removed", "list": list_name, "email": email}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "not_member", "list": list_name, "email": email}
            logger.error(f"Groups.io remove_member failed: {e}")
            return {"status": "error", "list": list_name, "email": email,
                    "error": str(e)}

    async def get_members(self, list_name: str) -> list[str]:
        if self._use_mock:
            _init_mock()
            return [email for email, lists in _mock_subscriptions.items() if list_name in lists]

        # Live: GET /getmembers (paginated)
        group_name = self._group_name_to_id(list_name)
        all_members = []
        page_token = None

        while True:
            params = {"group_name": group_name, "limit": 100}
            if page_token:
                params["page_token"] = page_token

            data = await self._request("GET", "/getmembers", params=params)
            for member in data.get("data", []):
                all_members.append(member.get("email", ""))

            page_token = data.get("next_page_token")
            if not page_token:
                break

        return all_members

    async def is_member(self, list_name: str, email: str) -> bool:
        if self._use_mock:
            _init_mock()
            return list_name in _mock_subscriptions.get(email, [])

        # Live: GET /getmember
        group_name = self._group_name_to_id(list_name)
        try:
            await self._request("GET", "/getmember", params={
                "group_name": group_name,
                "email": email,
            })
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    async def get_lists(self, foundation_id: str) -> list[str]:
        if self._use_mock:
            _init_mock()
            all_lists = set()
            for subs in _mock_subscriptions.values():
                all_lists.update(subs)
            # Add known AAIF lists
            all_lists.update([
                "governing-board@lists.aaif.io",
                "technical-committee@lists.aaif.io",
                "members-all@lists.aaif.io",
                "outreach-committee@lists.aaif.io",
                "wg-agentic-commerce@lists.aaif.io",
                "wg-accuracy-reliability@lists.aaif.io",
                "wg-identity-trust@lists.aaif.io",
                "wg-observability@lists.aaif.io",
                "wg-workflows@lists.aaif.io",
            ])
            return sorted(all_lists)

        # Live: GET /getgroups (paginated)
        all_groups = []
        page_token = None

        while True:
            params = {"limit": 100}
            if page_token:
                params["page_token"] = page_token

            data = await self._request("GET", "/getgroups", params=params)
            for group in data.get("data", []):
                group_email = group.get("email", "")
                if group_email:
                    all_groups.append(group_email)

            page_token = data.get("next_page_token")
            if not page_token:
                break

        return sorted(all_groups)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
