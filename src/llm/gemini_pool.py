"""Backward-compat shim — ``GeminiPool``은 이제 ``LLMPool`` (LiteLLM 기반)의 별칭.

기존 코드(`from src.llm.gemini_pool import GeminiPool`)는 변경 없이 동작.
새 코드는 ``src.llm.llm_pool.LLMPool``를 직접 사용 권장.
"""
from __future__ import annotations

from src.llm.llm_pool import (
    LLMPool,
    LLMPoolError,
    NetworkError,
    RateLimitError,
)

# Aliases ---------------------------------------------------------------
GeminiPool = LLMPool
GeminiPoolError = LLMPoolError

__all__ = [
    "GeminiPool",
    "GeminiPoolError",
    "LLMPool",
    "LLMPoolError",
    "NetworkError",
    "RateLimitError",
]


if __name__ == "__main__":
    pool = GeminiPool()
    out = pool.chat(
        [
            {
                "role": "system",
                "content": "Reply with strict JSON only: {\"ok\": true}.",
            },
            {"role": "user", "content": "ping"},
        ],
        max_output_tokens=64,
    )
    print("[smoke] response:", out[:200])
    print("[smoke] stats:", pool.stats())
