"""Loads configuration from environment variables / .env file."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

_allowed = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = {int(uid.strip()) for uid in _allowed.split(",") if uid.strip()}

DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
DB_PATH = Path(os.getenv("DB_PATH", "./data/letters.db"))
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "./data/exports"))

RCLONE_REMOTE = os.getenv("RCLONE_REMOTE", "gdrive")
RCLONE_FOLDER = os.getenv("RCLONE_FOLDER", "LettersToSpouse")

EXPORT_PASSPHRASE = os.getenv("EXPORT_PASSPHRASE", "").strip()

# Make sure required directories exist.
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def is_authorized(user_id: int) -> bool:
    """Only whitelisted Telegram user IDs may use the bot."""
    if not ALLOWED_USER_IDS:
        # Fail safe: if nobody is configured, nobody is allowed.
        return False
    return user_id in ALLOWED_USER_IDS
