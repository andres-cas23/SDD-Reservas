from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db import Base, get_db


@pytest.fixture
def repository_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    return root


@pytest.fixture
def secrets_dir(tmp_path: Path) -> Path:
    path = tmp_path / "secrets"
    path.mkdir()
    return path


@pytest.fixture
def settings(secrets_dir: Path) -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        jwt_secret="test-secret-value-that-is-at-least-32-bytes",
        app_base_url="http://testserver",
        smtp_host="localhost",
        smtp_sender="noreply@example.com",
        secrets_dir=secrets_dir,
        admin_email="admin@example.com",
    )


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db_session, settings, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("JWT_SECRET", settings.jwt_secret.get_secret_value())
    monkeypatch.setenv("APP_BASE_URL", settings.app_base_url)
    monkeypatch.setenv("SMTP_HOST", settings.smtp_host)
    monkeypatch.setenv("SMTP_SENDER", settings.smtp_sender)
    monkeypatch.setenv("SECRETS_DIR", str(settings.secrets_dir))

    from app.main import create_app

    application = create_app(settings)

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    with TestClient(application) as test_client:
        yield test_client
