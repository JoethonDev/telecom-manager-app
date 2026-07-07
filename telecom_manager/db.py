import sqlite3
import time
import logging
from datetime import datetime
from pathlib import Path
from .config import MANAGER_DB

_settings_cache = {}


def get_conn():
    conn = sqlite3.connect(str(MANAGER_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def now_ts():
    return int(time.time())


def get_setting(key, default=""):
    if key in _settings_cache:
        return _settings_cache[key]
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            val = row["value"] if row else default
            _settings_cache[key] = val
            return val
    except sqlite3.OperationalError:
        return default
    except Exception as e:
        logging.error("get_setting(%s) failed: %s", key, e)
        return default


def set_setting(key, value):
    ts = now_ts()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?",
            (key, value, ts, value, ts),
        )
    _settings_cache[key] = value


def clear_settings_cache():
    _settings_cache.clear()


def format_date(ts):
    if ts:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    return ""
