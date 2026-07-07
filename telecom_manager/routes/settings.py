from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..auth import login_required
from ..db import get_conn, now_ts, get_setting, set_setting, clear_settings_cache
from ..services.validators import validate_domain, validate_public_ip, validate_port
from ..services.links import get_effective_settings
from ..services import telecomctl

bp = Blueprint("settings", __name__)

PORT_KEYS = ["stunnel_port", "vmess_port", "vless_port", "ssh_compat_port"]


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    cfg = get_effective_settings()
    if request.method == "POST":
        connection_domain = request.form.get("connection_domain", "").strip()
        panel_domain = request.form.get("panel_domain", "").strip()
        public_ip = request.form.get("public_ip", "").strip()
        try:
            validate_domain(connection_domain)
            validate_domain(panel_domain)
            validate_public_ip(public_ip)
        except (ValueError, TypeError) as e:
            flash(str(e), "error")
            return redirect(url_for("settings.settings"))
        pairs = [("connection_domain", connection_domain), ("public_ip", public_ip)]
        if panel_domain:
            pairs.append(("panel_domain", panel_domain))
        for key in PORT_KEYS:
            val = request.form.get(key, "").strip()
            if val:
                try:
                    validate_port(val)
                except (ValueError, TypeError) as e:
                    flash(str(e), "error")
                    return redirect(url_for("settings.settings"))
                pairs.append((key, val))
        changed_ports = []
        with get_conn() as conn:
            for key, value in pairs:
                existing = None
                if key in PORT_KEYS:
                    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
                    existing = row["value"] if row else cfg.get(key, "")
                    if value == existing:
                        continue
                conn.execute(
                    "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                    (key, value or "", now_ts()),
                )
                if key in PORT_KEYS and value:
                    changed_ports.append((key, value))
        clear_settings_cache()
        domain_changed = connection_domain != cfg.get("connection_domain", "")
        panel_domain_changed = panel_domain != cfg.get("panel_domain", "")
        if panel_domain_changed and panel_domain:
            telecomctl.nginx_reconfigure(panel_domain)
        elif domain_changed and connection_domain:
            telecomctl.nginx_reconfigure(connection_domain)
        if changed_ports:
            new_cfg = get_effective_settings()
            ports_in_use = {new_cfg.get(k, "") for k in PORT_KEYS}
            listen_result = telecomctl.tele_ports()
            listening = set()
            if listen_result.returncode == 0:
                for line in listen_result.stdout.splitlines():
                    if "LISTEN" in line and ":" in line:
                        p = line.rsplit(":", 1)[-1].strip()
                        listening.add(p)
            for key, val in changed_ports:
                if val in ports_in_use and val != new_cfg.get(key, ""):
                    flash(f"Port {val} is already configured for another service", "error")
                    return redirect(url_for("settings.settings"))
                if val in listening and val != new_cfg.get(key, ""):
                    flash(f"Port {val} is already in use on this server", "error")
                    return redirect(url_for("settings.settings"))
            for key, val in changed_ports:
                service = key.replace("_port", "").replace("ssh_compat", "ssh-compat")
                result = telecomctl.port_set(service, val)
                if result.returncode != 0:
                    flash(f"Failed to apply port {val} for {service}: {result.stderr}", "error")
                else:
                    flash(f"Port for {service} changed to {val}. Service restarted.", "success")
        else:
            flash("Settings saved.", "success")
        return redirect(url_for("settings.settings"))
    return render_template("settings.html", settings=cfg)
