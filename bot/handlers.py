"""All Telegram command/message handlers for the Letters bot."""

from datetime import datetime
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from . import config, database, sync, export


# ---------- Access control ----------

def restricted(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        if not config.is_authorized(user_id):
            if update.message:
                await update.message.reply_text("This bot is private. You're not authorized.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def _get_buffer(context) -> list:
    return context.user_data.setdefault("buffer", [])


def _active_topic(context):
    return context.user_data.get("active_topic")


# ---------- Basic commands ----------

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalamu alaikum. This is your private letters journal.\n\n"
        "1. /newtopic <name> - create a topic\n"
        "2. /topics - pick the active topic\n"
        "3. Just type messages - they'll be queued\n"
        "4. /send - save the queued messages as one dated entry\n\n"
        "/help for the full command list."
    )


@restricted
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Topics:\n"
        "  /newtopic <name>\n"
        "  /deletetopic <name>\n"
        "  /topics - list & select active topic\n\n"
        "Entries:\n"
        "  (plain text) - queue a message\n"
        "  /preview - show queued messages\n"
        "  /send - save queued messages as one entry\n"
        "  /undo - delete the last saved entry in the active topic\n"
        "  /edit - replace the last saved entry's content\n\n"
        "Review:\n"
        "  /search <keyword>\n"
        "  /onthisday\n"
        "  /stats\n\n"
        "Backup:\n"
        "  /export [topic] - build one combined file\n"
        "  /syncstatus - last Google Drive sync result\n"
    )


# ---------- Topics ----------

@restricted
async def new_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /newtopic <name>")
        return
    name = " ".join(context.args).strip()
    if database.add_topic(name):
        context.user_data["active_topic"] = name
        await update.message.reply_text(f"Topic '{name}' created and set as active.")
    else:
        await update.message.reply_text(f"Topic '{name}' already exists.")


@restricted
async def delete_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /deletetopic <name>")
        return
    name = " ".join(context.args).strip()
    if database.delete_topic(name):
        if _active_topic(context) == name:
            context.user_data["active_topic"] = None
        await update.message.reply_text(
            f"Topic '{name}' and all of its entries were deleted."
        )
    else:
        await update.message.reply_text(f"No topic named '{name}' found.")


@restricted
async def list_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topics = database.list_topics()
    if not topics:
        await update.message.reply_text("No topics yet. Create one with /newtopic <name>.")
        return
    buttons = [[InlineKeyboardButton(t, callback_data=f"topic:{t}")] for t in topics]
    await update.message.reply_text(
        "Select a topic to make it active:", reply_markup=InlineKeyboardMarkup(buttons)
    )


@restricted
async def topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    topic = query.data.split(":", 1)[1]
    context.user_data["active_topic"] = topic
    context.user_data["buffer"] = []  # switching topics clears any unsent buffer
    await query.edit_message_text(f"Active topic set to '{topic}'. Send your messages, then /send.")


# ---------- Entry buffering & saving ----------

@restricted
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Any plain-text message: either replaces the entry being edited,
    or gets queued into the buffer for the next /send."""
    text = update.message.text

    if context.user_data.get("editing_entry_id"):
        entry_id = context.user_data.pop("editing_entry_id")
        database.update_entry(entry_id, text)
        sync.sync_database()
        await update.message.reply_text("Entry updated and re-synced.")
        return

    topic = _active_topic(context)
    if not topic:
        await update.message.reply_text(
            "No active topic. Use /topics to pick one, or /newtopic <name> to create one."
        )
        return

    _get_buffer(context).append(text)
    await update.message.reply_text(f"Queued ({len(_get_buffer(context))} message(s)). Send /send when ready.")


@restricted
async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buf = _get_buffer(context)
    if not buf:
        await update.message.reply_text("Nothing queued yet.")
        return
    await update.message.reply_text("Queued so far:\n\n" + "\n\n".join(buf))


@restricted
async def send_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = _active_topic(context)
    buf = _get_buffer(context)

    if not topic:
        await update.message.reply_text("No active topic. Use /topics first.")
        return
    if not buf:
        await update.message.reply_text("Nothing queued. Type a message first, then /send.")
        return

    content = "\n\n".join(buf)
    database.add_entry(topic, content, when=datetime.now())
    context.user_data["buffer"] = []

    ok, msg = sync.sync_database()
    status = "Synced to Google Drive." if ok else f"Saved locally, but sync failed: {msg}"
    await update.message.reply_text(f"Entry saved under '{topic}'. {status}")


@restricted
async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = _active_topic(context)
    if not topic:
        await update.message.reply_text("No active topic selected.")
        return
    last = database.get_last_entry(topic)
    if not last:
        await update.message.reply_text(f"No entries yet in '{topic}'.")
        return
    database.delete_entry(last["id"])
    sync.sync_database()
    await update.message.reply_text("Last entry deleted and change synced.")


@restricted
async def edit_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = _active_topic(context)
    if not topic:
        await update.message.reply_text("No active topic selected.")
        return
    last = database.get_last_entry(topic)
    if not last:
        await update.message.reply_text(f"No entries yet in '{topic}'.")
        return
    context.user_data["editing_entry_id"] = last["id"]
    await update.message.reply_text(
        f"Current entry:\n\n{last['content']}\n\nSend the replacement text now."
    )


# ---------- Review ----------

@restricted
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <keyword>")
        return
    keyword = " ".join(context.args)
    results = database.search_entries(keyword)
    if not results:
        await update.message.reply_text("No matches found.")
        return
    lines = []
    for r in results[:10]:
        dt = datetime.fromisoformat(r["created_at"])
        snippet = r["content"][:120].replace("\n", " ")
        lines.append(f"[{r['topic']}] {dt.strftime('%Y-%m-%d %H:%M')} — {snippet}...")
    await update.message.reply_text("\n\n".join(lines))


@restricted
async def on_this_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    results = database.entries_on_this_day(now.month, now.day, now.year)
    if not results:
        await update.message.reply_text("Nothing from previous years on this date yet.")
        return
    lines = []
    for r in results:
        dt = datetime.fromisoformat(r["created_at"])
        lines.append(f"[{r['topic']}] {dt.strftime('%Y')}:\n{r['content']}")
    await update.message.reply_text("\n\n---\n\n".join(lines))


@restricted
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = database.stats()
    per_topic = "\n".join(f"  - {t}: {n}" for t, n in s["per_topic"].items()) or "  (none)"
    await update.message.reply_text(
        f"Topics: {s['topics']}\n"
        f"Total entries: {s['entries']}\n"
        f"Total words: {s['words']}\n\n"
        f"Entries per topic:\n{per_topic}"
    )


# ---------- Export & sync ----------

@restricted
async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if config.EXPORT_PASSPHRASE:
        if not context.args or context.args[-1] != config.EXPORT_PASSPHRASE:
            await update.message.reply_text(
                "Export is passphrase-protected. Usage: /export [topic] <passphrase>"
            )
            return
        topic_args = context.args[:-1]
    else:
        topic_args = context.args

    topic = " ".join(topic_args).strip() or None
    path = export.export_all(topic)
    ok, msg = sync.sync_path(path)
    status = "and synced to Google Drive." if ok else f"but sync failed: {msg}"
    await update.message.reply_document(
        document=open(path, "rb"), caption=f"Exported {status}"
    )


@restricted
async def sync_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = sync.last_sync_status()
    if not s["time"]:
        await update.message.reply_text("No sync has been attempted yet.")
        return
    result = "OK" if s["ok"] else "FAILED"
    await update.message.reply_text(f"Last sync: {s['time']}\nResult: {result}\n{s['message']}")
