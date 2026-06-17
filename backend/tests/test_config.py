import pytest

from tidalwave.config import Settings


def test_defaults():
    s = Settings()
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert s.registration_mode == "allowlist"
    assert s.registration_allowlist == []


def test_allowlist_parses_csv(monkeypatch):
    monkeypatch.setenv("TIDALWAVE_REGISTRATION_ALLOWLIST", "alice, bob")
    s = Settings()
    assert s.registration_allowlist == ["alice", "bob"]


def test_invalid_registration_mode_rejected(monkeypatch):
    monkeypatch.setenv("TIDALWAVE_REGISTRATION_MODE", "nonsense")
    with pytest.raises(ValueError):
        Settings()
