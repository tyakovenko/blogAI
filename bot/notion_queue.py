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


def _text_blocks(text: str) -> list[dict]:
    """Split text into Notion paragraph blocks, max 2000 chars each."""
    blocks = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        # Notion rich_text max is 2000 chars per element
        for chunk in [para[i:i+2000] for i in range(0, len(para), 2000)]:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
            })
    return blocks


def save_generated_draft(url: str, notes: str, blog_post: str = "", linkedin: str = "") -> str:
    """
    Save a fully generated draft to Notion.
    Blog post goes into the page body. LinkedIn goes into the LinkedIn property.
    Either can be omitted if not generated. Status is set to Draft Generated.
    """
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        raise RuntimeError("NOTION_DATABASE_ID not set")

    client = _get_client()

    # Extract title from blog post — first "Title: ..." line, or first non-empty line.
    # Fall back to truncated notes, then URL.
    title = None
    if blog_post:
        for line in blog_post.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("title:"):
                title = stripped[len("title:"):].strip()
                break
            elif stripped:
                title = stripped[:120]
                break
    if not title:
        title = (notes[:80] + "...") if len(notes) > 80 else notes
    if not title:
        title = url

    properties = {
        "Name": {"title": [{"text": {"content": title}}]},
        "URL": {"url": url or None},
        "Notes": {"rich_text": [{"text": {"content": notes[:2000]}}]},
        "Status": {"select": {"name": "Draft Generated"}},
    }
    if blog_post:
        properties["Blog Post"] = {"rich_text": [{"text": {"content": blog_post[:2000]}}]}
    if linkedin:
        properties["LinkedIn"] = {"rich_text": [{"text": {"content": linkedin[:2000]}}]}

    page = client.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        children=_text_blocks(blog_post) if blog_post else [],
    )
    return page["url"]


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
            "URL": {"url": url or None},
            "Notes": {"rich_text": [{"text": {"content": notes}}]},
            "Status": {"select": {"name": "Inbox"}},
        },
    )
    return page["url"]
