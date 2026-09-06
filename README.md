# TimeSealed Bot

A private Telegram bot, hosted on your own phone via Termux, for writing dated
letters to your future spouse — organized by topic, backed up automatically
to Google Drive, and exportable into one file whenever you're ready to share it,
Insha Allah.

## How it works

1. Pick or create a **topic** (`/newtopic`, `/topics`).
2. Send one or more plain messages — they queue up.
3. Run `/send` to save everything queued as **one dated entry** under that topic.
4. The bot syncs your data to Google Drive automatically after every save.
5. Whenever you want a single shareable file, run `/export`.

Every entry is timestamped the moment it's saved — not edited afterward — so
the dates are a genuine record of when you wrote each thought.

## Setup (Termux, Android)

```bash
git clone <this-repo-url>
cd letters-bot
bash install.sh
```

Then:

1. Create a bot with **@BotFather** on Telegram, copy the token.
2. Get your numeric Telegram user ID from **@userinfobot**.
3. Edit `.env`:
   ```
   BOT_TOKEN=your_token_here
   ALLOWED_USER_IDS=your_numeric_id_here
   ```
4. Configure rclone for Google Drive:
   ```bash
   rclone config
   ```
   Termux has no browser, so when prompted for OAuth, either:
   - use `termux-open-url` if you have a browser app installed, or
   - run `rclone authorize "drive"` on a PC/laptop once, then paste the
     resulting token back into the Termux `rclone config` prompt.

   Name the remote `gdrive` (or update `RCLONE_REMOTE` in `.env` to match).
5. Keep Termux alive in the background:
   ```bash
   termux-wake-lock
   ```
6. Start the bot:
   ```bash
   python main.py
   ```

To keep it running after closing Termux, consider `termux-services`, or run
it inside `tmux`:
```bash
pkg install tmux
tmux new -s letters
python main.py
# detach with Ctrl+B then D; reattach later with: tmux attach -t letters
```

## Commands

**Topics**
- `/newtopic <name>` — create a topic and make it active
- `/deletetopic <name>` — delete a topic and all its entries
- `/topics` — list topics and pick the active one

**Writing**
- Plain text — queues a message under the active topic
- `/preview` — see what's queued
- `/send` — save the queue as one dated entry, then sync
- `/undo` — delete the last saved entry in the active topic
- `/edit` — replace the last saved entry's content

**Reviewing**
- `/search <keyword>` — search all entries
- `/onthisday` — entries from this date in past years
- `/stats` — entry/word counts per topic

**Backup & export**
- `/export [topic]` — combine entries into one Markdown file and send it to you
- `/syncstatus` — check the last Google Drive sync result

## Data & privacy

- All data lives locally in `data/letters.db` (SQLite) — never committed to
  git (see `.gitignore`).
- Only the Telegram user ID(s) listed in `ALLOWED_USER_IDS` can use the bot.
- Sync uses your own `rclone` + Google Drive remote — no third-party server
  ever sees your entries.
- Optionally set `EXPORT_PASSPHRASE` in `.env` to require a passphrase before
  `/export` will run, since that's the command that produces one file.

## Roadmap ideas

- Voice note / photo attachments per entry
- `rclone crypt` for encryption at rest on Drive
- PDF export in addition to Markdown
- Scheduled reminders to write (`termux-job-scheduler` cron)
