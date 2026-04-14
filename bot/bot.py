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
from app.config import AVAILABLE_MODELS, DEFAULT_MODEL_KEY, MODEL_SHORTCUTS
from .notion_queue import save_generated_draft

load_dotenv()

ALLOWED_USER_ID = int(os.getenv("TELEGRAM_ALLOWED_USER_ID", "0"))

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://\S+")

# Per-chat state:
# {chat_id: {"state": "idle"|"reviewing"|"awaiting_input", "mode": "blog"|"linkedin"|"all",
#             "url": str, "notes": str, "drafts": dict}}
_conversations: dict[int, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)

MODE_FORMATS = {
    "blog": ["Blog Post"],
    "linkedin": ["LinkedIn"],
    "all": None,  # None means all OUTPUT_FORMATS
}


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


def _run_pipeline(url: str, notes: str, mode: str = "all", model_key: str = DEFAULT_MODEL_KEY) -> dict:
    return generate_post(url, notes, tone="blog_social", formats=MODE_FORMATS[mode], model_key=model_key)


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

    if state in ("idle", "awaiting_input"):
        url, notes = _parse_message(text)
        if not url and not notes:
            await update.message.reply_text("Send a URL and/or notes.")
            return

        mode = _conversations.get(chat_id, {}).get("mode", "all")
        model_key = _conversations.get(chat_id, {}).get("model_key", DEFAULT_MODEL_KEY)
        await update.message.reply_text(f"Running pipeline ({mode} mode, {model_key})...")

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(_executor, _run_pipeline, url, notes, mode, model_key)
        except Exception as e:
            logger.error("Pipeline error: %s", e)
            await update.message.reply_text(f"Pipeline failed: {e}")
            return

        drafts = result["drafts"]
        _conversations[chat_id] = {"state": "reviewing", "mode": mode, "url": url, "notes": notes, "drafts": drafts}

        blog = drafts.get("Blog Post", "")
        linkedin = drafts.get("LinkedIn", "")

        if result.get("auto_notes"):
            await update.message.reply_text(f"No notes provided — used AI summary:\n\n{result['auto_notes']}")
        if blog:
            await update.message.reply_text(f"Blog Post:\n\n{blog}")
        if linkedin:
            await update.message.reply_text(f"LinkedIn:\n\n{linkedin}")
        await update.message.reply_text(
            f"Generated with {result['model_used']} in {result['latency']}s\n\n"
            "Reply to edit. /save to save to Notion. /discard to cancel."
        )

    elif state == "reviewing":
        conv = _conversations[chat_id]
        mode = conv.get("mode", "all")
        # Corrections apply to the primary draft for this mode
        draft_key = "LinkedIn" if mode == "linkedin" else "Blog Post"

        try:
            current_draft = conv["drafts"][draft_key]
        except KeyError:
            await update.message.reply_text(f"No {draft_key} draft found. Send a URL to start over.")
            return

        await update.message.reply_text("Applying correction...")

        loop = asyncio.get_event_loop()
        try:
            updated = await loop.run_in_executor(_executor, _apply_correction, current_draft, text)
        except Exception as e:
            logger.error("Correction error: %s", e)
            await update.message.reply_text(f"Correction failed: {e}")
            return

        _conversations[chat_id]["drafts"][draft_key] = updated
        label = "LinkedIn" if mode == "linkedin" else "Blog Post"
        await update.message.reply_text(f"{label}:\n\n{updated}")
        await update.message.reply_text("Reply to edit more. /save to save. /discard to cancel.")


async def handle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not _is_authorized(user_id):
        return

    existing = _conversations.get(chat_id, {})
    _conversations[chat_id] = {**existing, "state": "awaiting_input", "mode": mode}
    await update.message.reply_text(f"Mode set to {mode}. Send a URL and notes.")


async def handle_blog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_mode(update, context, "blog")


async def handle_linkedin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_mode(update, context, "linkedin")


async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_mode(update, context, "all")


async def handle_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not _is_authorized(user_id):
        return

    args = context.args  # words after /model

    if not args:
        # Show current model and available options
        current = _conversations.get(chat_id, {}).get("model_key", DEFAULT_MODEL_KEY)
        options = "\n".join(f"  {shortcut} → {key}" for shortcut, key in MODEL_SHORTCUTS.items())
        await update.message.reply_text(
            f"Current model: {current}\n\nAvailable:\n{options}\n\nUsage: /model gemma"
        )
        return

    shortcut = args[0].lower()
    model_key = MODEL_SHORTCUTS.get(shortcut)

    if not model_key:
        await update.message.reply_text(
            f"Unknown model '{shortcut}'. Options: {', '.join(MODEL_SHORTCUTS.keys())}"
        )
        return

    existing = _conversations.get(chat_id, {})
    _conversations[chat_id] = {**existing, "model_key": model_key}
    await update.message.reply_text(f"Model set to {model_key}.")


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
        # Use .get() so missing keys (e.g. linkedin in /blog mode) pass as empty string
        notion_url = save_generated_draft(
            url=conv["url"],
            notes=conv["notes"],
            blog_post=conv["drafts"].get("Blog Post", ""),
            linkedin=conv["drafts"].get("LinkedIn", ""),
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


# ── Error handler ─────────────────────────────────────────────────────────────

async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global fallback: any unhandled exception in any handler lands here.
    Always replies so the user sees the failure instead of silence.
    """
    logger.error("Unhandled exception in handler", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(f"Something went wrong: {context.error}")


# ── App builder ───────────────────────────────────────────────────────────────

def _build_app(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("blog", handle_blog))
    app.add_handler(CommandHandler("linkedin", handle_linkedin_cmd))
    app.add_handler(CommandHandler("all", handle_all))
    app.add_handler(CommandHandler("model", handle_model))
    app.add_handler(CommandHandler("save", handle_save))
    app.add_handler(CommandHandler("discard", handle_discard))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(handle_error)
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
            # Notify the allowed user that the bot is back online.
            # Can't message when down — but we can message on recovery.
            if ALLOWED_USER_ID:
                try:
                    await app.bot.send_message(chat_id=ALLOWED_USER_ID, text="Bot is online.")
                except Exception as e:
                    logger.warning("Could not send startup notification: %s", e)
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
