"""Temporal Information Firewall — validator + unit tests.

논문 표기: $\\mathcal{D}_{\\le t}$ — voter agent 는 시점 $t$ 까지의 이벤트만
관측. 어떤 retrieval/query 함수도 ``ts > cutoff`` 이벤트를 노출하면 invariant 위반.

이 모듈은:
1. ``assert_no_future_leakage(retriever, ...)`` — 결과를 검사하여 위반 시 raise.
2. ``run_self_tests()`` — 합성 시나리오로 retriever round-trip 검증.
   ``python -m src.kg.firewall`` 로 실행.

sim-engineer 시그널: ``run_self_tests()`` 가 0 반환 시 retriever를 import 해서
voter prompt 에 주입해도 됨.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from typing import Any

from src.kg.builder import build_kg_from_dicts
from src.kg.retriever import KGRetriever, RetrievalResult

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public assertion
# ---------------------------------------------------------------------------
class FirewallViolation(AssertionError):
    """Retrieval 결과에 cutoff 이후 이벤트가 포함됨 — invariant 위반."""


def assert_no_future_leakage(
    retriever: KGRetriever,
    persona: dict[str, Any],
    t: int,
    region_id: str,
    k: int = 5,
) -> RetrievalResult:
    """Retrieve 후, 모든 events_used 의 ts가 cutoff 이하인지 검증."""
    result = retriever.subgraph_at(persona, t, region_id, k=k)
    cutoff = retriever.cutoff_for(region_id, t)
    if cutoff is None:
        return result

    # events_used 는 timestep 만 포함 — 원본 ts 검증을 위해 G 에서 lookup
    for ev in result.events_used:
        eid = ev["event_id"]
        # 노드 id 역추적: type:event_id
        node_id = f"{ev['type']}:{eid}"
        attrs = retriever.G.nodes.get(node_id)
        if attrs is None:
            continue
        ts = attrs.get("ts")
        if isinstance(ts, datetime) and ts > cutoff:
            raise FirewallViolation(
                f"[firewall] event {eid} ts={ts} > cutoff={cutoff} "
                f"(region={region_id}, t={t})"
            )

    # 직렬화된 텍스트에도 미래 날짜가 들어가지 않았는지 보조 검사
    if cutoff and result.context_text:
        # 매우 보수적인 검사: cutoff 이후의 모든 이벤트 노드의 title 이
        # context_text 에 포함되면 안 됨.
        for n, attrs in retriever.G.nodes(data=True):
            if attrs.get("type") not in (
                "MediaEvent",
                "ScandalEvent",
                "Investigation",
                "Verdict",
                "PressConference",
                "PollPublication",
            ):
                continue
            ts = attrs.get("ts")
            title = attrs.get("title") or ""
            if (
                isinstance(ts, datetime)
                and ts > cutoff
                and title
                and title in result.context_text
            ):
                raise FirewallViolation(
                    f"[firewall] future event title leaked into context: "
                    f"node={n}, ts={ts}, cutoff={cutoff}"
                )

    return result


# ---------------------------------------------------------------------------
# Synthetic scenario for self-tests
# ---------------------------------------------------------------------------
def _make_synthetic_scenario() -> dict[str, Any]:
    """3 timestep, 5 events (각각 다른 시점) — firewall round-trip 검증."""
    base = datetime(2026, 4, 1)
    return {
        "scenario_id": "test_seoul_mayor",
        "region_id": "seoul_mayor",
        "election": {
            "election_id": "ROK_local_2026",
            "name": "제9회 전국동시지방선거",
            "date": "2026-06-03T00:00:00",
            "type": "local",
        },
        "contest": {
            "contest_id": "seoul_mayor_2026",
            "position_type": "metropolitan_mayor",
        },
        "district": {"province": "서울특별시", "district": None, "population": 9700000},
        "parties": [
            {"party_id": "p_dem", "name": "더불어민주당", "ideology": -0.4},
            {"party_id": "p_ppp", "name": "국민의힘", "ideology": 0.5},
        ],
        "candidates": [
            {"candidate_id": "c_kim", "name": "김민주", "party": "p_dem"},
            {"candidate_id": "c_lee", "name": "이보수", "party": "p_ppp"},
        ],
        "issues": [
            {"issue_id": "i_housing", "name": "부동산", "type": "부동산"},
            {"issue_id": "i_edu", "name": "입시정책", "type": "교육"},
        ],
        "frames": [
            {"frame_id": "f_judgement", "label": "정권심판"},
            {"frame_id": "f_stability", "label": "안정호소"},
        ],
        "events": [
            {
                "event_id": "ev_01",
                "type": "MediaEvent",
                "ts": (base + timedelta(days=1)).isoformat(),
                "source": "조선일보",
                "title": "서울시장 후보 1차 토론회 개최",
                "sentiment": 0.0,
                "about": ["c_kim", "c_lee"],
                "mentions": ["i_housing"],
                "frame_id": "f_stability",
            },
            {
                "event_id": "ev_02",
                "type": "ScandalEvent",
                "ts": (base + timedelta(days=15)).isoformat(),
                "source": "한겨레",
                "title": "이보수 후보 자녀 입시 의혹 제기",
                "sentiment": -0.5,
                "severity": 0.7,
                "credibility": 0.5,
                "target_candidate_id": "c_lee",
                "about": ["c_lee"],
                "mentions": ["i_edu"],
                "frame_id": "f_judgement",
            },
            {
                "event_id": "ev_03",
                "type": "PressConference",
                "ts": (base + timedelta(days=30)).isoformat(),
                "source": "민주당",
                "title": "김민주 부동산 공약 발표",
                "sentiment": 0.3,
                "about": ["c_kim"],
                "mentions": ["i_housing"],
                "frame_id": "f_judgement",
                "speaker": "김민주",
                "party_id": "p_dem",
            },
            {
                "event_id": "ev_04",
                "type": "Verdict",
                "ts": (base + timedelta(days=45)).isoformat(),
                "source": "서울중앙지법",
                "title": "이보수 후보 자녀 입시 의혹 1심 무죄",
                "sentiment": 0.2,
                "outcome": "acquittal",
                "target_candidate_id": "c_lee",
                "about": ["c_lee"],
            },
            {
                "event_id": "ev_05",
                "type": "MediaEvent",
                "ts": (base + timedelta(days=60)).isoformat(),
                "source": "JTBC",
                "title": "선거 D-3 종합 분석",
                "sentiment": 0.0,
                "about": ["c_kim", "c_lee"],
            },
        ],
        "polls": [
            {
                "poll_id": 1,
                "ts": (base + timedelta(days=20)).isoformat(),
                "sample_size": 1000,
                "leader_candidate": "c_kim",
                "leader_share": 0.42,
            },
            {
                "poll_id": 2,
                "ts": (base + timedelta(days=50)).isoformat(),
                "sample_size": 1200,
                "leader_candidate": "c_kim",
                "leader_share": 0.46,
            },
        ],
        "simulation": {
            "t_start": base.isoformat(),
            "t_end": (base + timedelta(days=63)).isoformat(),
            "timesteps": 4,
        },
    }


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------
def _test_firewall_blocks_future(retriever: KGRetriever) -> None:
    """timestep 0 (≈ t_start) 에는 거의 모든 이벤트가 차단되어야 함."""
    persona = {
        "district": "서울특별시",
        "age": 40,
        "occupation": "사무직",
        "education_level": "대졸",
        "professional_persona": "주택 구매를 고민하는 30대 직장인",
    }
    result = assert_no_future_leakage(retriever, persona, t=0, region_id="seoul_mayor")
    # t=0 → cutoff = t_start. base + 0d. ev_01 (base+1d) 는 차단되어야 함.
    assert all(
        "토론회" not in line for line in result.context_text.splitlines()
    ), f"[firewall test] t=0 에서 ev_01 가 노출됨: {result.context_text!r}"


def _test_firewall_progressive_disclosure(retriever: KGRetriever) -> None:
    """t 가 커질수록 노출 이벤트 수가 단조 증가."""
    persona = {
        "district": "서울특별시",
        "age": 40,
        "occupation": "사무직",
        "professional_persona": "주택 구매 관심",
    }
    counts = []
    for t in range(4):
        r = assert_no_future_leakage(retriever, persona, t=t, region_id="seoul_mayor", k=20)
        counts.append(len(r.events_used))
    assert counts == sorted(counts), (
        f"[firewall test] visible event counts must be monotone non-decreasing, "
        f"got {counts}"
    )


def _test_firewall_t_end_includes_all(retriever: KGRetriever) -> None:
    """t = T-1 (선거일) 에는 모든 이벤트가 후보군에 포함되어야 함 (cutoff=t_end)."""
    persona = {"district": "서울특별시", "age": 40, "occupation": "사무직"}
    result = assert_no_future_leakage(
        retriever, persona, t=3, region_id="seoul_mayor", k=20
    )
    seen = {e["event_id"] for e in result.events_used}
    expected = {"ev_01", "ev_02", "ev_03", "ev_04", "ev_05"}
    missing = expected - seen
    assert not missing, f"[firewall test] t=T-1 에서 누락: {missing}"


def _test_no_unknown_region(retriever: KGRetriever) -> None:
    persona = {"district": "?", "age": 30}
    result = retriever.subgraph_at(persona, t=2, region_id="unknown_region")
    assert result.events_used == [], "[firewall test] unknown region 은 빈 결과여야 함"


def _test_poll_firewall(retriever: KGRetriever) -> None:
    """t=0 (cutoff=t_start) 에는 어떤 poll 도 노출되어선 안 됨."""
    persona = {"district": "서울특별시", "age": 30}
    result = assert_no_future_leakage(
        retriever, persona, t=0, region_id="seoul_mayor", k=20
    )
    poll_ids = [e for e in result.events_used if e["type"] == "PollPublication"]
    assert poll_ids == [], f"[firewall test] t=0 에서 poll 누설: {poll_ids}"


def _test_persona_relevance_boost(retriever: KGRetriever) -> None:
    """주택 관심 페르소나는 부동산 이벤트가 top-k에 포함되어야 함 (cutoff 충분히 큼)."""
    persona = {
        "district": "서울특별시",
        "age": 38,
        "occupation": "직장인",
        "professional_persona": "전세금 인상으로 주택 구매를 고민하는 30대 직장인",
    }
    result = retriever.subgraph_at(persona, t=3, region_id="seoul_mayor", k=3)
    titles = " | ".join(e["event_id"] for e in result.events_used)
    # ev_03 (부동산 공약) 또는 ev_01 (부동산 토론) 중 하나는 top-3 에 포함.
    assert (
        "ev_03" in titles or "ev_01" in titles
    ), f"[firewall test] 부동산 이벤트가 top-3 에 없음: {titles}"


def _test_real_scenarios_cutoff_2026_04_25() -> None:
    """team-lead regression: 2026-04-25 cutoff 에서 한동훈/추경호/이진숙 4-25
    이벤트는 visible, 4-25 이후 이벤트는 차단되는지 검증.

    실 ``_workspace/data/scenarios/*.json`` 를 로드. 시나리오 미박제 또는
    해당 region 없으면 silently skip (CI 친화).
    """
    from datetime import datetime
    from pathlib import Path
    from src.kg.builder import build_kg_from_scenarios, DEFAULT_SCENARIO_DIR

    if not Path(DEFAULT_SCENARIO_DIR).exists():
        print("[firewall] SKIP cutoff_2026_04_25 — scenario dir 없음")
        return

    G, index = build_kg_from_scenarios()
    if not G.number_of_nodes():
        print("[firewall] SKIP cutoff_2026_04_25 — KG empty")
        return

    retriever = KGRetriever(G, index)
    cutoff = datetime(2026, 4, 25, 23, 59, 59)

    # 1) 모든 region 의 모든 event 노드에 대해: ts > cutoff 인 노드는
    #    _events_visible_at(region, cutoff) 결과에 절대 없어야 함.
    for region_id in index.by_region.keys():
        visible = retriever._events_visible_at(region_id, cutoff)
        for n, attrs in visible:
            ts = attrs.get("ts")
            assert (
                isinstance(ts, datetime) and ts <= cutoff
            ), f"[firewall] region={region_id} node={n} ts={ts} > cutoff"

    def _find(visible, predicate):
        return [a for _, a in visible if predicate(a)]

    # 2) 한동훈 부산 만덕 전입 (2026-04-14): visible.
    if "busan_buk_gap" in index.by_region:
        visible = retriever._events_visible_at("busan_buk_gap", cutoff)
        han = _find(visible, lambda a: "한동훈" in (a.get("title") or "")
                                       and "전입" in (a.get("title") or ""))
        assert han, (
            f"[firewall] busan_buk_gap 한동훈 4-14 전입 이벤트 누락. "
            f"visible event_ids = {[a.get('event_id') for _, a in visible]}"
        )

    # 3) daegu_dalseo_gap 4-25 boundary 이벤트 (추경호 / 이진숙): visible.
    if "daegu_dalseo_gap" in index.by_region:
        visible = retriever._events_visible_at("daegu_dalseo_gap", cutoff)
        choo = _find(visible, lambda a: "추경호" in (a.get("title") or ""))
        lee = _find(visible, lambda a: "이진숙" in (a.get("title") or ""))
        assert choo, "[firewall] daegu_dalseo_gap 추경호 4-25 이벤트 누락"
        assert lee, "[firewall] daegu_dalseo_gap 이진숙 4-25 이벤트 누락"

    # 4) 미래 이벤트 차단: 4-26 이후 ts 인 이벤트가 KG 에 있다면 어떤 region 의
    #    _events_visible_at(cutoff) 에도 포함되어선 안 됨.
    future_node_ids: list[str] = []
    for n, attrs in G.nodes(data=True):
        if attrs.get("type") not in (
            "MediaEvent", "ScandalEvent", "Investigation",
            "Verdict", "PressConference", "PollPublication",
        ):
            continue
        ts = attrs.get("ts")
        if isinstance(ts, datetime) and ts > cutoff:
            future_node_ids.append(n)
    for region_id in index.by_region.keys():
        visible_ids = {n for n, _ in retriever._events_visible_at(region_id, cutoff)}
        leak = visible_ids & set(future_node_ids)
        assert not leak, (
            f"[firewall] region={region_id} 미래 이벤트 leak: {leak}"
        )


def run_self_tests() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    G, index = build_kg_from_dicts([_make_synthetic_scenario()])
    retriever = KGRetriever(G, index)

    tests = [
        _test_firewall_blocks_future,
        _test_firewall_progressive_disclosure,
        _test_firewall_t_end_includes_all,
        _test_no_unknown_region,
        _test_poll_firewall,
        _test_persona_relevance_boost,
    ]
    real_tests = [
        _test_real_scenarios_cutoff_2026_04_25,
    ]
    failed = 0
    for fn in tests:
        try:
            fn(retriever)
            print(f"[firewall] PASS  {fn.__name__}")
        except AssertionError as exc:
            print(f"[firewall] FAIL  {fn.__name__}: {exc}")
            failed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[firewall] ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
            failed += 1
    for fn in real_tests:
        try:
            fn()
            print(f"[firewall] PASS  {fn.__name__}")
        except AssertionError as exc:
            print(f"[firewall] FAIL  {fn.__name__}: {exc}")
            failed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[firewall] ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
            failed += 1

    print(
        f"[firewall] nodes={G.number_of_nodes()} "
        f"edges={G.number_of_edges()} regions={list(index.by_region.keys())}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_self_tests())
