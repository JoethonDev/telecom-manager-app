#!/usr/bin/env python3
"""Maintenance script — runs periodically via systemd timer."""
import os
import sys
import time
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(str(Path(__file__).parent.parent.parent))

os.environ.setdefault("TELECOMCTL_MODE", "")
os.environ.setdefault("TELECOM_DEV", "")
os.environ.setdefault("MANAGER_DB", "/var/lib/telecom-manager/manager.db")
os.environ.setdefault("FLASK_SECRET", "maintenance")

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from telecom_manager.app import init_db
from telecom_manager.db import get_conn, now_ts, get_setting, set_setting, MANAGER_DB
from telecom_manager.services import telecomctl

init_db()


def expire_users():
    current = now_ts()
    with get_conn() as conn:
        for user in conn.execute(
            "SELECT * FROM vmess_users WHERE is_active = 1 AND expires_at <= ?", (current,)
        ).fetchall():
            telecomctl.xray_remove_vmess(user["username"])
            conn.execute("UPDATE vmess_users SET is_active = 0, updated_at = ? WHERE id = ?", (current, user["id"]))
            logging.info("Expired VMess: %s", user["username"])
        for user in conn.execute(
            "SELECT * FROM vless_users WHERE is_active = 1 AND expires_at <= ?", (current,)
        ).fetchall():
            telecomctl.xray_remove_vless(user["username"])
            conn.execute("UPDATE vless_users SET is_active = 0, updated_at = ? WHERE id = ?", (current, user["id"]))
            logging.info("Expired VLESS: %s", user["username"])
        for user in conn.execute(
            "SELECT * FROM ssh_users WHERE is_active = 1 AND expires_at <= ?", (current,)
        ).fetchall():
            telecomctl.ssh_disable_user(user["username"])
            conn.execute("UPDATE ssh_users SET is_active = 0, updated_at = ? WHERE id = ?", (current, user["id"]))
            logging.info("Expired SSH: %s", user["username"])


def collect_usage_logs():
    cursor_key = get_setting("journal_cursor", "")
    cursor_args = ["journalctl", "-u", "ssh", "-u", "sshd", "-u", "sshd-httpcustom", "--no-pager"]
    if cursor_key:
        cursor_args.extend(["--after-cursor", cursor_key])
    else:
        cursor_args.extend(["--since", "1 hour ago"])
    cursor_args.append("--show-cursor")

    import subprocess
    j = subprocess.run(cursor_args, capture_output=True, text=True)
    new_cursor = None
    with get_conn() as log_conn:
        managed_users = {row["username"] for row in log_conn.execute("SELECT username FROM ssh_users").fetchall()}
        for line in j.stdout.splitlines():
            if line.startswith("-- cursor:"):
                new_cursor = line.split(": ", 1)[1].strip()
            elif "Accepted " in line and (" password for " in line or " publickey for " in line):
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "for" and i + 1 < len(parts):
                        u = parts[i + 1]
                        if u in managed_users:
                            log_conn.execute(
                                "INSERT INTO usage_log (username, type, bytes_in, bytes_out, logged_at) VALUES (?, ?, 0, 0, ?)",
                                (u, "ssh_login_event", now_ts()),
                            )
    if new_cursor:
        set_setting("journal_cursor", new_cursor)


def collect_xray_logs():
    xlog = "/var/log/xray/access.log"
    xpos_key = "xray_access_pos"
    xpos = int(get_setting(xpos_key, "0"))
    try:
        sz = os.path.getsize(xlog)
        if sz < xpos:
            xpos = 0
        if sz > xpos:
            with get_conn() as log_conn:
                managed_vmess = {row["username"] for row in log_conn.execute("SELECT username FROM vmess_users").fetchall()}
                managed_vless = {row["username"] for row in log_conn.execute("SELECT username FROM vless_users").fetchall()}
                with open(xlog) as f:
                    f.seek(xpos)
                    for line in f:
                        if "accepted" in line and "email:" in line:
                            parts = line.split()
                            for i, p in enumerate(parts):
                                if p == "email:" and i + 1 < len(parts):
                                    u = parts[i + 1].rstrip("]")
                                    if u in managed_vmess:
                                        log_conn.execute(
                                            "INSERT INTO usage_log (username, type, bytes_in, bytes_out, logged_at) VALUES (?, ?, 0, 0, ?)",
                                            (u, "vmess_connection_event", now_ts()),
                                        )
                                    elif u in managed_vless:
                                        log_conn.execute(
                                            "INSERT INTO usage_log (username, type, bytes_in, bytes_out, logged_at) VALUES (?, ?, 0, 0, ?)",
                                            (u, "vless_connection_event", now_ts()),
                                        )
            set_setting(xpos_key, str(sz))
    except Exception:
        logging.warning("Xray access log collection failed")


