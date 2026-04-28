"""Admin auth — argon2-cffi password hash + JWT (HS256/RS256).

설계:
  - bootstrap_admin_user(settings): env `ADMIN_BOOTSTRAP_PASSWORD` 가 있으면
    admin user 1회 시드. 이미 있으면 멱등 no-op.
  - verify_password / hash_password: argon2-cffi.
  - issue_token / verify_token: PyJWT. 알고리즘은 settings 에서 결정 — 키쌍이
    있으면 RS256, 없으면 HS256 (개발 기본).
  - 사용자 저장은 in-process dict (해커톤). 프로덕션은 Postgres `admin_user`
    테이블로 마이그레이트 — db-postgres stream 합류 지점.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

import jwt  # PyJWT
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from ..settings import Settings

logger = logging.getLogger("backend.auth")

# Token TTL — 8h (task #87 spec).
DEFAULT_TTL_SECONDS = 8 * 3600

_HASHER = PasswordHasher()


@dataclass
class AdminUser:
    username: str
    password_hash: str
    role: str = "admin"
    created_at: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat())


# In-process store (해커톤 단계). DB 마이그레이트는 후속.
_USERS: dict[str, AdminUser] = {}
_USERS_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(plain: str) -> str:
    return _HASHER.hash(plain)


def verify_password(stored_hash: str, plain: str) -> bool:
    try:
        return _HASHER.verify(stored_hash, plain)
    except (VerifyMismatchError, VerificationError):
        return False


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------
def get_user(username: str) -> Optional[AdminUser]:
    with _USERS_LOCK:
        return _USERS.get(username)


def upsert_user(username: str, password_hash: str, role: str = "admin") -> AdminUser:
    with _USERS_LOCK:
        u = AdminUser(username=username, password_hash=password_hash, role=role)
        _USERS[username] = u
        return u


def reset_users_for_test() -> None:
    with _USERS_LOCK:
        _USERS.clear()


def bootstrap_admin_user(settings: Settings) -> Optional[AdminUser]:
    """Env `ADMIN_BOOTSTRAP_PASSWORD` 가 있으면 admin 1회 시드.

    이미 admin 이 있으면 password 갱신 없이 idempotent. 비밀번호 회전이 필요하면
    환경변수 갱신 후 process restart.
    """
    pw = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD") or os.environ.get(
        "POLITIKAST_ADMIN_BOOTSTRAP_PASSWORD"
    )
    if not pw:
        return None
    username = os.environ.get("ADMIN_BOOTSTRAP_USER", "admin")
    existing = get_user(username)
    if existing is not None:
        logger.info("admin bootstrap: user %s already exists, skipping", username)
        return existing
    logger.info("admin bootstrap: creating user %s", username)
    return upsert_user(username, hash_password(pw))


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def _signing_material(settings: Settings) -> tuple[str, str]:
    """Return (secret_or_key, alg). RS256 시 key 는 PEM private key 문자열."""
    alg = (settings.admin_jwt_alg or "HS256").upper()
    if alg.startswith("RS"):
        priv_pem = os.environ.get("ADMIN_JWT_PRIVATE_KEY_PEM")
        if not priv_pem:
            # RS256 요청됐지만 키 미설정 → 안전하게 HS256 폴백 + 경고.
            logger.warning("RS256 requested but ADMIN_JWT_PRIVATE_KEY_PEM not set — falling back to HS256")
            return settings.admin_jwt_secret, "HS256"
        return priv_pem, alg
    return settings.admin_jwt_secret, alg


def _verifying_material(settings: Settings) -> tuple[str, str]:
    alg = (settings.admin_jwt_alg or "HS256").upper()
    if alg.startswith("RS"):
        pub_pem = os.environ.get("ADMIN_JWT_PUBLIC_KEY_PEM")
        if pub_pem:
            return pub_pem, alg
        logger.warning("RS256 verify requested but ADMIN_JWT_PUBLIC_KEY_PEM not set — falling back to HS256")
        return settings.admin_jwt_secret, "HS256"
    return settings.admin_jwt_secret, alg


def issue_token(
    username: str,
    settings: Settings,
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    extra_claims: Optional[dict[str, Any]] = None,
) -> tuple[str, int]:
    """Issue access token. Returns (token, expires_in_seconds)."""
    now = dt.datetime.now(dt.timezone.utc)
    exp = now + dt.timedelta(seconds=ttl_seconds)
    payload: dict[str, Any] = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "role": "admin",
    }
    if extra_claims:
        payload.update(extra_claims)
    key, alg = _signing_material(settings)
    token = jwt.encode(payload, key, algorithm=alg)
    return token, ttl_seconds


def verify_token(token: str, settings: Settings) -> dict[str, Any]:
    key, alg = _verifying_material(settings)
    return jwt.decode(token, key, algorithms=[alg])


def authenticate(username: str, password: str) -> Optional[AdminUser]:
    user = get_user(username)
    if user is None:
        return None
    if not verify_password(user.password_hash, password):
        return None
    return user


__all__ = [
    "AdminUser",
    "DEFAULT_TTL_SECONDS",
    "authenticate",
    "bootstrap_admin_user",
    "get_user",
    "hash_password",
    "issue_token",
    "reset_users_for_test",
    "upsert_user",
    "verify_password",
    "verify_token",
]
