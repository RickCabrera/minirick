"""Autenticación con Supabase: OTP por email + persistencia de sesión local.

Flujo:
  1. `request_otp(email)` → Supabase manda un código de 6 dígitos al correo.
  2. `verify_otp_code(email, token)` → valida el código y retorna la sesión.
  3. `save_session(session)` → persiste los tokens en `session.json`.
  4. En llamadas posteriores, `ensure_session()` restaura tokens al cliente.
"""

from __future__ import annotations

import json
from typing import Any

from minirick.config import get_session_file
from minirick.db import get_client


class AuthError(Exception):
    """Error de autenticación con mensaje amigable para el usuario."""


def request_otp(email: str) -> None:
    """Pide a Supabase que mande un OTP al email indicado."""
    client = get_client()
    try:
        client.auth.sign_in_with_otp({"email": email})
    except Exception as exc:  # noqa: BLE001 — queremos wrap genérico
        raise AuthError(f"No se pudo enviar el código: {exc}") from exc


def verify_otp_code(email: str, token: str) -> dict[str, Any]:
    """Valida el código OTP y retorna un dict con los tokens de sesión."""
    client = get_client()
    try:
        response = client.auth.verify_otp(
            {"email": email, "token": token, "type": "email"}
        )
    except Exception as exc:  # noqa: BLE001
        raise AuthError(f"Código inválido o expirado: {exc}") from exc

    session = getattr(response, "session", None)
    if session is None:
        raise AuthError("Supabase no devolvió sesión. Intenta de nuevo.")

    return _session_to_dict(session)


def save_session(session_dict: dict[str, Any]) -> None:
    """Guarda los tokens de sesión en disco."""
    path = get_session_file()
    path.write_text(json.dumps(session_dict, indent=2), encoding="utf-8")


def load_session() -> dict[str, Any] | None:
    """Lee la sesión guardada. Retorna None si no existe o está corrupta."""
    path = get_session_file()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def logout() -> bool:
    """Borra la sesión local. Retorna True si había sesión, False si no."""
    path = get_session_file()
    if not path.exists():
        return False
    try:
        client = get_client()
        client.auth.sign_out()
    except Exception:  # noqa: BLE001 — el borrado local es lo importante
        pass
    path.unlink(missing_ok=True)
    return True


def ensure_session() -> dict[str, Any] | None:
    """Si hay sesión guardada, la restaura en el cliente. Retorna el dict o None."""
    session = load_session()
    if session is None:
        return None
    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    if not access_token or not refresh_token:
        return None
    try:
        client = get_client()
        client.auth.set_session(access_token, refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise AuthError(f"Sesión expirada o inválida: {exc}") from exc
    return session


def _session_to_dict(session: Any) -> dict[str, Any]:
    """Convierte el objeto Session de supabase-py a dict serializable."""
    user = getattr(session, "user", None)
    user_info: dict[str, Any] | None = None
    if user is not None:
        user_info = {
            "id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
        }
    return {
        "access_token": getattr(session, "access_token", None),
        "refresh_token": getattr(session, "refresh_token", None),
        "expires_at": getattr(session, "expires_at", None),
        "token_type": getattr(session, "token_type", None),
        "user": user_info,
    }
