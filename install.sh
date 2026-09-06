#!/data/data/com.termux/files/usr/bin/bash
# Quick setup for Termux. Run: bash install.sh

set -e

echo "Updating packages..."
pkg update -y && pkg upgrade -y

echo "Installing python, rclone, git..."
pkg install -y python rclone git

echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from .env.example — edit it now with your BOT_TOKEN and ALLOWED_USER_IDS:"
    echo "  nano .env"
fi

echo ""
echo "Next steps:"
echo "  1. Edit .env with your bot token and Telegram user ID"
echo "  2. Run: rclone config    (set up a remote named 'gdrive', or match RCLONE_REMOTE in .env)"
echo "  3. Run: termux-wake-lock  (keeps the bot alive while phone is locked)"
echo "  4. Run: python main.py"
