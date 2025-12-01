#!/usr/bin/env python3
"""Telegram toxicity filter bot for Render (Worker service, 24/7)"""


import os
import logging
import sys
from detoxify import Detoxify
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes


# ---------- Logging ----------
logger = logging.getLogger("toxicity_bot")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
logger.info("Starting Telegram toxicity bot")


# ---------- Configuration ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is required")
    sys.exit(1)


TOXICITY_THRESHOLD = float(os.getenv("TOXICITY_THRESHOLD", "0.7"))
CATEGORIES = [
    c.strip()
    for c in os.getenv("TOXIC_CATEGORIES", "toxicity,insult,threat,hate,obscene").split(
        ","
    )
]
DETOXIFY_MODEL = os.getenv("DETOXIFY_MODEL", "original")


# ---------- Load Model ----------
try:
    logger.info(f"Loading Detoxify model: {DETOXIFY_MODEL}")
    toxicity_model = Detoxify(DETOXIFY_MODEL)
    logger.info("Detoxify model loaded successfully")
except Exception as e:
    logger.exception("Failed to load Detoxify model")
    toxicity_model = None


# ---------- Core handler ----------
async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    user = update.message.from_user
    chat_id = update.message.chat_id

    if toxicity_model is None:
        logger.warning("Model not loaded; skipping analysis")
        return

    try:
        scores = toxicity_model.predict(text)
        logger.info(
            f"Message from @{getattr(user, 'username', user.id)}: {text} | scores: {scores}"
        )

        for category in CATEGORIES:
            score = float(scores.get(category, 0.0))
            if score >= TOXICITY_THRESHOLD:
                await _remove_and_warn(update, context, category, score)
                return

    except Exception:
        logger.exception("Error analyzing message")


async def _remove_and_warn(
    update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, score: float
):
    chat_id = update.message.chat_id
    user = update.message.from_user

    try:
        await context.bot.delete_message(chat_id, update.message.message_id)
        logger.info(f"Deleted message id={update.message.message_id}")
    except Exception:
        logger.exception("Failed to delete message; ensure bot is admin")

    username = getattr(user, "username", None) or (user.first_name or "user")
    try:
        await context.bot.send_message(
            chat_id,
            text=f"⚠️ @{username} your message was removed.\nReason: {category} detected ({score:.2f}).",
        )
        logger.info(f"Warned user @{username}")
    except Exception:
        logger.exception("Failed to send warning message")


# ---------- Bot Runner ----------
def run():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))
    logger.info("Starting polling...")
    app.run_polling()


if __name__ == "__main__":
    run()
