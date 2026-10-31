import hashlib
from functools import lru_cache

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.config import Settings

PASSWORD_MIN_LENGTH = 12


def _password_material(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError("La contraseña debe tener al menos 12 caracteres.")
    return bcrypt.hashpw(_password_material(password), bcrypt.gensalt(rounds=12)).decode(
        "ascii"
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        return False
    try:
        return bcrypt.checkpw(
            _password_material(password), password_hash.encode("ascii")
        )
    except (ValueError, UnicodeEncodeError):
        return False


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    return bcrypt.hashpw(
        _password_material("not-a-real-user-password"), bcrypt.gensalt(rounds=12)
    ).decode("ascii")


def create_access_token(user_id: str, settings: Settings, now: datetime | None = None):
    issued_at = now or datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=60)
    token_id = str(uuid4())
    encoded = jwt.encode(
        {
            "sub": user_id,
            "jti": token_id,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    return encoded, token_id, expires_at
