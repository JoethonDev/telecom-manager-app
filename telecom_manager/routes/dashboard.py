from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..auth import login_required
from ..db import get_conn, now_ts
from ..services.links import get_effective_settings, vmess_link, vless_link
from ..services import telecomctl

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    cfg = get_effective_settings()
    conn_host = cfg["connection_domain"] or cfg["public_ip"] or ""
    with get_conn() as conn:
        active_ssh = conn.execute("SELECT COUNT(*) as cnt FROM ssh_users WHERE is_active = 1").fetchone()["cnt"]
        active_vmess = conn.execute("SELECT COUNT(*) as cnt FROM vmess_users WHERE is_active = 1").fetchone()["cnt"]
        active_vless = conn.execute("SELECT COUNT(*) as cnt FROM vless_users WHERE is_active = 1").fetchone()["cnt"]
        expired_ssh = conn.execute("SELECT COUNT(*) as cnt FROM ssh_users WHERE is_active = 0").fetchone()["cnt"]
        expired_vmess = conn.execute("SELECT COUNT(*) as cnt FROM vmess_users WHERE is_active = 0").fetchone()["cnt"]
        expired_vless = conn.execute("SELECT COUNT(*) as cnt FROM vless_users WHERE is_active = 0").fetchone()["cnt"]
        today_usage = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_log WHERE logged_at > ?",
            (now_ts() - 86400,),
        ).fetchone()
        hourly = conn.execute(
            "SELECT (logged_at / 3600) * 3600 as h, COUNT(*) as cnt FROM usage_log WHERE logged_at > ? GROUP BY h ORDER BY h",
            (now_ts() - 86400,),
        ).fetchall()
    return render_template(
        "dashboard.html",
        active_ssh=active_ssh, active_vmess=active_vmess, active_vless=active_vless,
        expired_ssh=expired_ssh, expired_vmess=expired_vmess, expired_vless=expired_vless,
        today_usage=today_usage["cnt"] if today_usage else 0,
        hourly=[r["cnt"] for r in hourly],
        domain=conn_host,
        stunnel_port=cfg["stunnel_port"],
        vmess_port=cfg["vmess_port"],
        vless_port=cfg["vless_port"],
        default_sni=cfg["default_sni"],
        public_ip=cfg["public_ip"],
    )


@bp.route("/services/restart", methods=["POST"])
@login_required
def restart_services():
    from ..services import telecomctl
    result = telecomctl.tele_xray_restart()
    if result.returncode == 0:
        flash("Xray restarted", "success")
    else:
        flash(f"Failed to restart: {result.stderr}", "error")
    return redirect(url_for("dashboard"))
