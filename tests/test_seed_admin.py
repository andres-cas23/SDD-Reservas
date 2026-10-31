import base64
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import AccountHistory, User, VerificationToken, utc_now
from app.seed_admin import (
    ADMIN_ACTIVATION_FILE,
    activate_seeded_admin,
    seed_admin,
)
from app.security import verify_password
from app import seed_admin as seed_module


def test_seed_creates_admin_and_activation_file_outside_repository(
    db_session, settings, repository_root: Path
):
    activation_file = seed_admin(db_session, settings, repository_root)

    assert activation_file == settings.secrets_dir / ADMIN_ACTIVATION_FILE
    assert activation_file.is_file()
    assert repository_root not in activation_file.resolve().parents
    activation_url = activation_file.read_text(encoding="utf-8")
    token_value = parse_qs(urlparse(activation_url).fragment)["token"][0]
    decoded_token = base64.urlsafe_b64decode(token_value + "=" * (-len(token_value) % 4))
    assert len(decoded_token) == 32

    user = db_session.scalar(select(User).where(User.email == "admin@example.com"))
    assert user is not None
    assert user.status == "VERIFICADO"
    assert user.role == "ADMIN"
    assert user.password_hash is None

    token = db_session.scalar(
        select(VerificationToken).where(VerificationToken.user_id == user.id)
    )
    assert token is not None
    assert token.kind == "ADMIN_ACTIVATION"
    assert token.expires_at - token.created_at == timedelta(hours=24)
    assert len(db_session.scalars(select(AccountHistory)).all()) == 2


def test_admin_activation_sets_password_consumes_token_and_deletes_file(
    db_session, settings, repository_root: Path
):
    activation_file = seed_admin(db_session, settings, repository_root)
    activation_url = activation_file.read_text(encoding="utf-8")
    token_value = parse_qs(urlparse(activation_url).fragment)["token"][0]

    user = activate_seeded_admin(
        db_session, token_value, "a-long-password-123", settings
    )

    assert user.password_hash is not None
    assert verify_password("a-long-password-123", user.password_hash)
    assert not activation_file.exists()
    with pytest.raises(ValueError, match="no es válido"):
        activate_seeded_admin(
            db_session, token_value, "a-long-password-123", settings
        )


def test_admin_activation_rejects_short_or_expired_link(
    db_session, settings, repository_root: Path
):
    activation_file = seed_admin(db_session, settings, repository_root)
    token_value = parse_qs(urlparse(activation_file.read_text(encoding="utf-8")).fragment)[
        "token"
    ][0]
    token = db_session.scalar(select(VerificationToken))
    token.expires_at = utc_now() - timedelta(seconds=1)
    db_session.commit()

    with pytest.raises(ValueError, match="12 caracteres"):
        activate_seeded_admin(db_session, token_value, "short", settings)
    with pytest.raises(ValueError, match="expiró"):
        activate_seeded_admin(
            db_session, token_value, "a-long-password-123", settings
        )
    assert activation_file.exists()


def test_seed_requires_secrets_directory_outside_repository(
    db_session, settings, repository_root: Path
):
    settings.secrets_dir = repository_root / "secrets"

    with pytest.raises(ValueError, match="fuera del repositorio"):
        seed_admin(db_session, settings, repository_root)

    assert db_session.scalar(select(User)) is None


def test_failed_seed_does_not_remove_existing_activation_file(
    db_session, settings, repository_root: Path
):
    activation_file = settings.secrets_dir / ADMIN_ACTIVATION_FILE
    activation_file.write_text("existing-value", encoding="utf-8")

    with pytest.raises(FileExistsError):
        seed_admin(db_session, settings, repository_root)

    assert activation_file.read_text(encoding="utf-8") == "existing-value"
    assert db_session.scalar(select(User)) is None


def test_seed_is_idempotent_and_requires_admin_email(
    db_session, settings, repository_root: Path
):
    activation_file = seed_admin(db_session, settings, repository_root)
    original_contents = activation_file.read_text(encoding="utf-8")

    assert seed_admin(db_session, settings, repository_root) is None
    assert activation_file.read_text(encoding="utf-8") == original_contents

    settings.admin_email = None
    with pytest.raises(ValueError, match="ADMIN_EMAIL"):
        seed_admin(db_session, settings, repository_root)


def test_failed_database_commit_removes_new_activation_file(
    db_session, settings, repository_root: Path, monkeypatch
):
    def fail_commit():
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(SQLAlchemyError):
        seed_admin(db_session, settings, repository_root)

    activation_file = settings.secrets_dir / ADMIN_ACTIVATION_FILE
    assert not activation_file.exists()
    assert db_session.scalar(select(User)) is None


def test_seed_cli_never_prints_activation_link(
    settings, tmp_path: Path, monkeypatch, capsys
):
    class SessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, _type, _value, _traceback):
            return False

    token = "activation-token-must-not-be-printed"
    monkeypatch.setattr(seed_module, "get_settings", lambda: settings)
    monkeypatch.setattr(seed_module, "get_session_factory", lambda: SessionContext)
    monkeypatch.setattr(
        seed_module,
        "seed_admin",
        lambda _db, _settings, repository_root: tmp_path / token,
    )

    assert seed_module.main() == 0
    output = capsys.readouterr().out
    assert "Administrador inicial creado" in output
    assert token not in output


def test_seed_cli_reports_missing_configuration_without_secrets(
    settings, monkeypatch, capsys
):
    class SessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, _type, _value, _traceback):
            return False

    monkeypatch.setattr(seed_module, "get_settings", lambda: settings)
    monkeypatch.setattr(seed_module, "get_session_factory", lambda: SessionContext)
    monkeypatch.setattr(
        seed_module,
        "seed_admin",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("ADMIN_EMAIL is required")
        ),
    )

    assert seed_module.main() == 1
    output = capsys.readouterr()
    assert "ADMIN_EMAIL" in output.err
    assert "token" not in output.out.lower()


def test_activation_rejects_unknown_token(db_session, settings):
    with pytest.raises(ValueError, match="no es válido"):
        activate_seeded_admin(
            db_session, "unknown-token", "a-long-password-123", settings
        )


def test_seeded_admin_can_activate_through_api_and_file_is_removed(
    client, db_session, settings, repository_root: Path
):
    activation_file = seed_admin(db_session, settings, repository_root)
    activation_url = activation_file.read_text(encoding="utf-8")
    token_value = parse_qs(urlparse(activation_url).fragment)["token"][0]

    landing = client.get("/auth/activate-admin")
    assert landing.status_code == 200
    assert activation_file.exists()
    response = client.post(
        "/auth/activate-admin",
        json={"token": token_value, "password": "a-long-password-123"},
    )

    assert response.status_code == 200
    assert not activation_file.exists()
    user = db_session.scalar(select(User))
    assert verify_password("a-long-password-123", user.password_hash)
