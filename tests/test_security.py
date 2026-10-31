import logging
from urllib.parse import parse_qs, urlparse

from app.security import hash_password, verify_password


def test_bcrypt_hashes_minimum_and_long_passwords():
    password = "a-very-long-password"
    long_password = "a" * 100
    hashed = hash_password(password)
    long_hashed = hash_password(long_password)

    assert hashed.startswith("$2b$")
    assert long_hashed.startswith("$2b$")
    assert hashed != password
    assert verify_password(password, hashed)
    assert verify_password(long_password, long_hashed)
    assert not verify_password("different-password", hashed)


def test_passwords_and_tokens_are_not_written_to_application_logs(
    client, caplog
):
    caplog.set_level(logging.DEBUG)
    password = "a-very-long-password"
    sent = []
    client.app.state.send_verification = lambda recipient, link: sent.append(link)
    client.post(
        "/auth/register",
        json={
            "name": "Log Safety User",
            "email": "log-safety@example.com",
            "password": password,
        },
    )
    verification_token = parse_qs(urlparse(sent[0]).fragment)["token"][0]
    client.post("/auth/verify", json={"token": verification_token})
    login = client.post(
        "/auth/login",
        json={"email": "log-safety@example.com", "password": password},
    )
    access_token = login.json()["access_token"]
    client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert password not in caplog.text
    assert verification_token not in caplog.text
    assert access_token not in caplog.text
