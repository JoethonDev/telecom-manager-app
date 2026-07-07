"""Tests for input validators."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["TELECOM_DEV"] = "1"
os.environ["TELECOMCTL_MODE"] = "mock"
os.environ["MANAGER_DB"] = ":memory:"
os.environ["FLASK_SECRET"] = "test"


def test_validate_username_ok():
    from telecom_manager.services.validators import validate_username
    validate_username("valid_user_1")
    validate_username("test-user")
    assert True


def test_validate_username_invalid():
    from telecom_manager.services.validators import validate_username
    for bad in ["ab", "", "user with spaces", "user\nname", "a" * 33]:
        try:
            validate_username(bad)
            assert False, f"Should have raised for: {bad}"
        except ValueError:
            pass


def test_validate_domain_ok():
    from telecom_manager.services.validators import validate_domain
    validate_domain("example.com")
    validate_domain("sub.domain.org")
    assert True


def test_validate_domain_invalid():
    from telecom_manager.services.validators import validate_domain
    try:
        validate_domain("not a domain!")
        assert False
    except ValueError:
        pass


def test_validate_port():
    from telecom_manager.services.validators import validate_port
    validate_port("443")
    validate_port("1")
    validate_port("65535")
    for bad in ["0", "65536", "-1", "abc"]:
        try:
            validate_port(bad)
            assert False, f"Should have raised for: {bad}"
        except (ValueError, TypeError):
            pass


def test_validate_days():
    from telecom_manager.services.validators import validate_days
    validate_days("30")
    validate_days("1")
    validate_days("3650")
    for bad in ["0", "3651", "-1", "abc"]:
        try:
            validate_days(bad)
            assert False, f"Should have raised for: {bad}"
        except ValueError:
            pass


def test_validate_password():
    from telecom_manager.services.validators import validate_password
    validate_password("secure_pass_123")
    try:
        validate_password("")
        assert False
    except ValueError:
        pass
    try:
        validate_password("pass\nword")
        assert False
    except ValueError:
        pass


def test_validate_uuid():
    from telecom_manager.services.validators import validate_uuid
    validate_uuid("550e8400-e29b-41d4-a716-446655440000")
    try:
        validate_uuid("not-a-uuid")
        assert False
    except ValueError:
        pass


def test_normalize_sni():
    from telecom_manager.services.validators import normalize_sni
    result = normalize_sni("", "default.example.com")
    assert result == "default.example.com"
    result = normalize_sni("default.example.com", "default.example.com")
    assert result == "default.example.com"
    try:
        normalize_sni("other.example.com", "default.example.com")
        assert False
    except ValueError:
        pass


if __name__ == "__main__":
    test_validate_username_ok()
    test_validate_username_invalid()
    test_validate_domain_ok()
    test_validate_domain_invalid()
    test_validate_port()
    test_validate_days()
    test_validate_password()
    test_validate_uuid()
    test_normalize_sni()
    print("All validator tests passed.")
