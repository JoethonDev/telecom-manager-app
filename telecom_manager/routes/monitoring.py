from flask import Blueprint, render_template, jsonify
from ..auth import login_required
from ..db import get_conn, now_ts
from ..services import telecomctl

bp = Blueprint("monitoring", __name__)


@bp.route("/monitoring")
@login_required
def monitoring():
    now = now_ts()
    with get_conn() as conn:
        samples = conn.execute(
            "SELECT * FROM monitoring_samples WHERE sampled_at > ? ORDER BY sampled_at ASC",
            (now - 86400,),
        ).fetchall()
        bandwidth = conn.execute(
            "SELECT service, SUM(bytes_in) as total_in, SUM(bytes_out) as total_out FROM bandwidth_log WHERE sampled_at > ? GROUP BY service ORDER BY service",
            (now - 86400,),
        ).fetchall()
        user_bandwidth = conn.execute(
            "SELECT username, service_type, SUM(bytes_in) as total_in, SUM(bytes_out) as total_out FROM user_bandwidth_log WHERE sampled_at > ? GROUP BY username, service_type ORDER BY service_type, username",
            (now - 86400,),
        ).fetchall()
    return render_template("monitoring.html", samples=samples, bandwidth=bandwidth, user_bandwidth=user_bandwidth, now=now)


@bp.route("/diagnostics")
@login_required
def diagnostics():
    result = telecomctl.tele_diagnose()
    return render_template("diagnostics.html", output=result.stdout)
