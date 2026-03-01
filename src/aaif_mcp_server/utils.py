"""Utility functions for AAIF MCP Server.

Provides standardized response formatting for dry-run and execution modes,
as well as other cross-cutting utilities.
"""

from __future__ import annotations


def dry_run_response(
    *,
    entity: str,
    actions: dict,
    message: str,
    **extra
) -> dict:
    """Generate a standardized dry-run response.

    Used when a tool is called with dry_run=True to show what would happen
    without actually making changes.

    Args:
        entity: The type of entity being operated on (e.g., "contact", "mailing_list")
        actions: Dictionary of proposed actions (e.g., {"add_lists": [...], "remove_lists": [...]})
        message: Human-readable summary of what would happen
        **extra: Any additional fields to include in the response

    Returns:
        Dictionary with dry_run flag and standardized structure
    """
    return {
        "dry_run": True,
        "entity": entity,
        "proposed_actions": actions,
        "message": message,
        **extra
    }


def execute_response(
    *,
    entity: str,
    results: dict,
    message: str,
    **extra
) -> dict:
    """Generate a standardized execution response.

    Used when a tool actually executes changes (dry_run=False).

    Args:
        entity: The type of entity being operated on (e.g., "contact", "mailing_list")
        results: Dictionary of actual results from execution (e.g., {"added": [...], "errors": [...]})
        message: Human-readable summary of what was done
        **extra: Any additional fields to include in the response

    Returns:
        Dictionary with dry_run=False and standardized structure
    """
    return {
        "dry_run": False,
        "entity": entity,
        "results": results,
        "message": message,
        **extra
    }
