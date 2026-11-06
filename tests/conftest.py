from pathlib import Path
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.engine import make_url

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


@pytest.fixture(scope="session")
def postgresql_engine():
    database_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://reservas:reservas@localhost:5433/reservas_test",
    )
    parsed_url = make_url(database_url)
    if (
        parsed_url.get_backend_name() != "postgresql"
        or parsed_url.host not in {"localhost", "127.0.0.1"}
        or parsed_url.port != 5433
        or parsed_url.database != "reservas_test"
    ):
        raise ValueError(
            "Las pruebas PostgreSQL requieren TEST_DATABASE_URL apuntando a "
            "reservas_test en localhost:5433."
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.connect():
        pass

    from alembic import command
    from alembic.config import Config

    prior_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if prior_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prior_database_url

    yield engine
    engine.dispose()


@pytest.fixture
def postgresql_session(postgresql_engine):
    with postgresql_engine.begin() as connection:
        connection.exec_driver_sql(
            """
            TRUNCATE TABLE
                reservation_history,
                reservations,
                academic_spaces,
                account_history,
                verification_tokens,
                revoked_tokens,
                users
            CASCADE
            """
        )
    factory = sessionmaker(
        bind=postgresql_engine, autoflush=False, expire_on_commit=False
    )
    with factory() as session:
        yield session


@pytest.fixture
def postgresql_client(postgresql_session, settings):
    from app.main import create_app

    application = create_app(settings)

    def override_get_db():
        yield postgresql_session

    application.dependency_overrides[get_db] = override_get_db
    with TestClient(application) as test_client:
        yield test_client


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
