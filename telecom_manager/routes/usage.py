import csv
import io
from flask import Blueprint, render_template
from ..auth import login_required
from ..db import get_conn, now_ts, format_date

bp = Blueprint("usage", __name__)


@bp.route("/usage")
@login_required
def usage():
    with get_conn() as conn:
        logs = conn.execute(
            "SELECT * FROM usage_log WHERE logged_at > ? ORDER BY logged_at DESC LIMIT 500",
            (now_ts() - 86400 * 7,),
        ).fetchall()
        daily = conn.execute(
            "SELECT type, COUNT(*) as cnt FROM usage_log WHERE logged_at > ? GROUP BY type",
            (now_ts() - 86400,),
        ).fetchall()
    return render_template("usage.html", logs=logs, daily=daily)


@bp.route("/usage/export.csv")
@login_required
def usage_export():
    with get_conn() as conn:
        logs = conn.execute(
            "SELECT username, type, logged_at FROM usage_log ORDER BY logged_at DESC LIMIT 10000"
        ).fetchall()
    si = io.StringIO()
    w = csv.writer(si)
    w.writerow(["username", "type", "logged_at"])
    for row in logs:
        w.writerow([row["username"], row["type"], format_date(row["logged_at"])])
    return si.getvalue(), 200, {"Content-Type": "text/csv", "Content-Disposition": "attachment; filename=usage.csv"}
