"""익명 사용자 닉네임 generator (#91).

설계 결정
---------
- 한국어 형용사 50 + 명사 80 + 4자리 숫자 → 약 40M 조합 공간. 충돌은 거의 없음.
- 정치 중립 + NSFW-free 큐레이션 (`_workspace/data/registries/nickname_pool.json`).
- 본 모듈은 stdlib `random` (또는 명시 ``random.Random`` 인스턴스) 만 사용 — DB
  의존성 없음. 충돌 처리는 backend `anon_user_service` 가 (DB UNIQUE 제약 +
  retry-once) 책임.

Public API
----------
- ``load_pool(path: Path | None = None) -> NicknamePool``
- ``NicknamePool.random_nickname(rng: Random | None = None) -> str``
- ``generate_nickname()``  — 모듈 레벨 편의 함수, default pool 사용.
"""
from __future__ import annotations

import json
import random as _random
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POOL_PATH = (
    REPO_ROOT / "_workspace" / "data" / "registries" / "nickname_pool.json"
)


@dataclass(frozen=True)
class NicknamePool:
    """nickname_pool.json 의 in-memory mirror."""

    adjectives: tuple[str, ...]
    nouns: tuple[str, ...]
    digit_width: int = 4

    def __post_init__(self) -> None:
        if not self.adjectives:
            raise ValueError("NicknamePool: adjectives 비어있음")
        if not self.nouns:
            raise ValueError("NicknamePool: nouns 비어있음")
        if self.digit_width < 0 or self.digit_width > 10:
            raise ValueError(
                f"NicknamePool: digit_width={self.digit_width} 비정상"
            )

    # ------------------------------------------------------------------
    def random_nickname(self, rng: Optional[_random.Random] = None) -> str:
        """``{형용사}{명사}{4자리숫자}``. rng 미지정 시 secrets-seeded.

        실 운영에서는 매 호출 새 secrets 시드를 쓰는 것이 충돌 방지에 가장
        안전 — 공용 ``_random`` 모듈 상태를 오염시키지 않는다.
        """
        r = rng or _random.Random(secrets.randbits(64))
        adj = r.choice(self.adjectives)
        noun = r.choice(self.nouns)
        if self.digit_width == 0:
            return f"{adj}{noun}"
        max_n = 10 ** self.digit_width
        num = r.randrange(0, max_n)
        return f"{adj}{noun}{num:0{self.digit_width}d}"

    def combination_space(self) -> int:
        """이론적 조합 수 — 충돌 확률 추정용."""
        return len(self.adjectives) * len(self.nouns) * (10 ** self.digit_width)


def load_pool(path: Optional[Path] = None) -> NicknamePool:
    p = path or DEFAULT_POOL_PATH
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    adjectives = tuple(s.strip() for s in data.get("adjectives", []) if s and s.strip())
    nouns = tuple(s.strip() for s in data.get("nouns", []) if s and s.strip())
    return NicknamePool(adjectives=adjectives, nouns=nouns)


# Process-wide cached pool — 첫 호출 시 lazy load.
_DEFAULT_POOL: Optional[NicknamePool] = None


def get_default_pool() -> NicknamePool:
    global _DEFAULT_POOL
    if _DEFAULT_POOL is None:
        _DEFAULT_POOL = load_pool()
    return _DEFAULT_POOL


def generate_nickname(rng: Optional[_random.Random] = None) -> str:
    """편의 함수 — default pool 로 단일 nickname 생성."""
    return get_default_pool().random_nickname(rng=rng)


def generate_anon_token() -> str:
    """browser cookie 용 익명 토큰. 256-bit URL-safe."""
    return secrets.token_urlsafe(32)


__all__ = [
    "DEFAULT_POOL_PATH",
    "NicknamePool",
    "generate_anon_token",
    "generate_nickname",
    "get_default_pool",
    "load_pool",
]
