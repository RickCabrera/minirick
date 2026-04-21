"""Tests de `minirick.db` — cliente Supabase singleton."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from minirick import db


@pytest.fixture(autouse=True)
def _reset_db_singleton():
    """Asegura aislamiento entre tests: resetea el cliente singleton."""
    db.reset_client()
    yield
    db.reset_client()


def test_get_supabase_url_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    # Evita leer un .env real del cwd
    with patch.object(db, "_ensure_dotenv_loaded", lambda: None):
        assert db.get_supabase_url() == db.DEFAULT_SUPABASE_URL


def test_get_supabase_url_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://custom.supabase.co")
    with patch.object(db, "_ensure_dotenv_loaded", lambda: None):
        assert db.get_supabase_url() == "https://custom.supabase.co"


def test_get_supabase_key_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_KEY", "sb_publishable_test_key")
    with patch.object(db, "_ensure_dotenv_loaded", lambda: None):
        assert db.get_supabase_key() == "sb_publishable_test_key"


def test_get_client_returns_configured_singleton() -> None:
    fake_client = MagicMock(name="SupabaseClient")
    with patch.object(db, "create_client", return_value=fake_client) as creator:
        first = db.get_client()
        second = db.get_client()
    assert first is fake_client
    assert first is second
    # Solo debe crearlo una vez aunque se pida varias veces
    creator.assert_called_once()


def test_reset_client_forces_reinit() -> None:
    fake_a, fake_b = MagicMock(), MagicMock()
    with patch.object(db, "create_client", side_effect=[fake_a, fake_b]):
        a = db.get_client()
        db.reset_client()
        b = db.get_client()
    assert a is fake_a
    assert b is fake_b
