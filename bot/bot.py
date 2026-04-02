"""
BlogAI Telegram bot — capture article URL + notes from mobile.
Send one message: URL on any line, notes around it.
The bot parses them out and saves to the Notion drafts queue.

Can run standalone (python -m bot.bot) or embedded in the Gradio app
via start_polling_in_background().
"""

import asyncio
import logging
import os
import re
import threading

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from .notion_queue import save_draft

load_dotenv()

ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://\S+")


def parse_message(text: str) -> tuple[str, str]:
    """
    Extract (url, notes) from a single Telegram message.
    URL = first http/https link found.
    Notes = everything else, whitespace-collapsed.
    """
    url_match = URL_RE.search(text)
    if url_match:
        url = url_match.group(0).rstrip(".,)")
        notes = URL_RE.sub("", text).strip()
    else:
        url = ""
        notes = text.strip()
    return url, notes


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
        logger.warning("Unauthorized message from user_id=%s", user_id)
        return

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Send a URL and/or notes in one message.")
        return

    url, notes = parse_message(text)

    if not url and not notes:
        await update.message.reply_text("Nothing to save.")
        return

    try:
        notion_url = save_draft(url=url, notes=notes)
        if url and notes:
            reply = "Saved. URL + notes queued in Notion."
        elif url:
            reply = "Saved. URL queued (no notes)."
        else:
            reply = "Saved as notes (no URL detected)."
        await update.message.reply_text(reply)
        logger.info("Saved draft — url=%s notes_len=%d notion=%s", url, len(notes), notion_url)
    except Exception as e:
        logger.error("Failed to save draft: %s", e)
        await update.message.reply_text(f"Failed to save: {e}")


def _build_app(token: str):
    app = ApplicationBuilder().token(token).build()
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
            await asyncio.Event().wait()  # run until process exits

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
