"""Wraps rclone to push local data to Google Drive.

Requires rclone to be installed and configured beforehand:
    pkg install rclone
    rclone config      # set up a remote named to match RCLONE_REMOTE in .env

Termux has no browser, so authorize rclone using the "remote authorization"
trick: run `rclone authorize "drive"` on a machine with a browser, then paste
the resulting token into `rclone config` here. Full steps are in README.md.
"""

import subprocess
import shutil
from datetime import datetime

from . import config

_last_sync_result = {"time": None, "ok": None, "message": ""}


def rclone_available() -> bool:
    return shutil.which("rclone") is not None


def sync_path(local_path) -> tuple[bool, str]:
    """Copies a local file or directory to the configured rclone remote/folder."""
    if not rclone_available():
        msg = "rclone is not installed or not on PATH."
        _record(False, msg)
        return False, msg

    remote_target = f"{config.RCLONE_REMOTE}:{config.RCLONE_FOLDER}"
    try:
        result = subprocess.run(
            ["rclone", "copy", str(local_path), remote_target, "--quiet"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            _record(True, f"Synced to {remote_target}")
            return True, f"Synced to {remote_target}"
        else:
            msg = result.stderr.strip() or "Unknown rclone error"
            _record(False, msg)
            return False, msg
    except subprocess.TimeoutExpired:
        _record(False, "rclone sync timed out")
        return False, "rclone sync timed out"
    except Exception as e:
        _record(False, str(e))
        return False, str(e)


def sync_database():
    """Convenience: syncs the whole data directory (db + exports)."""
    return sync_path(config.DATA_DIR)


def _record(ok: bool, message: str):
    _last_sync_result["time"] = datetime.now().isoformat()
    _last_sync_result["ok"] = ok
    _last_sync_result["message"] = message


def last_sync_status() -> dict:
    return dict(_last_sync_result)
