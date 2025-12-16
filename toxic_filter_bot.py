import logging
import time
import sqlite3
from datetime import datetime
import re
from detoxify import Detoxify
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
)
import os


DB_NAME = "deleted_messages.db"
BOT_TOKEN = os.getenv("BOT_TOKEN")


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS deleted_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            message TEXT,
            reason TEXT,
            timestamp TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def save_deleted_message(chat_id, user_id, username, message, reason):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO deleted_messages
        (chat_id, user_id, username, message, reason, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (chat_id, user_id, username, message, reason, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# -------------------------------------
# Load Detoxify Model
# -------------------------------------
toxicity_model = Detoxify("original")

TOXICITY_THRESHOLD = 0.90
TOXIC_CATEGORIES = ["toxicity", "insult", "threat", "hate", "obscene"]


# -------------------------------------
# FULL NEGATIVE WORD LIST (400+ words)
# -------------------------------------
NEGATIVE_WORDS = {
    "scam",
    "scammer",
    "fraud",
    "fraudster",
    "419",
    "criminal",
    "thief",
    "crook",
    "liar",
    "misleader",
    "idiot",
    "stupid",
    "dumb",
    "fool",
    "foolish",
    "nonsense",
    "nonsensical",
    "useless",
    "worthless",
    "bastard",
    "bitch",
    "ashawo",
    "prostitute",
    "hoe",
    "slut",
    "whore",
    "harlot",
    "simp",
    "loser",
    "coward",
    "trash",
    "garbage",
    "pig",
    "goat",
    "animal",
    "dog",
    "snake",
    "demon",
    "witch",
    "wizard",
    "satan",
    "devil",
    "crazy",
    "mad",
    "insane",
    "lunatic",
    "psycho",
    "retard",
    "moron",
    "imbecile",
    "silly",
    "disgrace",
    "curse",
    "cursed",
    "accursed",
    "fuck",
    "fucking",
    "fucked",
    "shit",
    "bullshit",
    "ass",
    "arse",
    "asshole",
    "prick",
    "dick",
    "pussy",
    "cock",
    "bastard",
    "bloody",
    "hell",
    "damn",
    "damned",
    "cunt",
    "motherfucker",
    "terrorist",
    "killer",
    "murderer",
    "rapist",
    "abuser",
    "predator",
    "evil",
    "wicked",
    "toxic",
    "poison",
    "horrible",
    "terrible",
    "disgusting",
    "dirty",
    "filthy",
    "nasty",
    "rotten",
    "stinky",
    "smelly",
    "ugly",
    "weak",
    "pathetic",
    "shameless",
    "heartless",
    "soulless",
    "brainless",
    "dense",
    "dolt",
    "blockhead",
    "jerk",
    "clown",
    "joker",
    "bozo",
    "buffoon",
    "idiotic",
    "trash",
    "scrap",
    "reject",
    "failure",
    "frail",
    "stupid",
    "ignorant",
    "illiterate",
    "slow",
    "dull",
    "lazy",
    "beggar",
    "parasite",
    "leech",
    "mooch",
    "scoundrel",
    "villain",
    "rogue",
    "miscreant",
    "pest",
    "plague",
    "vermin",
    "disease",
    "virus",
    "toxin",
    "snake",
    "cobra",
    "viper",
    "rat",
    "rodent",
    "goat",
    "donkey",
    "monkey",
    "chimp",
    "baboon",
    "ape",
    "hog",
    "pig",
    "cow",
    "buffalo",
    "camel",
    "sheep",
    "worm",
    "bug",
    "insect",
    "maggot",
    "cockroach",
    "roach",
    "dirt",
    "rubbish",
    "junk",
    "waste",
    "scrap",
    "leftover",
    "reject",
    "castaway",
    "outcast",
    "nobody",
    "nigga",
    "negro",
    "coon",
    "chimp",
    "monkey",
    "ape",  # racial slurs (detect only)
    "stinker",
    "weirdo",
    "creep",
    "pervert",
    "idiotic",
    "barbaric",
    "freak",
    "lunatic",
    "dumbass",
    "shitty",
    "crappy",
    "pathetic",
    "annoying",
    "frustrating",
    "irritating",
    "vile",
    "abhorrent",
    "hateful",
    "bigot",
    "racist",
    "sexist",
    "misogynist",
    "misandrist",
    "oppressor",
    "abomination",
    "atrocity",
    "offender",
    "foul",
    "gross",
    "mean",
    "hostile",
    "aggressive",
    "bull",
    "goat",
    "mumu",
    "ode",
    "werey",
    "ode",
    "oloshi",
    "olosho",
    "olodo",
    "oloriburuku",
    "senseless",
    "maddo",
    "jaga",
    # common Nigerian insults added
    "shameless",
    "senseless",
    "ewu",
    "osiso",
    "onye",
    "onyeoshi",
    "ogbanje",
    "rug",
    "rugs",
    "rugger" "fud",
    "pump",
    "dump",
    "dumps",
    "dip",
}


# -------------------------------------
# Function: Detect standalone negative words
# -------------------------------------
def contains_negative_word(text: str) -> str | None:
    text = text.lower()
    words = re.findall(r"\b\w+\b", text)

    for w in words:
        if w in NEGATIVE_WORDS:
            return w
    return None


# -------------------------------------
# Main Analyzer
# -------------------------------------
async def analyze_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text

    # 1️⃣ Check standalone words
    found_word = contains_negative_word(text)
    if found_word:
        await delete_and_warn(
            update, context, reason=f'Negative word detected: "{found_word}"'
        )
        return

    # 2️⃣ Check Detoxify toxicity levels
    scores = toxicity_model.predict(text)
    for category in TOXIC_CATEGORIES:
        if scores.get(category, 0) >= TOXICITY_THRESHOLD:
            await delete_and_warn(update, context, reason=f"{category} detected")
            return


# -------------------------------------
# Delete + warn user
# -------------------------------------
async def delete_and_warn(
    update: Update, context: ContextTypes.DEFAULT_TYPE, reason=""
):

    message = update.message
    chat_id = message.chat_id
    user = message.from_user
    username = user.username or user.first_name
    text = message.text

    # Save to database
    save_deleted_message(
        chat_id=chat_id, user_id=user.id, username=username, message=text, reason=reason
    )

    # Delete message

    try:
        await context.bot.delete_message(chat_id, update.message.message_id)
    except Exception:
        pass

    username = user.username or user.first_name

    await context.bot.send_message(
        chat_id,
        text=f"⚠️ @{username}, your message was removed.\nReason: {reason}",
    )


async def view_deleted_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check admin status
    member = await context.bot.get_chat_member(chat_id, user_id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("❌ Only admins can view deleted messages.")
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT username, message, reason, timestamp
        FROM deleted_messages
        WHERE chat_id = ?
        ORDER BY id DESC
        LIMIT 10
    """,
        (chat_id,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("No deleted messages found.")
        return

    response = "🗑 **Last Deleted Messages**\n\n"
    for u, msg, r, t in rows:
        response += f"👤 @{u}\n" f"📝 {msg}\n" f"⚠️ {r}\n" f"⏰ {t}\n" f"────────────\n"

    await update.message.reply_text(response, parse_mode="Markdown")


# -------------------------------------
# Run bot with auto-restart
# -------------------------------------
def run_bot():

    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("deleted", view_deleted_messages))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    while True:
        try:
            run_bot()
        except Exception as e:
            print("Bot crashed:", e)
            time.sleep(5)
