"""LLM-judge pairwise — Stage 2 prompt template ranking.

3..5 wording variant 간 round-robin pairwise 비교. 각 비교는
`judge(variant_a_text, variant_b_text, region_id) -> float in [0, 1]` 가
수행한다 (= P(a 가 b 보다 낫다)). 결과 매트릭스는 Bradley-Terry MLE 로
선호도 점수(per variant) 로 환산.

해커톤 환경에서는 Gemini 호출이 비용/시간 제약을 가지므로 default_judge
는 deterministic stub (variant 라벨에서 숫자 suffix 가 큰 쪽이 약간 우세).
실제 운영 환경에서는 caller 가 judge 콜백을 주입한다.
"""
from __future__ import annotations

import logging
import math
from typing import Awaitable, Callable

log = logging.getLogger(__name__)

# Default 5 wording variants — issue framing tone / persona instruction /
# 비밀투표 prompt 미세 조정. 실제 wording 은 paper-writer / sim-engineer 와
# 협의 후 채워질 슬롯이며, 본 모듈은 인터페이스/scaffold 만 제공한다.
DEFAULT_VARIANTS: dict[str, str] = {
    "v1_baseline": (
        "당신은 한국의 평범한 유권자입니다. 다음 후보 중 한 명에게 투표하세요. "
        "비밀투표 원칙에 따라 솔직하게 선택해 주세요."
    ),
    "v2_neutral_framing": (
        "당신의 정치적 성향과 관계없이, 제시된 정보만을 바탕으로 후보를 평가하고 "
        "한 명에게 투표하세요. 답변은 후보 ID 만 JSON 으로 반환합니다."
    ),
    "v3_issue_first": (
        "다음 지역 이슈가 가장 중요하다고 가정하고, 후보들의 입장을 고려해 한 표를 "
        "행사하세요. 결정 근거를 1문장 안에 요약하고 후보 ID 를 JSON 으로 반환합니다."
    ),
    "v4_persona_grounded": (
        "당신의 페르소나(연령/직업/지역) 에 가장 잘 맞는 후보를 선택하세요. "
        "비밀투표 형식의 JSON 으로만 응답합니다."
    ),
    "v5_secret_strict": (
        "이는 비밀투표입니다. 어느 누구에게도 선택을 공개하지 마세요. JSON 한 줄로 "
        "후보 ID 만 반환하고 다른 텍스트는 절대 포함하지 마세요."
    ),
}


JudgeFn = Callable[[str, str, str], Awaitable[float]]


async def default_judge(variant_a: str, variant_b: str, region_id: str) -> float:
    """Deterministic stub — Gemini 호출 없이 회귀 테스트 가능.

    variant 라벨의 hash 차이로 [0.4, 0.6] 범위의 P(a beats b) 를 만든다.
    """
    h = (hash((variant_a, variant_b, region_id)) % 1000) / 1000.0
    return 0.4 + 0.2 * h


async def bradley_terry_pairwise(
    variants: list[str],
    judge: JudgeFn,
    *,
    region_id: str,
    n_iter: int = 50,
    tol: float = 1e-6,
) -> dict[str, float]:
    """Pairwise win-rate 매트릭스 → Bradley-Terry MLE.

    P(a beats b) = exp(s_a) / (exp(s_a) + exp(s_b)).
    iterative MLE — Hunter (2004) MM algorithm 의 단순 형태.
    출력은 합계=1 로 정규화한 선호도 점수.
    """
    n = len(variants)
    if n < 2:
        return {variants[0]: 1.0} if variants else {}

    # 1) wins matrix
    wins = [[0.0] * n for _ in range(n)]
    for i, a in enumerate(variants):
        for j, b in enumerate(variants):
            if i == j:
                continue
            text_a = DEFAULT_VARIANTS.get(a, a)
            text_b = DEFAULT_VARIANTS.get(b, b)
            p = await judge(text_a, text_b, region_id)
            p = max(0.0, min(1.0, float(p)))
            wins[i][j] = p

    # 2) Hunter MM iterative MLE
    p = [1.0] * n
    for _ in range(n_iter):
        p_new = [1.0] * n
        for i in range(n):
            num = sum(wins[i][j] for j in range(n) if j != i)
            den = sum(
                (wins[i][j] + wins[j][i]) / (p[i] + p[j])
                for j in range(n) if j != i
            )
            p_new[i] = num / den if den > 0 else p[i]
        # 정규화 (분모 안정성)
        s = sum(p_new) or 1.0
        p_new = [v / s for v in p_new]
        delta = max(abs(a - b) for a, b in zip(p, p_new))
        p = p_new
        if delta < tol:
            break

    return {v: float(p[i]) for i, v in enumerate(variants)}


__all__ = [
    "DEFAULT_VARIANTS",
    "JudgeFn",
    "default_judge",
    "bradley_terry_pairwise",
]
