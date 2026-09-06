"""Entry point: run with `python main.py` inside Termux (or anywhere)."""

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from bot import config, database, handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
    if not config.ALLOWED_USER_IDS:
        raise SystemExit("ALLOWED_USER_IDS is not set. Add your Telegram user ID to .env.")

    database.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Basic
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_cmd))

    # Topics
    app.add_handler(CommandHandler("newtopic", handlers.new_topic))
    app.add_handler(CommandHandler("deletetopic", handlers.delete_topic))
    app.add_handler(CommandHandler("topics", handlers.list_topics))
    app.add_handler(CallbackQueryHandler(handlers.topic_selected, pattern=r"^topic:"))

    # Entries
    app.add_handler(CommandHandler("preview", handlers.preview))
    app.add_handler(CommandHandler("send", handlers.send_entry))
    app.add_handler(CommandHandler("undo", handlers.undo))
    app.add_handler(CommandHandler("edit", handlers.edit_last))

    # Review
    app.add_handler(CommandHandler("search", handlers.search))
    app.add_handler(CommandHandler("onthisday", handlers.on_this_day))
    app.add_handler(CommandHandler("stats", handlers.stats))

    # Export & sync
    app.add_handler(CommandHandler("export", handlers.export_cmd))
    app.add_handler(CommandHandler("syncstatus", handlers.sync_status))

    # Plain text -> buffer or edit target
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
