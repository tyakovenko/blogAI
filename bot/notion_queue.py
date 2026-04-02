"""
Notion drafts queue — saves incoming notes to the BlogAI Drafts database.
Requires NOTION_TOKEN and NOTION_DATABASE_ID in environment.
"""

import os
from notion_client import Client

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        token = os.getenv("NOTION_TOKEN")
        if not token:
            raise RuntimeError("NOTION_TOKEN not set")
        _client = Client(auth=token)
    return _client


def save_draft(url: str, notes: str) -> str:
    """
    Save a draft to the Notion queue.
    Returns the URL of the created page.
    """
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        raise RuntimeError("NOTION_DATABASE_ID not set")

    client = _get_client()
    title = url if url else (notes[:80] + "..." if len(notes) > 80 else notes)

    page = client.pages.create(
        parent={"database_id": database_id},
        properties={
            "Name": {"title": [{"text": {"content": title}}]},
            "userDefined:URL": {"url": url or None},
            "Notes": {"rich_text": [{"text": {"content": notes}}]},
            "Status": {"select": {"name": "Inbox"}},
        },
    )
    return page["url"]
