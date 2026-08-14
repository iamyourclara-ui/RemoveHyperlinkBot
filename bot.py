import os
import re
import logging
import threading

from flask import Flask
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# FLASK APP FOR HEALTH CHECK
# ==========================================

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "Bot is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================================
# BOT TOKEN
# ==========================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. Please set your token in CMD first."
    )


# ==========================================
# BOT INFORMATION
# ==========================================

BOT_USERNAME = "ladomaputi_bot"

ADD_TO_GROUP_URL = (
    f"https://t.me/{BOT_USERNAME}?startgroup=true"
)

BOT_URL = f"https://t.me/{BOT_USERNAME}"


# ==========================================
# WARNING MESSAGE
# ==========================================

WARNING_TEXT = (
    "🚫 Message Deleted\n\n"
    "Sorry! Messages containing website URLs or "
    "hyperlinks are not allowed here.\n\n"
    "Want the same protection in your group?\n"
    f"Add @{BOT_USERNAME} as an administrator."
)


# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ==========================================
# LINK DETECTION
# ==========================================

URL_REGEX = re.compile(
    r"(https?://|www\.)\S+",
    re.IGNORECASE
)


def contains_link(message) -> bool:

    # -----------------------------
    # Normal text
    # -----------------------------

    if message.text:

        if URL_REGEX.search(message.text):
            return True

        if message.entities:

            for entity in message.entities:

                if entity.type in (
                    "url",
                    "text_link"
                ):
                    return True


    # -----------------------------
    # Caption
    # -----------------------------

    if message.caption:

        if URL_REGEX.search(message.caption):
            return True

        if message.caption_entities:

            for entity in message.caption_entities:

                if entity.type in (
                    "url",
                    "text_link"
                ):
                    return True


    return False


# ==========================================
# CHECK ADMIN
# ==========================================

async def is_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> bool:

    message = update.effective_message
    chat = update.effective_chat

    if not message or not chat:
        return False


    # --------------------------------------
    # Anonymous administrator
    # --------------------------------------

    if message.sender_chat:

        # In groups/supergroups, messages sent
        # on behalf of the group are normally
        # anonymous administrator messages.

        if chat.type in (
            "group",
            "supergroup"
        ):
            return True


    # --------------------------------------
    # No identifiable user
    # --------------------------------------

    if not message.from_user:
        return False


    user_id = message.from_user.id


    # --------------------------------------
    # Private chat
    # --------------------------------------

    if chat.type == "private":
        return False


    # --------------------------------------
    # Check Telegram administrator status
    # --------------------------------------

    try:

        member = await context.bot.get_chat_member(
            chat_id=chat.id,
            user_id=user_id
        )

        if member.status in (
            "administrator",
            "creator"
        ):
            return True

    except Exception as e:

        logger.warning(
            "Could not check admin status: %s",
            e
        )


    return False


# ==========================================
# SEND WARNING
# ==========================================

async def send_warning(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.effective_chat

    if not chat:
        return


    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Add Me to Your Group",
                    url=ADD_TO_GROUP_URL
                )
            ],
            [
                InlineKeyboardButton(
                    f"🤖 @{BOT_USERNAME}",
                    url=BOT_URL
                )
            ]
        ]
    )


    await context.bot.send_message(
        chat_id=chat.id,
        text=WARNING_TEXT,
        reply_markup=keyboard
    )


# ==========================================
# MAIN MESSAGE HANDLER
# ==========================================

async def remove_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.effective_message
    chat = update.effective_chat

    if not message or not chat:
        return


    # --------------------------------------
    # Ignore messages without links
    # --------------------------------------

    if not contains_link(message):
        return


    # --------------------------------------
    # ADMIN CHECK
    # --------------------------------------

    if await is_admin(update, context):

        logger.info(
            "Admin message with link ignored in chat %s",
            chat.id
        )

        return


    # --------------------------------------
    # Delete message
    # --------------------------------------

    try:

        await message.delete()

        logger.info(
            "Deleted hyperlink message in chat %s",
            chat.id
        )

    except Exception as e:

        logger.error(
            "Could not delete message: %s",
            e
        )

        return


    # --------------------------------------
    # Send warning
    # --------------------------------------

    try:

        await send_warning(
            update,
            context
        )

        logger.info(
            "Warning sent to chat %s",
            chat.id
        )

    except Exception as e:

        logger.error(
            "Could not send warning: %s",
            e
        )


# ==========================================
# ERROR HANDLER
# ==========================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Bot error: %s",
        context.error
    )


# ==========================================
# START BOT
# ==========================================

def main():

    print("==============================")
    print("Remove Hyperlink Bot")
    print("==============================")
    print("Bot is running!")
    print("Monitoring groups and channels...")
    print("Admin links will NOT be deleted.")
    print("")

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )


    # --------------------------------------
    # Group / Supergroup messages
    # --------------------------------------

    application.add_handler(
        MessageHandler(
            filters.ALL,
            remove_link
        )
    )


    # --------------------------------------
    # Channel posts
    # --------------------------------------

    application.add_handler(
        MessageHandler(
            filters.UpdateType.CHANNEL_POSTS,
            remove_link
        )
    )


    application.add_error_handler(
        error_handler
    )


    # --------------------------------------
    # Start polling
    # --------------------------------------

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":
    main()