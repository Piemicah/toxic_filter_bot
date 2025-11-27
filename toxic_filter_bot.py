import logging
from detoxify import Detoxify
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Load toxicity model (Detoxify)
toxicity_model = Detoxify("original")

# Toxicity threshold (increase = more strict)
TOXICITY_THRESHOLD = 0.75

# Optional: specific categories to monitor
TOXIC_CATEGORIES = ["toxicity", "insult", "threat", "hate", "obscene"]


async def analyze_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    text = update.message.text

    # Run toxicity analysis
    scores = toxicity_model.predict(text)

    # Example scores:
    # {'toxicity': 0.92, 'insult': 0.88, ...}

    # Check if any monitored category is above threshold
    for category in TOXIC_CATEGORIES:
        score = scores.get(category, 0)
        if score >= TOXICITY_THRESHOLD:
            await delete_and_warn(
                update, context, reason=f"{category} score too high ({score:.2f})"
            )
            return  # stop after one detection


async def delete_and_warn(
    update: Update, context: ContextTypes.DEFAULT_TYPE, reason=""
):
    chat_id = update.message.chat_id
    user = update.message.from_user

    # Delete the message
    try:
        await context.bot.delete_message(chat_id, update.message.message_id)
    except:
        pass  # Bot must be admin!

    # Send warning in the chat
    await context.bot.send_message(
        chat_id, text=f"⚠️ @{user.username} your message was removed.\nReason: {reason}"
    )


def main():
    BOT_TOKEN = "8536975334:AAHjCrCvzKA6wAl-6IuqI02EoSpsRz2DPG0"

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Listen for any text messages
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), analyze_message))

    print("Toxicity Filter Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()
