"""Anonymous user service — cookie politikast_uid 기반."""
from __future__ import annotations

import random
import uuid
from typing import Optional

from . import _community_store as cs

# 한국어 닉네임 풀 (#91 db-postgres 가 더 큰 풀 + DB 시드 예정).
# 기본은 process-local 작은 풀 — DB 풀 도착 시 swap.
_DEFAULT_ADJECTIVES = (
    "성실한", "조용한", "활기찬", "신중한", "용감한", "현명한",
    "다정한", "고요한", "단단한", "맑은", "푸른", "공정한",
)
_DEFAULT_NOUNS = (
    "유권자", "시민", "주민", "동료", "이웃", "독자",
    "참여자", "관찰자", "분석가", "방문자", "토론자", "기록자",
)


def generate_default_nickname(seed: Optional[int] = None) -> str:
    rng = random.Random(seed)
    return f"{rng.choice(_DEFAULT_ADJECTIVES)} {rng.choice(_DEFAULT_NOUNS)} #{rng.randint(100, 999)}"


def get_or_create_user(
    cookie_user_id: Optional[str], display_name: Optional[str] = None
) -> cs.AnonUser:
    """cookie 의 uid 로 멱등 fetch-or-create."""
    store = cs.get_store()
    if cookie_user_id:
        existing = store.get_user(cookie_user_id)
        if existing is not None:
            return existing
    new_id = cookie_user_id or f"u_{uuid.uuid4().hex[:12]}"
    name = display_name or generate_default_nickname()
    return store.upsert_user(new_id, name)


def get_user(user_id: str) -> Optional[cs.AnonUser]:
    return cs.get_store().get_user(user_id)


def update_nickname(user_id: str, new_name: str) -> cs.AnonUser:
    new_name = (new_name or "").strip()
    if not (1 <= len(new_name) <= 20):
        raise ValueError("display_name length must be 1..20")
    return cs.get_store().update_user_nickname(user_id, new_name)


def ban_user(user_id: str, reason: Optional[str] = None) -> cs.AnonUser:
    return cs.get_store().ban_user(user_id, reason)


__all__ = [
    "generate_default_nickname",
    "get_or_create_user",
    "get_user",
    "update_nickname",
    "ban_user",
]
