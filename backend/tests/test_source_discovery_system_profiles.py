"""Tests for Windows technical-profile filtering."""

from app.modules.source_discovery import SourceDiscoveryService


def test_windows_technical_profiles_are_ignored() -> None:
    names = (
        "TEMP",
        "TEMP.Font Driver Host",
        "TEMP.Font Driver Host.000",
        "TEMP.Font Driver Host.999",
        "UMFD-0",
        "UMFD-0.Font Driver Host",
        "UMFD-0.Font Driver Host.000",
        "UMFD-0.Font Driver Host.999",
        "WsiAccount",
    )

    for name in names:
        assert SourceDiscoveryService._should_ignore_user(name) is True


def test_real_user_profile_is_not_ignored() -> None:
    assert SourceDiscoveryService._should_ignore_user("fred") is False
