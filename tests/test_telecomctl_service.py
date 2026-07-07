"""Tests for telecomctl service wrapper (mock mode)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["TELECOM_DEV"] = "1"
os.environ["TELECOMCTL_MODE"] = "mock"
os.environ["MANAGER_DB"] = ":memory:"
os.environ["FLASK_SECRET"] = "test"


def test_xray_add_vless():
    from telecom_manager.services import telecomctl
    result = telecomctl.xray_add_vless("testUser", "550e8400-e29b-41d4-a716-446655440000")
    assert result.returncode == 0
    assert "ok" in result.stdout


def test_xray_remove_vless():
    from telecom_manager.services import telecomctl
    result = telecomctl.xray_remove_vless("testUser")
    assert result.returncode == 0


def test_xray_add_vmess():
    from telecom_manager.services import telecomctl
    result = telecomctl.xray_add_vmess("testUser", "550e8400-e29b-41d4-a716-446655440000")
    assert result.returncode == 0
    assert "ok" in result.stdout


def test_xray_remove_vmess():
    from telecom_manager.services import telecomctl
    result = telecomctl.xray_remove_vmess("testUser")
    assert result.returncode == 0


def test_xray_list_users():
    from telecom_manager.services import telecomctl
    result = telecomctl.xray_list_users()
    assert result == []


def test_xray_status():
    from telecom_manager.services import telecomctl
    result = telecomctl.tele_xray_test_config()
    assert result.returncode == 0


def test_ssh_add_user():
    from telecom_manager.services import telecomctl
    result = telecomctl.ssh_add_user("testUser", "pass123", "2026-12-31")
    assert result.returncode == 0


def test_ssh_disable_user():
    from telecom_manager.services import telecomctl
    result = telecomctl.ssh_disable_user("testUser")
    assert result.returncode == 0


def test_ssh_delete_user():
    from telecom_manager.services import telecomctl
    result = telecomctl.ssh_delete_user("testUser")
    assert result.returncode == 0


def test_tele_status():
    from telecom_manager.services import telecomctl
    result = telecomctl.tele_status()
    assert result.returncode == 0


def test_tele_ports():
    from telecom_manager.services import telecomctl
    result = telecomctl.tele_ports()
    assert result.returncode == 0


def test_tele_diagnose():
    from telecom_manager.services import telecomctl
    result = telecomctl.tele_diagnose()
    assert result.returncode == 0


def test_generate_uuid():
    from telecom_manager.services import telecomctl
    uuid_str = telecomctl.generate_uuid()
    assert uuid_str.count("-") == 4
    assert len(uuid_str) == 36


if __name__ == "__main__":
    test_xray_add_vless()
    test_xray_remove_vless()
    test_xray_add_vmess()
    test_xray_remove_vmess()
    test_xray_list_users()
    test_xray_status()
    test_ssh_add_user()
    test_ssh_disable_user()
    test_ssh_delete_user()
    test_tele_status()
    test_tele_ports()
    test_tele_diagnose()
    test_generate_uuid()
    print("All telecomctl service tests passed.")
