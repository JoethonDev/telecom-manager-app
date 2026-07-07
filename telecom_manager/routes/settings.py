from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..auth import login_required
from ..db import get_conn, now_ts, get_setting, set_setting, clear_settings_cache
from ..services.validators import validate_domain, validate_public_ip
from ..services.links import get_effective_settings

bp = Blueprint("settings", __name__)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    cfg = get_effective_settings()
    if request.method == "POST":
        connection_domain = request.form.get("connection_domain", "").strip()
        public_ip = request.form.get("public_ip", "").strip()
        try:
            validate_domain(connection_domain)
            validate_public_ip(public_ip)
        except (ValueError, TypeError) as e:
            flash(str(e), "error")
            return redirect(url_for("settings"))
        with get_conn() as conn:
            for key, value in (("connection_domain", connection_domain), ("public_ip", public_ip)):
                conn.execute(
                    "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                    (key, value, now_ts()),
                )
        clear_settings_cache()
        flash("Connection settings saved.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", settings=cfg)
