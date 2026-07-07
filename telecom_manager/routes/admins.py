import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from ..auth import login_required
from ..db import get_conn, now_ts

bp = Blueprint("admins", __name__)


@bp.route("/admins", methods=["GET", "POST"])
@login_required
def admins():
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "add":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not username or not password:
                flash("Username and password required", "error")
            elif not re.match(r"^[a-zA-Z0-9_]{3,32}$", username):
                flash("Invalid username (3-32 chars, letters/digits/_)", "error")
            elif not password or "\n" in password or "\r" in password:
                flash("Admin password cannot be empty or contain control characters", "error")
            else:
                with get_conn() as conn:
                    try:
                        conn.execute(
                            "INSERT INTO admins (username, password_hash, created_at) VALUES (?, ?, ?)",
                            (username, generate_password_hash(password), now_ts()),
                        )
                        flash(f"Admin {username} created", "success")
                    except Exception:
                        flash(f"Admin {username} already exists", "error")
        elif action == "delete":
            admin_id = request.form.get("admin_id", "")
            with get_conn() as conn:
                total = conn.execute("SELECT COUNT(*) AS cnt FROM admins").fetchone()[0]
                admin = conn.execute("SELECT * FROM admins WHERE id = ?", (admin_id,)).fetchone()
                if not admin:
                    flash("Admin not found", "error")
                elif total <= 1:
                    flash("Cannot delete the last admin", "error")
                elif admin["id"] == session.get("user_id"):
                    flash("Cannot delete yourself", "error")
                else:
                    conn.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
                    flash(f"Admin {admin['username']} deleted", "info")
    with get_conn() as conn:
        admins = conn.execute("SELECT id, username, created_at FROM admins ORDER BY id").fetchall()
    return render_template("admins.html", admins=admins)
