"""Wrapper for telecomctl privileged operations."""
import json
import os
import subprocess
import uuid as uuid_mod
from ..config import TELECOMCTL_PATH, TELECOM_DEV, TELECOMCTL_MODE


def _run(cmd_args):
    """Run telecomctl via sudo (production) or mock (dev)."""
    if TELECOM_DEV and TELECOMCTL_MODE == "mock":
        return _mock_run(cmd_args)
    full_cmd = ["sudo", TELECOMCTL_PATH] + cmd_args
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    return result


def _mock_run(cmd_args):
    """Mock telecomctl responses for local dev."""
    import time
    import random

    class MockResult:
        def __init__(self, stdout="", stderr="", returncode=0):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    cmd = " ".join(cmd_args)

    if "xray list-users" in cmd:
        return MockResult("")
    if "xray status" in cmd:
        return MockResult("active")
    if "xray test-config" in cmd:
        return MockResult("ok")
    if "xray restart" in cmd:
        return MockResult("ok")
    if "status" in cmd:
        return MockResult("xray: active\nstunnel4: active\nsshd-httpcustom: active\nssh: active")
    if "ports" in cmd:
        return MockResult("LISTEN 0.0.0.0:443\nLISTEN 0.0.0.0:2053\nLISTEN 0.0.0.0:8443\nLISTEN 127.0.0.1:9000\nLISTEN 127.0.0.1:2222")
    if "logs" in cmd:
        return MockResult("(mock log output)\n")
    if "diagnose" in cmd:
        return MockResult("(mock diagnostics)")
    if "fix-permissions" in cmd:
        return MockResult("permissions repaired")
    if "ssh add-user" in cmd or "ssh enable-user" in cmd or "ssh disable-user" in cmd or "ssh delete-user" in cmd:
        return MockResult("ok")
    if "ssh list-users" in cmd:
        return MockResult("")
    if "xray add" in cmd or "xray remove" in cmd or "xray enable" in cmd or "xray disable" in cmd:
        return MockResult("ok")

    return MockResult("", "unknown command", 1)


def xray_add_vless(username, uuid_str):
    return _run(["xray", "add-vless", "--username", username, "--uuid", uuid_str])


def xray_remove_vless(username):
    return _run(["xray", "remove-vless", "--username", username])


def xray_enable_vless(username, uuid_str):
    return _run(["xray", "enable-vless", "--username", username, "--uuid", uuid_str])


def xray_disable_vless(username):
    return _run(["xray", "disable-vless", "--username", username])


def xray_add_vmess(username, uuid_str):
    return _run(["xray", "add-vmess", "--username", username, "--uuid", uuid_str])


def xray_remove_vmess(username):
    return _run(["xray", "remove-vmess", "--username", username])


def xray_enable_vmess(username, uuid_str):
    return _run(["xray", "enable-vmess", "--username", username, "--uuid", uuid_str])


def xray_disable_vmess(username):
    return _run(["xray", "disable-vmess", "--username", username])


def xray_list_users():
    result = _run(["xray", "list-users"])
    if result.returncode != 0:
        return []
    users = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            users.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return users


def ssh_add_user(username, password, expires_at):
    return _run(["ssh", "add-user", "--username", username, "--password", password, "--expires-at", expires_at])


def ssh_disable_user(username):
    return _run(["ssh", "disable-user", "--username", username])


def ssh_enable_user(username, expires_at):
    return _run(["ssh", "enable-user", "--username", username, "--expires-at", expires_at])


def ssh_delete_user(username):
    return _run(["ssh", "delete-user", "--username", username])


def tele_status():
    return _run(["status"])


def tele_ports():
    return _run(["ports"])


def tele_logs(service="xray", lines=100):
    return _run(["logs", "--service", service, "--lines", str(lines)])


def tele_diagnose():
    return _run(["diagnose"])


def tele_fix_permissions():
    return _run(["fix-permissions"])


def tele_xray_test_config():
    return _run(["xray", "test-config"])


def tele_xray_restart():
    return _run(["xray", "restart"])


def generate_uuid():
    if TELECOM_DEV and TELECOMCTL_MODE == "mock":
        return str(uuid_mod.uuid4())
    result = subprocess.run(["xray", "uuid"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return str(uuid_mod.uuid4())
