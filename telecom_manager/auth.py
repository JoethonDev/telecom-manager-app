import time
import secrets
from functools import wraps
from flask import session, flash, redirect, url_for, request
from werkzeug.security import check_password_hash, generate_password_hash
from .db import get_conn, now_ts

LOGIN_ATTEMPTS = {}
LOGIN_REQUIRED_MSG = "authentication required"
PASSWORD_RE = r"^[a-zA-Z0-9_][a-zA-Z0-9_-]{2,31}$"


def check_login_throttled(key):
    now = time.time()
    bucket = LOGIN_ATTEMPTS.setdefault(key, [])
    bucket[:] = [t for t in bucket if now - t < 300]
    return len(bucket) >= 5


def note_login_attempt(key, ok):
    bucket = LOGIN_ATTEMPTS.setdefault(key, [])
    if ok:
        LOGIN_ATTEMPTS.pop(key, None)
    else:
        bucket.append(time.time())


def authenticate(username, password):
    with get_conn() as conn:
        admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
    if admin and check_password_hash(admin["password_hash"], password):
        return admin
    return None


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "user_id" not in session:
            flash(LOGIN_REQUIRED_MSG, "error")
            return redirect(url_for("login", next=request.path))
        return f(*a, **kw)
    return wrapper


def create_admin(username, password):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), now_ts()),
        )
