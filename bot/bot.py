"""
BlogAI Telegram bot — capture article URL + notes from mobile.
Send one message: URL on any line, notes around it.
The bot parses them out and saves to the Notion drafts queue.
"""

import logging
import os
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from notion_queue import save_draft

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
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
        url = url_match.group(0).rstrip(".,)")  # strip common trailing punctuation
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
            reply = f"Saved. URL + notes queued in Notion."
        elif url:
            reply = f"Saved. URL queued (no notes)."
        else:
            reply = f"Saved as notes (no URL detected)."
        await update.message.reply_text(reply)
        logger.info("Saved draft — url=%s notes_len=%d notion=%s", url, len(notes), notion_url)
    except Exception as e:
        logger.error("Failed to save draft: %s", e)
        await update.message.reply_text(f"Failed to save: {e}")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
