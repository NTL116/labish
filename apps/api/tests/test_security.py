from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    get_key_pair,
    hash_password,
    verify_password,
)


def test_hash_password_uses_bcrypt_and_verifies() -> None:
    hashed = hash_password("s3cret-value")

    assert hashed != "s3cret-value"
    assert hashed.startswith("$2")
    assert verify_password("s3cret-value", hashed)
    assert not verify_password("wrong-password", hashed)


def test_hashes_are_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_key_pair_is_generated_and_cached() -> None:
    pair = get_key_pair()
    assert "BEGIN" in pair.private_key_pem
    assert "BEGIN PUBLIC KEY" in pair.public_key_pem
    assert get_key_pair() is pair


def test_create_and_decode_access_token_roundtrip() -> None:
    token = create_access_token(subject="user-123")
    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["iss"] == "labish-services"
    assert payload["aud"] == "labish-web"
    assert payload["jti"]


def test_token_uses_rs256_header() -> None:
    token = create_access_token(subject="user-123")
    header = jwt.get_unverified_header(token)
    assert header["alg"] == JWT_ALGORITHM


def test_expired_token_is_rejected() -> None:
    token = create_access_token(
        subject="user-123", expires_delta=timedelta(seconds=-10)
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_is_rejected() -> None:
    token = create_access_token(subject="user-123")
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered)


def test_token_signed_with_foreign_key_is_rejected() -> None:
    from app.core.security import _generate_rsa_key_pair

    foreign = _generate_rsa_key_pair()
    forged = jwt.encode(
        {"sub": "attacker", "iss": "labish-services", "aud": "labish-web"},
        foreign.private_key_pem,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)
