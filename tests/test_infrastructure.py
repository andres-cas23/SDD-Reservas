from pydantic import SecretStr

from app import db as database
from app.mailer import send_verification_email
from app.security import hash_password, verify_password


def test_smtp_delivery_uses_configured_tls_and_credentials(
    settings, monkeypatch
):
    class SMTPStub:
        def __init__(self, host, port, timeout):
            self.connection = (host, port, timeout)
            self.tls_started = False
            self.login_args = None
            self.message = None

        def __enter__(self):
            return self

        def __exit__(self, _type, _value, _traceback):
            return False

        def starttls(self):
            self.tls_started = True

        def login(self, username, password):
            self.login_args = (username, password)

        def send_message(self, message):
            self.message = message

    settings.smtp_use_tls = True
    settings.smtp_username = "smtp-user"
    settings.smtp_password = SecretStr("smtp-secret")
    smtp = SMTPStub("localhost", 1025, 10)
    monkeypatch.setattr("app.mailer.smtplib.SMTP", lambda *args, **kwargs: smtp)

    send_verification_email(
        settings, "user@example.com", "https://example.com/auth/verify#token=secret"
    )

    assert smtp.connection == ("localhost", 1025, 10)
    assert smtp.tls_started
    assert smtp.login_args == ("smtp-user", "smtp-secret")
    assert smtp.message["To"] == "user@example.com"
    assert "token=secret" in smtp.message.get_content()


def test_smtp_delivery_supports_local_mailpit_without_tls_or_auth(
    settings, monkeypatch
):
    class SMTPStub:
        tls_started = False
        login_called = False
        message = None

        def __enter__(self):
            return self

        def __exit__(self, _type, _value, _traceback):
            return False

        def starttls(self):
            self.tls_started = True

        def login(self, _username, _password):
            self.login_called = True

        def send_message(self, message):
            self.message = message

    smtp = SMTPStub()
    monkeypatch.setattr("app.mailer.smtplib.SMTP", lambda *args, **kwargs: smtp)

    send_verification_email(settings, "user@example.com", "http://localhost/verify")

    assert not smtp.tls_started
    assert not smtp.login_called
    assert smtp.message["Subject"] == "Verifica tu cuenta"


def test_session_factory_and_database_dependency(monkeypatch, settings):
    database.get_session_factory.cache_clear()
    monkeypatch.setattr(database, "get_settings", lambda: settings)
    factory = database.get_session_factory()
    assert factory.kw["bind"].url.drivername == "sqlite+pysqlite"
    assert factory.kw["bind"].url.database == ":memory:"

    database.get_session_factory.cache_clear()
    independent_factory = database.build_session_factory(
        "sqlite+pysqlite:///:memory:"
    )
    with independent_factory() as session:
        assert session.is_active
    independent_factory.kw["bind"].dispose()

    class SessionStub:
        closed = False

        def close(self):
            self.closed = True

    session = SessionStub()
    monkeypatch.setattr(
        database, "get_session_factory", lambda: lambda: session
    )
    dependency = database.get_db()
    assert next(dependency) is session
    dependency.close()
    assert session.closed


def test_password_hash_validation_handles_invalid_input():
    hashed = hash_password("a-valid-password")
    assert not verify_password("short", "not-a-valid-bcrypt-hash")
    assert not verify_password("a-valid-password", None)
    assert not verify_password("a-valid-password", "not-a-valid-bcrypt-hash")
    assert verify_password("a-valid-password", hashed)
