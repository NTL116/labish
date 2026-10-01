"""RS256 JWT signing/verification and bcrypt password hashing.

Custom, explicit implementation using PyJWT and passlib — no third-party
auth frameworks. RSA keys are resolved from settings (inline PEM content
or file paths); when neither is configured, an ephemeral pair is
generated at startup for local development.
"""

import base64
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from passlib.context import CryptContext

from app.core.config import get_settings

JWT_ALGORITHM = "RS256"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


@dataclass(frozen=True)
class RSAKeyPair:
    private_key_pem: str
    public_key_pem: str


def _generate_rsa_key_pair() -> RSAKeyPair:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return RSAKeyPair(private_key_pem=private_pem, public_key_pem=public_pem)


@lru_cache
def get_key_pair() -> RSAKeyPair:
    """Resolve the RS256 key pair.

    Precedence: inline PEM settings, then PEM file paths, then an
    ephemeral generated pair for local development.
    """
    settings = get_settings()

    private_pem = settings.jwt_private_key
    public_pem = settings.jwt_public_key

    if private_pem is None and settings.jwt_private_key_path:
        private_pem = Path(settings.jwt_private_key_path).read_text()
    if public_pem is None and settings.jwt_public_key_path:
        public_pem = Path(settings.jwt_public_key_path).read_text()

    if private_pem and public_pem:
        return RSAKeyPair(private_key_pem=private_pem, public_key_pem=public_pem)

    return _generate_rsa_key_pair()


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expire,
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload, get_key_pair().private_key_pem, algorithm=JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """Verify signature/claims with the public key and return the payload.

    Raises ``jwt.InvalidTokenError`` (or a subclass) when invalid.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        get_key_pair().public_key_pem,
        algorithms=[JWT_ALGORITHM],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )


@lru_cache
def _get_secret_cipher() -> Fernet:
    """Symmetric cipher for encrypting stored integration credentials.

    The Fernet key is derived from the RS256 private key so no extra
    secret needs to be provisioned: stable whenever JWT key material is
    configured, and ephemeral (matching JWT behaviour) in local dev.
    """
    digest = hashlib.sha256(
        get_key_pair().private_key_pem.encode()
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a credential for at-rest storage (e.g. SAPConfig.password)."""
    return _get_secret_cipher().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a credential previously produced by ``encrypt_secret``."""
    return _get_secret_cipher().decrypt(ciphertext.encode()).decode()
