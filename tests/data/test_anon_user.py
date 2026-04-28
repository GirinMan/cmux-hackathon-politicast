"""한국어 닉네임 generator (#91) — pool 큐레이션 + 결정성 + 안전성."""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pytest

from src.data.anon_user import (
    DEFAULT_POOL_PATH,
    NicknamePool,
    generate_anon_token,
    generate_nickname,
    get_default_pool,
    load_pool,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 풀 자체 검증 — task spec 의 50/80 + 정치 중립 + NSFW-free
# ---------------------------------------------------------------------------
def test_pool_has_required_counts() -> None:
    data = json.loads(DEFAULT_POOL_PATH.read_text())
    assert len(data["adjectives"]) >= 50, (
        f"adjectives={len(data['adjectives'])} < 50 (task spec 위반)"
    )
    assert len(data["nouns"]) >= 80, (
        f"nouns={len(data['nouns'])} < 80 (task spec 위반)"
    )


# 정치 중립성 — 후보/정당/이념 키워드 미포함.
_POLITICAL_KEYWORDS = (
    "보수", "진보", "좌파", "우파", "좌익", "우익",
    "민주", "국민의힘", "정의당", "조국혁신",
    "대통령", "장관", "의원",
    "윤석열", "이재명", "한동훈", "오세훈", "추경호",
)


def test_pool_is_politically_neutral() -> None:
    data = json.loads(DEFAULT_POOL_PATH.read_text())
    pool_strs = data["adjectives"] + data["nouns"]
    leaks: list[str] = []
    for w in pool_strs:
        for kw in _POLITICAL_KEYWORDS:
            if kw in w:
                leaks.append(f"{w!r} contains political kw {kw!r}")
    assert not leaks, "\n".join(leaks)


# 간단한 NSFW 휴리스틱 — 명백한 한국어/영어 비속어 토큰 spot-check.
_NSFW_KEYWORDS = (
    "병신", "씨발", "좆", "보지", "자지", "fuck", "shit", "bitch",
)


def test_pool_is_nsfw_free() -> None:
    data = json.loads(DEFAULT_POOL_PATH.read_text())
    for w in data["adjectives"] + data["nouns"]:
        for kw in _NSFW_KEYWORDS:
            assert kw not in w.lower(), f"NSFW token leaked into pool: {w!r}"


# ---------------------------------------------------------------------------
# Generator 동작
# ---------------------------------------------------------------------------
def test_load_pool_default_path() -> None:
    pool = load_pool()
    assert isinstance(pool, NicknamePool)
    assert len(pool.adjectives) >= 50
    assert len(pool.nouns) >= 80
    assert pool.combination_space() >= 50 * 80 * 10000


def test_random_nickname_format() -> None:
    pool = load_pool()
    pattern = re.compile(r"^[가-힯]+\d{4}$")
    for _ in range(100):
        nick = pool.random_nickname()
        # 형용사+명사+4자리 — 한글 + 숫자 4개
        assert pattern.match(nick), f"형식 위반: {nick!r}"


def test_random_nickname_deterministic_with_seeded_rng() -> None:
    pool = load_pool()
    rng_a = random.Random(12345)
    rng_b = random.Random(12345)
    seq_a = [pool.random_nickname(rng_a) for _ in range(10)]
    seq_b = [pool.random_nickname(rng_b) for _ in range(10)]
    assert seq_a == seq_b


def test_random_nickname_diverse() -> None:
    """1000 회 호출 시 unique 비율 ≥ 99% — 충돌 거의 없음."""
    pool = load_pool()
    nicks = {pool.random_nickname() for _ in range(1000)}
    assert len(nicks) >= 990, f"중복 과다: unique={len(nicks)}"


def test_generate_nickname_module_helper() -> None:
    nick = generate_nickname()
    assert nick and isinstance(nick, str)


def test_generate_anon_token_is_safe() -> None:
    a = generate_anon_token()
    b = generate_anon_token()
    assert a != b
    assert len(a) >= 32, f"token too short: {a!r}"
    # URL-safe charset
    assert re.match(r"^[A-Za-z0-9_-]+$", a), f"non URL-safe: {a!r}"


def test_get_default_pool_singleton() -> None:
    p1 = get_default_pool()
    p2 = get_default_pool()
    assert p1 is p2


def test_empty_pool_raises() -> None:
    with pytest.raises(ValueError):
        NicknamePool(adjectives=(), nouns=("토끼",))
    with pytest.raises(ValueError):
        NicknamePool(adjectives=("따뜻한",), nouns=())


def test_digit_width_zero_emits_no_digits() -> None:
    pool = NicknamePool(
        adjectives=("따뜻한",), nouns=("토끼",), digit_width=0
    )
    assert pool.random_nickname() == "따뜻한토끼"
