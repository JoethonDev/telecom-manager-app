"""Tests for connection link generation."""
import os
import sys
import json as json_mod
import base64
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["TELECOM_DEV"] = "1"
os.environ["TELECOMCTL_MODE"] = "mock"
os.environ["MANAGER_DB"] = ":memory:"
os.environ["FLASK_SECRET"] = "test"
os.environ["VMESS_PORT"] = "2053"
os.environ["VLESS_PORT"] = "8443"
os.environ["VLESS_FLOW"] = "xtls-rprx-vision"
os.environ["TLS_SERVER_NAME"] = "test.example.com"
os.environ["PUBLIC_IP"] = "203.0.113.10"


def test_vmess_link():
    from telecom_manager.services.links import vmess_link
    link = vmess_link("testuser", "550e8400-e29b-41d4-a716-446655440000", "sni.example.com")
    assert link.startswith("vmess://")
    encoded = link[8:]
    decoded = json_mod.loads(base64.b64decode(encoded))
    assert decoded["ps"] == "testuser"
    assert decoded["id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert decoded["sni"] == "sni.example.com"
    assert decoded["port"] == "2053"


def test_vless_link():
    from telecom_manager.services.links import vless_link
    link = vless_link("testuser", "550e8400-e29b-41d4-a716-446655440000", "sni.example.com")
    assert link.startswith("vless://")
    assert "550e8400-e29b-41d4-a716-446655440000" in link
    assert "sni.example.com" in link
    assert "8443" in link


def test_ssh_connection_string():
    from telecom_manager.services.links import ssh_connection_string
    result = ssh_connection_string("testuser")
    assert "@" in result
    assert "testuser" in result


if __name__ == "__main__":
    test_vmess_link()
    test_vless_link()
    test_ssh_connection_string()
    print("All link tests passed.")
