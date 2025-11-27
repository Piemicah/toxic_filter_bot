import logging
import time
from detoxify import Detoxify
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

# -----------------------------------------------------------
# Logging (writes logs to PythonAnywhere "files" tab → bot.log)
# -----------------------------------------------------------
logging.basicConfig(
    filename="bot.log",
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.info("Bot starting...")

# -----------------------------------------------------------
# Load Fast Toxicity Model
# -----------------------------------------------------------
try:
    toxicity_model = Detoxify("unbiased-small")
    logging.info("Detoxify model loaded successfully.")
except Exception as e:
    logging.error(f"Detoxify failed to load: {e}")
    toxicity_model = None


# -----------------------------------------------------------
# Configuration
# -----------------------------------------------------------
TOXICITY_THRESHOLD = 0.70

CATEGORIES = [
    "toxicity",
    "insult",
    "threat",
    "hate",
    "obscene",
]


# -----------------------------------------------------------
# Core Handler
# -----------------------------------------------------------
async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    text = update.message.text

    # Model is required
    if toxicity_model is None:
        return

    try:
        scores = toxicity_model.predict(text)
        logging.info(f"Message: '{text}' Scores: {scores}")

        # Check toxicity
        for category in CATEGORIES:
            score = float(scores.get(category, 0))
            if score >= TOXICITY_THRESHOLD:
                await remove(update, context, category, score)
                return

    except Exception as e:
        logging.error(f"Error analyzing message: {e}")


# -----------------------------------------------------------
# Remove Message & Warn User
# -----------------------------------------------------------
async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE, category, score):
    chat_id = update.message.chat_id
    user = update.message.from_user

    # Delete message
    try:
        await context.bot.delete_message(chat_id, update.message.message_id)
    except Exception as e:
        logging.error(f"Delete failed: {e}")

    # Send warning
    try:
        await context.bot.send_message(
            chat_id,
            text=(
                f"⚠️ @{user.username} your message was removed.\n"
                f"Reason: **{category} detected** ({score:.2f})"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logging.error(f"Warning message failed: {e}")


# -----------------------------------------------------------
# Bot Runner with Auto-Restart Protection
# -----------------------------------------------------------
def run_bot():
    BOT_TOKEN = "8536975334:AAHjCrCvzKA6wAl-6IuqI02EoSpsRz2DPG0"

    while True:  # auto restart loop (PythonAnywhere safe)
        try:
            app = ApplicationBuilder().token(BOT_TOKEN).build()
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))

            logging.info("Bot polling started.")
            app.run_polling()

        except Exception as e:
            logging.error(f"Bot crashed: {e}")
            time.sleep(5)  # prevent crash loop


if __name__ == "__main__":
    run_bot()
