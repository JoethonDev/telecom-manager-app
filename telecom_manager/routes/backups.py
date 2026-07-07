import glob
import os
from pathlib import Path
from flask import Blueprint, render_template, jsonify
from ..auth import login_required
from ..db import MANAGER_DB

bp = Blueprint("backups", __name__)


@bp.route("/backups")
@login_required
def backups():
    bk_dir = MANAGER_DB.parent / "backups"
    files = sorted(glob.glob(str(bk_dir / "manager.db.*")), reverse=True) if bk_dir.exists() else []
    return render_template("backups.html", backups=[{
        "path": f, "name": os.path.basename(f), "size": os.path.getsize(f),
        "mtime": os.path.getmtime(f),
    } for f in files])
