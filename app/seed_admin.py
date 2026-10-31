import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session_factory
from app.models import AccountHistory, User, VerificationToken, utc_now
from app.security import hash_opaque_token, hash_password

TOKEN_TTL_SECONDS = 24 * 60 * 60
ADMIN_ACTIVATION_FILE = "admin-activation.txt"


def _outside_repository(path: Path, repository_root: Path) -> Path:
    resolved = path.expanduser().resolve()
    root = repository_root.resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError("SECRETS_DIR debe estar fuera del repositorio.")
    return resolved


def seed_admin(
    db: Session,
    settings: Settings,
    repository_root: Path,
) -> Path | None:
    if not settings.admin_email:
        raise ValueError("ADMIN_EMAIL es obligatoria para crear el administrador inicial.")

    secrets_dir = _outside_repository(settings.secrets_dir, repository_root)
    email = str(settings.admin_email).strip().casefold()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        return None

    now = utc_now()
    raw_token = secrets.token_urlsafe(32)
    user = User(
        name="Administrador",
        email=email,
        password_hash=None,
        status="VERIFICADO",
        role="ADMIN",
        created_at=now,
    )
    db.add(user)
    db.flush()
    db.add_all(
        [
            AccountHistory(
                target_user_id=user.id,
                actor_user_id=None,
                change_type="STATE",
                old_value=None,
                new_value="VERIFICADO",
                created_at=now,
            ),
            AccountHistory(
                target_user_id=user.id,
                actor_user_id=None,
                change_type="ROLE",
                old_value=None,
                new_value="ADMIN",
                created_at=now,
            ),
            VerificationToken(
                user_id=user.id,
                token_hash=hash_opaque_token(raw_token),
                kind="ADMIN_ACTIVATION",
                created_at=now,
                expires_at=now + timedelta(seconds=TOKEN_TTL_SECONDS),
            ),
        ]
    )

    activation_file = secrets_dir / ADMIN_ACTIVATION_FILE
    activation_url = (
        f"{settings.app_base_url.rstrip('/')}/auth/activate-admin#"
        f"{urlencode({'token': raw_token})}"
    )
    secrets_dir.mkdir(parents=True, exist_ok=True)
    file_created = False
    try:
        descriptor = os.open(activation_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        file_created = True
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(activation_url)
        db.commit()
    except (OSError, SQLAlchemyError):
        db.rollback()
        if file_created:
            activation_file.unlink(missing_ok=True)
        raise

    return activation_file


def activate_seeded_admin(db: Session, token_value: str, password: str, settings: Settings) -> User:
    if len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres.")

    now = utc_now()
    token = db.scalar(
        select(VerificationToken).where(
            VerificationToken.token_hash == hash_opaque_token(token_value),
            VerificationToken.kind == "ADMIN_ACTIVATION",
            VerificationToken.consumed_at.is_(None),
        )
    )
    if token is None:
        raise ValueError("El enlace de activación no es válido.")

    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at <= now:
        raise ValueError("El enlace de activación expiró.")

    user = db.get(User, token.user_id)
    if user is None or user.role != "ADMIN" or user.password_hash is not None:
        raise ValueError("El enlace de activación no es válido.")

    user.password_hash = hash_password(password)
    token.consumed_at = now
    db.flush()
    activation_file = settings.secrets_dir / ADMIN_ACTIVATION_FILE
    activation_file.unlink()
    db.commit()
    return user


def main() -> int:
    settings = get_settings()
    factory = get_session_factory()
    try:
        with factory() as db:
            activation_file = seed_admin(
                db,
                settings,
                repository_root=Path(__file__).resolve().parents[1],
            )
    except (OSError, SQLAlchemyError, ValueError) as error:
        print(f"No se pudo crear el administrador inicial: {error}", file=sys.stderr)
        return 1

    if activation_file is None:
        print("El administrador inicial ya existe.")
    else:
        print("Administrador inicial creado; enlace de activación guardado fuera del repositorio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
