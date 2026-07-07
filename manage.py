#!/usr/bin/env python3
"""CLI management commands for Telecom Manager."""
import os
import sys
import time
import sqlite3
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("TELECOMCTL_MODE", "mock")
os.environ.setdefault("TELECOM_DEV", "1")
os.environ.setdefault("MANAGER_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "var", "dev", "manager.db"))


def cmd_migrate():
    from telecom_manager.app import init_db
    init_db()
    print("Migrations complete.")


def cmd_runserver():
    from telecom_manager.app import app
    from telecom_manager.config import PANEL_PORT
    app.run(host="127.0.0.1", port=PANEL_PORT, debug=True)


def cmd_create_admin():
    from telecom_manager.db import get_conn, now_ts
    from werkzeug.security import generate_password_hash

    username = os.environ.get("ADMIN_USER", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "")

    if not password:
        import getpass
        password = getpass.getpass("Admin password: ")

    if not password:
        print("Password cannot be empty", file=sys.stderr)
        sys.exit(1)

    Path(os.environ["MANAGER_DB"]).parent.mkdir(parents=True, exist_ok=True)
    cmd_migrate()

    with get_conn() as conn:
        existing = conn.execute("SELECT 1 FROM admins WHERE username = ?", (username,)).fetchone()
        if existing:
            print(f"Admin {username} already exists")
            return
        conn.execute(
            "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), now_ts()),
        )
    print(f"Admin {username} created")


def cmd_expire_users():
    from telecom_manager.app import init_db
    from telecom_manager.db import get_conn, now_ts
    from telecom_manager.services import telecomctl

    init_db()
    current = now_ts()
    with get_conn() as conn:
        for user in conn.execute(
            "SELECT * FROM vmess_users WHERE is_active = 1 AND expires_at <= ?",
            (current,),
        ).fetchall():
            telecomctl.xray_remove_vmess(user["username"])
            conn.execute(
                "UPDATE vmess_users SET is_active = 0, updated_at = ? WHERE id = ?",
                (current, user["id"]),
            )
            print(f"Expired VMess: {user['username']}")
        for user in conn.execute(
            "SELECT * FROM vless_users WHERE is_active = 1 AND expires_at <= ?",
            (current,),
        ).fetchall():
            telecomctl.xray_remove_vless(user["username"])
            conn.execute(
                "UPDATE vless_users SET is_active = 0, updated_at = ? WHERE id = ?",
                (current, user["id"]),
            )
            print(f"Expired VLESS: {user['username']}")
        for user in conn.execute(
            "SELECT * FROM ssh_users WHERE is_active = 1 AND expires_at <= ?",
            (current,),
        ).fetchall():
            telecomctl.ssh_disable_user(user["username"])
            conn.execute(
                "UPDATE ssh_users SET is_active = 0, updated_at = ? WHERE id = ?",
                (current, user["id"]),
            )
            print(f"Expired SSH: {user['username']}")
    print("Expire users complete.")


def cmd_health_check():
    import urllib.request
    from telecom_manager.config import PANEL_PORT
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{PANEL_PORT}/health")
        if resp.read() == b"ok":
            print("Health check passed")
            sys.exit(0)
        else:
            print("Health check failed: unexpected response")
            sys.exit(1)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: manage.py <migrate|runserver|create-admin|expire-users|health-check>")
        sys.exit(1)

    command = sys.argv[1]
    commands = {
        "migrate": cmd_migrate,
        "runserver": cmd_runserver,
        "create-admin": cmd_create_admin,
        "expire-users": cmd_expire_users,
        "health-check": cmd_health_check,
    }
    fn = commands.get(command)
    if not fn:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
    fn()
