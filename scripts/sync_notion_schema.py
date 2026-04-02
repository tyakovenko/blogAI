"""
Sync OUTPUT_FORMATS from app/config.py to the Notion Blog Posts database.

Adds a RICH_TEXT column for any format that doesn't have one yet.
Blog Post drafts are stored as page body content (not a column) — skipped here.
Run this whenever you add a new format to OUTPUT_FORMATS.

Usage:
    python scripts/sync_notion_schema.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from notion_client import Client

from app.config import OUTPUT_FORMATS

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Formats stored as page body, not columns — exclude from schema sync
BODY_FORMATS = {"Blog Post"}


def get_existing_columns(client: Client, database_id: str) -> set[str]:
    db = client.databases.retrieve(database_id=database_id)
    return set(db["properties"].keys())


def sync_schema() -> None:
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN not set in .env")
    if not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_DATABASE_ID not set in .env")

    client = Client(auth=NOTION_TOKEN)
    existing = get_existing_columns(client, NOTION_DATABASE_ID)

    formats_to_add = [
        fmt for fmt in OUTPUT_FORMATS
        if fmt not in BODY_FORMATS and fmt not in existing
    ]

    if not formats_to_add:
        print("Schema already up to date.")
        return

    new_properties = {
        fmt: {"rich_text": {}} for fmt in formats_to_add
    }

    client.databases.update(
        database_id=NOTION_DATABASE_ID,
        properties=new_properties,
    )

    for fmt in formats_to_add:
        print(f"Added column: {fmt}")


if __name__ == "__main__":
    sync_schema()
