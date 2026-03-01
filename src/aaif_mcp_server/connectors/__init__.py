"""Connector layer — abstract interfaces + implementations for external systems."""
from .base import BaseConnector
from .salesforce import SalesforceConnector
from .groupsio import GroupsIOConnector

__all__ = ["BaseConnector", "SalesforceConnector", "GroupsIOConnector"]