def collect_monitoring_samples():
    cpu = 0
    try:
        with open("/proc/stat") as f:
            parts = f.readline().split()
        values = [int(x) for x in parts[1:8]]
        idle = values[3] + values[4]
        total = sum(values)
        prev_total = int(get_setting("cpu_stat_prev_total", "0"))
        prev_idle = int(get_setting("cpu_stat_prev_idle", "0"))
        delta_total = total - prev_total
        delta_idle = idle - prev_idle
        if delta_total > 0:
            cpu = (1 - (delta_idle / delta_total)) * 100
        set_setting("cpu_stat_prev_total", str(total))
        set_setting("cpu_stat_prev_idle", str(idle))
    except Exception:
        pass

    mem = 0
    try:
        with open("/proc/meminfo") as f:
            lines = f.read().splitlines()
        total = int([x for x in lines if x.startswith("MemTotal:")][0].split()[1])
        avail = int([x for x in lines if x.startswith("MemAvailable:")][0].split()[1])
        mem = (total - avail) / total * 100
    except Exception:
        logging.exception("Memory sample failed")

    disk = 0
    try:
        d = os.statvfs("/")
        disk = (d.f_blocks - d.f_bfree) / d.f_blocks * 100
    except Exception:
        logging.exception("Disk sample failed")

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO monitoring_samples (cpu_pct, mem_pct, disk_pct, sampled_at) VALUES (?, ?, ?, ?)",
            (round(cpu, 1), round(mem, 1), round(disk, 1), now_ts()),
        )
        conn.execute("DELETE FROM monitoring_samples WHERE sampled_at < ?", (now_ts() - 86400 * 90,))
        conn.execute("DELETE FROM usage_log WHERE logged_at < ?", (now_ts() - 86400 * 90,))


def backup_database():
    bk_dir = MANAGER_DB.parent / "backups"
    bk_dir.mkdir(parents=True, exist_ok=True)
    bks = sorted(f for f in os.listdir(str(bk_dir)) if f.startswith("manager.db."))
    latest_mtime = max((os.path.getmtime(os.path.join(str(bk_dir), f)) for f in bks), default=0)
    if time.time() - latest_mtime >= 86400:
        ts = int(time.time())
        bk_path = str(bk_dir / f"manager.db.{ts}")
        with sqlite3.connect(str(MANAGER_DB)) as src, sqlite3.connect(bk_path) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Database backup integrity check failed")
        bks.append(os.path.basename(bk_path))
    while len(bks) > 7:
        os.remove(os.path.join(str(bk_dir), bks.pop(0)))


def reconcile_users():
    import subprocess
    with get_conn() as conn:
        for user in conn.execute("SELECT * FROM ssh_users WHERE is_active = 1").fetchall():
            r = subprocess.run(["id", user["username"]], capture_output=True)
            if r.returncode != 0:
                logging.warning("Reconciling %s: linux user missing, marking inactive", user["username"])
                conn.execute("UPDATE ssh_users SET is_active = 0, updated_at = ? WHERE id = ?", (now_ts(), user["id"]))
        current = now_ts()
        for user in conn.execute("SELECT * FROM vmess_users WHERE is_active = 1").fetchall():
            if user["expires_at"] <= current:
                logging.warning("Reconciling %s: past expiry, marking inactive", user["username"])
                conn.execute("UPDATE vmess_users SET is_active = 0, updated_at = ? WHERE id = ?", (now_ts(), user["id"]))
        for user in conn.execute("SELECT * FROM vless_users WHERE is_active = 1").fetchall():
            if user["expires_at"] <= current:
                logging.warning("Reconciling %s: past expiry, marking inactive", user["username"])
                conn.execute("UPDATE vless_users SET is_active = 0, updated_at = ? WHERE id = ?", (now_ts(), user["id"]))


if __name__ == "__main__":
    expire_users()
    collect_usage_logs()
    collect_xray_logs()
    collect_monitoring_samples()
    backup_database()
    reconcile_users()
