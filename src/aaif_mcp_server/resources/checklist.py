from __future__ import annotations
"""MCP Resource: checklist:// — Onboarding checklist templates.

URI patterns:
  checklist://aaif              → Full D1-D5 checklist template
  checklist://aaif/{deliverable} → Single deliverable (e.g., checklist://aaif/D3)
"""

from ..config import CHECKLIST_TEMPLATES


async def get_checklist_template(foundation_id: str = "aaif") -> dict:
    """Return the full onboarding checklist template."""
    template = CHECKLIST_TEMPLATES.get(foundation_id)
    if not template:
        return {"error": "NOT_FOUND", "message": f"No checklist for '{foundation_id}'"}

    return template.model_dump(mode="json")


async def get_deliverable_template(deliverable_id: str, foundation_id: str = "aaif") -> dict:
    """Return a single deliverable's checklist items."""
    template = CHECKLIST_TEMPLATES.get(foundation_id)
    if not template:
        return {"error": "NOT_FOUND", "message": f"No checklist for '{foundation_id}'"}

    for d in template.deliverables:
        if d["id"] == deliverable_id.upper():
            return d

    return {
        "error": "DELIVERABLE_NOT_FOUND",
        "message": f"No deliverable '{deliverable_id}' in '{foundation_id}'",
        "available": [d["id"] for d in template.deliverables],
    }
