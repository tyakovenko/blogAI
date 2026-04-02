"""
BlogAI Telegram bot — interactive pipeline + Notion save.

Flow:
  1. Send URL + optional notes → pipeline runs → Blog Post + LinkedIn drafts returned
  2. Reply with a correction instruction → Haiku applies it → revised Blog Post returned
  3. /save  → save current drafts to Notion (Status: Draft Generated)
  4. /discard → cancel current draft

State is in-memory per chat_id. Restarts clear state.
"""

import asyncio
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from app.pipeline import generate_post
from .notion_queue import save_generated_draft

load_dotenv()

ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://\S+")

# Per-chat state: {chat_id: {"state": "idle"|"reviewing", "url": str, "notes": str, "drafts": dict}}
_conversations: dict[int, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_message(text: str) -> tuple[str, str]:
    url_match = URL_RE.search(text)
    if url_match:
        url = url_match.group(0).rstrip(".,)")
        notes = URL_RE.sub("", text).strip()
    else:
        url = ""
        notes = text.strip()
    return url, notes


def _run_pipeline(url: str, notes: str) -> dict:
    return generate_post(url, notes, tone="blog_social")


def _apply_correction(draft: str, instruction: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        system=(
            "You are editing a blog post draft. Apply the user's correction exactly as instructed. "
            "Return only the revised post — no preamble, no commentary."
        ),
        messages=[{"role": "user", "content": f"Draft:\n{draft}\n\nCorrection: {instruction}"}],
    )
    return response.content[0].text.strip()


def _is_authorized(user_id: int) -> bool:
    return not ALLOWED_USER_ID or user_id == ALLOWED_USER_ID


# ── Handlers ─────────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not _is_authorized(user_id):
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    state = _conversations.get(chat_id, {}).get("state", "idle")

    if state == "idle":
        url, notes = _parse_message(text)
        if not url and not notes:
            await update.message.reply_text("Send a URL and/or notes.")
            return

        await update.message.reply_text("Running pipeline...")

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(_executor, _run_pipeline, url, notes)
        except Exception as e:
            logger.error("Pipeline error: %s", e)
            await update.message.reply_text(f"Pipeline failed: {e}")
            return

        drafts = result["drafts"]
        _conversations[chat_id] = {"state": "reviewing", "url": url, "notes": notes, "drafts": drafts}

        blog = drafts.get("Blog Post", "")
        linkedin = drafts.get("LinkedIn", "")

        await update.message.reply_text(f"*Blog Post*\n\n{blog}", parse_mode="Markdown")
        await update.message.reply_text(f"*LinkedIn*\n\n{linkedin}", parse_mode="Markdown")
        await update.message.reply_text(
            f"Generated with {result['model_used']} in {result['latency']}s\n\n"
            "Reply to edit the blog post. /save to save to Notion. /discard to cancel."
        )

    elif state == "reviewing":
        current_draft = _conversations[chat_id]["drafts"]["Blog Post"]
        await update.message.reply_text("Applying correction...")

        loop = asyncio.get_event_loop()
        try:
            updated = await loop.run_in_executor(_executor, _apply_correction, current_draft, text)
        except Exception as e:
            logger.error("Correction error: %s", e)
            await update.message.reply_text(f"Correction failed: {e}")
            return

        _conversations[chat_id]["drafts"]["Blog Post"] = updated
        await update.message.reply_text(f"*Blog Post*\n\n{updated}", parse_mode="Markdown")
        await update.message.reply_text("Reply to edit more. /save to save. /discard to cancel.")


async def handle_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not _is_authorized(user_id):
        return

    conv = _conversations.get(chat_id)
    if not conv or conv.get("state") != "reviewing":
        await update.message.reply_text("Nothing to save. Send a URL + notes first.")
        return

    await update.message.reply_text("Saving to Notion...")
    try:
        notion_url = save_generated_draft(
            url=conv["url"],
            notes=conv["notes"],
            blog_post=conv["drafts"]["Blog Post"],
            linkedin=conv["drafts"]["LinkedIn"],
        )
        _conversations.pop(chat_id, None)
        await update.message.reply_text(f"Saved. {notion_url}")
        logger.info("Draft saved to Notion: %s", notion_url)
    except Exception as e:
        logger.error("Notion save error: %s", e)
        await update.message.reply_text(f"Failed to save: {e}")


async def handle_discard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not _is_authorized(user_id):
        return

    _conversations.pop(chat_id, None)
    await update.message.reply_text("Draft discarded.")


# ── App builder ───────────────────────────────────────────────────────────────

def _build_app(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("save", handle_save))
    app.add_handler(CommandHandler("discard", handle_discard))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


def start_polling_in_background() -> None:
    """Start the bot in a background daemon thread alongside the Gradio app."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot will not start")
        return

    async def _run() -> None:
        app = _build_app(token)
        async with app:
            await app.start()
            await app.updater.start_polling()
            await asyncio.Event().wait()

    def _thread() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())

    threading.Thread(target=_thread, daemon=True, name="telegram-bot").start()
    logger.info("Telegram bot polling started in background thread")


if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    _build_app(token).run_polling()
