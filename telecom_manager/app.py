import logging
from datetime import timedelta
from pathlib import Path

from flask import Flask, flash, redirect, request, render_template, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from .config import (
    FLASK_SECRET, PANEL_DOMAIN, DOMAIN, PANEL_PORT,
)
from .csrf import csrf_token
from .db import get_conn, now_ts, get_setting, set_setting, clear_settings_cache, MANAGER_DB, format_date
from .auth import login_required, check_login_throttled, note_login_attempt, authenticate, create_admin
from .routes.dashboard import bp as dashboard_bp
from .routes.users import bp as users_bp
from .routes.settings import bp as settings_bp
from .routes.monitoring import bp as monitoring_bp
from .routes.admins import bp as admins_bp
from .routes.backups import bp as backups_bp
from .routes.usage import bp as usage_bp

app = Flask(__name__)
app.secret_key = FLASK_SECRET

_trusted_hosts = ["localhost", "127.0.0.1", "[::1]"]
if PANEL_DOMAIN:
    _trusted_hosts.append(PANEL_DOMAIN)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
    MAX_CONTENT_LENGTH=64 * 1024,
)

app.register_blueprint(dashboard_bp)
app.register_blueprint(users_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(monitoring_bp)
app.register_blueprint(admins_bp)
app.register_blueprint(backups_bp)
app.register_blueprint(usage_bp)

# ponytail: alias for stale templates that call url_for('dashboard')
app.add_url_rule(
    "/dashboard",
    endpoint="dashboard",
    view_func=dashboard_bp.view_functions["dashboard"],
)


@app.context_processor
def inject_globals():
    from .services.links import vmess_link, vless_link
    return dict(session=session, csrf_token=csrf_token, format_date=format_date,
                vmess_link=vmess_link, vless_link=vless_link)


@app.before_request
def csrf_check():
    if request.method == "POST" and request.endpoint not in ("health", "static", "login"):
        if "user_id" not in session:
            return "authentication required", 401
        token = request.form.get("_csrf", "")
        if not token or not token == session.get("_csrf", ""):
            return "CSRF validation failed", 403


@app.after_request
def no_store(response):
    if request.endpoint not in ("health", "static"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/health")
def health():
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return "ok"
    except Exception:
        return "unhealthy", 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        key = f"{request.remote_addr}:{request.form.get('username', '').strip()}"
        if check_login_throttled(key):
            flash("Too many login attempts. Try again later.", "error")
            return redirect(url_for("login"))
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = authenticate(username, password)
        if admin:
            session.clear()
            session["user_id"] = admin["id"]
            session["username"] = admin["username"]
            session.permanent = True
            note_login_attempt(key, True)
            next_url = request.args.get("next", url_for("dashboard.dashboard"))
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard.dashboard")
            return redirect(next_url)
        note_login_attempt(key, False)
        flash("Invalid username or password", "error")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))


@app.route("/")
def index():
    return redirect(url_for("dashboard.dashboard"))


@app.errorhandler(Exception)
def handle_error(error):
    if isinstance(error, HTTPException):
        return error
    app.logger.error("Unhandled exception", exc_info=True)
    return render_template("error.html", message="Internal server error"), 500


def init_db():
    MANAGER_DB.parent.mkdir(parents=True, exist_ok=True)
    migrate_schema()
    from .config import ADMIN_USER, ADMIN_PASSWORD_HASH
    if ADMIN_USER and ADMIN_PASSWORD_HASH:
        with get_conn() as conn:
            existing = conn.execute("SELECT 1 FROM admins WHERE username = ?", (ADMIN_USER,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (ADMIN_USER, ADMIN_PASSWORD_HASH, now_ts()),
                )
    clear_settings_cache()


def migrate_schema():
    ver = int(get_setting("schema_version", "0"))
    migrations = []
    if ver < 1:
        migrations.append("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL)")
        migrations.append("CREATE TABLE IF NOT EXISTS ssh_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_note TEXT, sni TEXT NOT NULL, expires_at INTEGER NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)")
        migrations.append("CREATE TABLE IF NOT EXISTS vmess_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, uuid TEXT UNIQUE NOT NULL, sni TEXT NOT NULL, expires_at INTEGER NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)")
    if ver < 2:
        migrations.append("CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL)")
    if ver < 3:
        migrations.append("CREATE TABLE IF NOT EXISTS usage_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, type TEXT NOT NULL, bytes_in INTEGER DEFAULT 0, bytes_out INTEGER DEFAULT 0, logged_at INTEGER NOT NULL)")
    if ver < 4:
        migrations.append("CREATE INDEX IF NOT EXISTS idx_usage_logged_at ON usage_log(logged_at)")
        migrations.append("CREATE TABLE IF NOT EXISTS monitoring_samples (id INTEGER PRIMARY KEY AUTOINCREMENT, cpu_pct REAL NOT NULL DEFAULT 0, mem_pct REAL NOT NULL DEFAULT 0, disk_pct REAL NOT NULL DEFAULT 0, sampled_at INTEGER NOT NULL)")
    if ver < 5:
        migrations.append("CREATE TABLE IF NOT EXISTS vless_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, uuid TEXT UNIQUE NOT NULL, sni TEXT NOT NULL, expires_at INTEGER NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)")
    if ver < 6:
        migrations.append("CREATE TABLE IF NOT EXISTS bandwidth_log (id INTEGER PRIMARY KEY AUTOINCREMENT, service TEXT NOT NULL, bytes_in INTEGER NOT NULL DEFAULT 0, bytes_out INTEGER NOT NULL DEFAULT 0, sampled_at INTEGER NOT NULL)")
    if ver < 7:
        migrations.append("CREATE TABLE IF NOT EXISTS user_bandwidth_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, service_type TEXT NOT NULL, bytes_in INTEGER NOT NULL DEFAULT 0, bytes_out INTEGER NOT NULL DEFAULT 0, sampled_at INTEGER NOT NULL)")
    target = 7
    if migrations:
        with get_conn() as conn:
            for sql in migrations:
                conn.execute(sql)
            ts = now_ts()
            conn.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?",
                ("schema_version", str(target), ts, str(target), ts),
            )
        clear_settings_cache()
        app.logger.info("Schema migrated from v%s to v%s", ver, target)


init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PANEL_PORT)
