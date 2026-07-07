import os
from pathlib import Path

TELECOM_DEV = os.environ.get("TELECOM_DEV", "") == "1"
TELECOMCTL_MODE = os.environ.get("TELECOMCTL_MODE", "")  # "mock" or ""
MANAGER_DB = Path(os.environ.get("MANAGER_DB", "/var/lib/telecom-manager/manager.db"))
PANEL_PORT = int(os.environ.get("PANEL_PORT", "9000"))
FLASK_SECRET = os.environ.get("FLASK_SECRET") or os.urandom(32).hex()
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

DOMAIN = os.environ.get("MANAGER_DOMAIN", "")
PANEL_DOMAIN = os.environ.get("PANEL_DOMAIN", "")
VMESS_PORT = os.environ.get("VMESS_PORT", "2053")
VLESS_PORT = os.environ.get("VLESS_PORT", "8443")
VLESS_FLOW = os.environ.get("VLESS_FLOW", "xtls-rprx-vision")
DEFAULT_SNI = os.environ.get("TLS_SERVER_NAME", "localhost")
PUBLIC_IP = os.environ.get("PUBLIC_IP", "")
PUBLIC_IPV6 = os.environ.get("PUBLIC_IPV6", "")
STUNNEL_PORT = os.environ.get("STUNNEL_PORT", "443")
SSH_TARGET_PORT = os.environ.get("SSH_TARGET_PORT", "22")
SSH_COMPAT_PORT = os.environ.get("SSH_COMPAT_PORT", "2222")

TELECOMCTL_PATH = "/usr/local/sbin/telecomctl"
