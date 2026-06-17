import pytest

from tidalwave.auth.registration import RegistrationDenied, ensure_allowed


def test_open_mode_allows_anyone():
    ensure_allowed("alice", mode="open", allowlist=[])  # no exception


def test_allowlist_allows_listed_user_case_insensitive():
    ensure_allowed("Alice", mode="allowlist", allowlist=["alice"])


def test_allowlist_denies_unlisted_user():
    with pytest.raises(RegistrationDenied):
        ensure_allowed("mallory", mode="allowlist", allowlist=["alice"])
