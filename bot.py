def main():
    import asyncio
    
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

    # Create event loop for the bot
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

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
