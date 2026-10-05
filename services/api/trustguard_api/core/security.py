# services/api/trustguard_api/core/security.py
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt

from trustguard_api.core.config import settings

def hash_password(password: str) -> str:
    """
    Secure salted PBKDF2-HMAC-SHA256 password hasher.
    Standard, cross-platform, zero C-compiler dependency issues.
    """
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"pbkdf2_sha256${salt}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split('$')
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
            return False
        salt = parts[1]
        expected_key = parts[2]
        key = hashlib.pbkdf2_hmac(
            'sha256',
            plain_password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(key.hex(), expected_key)
    except Exception:
        return False

def hash_token(raw_token: str) -> str:
    """
    Hashes refresh token for secure database storage.
    Raw refresh tokens are never persisted in the database.
    """
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None

def generate_refresh_token() -> str:
    """Generates an opaque, cryptographically secure 64-character URL-safe string."""
    return secrets.token_urlsafe(48)
