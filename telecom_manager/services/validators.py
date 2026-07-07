"""Input validators."""
import re
import ipaddress
from pathlib import Path

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_-]{2,31}$")
DOMAIN_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def validate_username(username):
    if not USERNAME_RE.match(username):
        raise ValueError("Invalid username. Use 3-32 chars: letters, numbers, _, -")


def validate_domain(value):
    if value and not DOMAIN_RE.match(value):
        raise ValueError(f"Invalid domain: {value}")


def validate_port(value):
    port = int(value)
    if port < 1 or port > 65535:
        raise ValueError(f"Invalid port: {value}")


def validate_public_ip(value):
    if value:
        ipaddress.ip_address(value)


def validate_days(value):
    days = int(value)
    if days < 1 or days > 3650:
        raise ValueError("Days must be between 1 and 3650")


def validate_password(value):
    if not value:
        raise ValueError("Password cannot be empty")
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError("Password contains an invalid control character")


def validate_uuid(value):
    if not UUID_RE.match(value):
        raise ValueError("Invalid UUID format")


def validate_timezone(value):
    if value and not Path(f"/usr/share/zoneinfo/{value}").exists():
        raise ValueError(f"Invalid timezone: {value}")


def normalize_sni(value, default_sni):
    value = (value or "").strip()
    if value and value != default_sni:
        raise ValueError(f"SNI is fixed to {default_sni} by the server certificate")
    return default_sni
