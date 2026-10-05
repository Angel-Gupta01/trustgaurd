# services/api/tests/test_security.py
from datetime import timedelta
from trustguard_api.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    hash_token,
    generate_refresh_token,
)

def test_password_hashing():
    raw_pass = "SuperSecurePassword!2026"
    hashed = hash_password(raw_pass)
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_lifecycle():
    user_data = {"sub": "123e4567-e89b-12d3-a456-426614174000", "email": "test@trustguard.ai", "role": "USER"}
    token = create_access_token(user_data, expires_delta=timedelta(minutes=10))
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == user_data["sub"]
    assert decoded["email"] == user_data["email"]
    assert decoded["role"] == user_data["role"]

def test_refresh_token_hashing():
    raw_token = generate_refresh_token()
    token_hash = hash_token(raw_token)
    assert len(token_hash) == 64
    assert hash_token(raw_token) == token_hash
