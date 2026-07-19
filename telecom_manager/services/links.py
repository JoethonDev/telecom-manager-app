"""Connection link generation for VMess and VLESS."""
import base64
import json as json_mod
from urllib.parse import urlencode, quote
from ..db import get_setting
from ..config import DOMAIN, VMESS_PORT, VLESS_PORT, VLESS_FLOW, DEFAULT_SNI, PUBLIC_IP, PUBLIC_IPV6


def get_effective_settings():
    return {
        "connection_domain": get_setting("connection_domain", DOMAIN),
        "panel_domain": get_setting("panel_domain", ""),
        "default_sni": get_setting("default_sni", DEFAULT_SNI),
        "stunnel_port": get_setting("stunnel_port", "443"),
        "ssh_target_port": "22",
        "ssh_compat_port": "2222",
        "vmess_port": get_setting("vmess_port", VMESS_PORT),
        "vless_port": get_setting("vless_port", VLESS_PORT),
        "vless_flow": get_setting("vless_flow", VLESS_FLOW),
        "panel_port": "9000",
        "timezone": get_setting("timezone", ""),
        "public_ip": get_setting("public_ip", PUBLIC_IP),
    }


def vmess_link(username, uuid, sni):
    cfg = get_effective_settings()
    conn_host = cfg["connection_domain"] or cfg["public_ip"] or PUBLIC_IPV6
    payload = {
        "v": "2", "ps": username, "add": conn_host,
        "port": cfg["vmess_port"], "id": uuid, "aid": "0",
        "net": "tcp", "type": "none", "host": "", "path": "",
        "tls": "tls", "sni": sni or cfg["default_sni"],
    }
    encoded = base64.b64encode(json_mod.dumps(payload).encode()).decode()
    return f"vmess://{encoded}"


def vless_link(username, uuid, sni):
    cfg = get_effective_settings()
    conn_host = cfg["connection_domain"] or cfg["public_ip"] or PUBLIC_IPV6
    params = {
        "security": "tls",
        "encryption": "none",
        "headerType": "none",
        "type": "tcp",
        "flow": cfg["vless_flow"],
        "sni": sni or cfg["default_sni"],
        "fp": "chrome",
        "allowInsecure": "1",
        "packetEncoding": "xudp",
    }
    return f"vless://{uuid}@{conn_host}:{cfg['vless_port']}/?{urlencode(params)}#{quote(username)}"


def ssh_connection_string(username):
    cfg = get_effective_settings()
    conn_host = cfg["connection_domain"] or cfg["public_ip"] or PUBLIC_IPV6
    return f"{conn_host}:{cfg['stunnel_port']}@{username}"
