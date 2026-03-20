"""
Authentication module for Exam Attendance System.
Role-based token auth for admin and invigilator access.
"""

import uuid
import time
import os
from core.state import exam_state

# ── Credentials (read from environment in production) ──────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
INVIGILATOR_PASSWORD = os.environ.get("INVIGILATOR_PASSWORD", "invig123")

CREDENTIALS = {
    "admin": {
        "username": "admin",
        "password": ADMIN_PASSWORD,
        "role": "admin",
    },
    "invigilator": {
        "username": "invigilator",
        "password": INVIGILATOR_PASSWORD,
        "role": "invigilator",
    },
}

TOKEN_EXPIRY_HOURS = 12


def login(username: str, password: str) -> dict | None:
    """Validate credentials and return token info, or None if invalid."""
    for _key, cred in CREDENTIALS.items():
        if username == cred["username"] and password == cred["password"]:
            token = uuid.uuid4().hex
            expiry = time.time() + TOKEN_EXPIRY_HOURS * 3600
            exam_state.save_token(token, cred["role"], expiry)
            return {"token": token, "role": cred["role"]}
    return None


def verify_token(token: str) -> dict | None:
    """Check whether a token is valid and not expired. Returns role info or None."""
    if not token:
        return None
    return exam_state.verify_token_db(token)


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
    exam_state.revoke_token_db(token)


def clear_all_tokens() -> None:
    """Revoke every active token (used on daily reset)."""
    exam_state.clear_tokens_db()
