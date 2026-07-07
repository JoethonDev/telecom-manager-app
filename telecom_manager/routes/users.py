from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..auth import login_required
from ..db import get_conn, now_ts, get_setting, set_setting, clear_settings_cache
from ..services.links import get_effective_settings, vmess_link, vless_link
from ..services.validators import validate_username, validate_days, validate_password, normalize_sni
from ..services import telecomctl

bp = Blueprint("users", __name__)


def days_to_expiry(days):
    return int((datetime.now() + timedelta(days=int(days))).timestamp())


def get_default_sni():
    from ..config import DEFAULT_SNI
    return get_setting("default_sni", DEFAULT_SNI)


@bp.route("/users")
@login_required
def users():
    cfg = get_effective_settings()
    conn_host = cfg["connection_domain"] or cfg["public_ip"] or ""
    with get_conn() as conn:
        ssh_users = conn.execute("SELECT * FROM ssh_users ORDER BY id DESC").fetchall()
        vmess_users = conn.execute("SELECT * FROM vmess_users ORDER BY id DESC").fetchall()
        vless_users = conn.execute("SELECT * FROM vless_users ORDER BY id DESC").fetchall()
    active_ssh = sum(1 for u in ssh_users if u["is_active"])
    active_vmess = sum(1 for u in vmess_users if u["is_active"])
    active_vless = sum(1 for u in vless_users if u["is_active"])
    return render_template(
        "users.html",
        ssh_users=ssh_users, vmess_users=vmess_users, vless_users=vless_users,
        active_ssh=active_ssh, active_vmess=active_vmess, active_vless=active_vless,
        domain=conn_host,
        stunnel_port=cfg["stunnel_port"], vmess_port=cfg["vmess_port"], vless_port=cfg["vless_port"],
        default_sni=cfg["default_sni"], public_ip=cfg["public_ip"],
    )


@bp.route("/ssh/add", methods=["POST"])
@login_required
def add_ssh():
    username = request.form["username"].strip()
    password = request.form["password"]
    days = request.form["days"]
    try:
        validate_days(days)
        validate_password(password)
        sni = normalize_sni(request.form.get("sni"), get_default_sni())
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    expires_at = days_to_expiry(days)
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM ssh_users WHERE username = ?", (username,)).fetchone():
            flash(f"SSH user already exists: {username}", "error")
            return redirect(url_for("users"))
    expire_date = datetime.fromtimestamp(expires_at).strftime("%Y-%m-%d")
    result = telecomctl.ssh_add_user(username, password, expire_date)
    if result.returncode != 0:
        flash(f"Failed to create SSH user: {result.stderr}", "error")
        return redirect(url_for("users"))
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO ssh_users (username, password_note, sni, expires_at, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                (username, "stored only in Linux shadow", sni, expires_at, now_ts(), now_ts()),
            )
    except Exception as e:
        telecomctl.ssh_delete_user(username)
        flash(f"Failed to save SSH user: {e}", "error")
        return redirect(url_for("users"))
    flash(f"SSH user {username} created", "success")
    return redirect(url_for("users"))


