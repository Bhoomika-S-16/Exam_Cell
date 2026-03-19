"""
Authentication module for Exam Attendance System.
Role-based token auth for admin and invigilator access.
"""

import uuid
import time

# ── Credentials (change in production!) ────────────────────────────────────────
CREDENTIALS = {
    "admin": {
        "username": "admin",
        "password": "admin123",
        "role": "admin",
    },
    "invigilator": {
        "username": "invigilator",
        "password": "invig123",
        "role": "invigilator",
    },
}

# ── Token Store ────────────────────────────────────────────────────────────────
# { token_string: { "role": str, "expiry": float } }
_active_tokens: dict[str, dict] = {}

TOKEN_EXPIRY_HOURS = 12


def login(username: str, password: str) -> dict | None:
    """Validate credentials and return token info, or None if invalid."""
    for _key, cred in CREDENTIALS.items():
        if username == cred["username"] and password == cred["password"]:
            token = uuid.uuid4().hex
            _active_tokens[token] = {
                "role": cred["role"],
                "expiry": time.time() + TOKEN_EXPIRY_HOURS * 3600,
            }
            return {"token": token, "role": cred["role"]}
    return None


def verify_token(token: str) -> dict | None:
    """Check whether a token is valid and not expired. Returns role info or None."""
    if not token:
        return None
    info = _active_tokens.get(token)
    if info is None:
        return None
    if time.time() > info["expiry"]:
        _active_tokens.pop(token, None)
        return None
    return {"role": info["role"]}


def verify_admin_token(token: str) -> bool:
    """Check if a token belongs to an admin."""
    info = verify_token(token)
    return info is not None and info["role"] == "admin"


def verify_invigilator_token(token: str) -> bool:
    """Check if a token belongs to an invigilator."""
    info = verify_token(token)
    return info is not None and info["role"] == "invigilator"


def revoke_token(token: str) -> None:
    """Remove a token (logout)."""
    _active_tokens.pop(token, None)


def clear_all_tokens() -> None:
    """Revoke every active token (used on daily reset)."""
    _active_tokens.clear()
