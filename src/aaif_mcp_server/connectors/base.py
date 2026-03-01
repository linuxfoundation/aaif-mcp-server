from __future__ import annotations
"""Abstract base connector interface.

All connectors implement this interface so tools can be tested with mock data
and swapped to real APIs without changing tool logic.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import Contact, MemberOrg


class BaseConnector(ABC):
    """Abstract base for all external system connectors."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection (auth, session setup)."""
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """Return connector health status."""
        ...


class BaseCRMConnector(BaseConnector):
    """Abstract CRM connector (Salesforce, HubSpot)."""

    @abstractmethod
    async def get_org(self, org_id: str) -> Optional[MemberOrg]:
        ...

    @abstractmethod
    async def get_org_by_name(self, org_name: str) -> Optional[MemberOrg]:
        ...

    @abstractmethod
    async def get_contacts(self, org_id: str) -> list[Contact]:
        ...

    @abstractmethod
    async def list_orgs(self, foundation_id: str = "aaif") -> list[MemberOrg]:
        ...


class BaseMailingListConnector(BaseConnector):
    """Abstract mailing list connector (Groups.io, Google Groups)."""

    @abstractmethod
    async def add_member(self, list_name: str, email: str) -> dict:
        ...

    @abstractmethod
    async def remove_member(self, list_name: str, email: str) -> dict:
        ...

    @abstractmethod
    async def get_members(self, list_name: str) -> list[str]:
        ...

    @abstractmethod
    async def is_member(self, list_name: str, email: str) -> bool:
        ...

    @abstractmethod
    async def get_lists(self, foundation_id: str) -> list[str]:
        ...
