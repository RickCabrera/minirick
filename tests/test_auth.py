"""Tests de `minirick.auth` — sesión local y OTP."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minirick import auth, db


@pytest.fixture
def session_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige `get_session_file` a un archivo temporal."""
    path = tmp_path / "session.json"
    monkeypatch.setattr(auth, "get_session_file", lambda: path)
    return path


@pytest.fixture(autouse=True)
def _reset_db_singleton():
    db.reset_client()
    yield
    db.reset_client()


def test_load_session_returns_none_when_missing(session_file: Path) -> None:
    assert not session_file.exists()
    assert auth.load_session() is None


def test_load_session_returns_none_on_corrupt_file(session_file: Path) -> None:
    session_file.write_text("{not json", encoding="utf-8")
    assert auth.load_session() is None


def test_save_and_load_session_roundtrip(session_file: Path) -> None:
    data = {"access_token": "abc", "refresh_token": "xyz", "user": {"email": "r@r.co"}}
    auth.save_session(data)
    assert session_file.exists()
    assert auth.load_session() == data


def test_logout_returns_false_when_no_session(session_file: Path) -> None:
    assert auth.logout() is False
    assert not session_file.exists()


def test_logout_deletes_session_file(session_file: Path) -> None:
    auth.save_session({"access_token": "a", "refresh_token": "b"})
    assert session_file.exists()

    fake_client = MagicMock()
    with patch.object(auth, "get_client", return_value=fake_client):
        assert auth.logout() is True

    assert not session_file.exists()
    fake_client.auth.sign_out.assert_called_once()


def test_logout_deletes_file_even_if_signout_fails(session_file: Path) -> None:
    auth.save_session({"access_token": "a", "refresh_token": "b"})
    fake_client = MagicMock()
    fake_client.auth.sign_out.side_effect = RuntimeError("network down")
    with patch.object(auth, "get_client", return_value=fake_client):
        assert auth.logout() is True
    assert not session_file.exists()


def test_request_otp_calls_supabase() -> None:
    fake_client = MagicMock()
    with patch.object(auth, "get_client", return_value=fake_client):
        auth.request_otp("foo@bar.com")
    fake_client.auth.sign_in_with_otp.assert_called_once_with({"email": "foo@bar.com"})


def test_request_otp_wraps_errors() -> None:
    fake_client = MagicMock()
    fake_client.auth.sign_in_with_otp.side_effect = RuntimeError("boom")
    with patch.object(auth, "get_client", return_value=fake_client):
        with pytest.raises(auth.AuthError, match="No se pudo enviar"):
            auth.request_otp("foo@bar.com")


def test_verify_otp_returns_session_dict() -> None:
    fake_session = MagicMock(
        access_token="tok_a",
        refresh_token="tok_r",
        expires_at=1234567890,
        token_type="bearer",
    )
    fake_session.user = MagicMock(id="uid", email="foo@bar.com")
    fake_response = MagicMock(session=fake_session)
    fake_client = MagicMock()
    fake_client.auth.verify_otp.return_value = fake_response

    with patch.object(auth, "get_client", return_value=fake_client):
        result = auth.verify_otp_code("foo@bar.com", "123456")

    fake_client.auth.verify_otp.assert_called_once_with(
        {"email": "foo@bar.com", "token": "123456", "type": "email"}
    )
    assert result["access_token"] == "tok_a"
    assert result["refresh_token"] == "tok_r"
    assert result["user"]["email"] == "foo@bar.com"


def test_verify_otp_raises_when_no_session() -> None:
    fake_client = MagicMock()
    fake_client.auth.verify_otp.return_value = MagicMock(session=None)
    with patch.object(auth, "get_client", return_value=fake_client):
        with pytest.raises(auth.AuthError, match="no devolvió sesión"):
            auth.verify_otp_code("foo@bar.com", "000000")


def test_ensure_session_returns_none_when_missing(session_file: Path) -> None:
    assert auth.ensure_session() is None


def test_ensure_session_restores_tokens(session_file: Path) -> None:
    session_file.write_text(
        json.dumps({"access_token": "a", "refresh_token": "b"}), encoding="utf-8"
    )
    fake_client = MagicMock()
    with patch.object(auth, "get_client", return_value=fake_client):
        result = auth.ensure_session()
    assert result == {"access_token": "a", "refresh_token": "b"}
    fake_client.auth.set_session.assert_called_once_with("a", "b")


def test_ensure_session_persists_rotated_tokens(session_file: Path) -> None:
    """Bug B: si supabase rota los tokens en set_session, deben persistirse a disco."""
    session_file.write_text(
        json.dumps({"access_token": "old_a", "refresh_token": "old_r"}),
        encoding="utf-8",
    )

    fresh_session = MagicMock(
        access_token="new_a",
        refresh_token="new_r",
        expires_at=9999999999,
        token_type="bearer",
    )
    fresh_session.user = MagicMock(id="uid", email="r@r.co")

    fake_client = MagicMock()
    # supabase-py retorna un wrapper con .session anidada
    fake_client.auth.get_session.return_value = MagicMock(session=fresh_session)
    fake_client.auth.set_session.return_value = None

    with patch.object(auth, "get_client", return_value=fake_client):
        result = auth.ensure_session()

    fake_client.auth.set_session.assert_called_once_with("old_a", "old_r")
    assert result["access_token"] == "new_a"
    assert result["refresh_token"] == "new_r"

    on_disk = json.loads(session_file.read_text(encoding="utf-8"))
    assert on_disk["access_token"] == "new_a"
    assert on_disk["refresh_token"] == "new_r"