@bp.route("/ssh/disable", methods=["POST"])
@login_required
def disable_ssh():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM ssh_users WHERE username = ?", (username,)).fetchone():
            flash("SSH user not found", "error")
            return redirect(url_for("users"))
    result = telecomctl.ssh_disable_user(username)
    if result.returncode != 0:
        flash(f"Failed to disable SSH user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("UPDATE ssh_users SET is_active = 0, updated_at = ? WHERE username = ?", (now_ts(), username))
    flash(f"SSH user {username} disabled", "info")
    return redirect(url_for("users"))


@bp.route("/ssh/enable", methods=["POST"])
@login_required
def enable_ssh():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        user = conn.execute("SELECT * FROM ssh_users WHERE username = ?", (username,)).fetchone()
        if not user:
            flash("SSH user not found", "error")
            return redirect(url_for("users"))
        if user["expires_at"] <= now_ts():
            flash("Expired users cannot be enabled; recreate the account with a new expiry", "error")
            return redirect(url_for("users"))
    expire_date = datetime.fromtimestamp(user["expires_at"]).strftime("%Y-%m-%d")
    result = telecomctl.ssh_enable_user(username, expire_date)
    if result.returncode != 0:
        flash(f"Failed to enable SSH user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("UPDATE ssh_users SET is_active = 1, updated_at = ? WHERE username = ?", (now_ts(), username))
    flash(f"SSH user {username} enabled", "success")
    return redirect(url_for("users"))


@bp.route("/ssh/delete", methods=["POST"])
@login_required
def delete_ssh():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM ssh_users WHERE username = ?", (username,)).fetchone():
            flash("SSH user not found", "error")
            return redirect(url_for("users"))
    result = telecomctl.ssh_delete_user(username)
    if result.returncode != 0:
        flash(f"Failed to delete SSH user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("DELETE FROM ssh_users WHERE username = ?", (username,))
    flash(f"SSH user {username} deleted", "info")
    return redirect(url_for("users"))


@bp.route("/vmess/add", methods=["POST"])
@login_required
def add_vmess():
    username = request.form["username"].strip()
    days = request.form["days"]
    try:
        validate_days(days)
        sni = normalize_sni(request.form.get("sni"), get_default_sni())
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    expires_at = days_to_expiry(days)
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM vmess_users WHERE username = ?", (username,)).fetchone():
            flash(f"VMess user already exists: {username}", "error")
            return redirect(url_for("users"))
    uuid_str = telecomctl.generate_uuid()
    if not uuid_str:
        flash("Failed to generate UUID", "error")
        return redirect(url_for("users"))
    result = telecomctl.xray_add_vmess(username, uuid_str)
    if result.returncode != 0:
        flash(f"Failed to add Xray client: {result.stderr}", "error")
        return redirect(url_for("users"))
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO vmess_users (username, uuid, sni, expires_at, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                (username, uuid_str, sni, expires_at, now_ts(), now_ts()),
            )
    except Exception as e:
        telecomctl.xray_remove_vmess(username)
        flash(f"Failed to save VMess user: {e}", "error")
        return redirect(url_for("users"))
    flash(f"VMess user {username} created", "success")
    return redirect(url_for("users"))


@bp.route("/vmess/disable", methods=["POST"])
@login_required
def disable_vmess():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM vmess_users WHERE username = ?", (username,)).fetchone():
            flash("VMess user not found", "error")
            return redirect(url_for("users"))
    result = telecomctl.xray_disable_vmess(username)
    if result.returncode != 0:
        flash(f"Failed to disable VMess user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("UPDATE vmess_users SET is_active = 0, updated_at = ? WHERE username = ?", (now_ts(), username))
    flash(f"VMess user {username} disabled", "info")
    return redirect(url_for("users"))


@bp.route("/vmess/enable", methods=["POST"])
@login_required
def enable_vmess():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        user = conn.execute("SELECT * FROM vmess_users WHERE username = ?", (username,)).fetchone()
        if not user:
            flash("VMess user not found", "error")
            return redirect(url_for("users"))
        if user["expires_at"] <= now_ts():
            flash("Expired users cannot be enabled; recreate the account with a new expiry", "error")
            return redirect(url_for("users"))
    result = telecomctl.xray_enable_vmess(user["username"], user["uuid"])
    if result.returncode != 0:
        flash(f"Failed to enable VMess user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("UPDATE vmess_users SET is_active = 1, updated_at = ? WHERE username = ?", (now_ts(), username))
    flash(f"VMess user {username} enabled", "success")
    return redirect(url_for("users"))


@bp.route("/vmess/delete", methods=["POST"])
@login_required
def delete_vmess():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM vmess_users WHERE username = ?", (username,)).fetchone():
            flash("VMess user not found", "error")
            return redirect(url_for("users"))
    result = telecomctl.xray_remove_vmess(username)
    if result.returncode != 0:
        flash(f"Failed to remove VMess user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("DELETE FROM vmess_users WHERE username = ?", (username,))
    flash(f"VMess user {username} deleted", "info")
    return redirect(url_for("users"))


@bp.route("/vless/add", methods=["POST"])
@login_required
def add_vless():
    username = request.form["username"].strip()
    days = request.form["days"]
    try:
        validate_days(days)
        sni = normalize_sni(request.form.get("sni"), get_default_sni())
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    expires_at = days_to_expiry(days)
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM vless_users WHERE username = ?", (username,)).fetchone():
            flash(f"VLESS user already exists: {username}", "error")
            return redirect(url_for("users"))
    uuid_str = telecomctl.generate_uuid()
    if not uuid_str:
        flash("Failed to generate UUID", "error")
        return redirect(url_for("users"))
    result = telecomctl.xray_add_vless(username, uuid_str)
    if result.returncode != 0:
        flash(f"Failed to add Xray client: {result.stderr}", "error")
        return redirect(url_for("users"))
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO vless_users (username, uuid, sni, expires_at, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                (username, uuid_str, sni, expires_at, now_ts(), now_ts()),
            )
    except Exception as e:
        telecomctl.xray_remove_vless(username)
        flash(f"Failed to save VLESS user: {e}", "error")
        return redirect(url_for("users"))
    flash(f"VLESS user {username} created", "success")
    return redirect(url_for("users"))


@bp.route("/vless/disable", methods=["POST"])
@login_required
def disable_vless():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM vless_users WHERE username = ?", (username,)).fetchone():
            flash("VLESS user not found", "error")
            return redirect(url_for("users"))
    result = telecomctl.xray_disable_vless(username)
    if result.returncode != 0:
        flash(f"Failed to disable VLESS user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("UPDATE vless_users SET is_active = 0, updated_at = ? WHERE username = ?", (now_ts(), username))
    flash(f"VLESS user {username} disabled", "info")
    return redirect(url_for("users"))


@bp.route("/vless/enable", methods=["POST"])
@login_required
def enable_vless():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        user = conn.execute("SELECT * FROM vless_users WHERE username = ?", (username,)).fetchone()
        if not user:
            flash("VLESS user not found", "error")
            return redirect(url_for("users"))
        if user["expires_at"] <= now_ts():
            flash("Expired users cannot be enabled; recreate the account with a new expiry", "error")
            return redirect(url_for("users"))
    result = telecomctl.xray_enable_vless(user["username"], user["uuid"])
    if result.returncode != 0:
        flash(f"Failed to enable VLESS user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("UPDATE vless_users SET is_active = 1, updated_at = ? WHERE username = ?", (now_ts(), username))
    flash(f"VLESS user {username} enabled", "success")
    return redirect(url_for("users"))


@bp.route("/vless/delete", methods=["POST"])
@login_required
def delete_vless():
    username = request.form["username"].strip()
    try:
        validate_username(username)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM vless_users WHERE username = ?", (username,)).fetchone():
            flash("VLESS user not found", "error")
            return redirect(url_for("users"))
    result = telecomctl.xray_remove_vless(username)
    if result.returncode != 0:
        flash(f"Failed to remove VLESS user: {result.stderr}", "error")
        return redirect(url_for("users"))
    with get_conn() as conn:
        conn.execute("DELETE FROM vless_users WHERE username = ?", (username,))
    flash(f"VLESS user {username} deleted", "info")
    return redirect(url_for("users"))
