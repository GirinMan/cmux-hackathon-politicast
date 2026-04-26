"""Offline smoke test for the sim core — no Gemini calls.

Stubs the LLM backend with a deterministic-random JSON response so we can
verify ElectionEnv loop, poll consensus, secret-ballot tally, and result
schema serialization without burning RPM. Run:

    docker compose run --rm app python -m src.sim.smoke
    # or just:
    python -m src.sim.smoke
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import sys
from pathlib import Path

from .election_env import ElectionEnv
from .run_scenario import _append_index
from .voter_agent import VoterAgent

logger = logging.getLogger(__name__)


def _mock_backend_factory(seed: int = 7):
    rng = random.Random(seed)

    async def _backend(system_prompt: str, user_prompt: str, extras):
        # Sample candidate ids out of the user prompt's "[후보]" block.
        # Skip withdrawn candidates (mimic the real LLM honoring the system rule).
        ids: list[str] = []
        in_block = False
        for line in user_prompt.splitlines():
            if line.startswith("[후보]"):
                in_block = True
                continue
            if in_block:
                if not line.strip().startswith("- "):
                    break
                tail = line.strip()[2:]
                if "[출마 포기]" in tail:
                    continue
                ids.append(tail.split("|")[0].strip())
        if not ids:
            ids = ["cand_A", "cand_B"]
        # Bias slightly toward first candidate to make winner deterministic-ish
        weights = [3.0] + [1.0] * (len(ids) - 1)
        choice = rng.choices(ids, weights=weights, k=1)[0]
        if rng.random() < 0.05:
            choice = None  # 5% abstain
        await asyncio.sleep(0)  # yield to event loop
        return json.dumps(
            {
                "vote": choice,
                "turnout": choice is not None,
                "confidence": round(0.5 + rng.random() * 0.4, 2),
                "reason": "정책 우선순위 일치",
                "key_factors": ["경제", "복지"],
            },
            ensure_ascii=False,
        )

    return _backend


async def _run() -> int:
    candidates = [
        {"id": "cand_A", "name": "후보 A", "party": "더불어민주당", "withdrawn": False},
        {"id": "cand_B", "name": "후보 B", "party": "국민의힘", "withdrawn": False},
        {"id": "cand_C", "name": "후보 C", "party": "무소속", "withdrawn": True},
    ]
    backend = _mock_backend_factory(seed=11)

    voters = [
        VoterAgent(
            persona={
                "uuid": f"smoke-{i:03d}",
                "age": 25 + (i * 5) % 50,
                "sex": "여" if i % 2 else "남",
                "education_level": "대졸",
                "occupation": "사무직",
                "marital_status": "기혼" if i % 3 else "미혼",
                "province": "서울특별시",
                "district": "강남구" if i % 2 else "노원구",
            },
            persona_text={
                "persona": "30대 직장인. 출퇴근 교통과 주거비에 예민.",
                "professional_persona": "사무직 7년차.",
                "family_persona": "맞벌이 가구.",
                "cultural_background": "서울 거주 10년.",
            },
            backend=backend,
        )
        for i in range(20)
    ]

    env = ElectionEnv(
        region_id="seoul_mayor",
        contest_id="seoul_mayor_2026",
        candidates=candidates,
        timesteps=2,
        kg_retriever=None,
        scenario_meta={
            "scenario_id": "seoul_mayor__smoke",
            "label": "서울시장 (smoke)",
            "gov_approval": 0.35,
            "seed_events": [
                {
                    "timestep": 0,
                    "type": "policy_announcement",
                    "target": "cand_A",
                    "polarity": 0.4,
                    "summary": "재개발 가속화 공약 발표",
                }
            ],
        },
        concurrency=8,
        n_interviews=3,
    )

    result = await env.run(voters)

    # Verify required fields against result_schema.json
    required_top = {
        "scenario_id", "region_id", "contest_id", "timestep_count",
        "persona_n", "candidates", "poll_trajectory", "final_outcome",
        "demographics_breakdown", "virtual_interviews", "kg_events_used",
    }
    missing = required_top - set(result.keys())
    assert not missing, f"missing fields: {missing}"
    assert len(result["poll_trajectory"]) == 2
    assert result["final_outcome"]["winner"] in {"cand_A", "cand_B"}
    assert all(0.0 <= v <= 1.0 for v in result["final_outcome"]["vote_share_by_candidate"].values())
    assert len(result["virtual_interviews"]) == 3

    out_dir = Path(__file__).resolve().parents[2] / "_workspace" / "snapshots" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "seoul_mayor__smoke.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    _append_index(out_path, result)
    print(f"[smoke] OK — winner={result['final_outcome']['winner']} | wrote {out_path}")
    print(f"[smoke] poll_trajectory shares t0 = {result['poll_trajectory'][0]['support_by_candidate']}")
    print(f"[smoke] poll_trajectory shares t1 = {result['poll_trajectory'][1]['support_by_candidate']}")
    print(f"[smoke] turnout = {result['final_outcome']['turnout']:.2f}")
    print(f"[smoke] voter_stats = {result['meta']['voter_stats']}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(levelname)s %(name)s: %(message)s")
    sys.exit(asyncio.run(_run()))
