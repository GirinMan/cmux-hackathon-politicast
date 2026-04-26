"""PolitiKAST Streamlit dashboard — entry point.

Multi-page app. Streamlit auto-discovers `pages/*.py` and routes via the
sidebar nav. This file is the landing page (overview + freshness banner).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `ui.dashboard.components.*` importable when run from repo root.
_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parent
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import streamlit as st  # noqa: E402

from components.data_loader import (  # noqa: E402
    HIGHLIGHT_REGIONS,
    REGION_ORDER,
    emit_cost_alerts,
    get_llm_info,
    get_region_label,
    is_cache_artifact,
    is_real_live,
    load_all_results,
    load_contracts,
    load_kg,
    load_policy,
    render_placeholder_banner,
    render_sidebar,
    result_status_badge,
)

st.set_page_config(
    page_title="PolitiKAST · Korean Local Election Simulation",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

ctx = render_sidebar("Overview")

st.title("🗳️ PolitiKAST")
st.caption(
    "Political Knowledge-Augmented Multi-Agent Simulation of Voter Trajectories "
    "for Korean Local Elections"
)

results, is_placeholder = load_all_results()
kg, kg_is_placeholder = load_kg()
contracts = load_contracts()

# Surface policy incidents/swaps as a top banner so the audience sees the
# story without expanding the provenance card.
_policy_top = load_policy() or {}
_layer_top = _policy_top.get("llm_layer") or {}
_models_top = [
    _layer_top.get(k)
    for k in ("voter_normal_model", "voter_educated_model", "interview_model", "dev_routing")
]
_providers_top = {m.split("/", 1)[0] for m in _models_top if isinstance(m, str) and "/" in m}
if _providers_top == {"gemini"} and all(m == _models_top[0] for m in _models_top):
    st.warning(
        f"**OpenAI Tier 0 quota incident** (13:15) → provider mix 폐기, "
        f"v{_policy_top.get('version','?')} Gemini-only fire (`gemini/gemini-3.1-flash-lite-preview`). "
        "비용 $0 (preview tier).",
        icon="🔁",
    )

# v1.4 invalidation banner — surfaces the validation_v14._INVALID block from
# policy.json verbatim so the audience sees that the 22min "validation" was
# retracted at 13:42.
_v14 = (_policy_top.get("validation_v14") or {})
_v14_invalid = _v14.get("_INVALID_13_42_sim_correction") if isinstance(_v14, dict) else None
if isinstance(_v14_invalid, dict):
    verdict = _v14_invalid.get("verdict") or "INVALID"
    root = _v14_invalid.get("actual_root_cause") or "—"
    impl1 = _v14_invalid.get("implication_1") or ""
    impl2 = _v14_invalid.get("implication_2") or ""
    st.error(
        f"**v1.4 validation INVALIDATED (13:42)** — {verdict}.  \n"
        f"근본원인: {root}.  \n"
        f"⇒ {impl1} · {impl2}.  \n"
        "v1.4 결과는 paper Limitations 박제용으로만 보존, 헤드라인에서 제외 (badge 🚨).",
        icon="🚨",
    )

if is_placeholder:
    render_placeholder_banner()

# ---------------------------------------------------------------------------
# Top metrics
# ---------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
real_live_count = sum(1 for r in results.values() if is_real_live(r))
mock_count = sum(1 for r in results.values() if r.get("is_mock"))
placeholder_count = sum(1 for r in results.values() if r.get("_placeholder"))
cache_artifact_count = sum(
    1 for r in results.values()
    if not r.get("is_mock") and not r.get("_placeholder") and is_cache_artifact(r)
)
delta_parts = []
if cache_artifact_count:
    delta_parts.append(f"🚨 {cache_artifact_count} v1.4 model-determinism artifact")
if mock_count:
    delta_parts.append(f"{mock_count} mock")
if placeholder_count:
    delta_parts.append(f"{placeholder_count} placeholder")
m1.metric(
    "Regions ✅ live",
    f"{real_live_count} / 5",
    delta=" · ".join(delta_parts) if delta_parts else None,
    delta_color="inverse" if cache_artifact_count else "off",
)
total_personas = sum(r.get("persona_n", 0) for r in results.values())
m2.metric("Total personas (sim)", f"{total_personas:,}")
total_interviews = sum(len(r.get("virtual_interviews", [])) for r in results.values())
m3.metric("Virtual interviews", f"{total_interviews:,}")
kg_nodes = len(kg.get("nodes", [])) if kg else 0
m4.metric("KG nodes", f"{kg_nodes:,}")

st.divider()

# ---------------------------------------------------------------------------
# Highlight card — micro 총선 시연 포인트
# ---------------------------------------------------------------------------
for hl in HIGHLIGHT_REGIONS:
    if hl in results:
        r = results[hl]
        with st.container(border=True):
            hcol1, hcol2 = st.columns([2, 1])
            with hcol1:
                st.markdown(f"### ⭐ {get_region_label(hl)} — 미니총선 메인 시연")
                cands = r.get("candidates", [])
                if len(cands) >= 2:
                    matchup = " vs ".join(
                        f"**{c.get('name','-')}** ({c.get('party','-')})" for c in cands[:2]
                    )
                    st.markdown(matchup)
                shares = r.get("final_outcome", {}).get("vote_share_by_candidate", {})
                winner_id = r.get("final_outcome", {}).get("winner")
                winner_name = next(
                    (c["name"] for c in cands if c["id"] == winner_id), winner_id or "-"
                )
                if shares:
                    margin_top2 = sorted(shares.values(), reverse=True)
                    margin = (margin_top2[0] - margin_top2[1]) if len(margin_top2) >= 2 else 0
                    st.caption(
                        f"예상 승자: **{winner_name}** · 격차 {margin:+.1%} · "
                        f"투표율 {r.get('final_outcome', {}).get('turnout', 0):.1%}"
                    )
                badge = result_status_badge(r)
                hint = ""
                if r.get("_placeholder"):
                    hint = " — 실 시뮬 결과 박제되면 자동 전환"
                elif r.get("is_mock"):
                    hint = " — mock 백엔드, LLM 키 활성화 시 동일 경로 덮어쓰기"
                st.caption(f"{badge}{hint}")
            with hcol2:
                # mini bar of shares
                if shares:
                    items = sorted(shares.items(), key=lambda kv: -kv[1])[:4]
                    cnames = {c["id"]: c.get("name", c["id"]) for c in cands}
                    cnames["abstain"] = "기권"
                    for cid, share in items:
                        st.markdown(f"**{cnames.get(cid, cid)}** — {share:.1%}")
                        st.progress(min(max(share, 0.0), 1.0))

# ---------------------------------------------------------------------------
# Region status grid
# ---------------------------------------------------------------------------
st.subheader("Region 상태")
cols = st.columns(5)
for i, region_id in enumerate(REGION_ORDER):
    with cols[i]:
        st.markdown(f"**{get_region_label(region_id)}**")
        if region_id in results:
            r = results[region_id]
            outcome = r.get("final_outcome", {})
            shares = outcome.get("vote_share_by_candidate", {})
            winner_id = outcome.get("winner")
            winner_name = next(
                (c["name"] for c in r.get("candidates", []) if c["id"] == winner_id),
                winner_id or "-",
            )
            st.caption(result_status_badge(r))
            st.metric(
                "Winner",
                winner_name,
                delta=f"{shares.get(winner_id, 0):.1%}" if winner_id else None,
            )
            st.caption(f"timesteps: {r.get('timestep_count', '-')}")
            st.caption(f"personas: {r.get('persona_n', '-')}")
        else:
            st.caption("⏳ pending")
            st.write("—")

st.divider()

# ---------------------------------------------------------------------------
# Navigation hint + KG/contract pane
# ---------------------------------------------------------------------------
left, right = st.columns([2, 1])

with left:
    st.subheader("페이지 가이드")
    st.markdown(
        """
        - **1 · Scenario Designer** — region 선택, 시나리오 파라미터, 실행 트리거
        - **2 · Poll Trajectory** — timestep × 후보 지지율 추이, consensus 신뢰구간
        - **3 · Final Outcome** — 후보별 최종 득표율, 투표율 게이지, 시·구 단위 분포
        - **4 · Demographics** — 연령/학력/지역구별 stacked bar, 광주(진보) vs 대구(보수) 비교
        - **5 · Virtual Interviews** — 페르소나 카드 (vote, reason, key_factors)
        - **6 · KG Viewer** — Election + Event/Discourse 지식그래프, 시점별 슬라이더
        """
    )

with right:
    st.subheader("Build provenance")
    llm = get_llm_info()
    decision = llm.get("decision") or "—"
    policy = load_policy() or {}
    policy_version = policy.get("version") or "—"
    policy_status = policy.get("status") or policy.get("_status") or "—"
    llm_layer = policy.get("llm_layer") or {}
    cost_guard = policy.get("cost_guard") or {}
    cg_thresholds = (cost_guard.get("thresholds_usd") or {}) if isinstance(cost_guard, dict) else {}
    feature_flags = policy.get("feature_flags_global") or {}

    # Aggregate live-run telemetry (cost per provider, calls) across loaded results.
    live_results = [r for r in results.values() if is_real_live(r)]
    archive_results = [
        r for r in results.values()
        if (r.get("is_archive") or (r.get("meta") or {}).get("is_archive"))
    ]
    cost_by_provider: dict[str, float] = {}
    thresholds_by_provider: dict[str, float] = {}
    total_voter_calls = 0
    total_parse_fail = 0
    total_abstain = 0
    total_429 = 0
    total_wall_seconds = 0.0
    latency_ms_sum = 0.0
    latency_ms_count = 0
    total_cache_hits = 0
    total_cache_misses = 0
    total_pool_calls = 0  # actual LLM-side calls (excludes voter-stat cache hits)
    concurrency_values: list[int] = []
    actual_keys_values: list[int] = []
    effective_models: set[str] = set()
    calls_by_model: dict[str, int] = {}
    features_union: set[str] = set()
    cost_tracking_any = False
    for r in live_results:
        meta = r.get("meta") or {}
        ps = meta.get("pool_stats") or {}
        cost = ps.get("cost_usd")
        if isinstance(cost, dict):
            for prov, val in cost.items():
                if isinstance(val, (int, float)):
                    cost_by_provider[prov] = cost_by_provider.get(prov, 0.0) + float(val)
        elif isinstance(cost, (int, float)):
            cost_by_provider["total"] = cost_by_provider.get("total", 0.0) + float(cost)
        thr = ps.get("cost_thresholds")
        if isinstance(thr, dict):
            for prov, val in thr.items():
                if isinstance(val, (int, float)):
                    thresholds_by_provider[prov] = float(val)
        if ps.get("cost_tracking_enabled"):
            cost_tracking_any = True
        per_key = ps.get("per_key") or []
        if isinstance(per_key, list):
            for k in per_key:
                if isinstance(k, dict) and isinstance(k.get("total_429"), int):
                    total_429 += k["total_429"]
        if isinstance(ps.get("cache_hits"), int):
            total_cache_hits += ps["cache_hits"]
        if isinstance(ps.get("cache_misses"), int):
            total_cache_misses += ps["cache_misses"]
        if isinstance(ps.get("total_calls"), int):
            total_pool_calls += ps["total_calls"]
        ws = meta.get("wall_seconds")
        if isinstance(ws, (int, float)):
            total_wall_seconds += float(ws)
        conc = meta.get("concurrency")
        if isinstance(conc, int):
            concurrency_values.append(conc)
        aku = meta.get("actual_keys_used")
        if isinstance(aku, int):
            actual_keys_values.append(aku)
        em = meta.get("effective_model")
        if isinstance(em, str) and em:
            effective_models.add(em)
        cbm = (meta.get("voter_stats") or {}).get("calls_by_model") or meta.get("calls_by_model") or {}
        if isinstance(cbm, dict):
            for mname, n in cbm.items():
                if isinstance(n, int):
                    calls_by_model[mname] = calls_by_model.get(mname, 0) + n
        feats = meta.get("features")
        if isinstance(feats, list):
            features_union.update(str(f) for f in feats)
        vs = meta.get("voter_stats") or {}
        if isinstance(vs.get("calls"), int):
            total_voter_calls += vs["calls"]
        if isinstance(vs.get("parse_fail"), int):
            total_parse_fail += vs["parse_fail"]
        if isinstance(vs.get("abstain"), int):
            total_abstain += vs["abstain"]
        if isinstance(vs.get("latency_ms_sum"), (int, float)) and isinstance(vs.get("calls"), int):
            latency_ms_sum += float(vs["latency_ms_sum"])
            latency_ms_count += vs["calls"]

    mixed_active = bool(live_results)

    voter_normal = llm_layer.get("voter_normal_model") or "gemini/gemini-3.1-flash-lite-preview"
    voter_educated = llm_layer.get("voter_educated_model") or "gemini/gemini-3.1-flash-lite-preview"
    interview_model = llm_layer.get("interview_model") or "gemini/gemini-3.1-flash-lite-preview"
    dev_routing = llm_layer.get("dev_routing") or "gemini/gemini-3.1-flash-lite-preview"
    thinking_off = llm_layer.get("thinking_off")
    thinking_label = "OFF (전 모델)" if thinking_off else ("ON" if thinking_off is False else "—")

    # v1.3: detect Gemini-only unification (all 4 model slots equal & gemini provider).
    layer_models = [voter_normal, voter_educated, interview_model, dev_routing]
    layer_providers = [m.split("/", 1)[0] if isinstance(m, str) and "/" in m else "" for m in layer_models]
    gemini_only = (
        all(m == voter_normal for m in layer_models)
        and all(p == "gemini" for p in layer_providers)
    )

    def _fmt_model(m: str) -> str:
        # Already provider/-prefixed in policy v1.3; otherwise prepend openai/.
        if isinstance(m, str) and "/" in m:
            return m
        return f"openai/{m}"

    calls_row = (
        f"| voter calls (Σ) | {total_voter_calls:,} (parse_fail {total_parse_fail}) |\n"
        if total_voter_calls else ""
    )
    if gemini_only:
        mixed_row = (
            f"| voter (unified) | `{voter_normal}` |\n"
            f"| interview | `{interview_model}` |\n"
            f"| persona-conditional branching | metadata only — branching inactive in v{policy_version} |\n"
            f"| thinking | {thinking_label} |\n"
        )
    else:
        mixed_row = (
            f"| voter — normal (학사 미만) | `{_fmt_model(voter_normal)}` |\n"
            f"| voter — educated (학사+) | `{_fmt_model(voter_educated)}` |\n"
            f"| interview | `{_fmt_model(interview_model)}` |\n"
            f"| dev override | `{dev_routing}` |\n"
            f"| thinking | {thinking_label} |\n"
        )
    archive_row = (
        f"| 📦 archive results | {len(archive_results)} (v1.1 early validation) |\n"
        if archive_results else ""
    )

    artifact_results = [
        r for r in results.values()
        if not r.get("is_mock") and not r.get("_placeholder") and is_cache_artifact(r)
    ]
    artifact_row = (
        f"| 🚨 v1.4 model-determinism artifact | {len(artifact_results)} "
        f"(H1 REJECTED 14:10 · H2 REJECTED 14:10 · H3 PROVISIONAL · Limitations only) |\n"
        if artifact_results else ""
    )

    # persona_text 결측 카운터 — 가능한 키들에서 fallback chain.
    persona_missing_total = 0
    persona_total = 0
    persona_missing_seen = False
    for r in (live_results + artifact_results):
        meta = r.get("meta") or {}
        ps_stats = meta.get("persona_stats") or {}
        miss = (
            ps_stats.get("text_missing")
            if isinstance(ps_stats, dict) else None
        )
        if miss is None:
            miss = meta.get("persona_text_missing")
        if isinstance(miss, int):
            persona_missing_total += miss
            persona_missing_seen = True
        n = r.get("persona_n")
        if isinstance(n, int):
            persona_total += n
    persona_row = ""
    if persona_missing_seen:
        rate = (persona_missing_total / persona_total * 100) if persona_total else 0.0
        warn = " ⚠️" if rate >= 5.0 else ""
        persona_row = f"| persona_text 결측 | {persona_missing_total}/{persona_total} ({rate:.1f}%){warn} |\n"

    # Effective model (per-result meta.effective_model) — defeats the
    # "pool default" misleading label when sim does provider routing.
    if effective_models:
        eff_label = ", ".join(sorted(effective_models))
        effective_row = f"| effective model (meta) | `{eff_label}` |\n"
    else:
        effective_row = ""

    # actual_keys_used aggregate — surfaces the .env / docker mismatch
    # noted by sim-engineer (3 박제 vs 1 활성).
    if actual_keys_values:
        aku_unique = sorted(set(actual_keys_values))
        if len(aku_unique) == 1:
            aku_label = f"{aku_unique[0]}"
        else:
            aku_label = f"mix [{', '.join(str(v) for v in aku_unique)}]"
        actual_keys_row = f"| pool — actual keys used | {aku_label} |\n"
    else:
        actual_keys_row = ""

    # voter calls_by_model breakdown (e.g. nano/mini/sonnet) — replaces the
    # generic mixed-model claim with empirical per-model counts.
    if calls_by_model:
        cbm_total = sum(calls_by_model.values()) or 1
        cbm_parts = " · ".join(
            f"`{m}` {n:,} ({n/cbm_total*100:.1f}%)"
            for m, n in sorted(calls_by_model.items(), key=lambda kv: -kv[1])
        )
        cbm_row = f"| calls_by_model (Σ) | {cbm_parts} |\n"
    else:
        cbm_row = ""

    # features union across live results — phase identifier (mock has 1
    # feature; v1.4 fire has 5 — bandwagon/underdog/second_order/kg_retrieval/virtual_interview).
    if features_union:
        feat_parts = " · ".join(f"`{f}`" for f in sorted(features_union))
        features_row = f"| features (∪ live) | {feat_parts} ({len(features_union)}) |\n"
    else:
        features_row = ""

    st.markdown(
        f"""
        | 항목 | 상태 |
        |---|---|
        | policy version | `v{policy_version}` |
        | policy status | {policy_status} |
        | results | {'placeholder 🛰️' if is_placeholder else 'live ✅'} |
        | KG | {'placeholder 🛰️' if kg_is_placeholder else 'live ✅'} |
        | contracts | {len(contracts)} loaded |
        | regions present | {len(results)} / 5 |
        {archive_row}{artifact_row}| LLM provider (pool default) | `{llm['provider']}` |
        | LLM model (pool default) | `{llm['model']}` |
        {effective_row}{mixed_row}{actual_keys_row}{cbm_row}{features_row}{persona_row}{calls_row}| LLM decision | {decision} |
        """
    )
    if gemini_only:
        st.caption(
            f"v{policy_version}: OpenAI Tier 0 quota incident(13:15) 대응 — provider mix 폐기, "
            "voter+interview 모두 `gemini/gemini-3.1-flash-lite-preview` 단일 모델. "
            "persona-conditional 분기 코드는 보존되었으나 양쪽 env가 동일 모델을 가리켜 fire에서 비활성. "
            "thinking은 전 모델 OFF."
        )
    else:
        st.caption(
            "voter는 학력 분기(nano ≈67% / mini ≈33%)로 per-call routing되므로 `pool_stats.model`은 pool 기본값에 해당합니다. "
            "thinking은 전 모델 OFF (Gemini 3.x truncation + OpenAI gpt-5.4 reasoning_effort=none)."
        )

    # ---- Per-provider cost meter (policy v1.2 cost_guard) ---------------
    if cg_thresholds or thresholds_by_provider:
        st.markdown("**Cost meter** — `pool_stats.cost_usd[provider]` vs `cost_guard.thresholds_usd`")
        # Prefer policy thresholds; fall back to result-embedded thresholds.
        merged_thresholds = {**thresholds_by_provider, **{k: float(v) for k, v in cg_thresholds.items() if isinstance(v, (int, float))}}
        # Persist 70/90/100% threshold transitions to alerts.log (no spam — state-file deduped).
        new_alerts = emit_cost_alerts(cost_by_provider, merged_thresholds, source="dashboard.landing")
        if new_alerts:
            for ev in new_alerts:
                st.toast(
                    f"⚠️ cost {ev['level']}: {ev['provider']} ${ev['spent_usd']:.4f} / ${ev['threshold_usd']:.2f} "
                    f"({ev['ratio']*100:.1f}%)",
                    icon="🚨",
                )
        # Order: openai → anthropic → gemini, then any extras.
        ordered = [p for p in ("openai", "anthropic", "gemini") if p in merged_thresholds]
        ordered += [p for p in merged_thresholds if p not in ordered]
        for prov in ordered:
            thr = merged_thresholds.get(prov, 0.0)
            spent = cost_by_provider.get(prov, 0.0)
            ratio = (spent / thr) if thr > 0 else 0.0
            ratio_clamped = max(0.0, min(1.0, ratio))
            warn = " ⚠️" if ratio >= 0.7 else ""
            st.progress(
                ratio_clamped,
                text=f"{prov}: ${spent:.4f} / ${thr:.2f} ({ratio*100:.1f}%){warn}",
            )
        if gemini_only:
            st.caption(
                "🛈 v1.3 Gemini-only — preview tier(`gemini-3.1-flash-lite-preview`)는 **무료**라 cost meter는 항상 0%로 머무릅니다. "
                "guard rail은 모델 swap 회복 경로(`anthropic/claude-haiku-4-5` 또는 `openai/gpt-4o-mini`)를 위해 유지."
            )
        elif not cost_tracking_any and live_results:
            st.caption(
                "🛈 `cost_tracking_enabled=false` (dev / `POLITIKAST_ENV=dev`) — meter는 prod fire 결과 박제 시 채워집니다."
            )

    # ---- Throughput gauges (14:05 보고 시점 — abstain / 429 / latency) ----
    if live_results and total_voter_calls:
        abstain_rate = (total_abstain / total_voter_calls) if total_voter_calls else 0.0
        parse_fail_rate = (total_parse_fail / total_voter_calls) if total_voter_calls else 0.0
        mean_latency_ms = (latency_ms_sum / latency_ms_count) if latency_ms_count else 0.0
        # pool_effective_rpm — real network LLM hits per minute. cache hits
        # never touch the API and `pool_stats.total_calls` includes them, so
        # we use `cache_misses` (actual API requests). Cache가 0인 결과만
        # 있을 때만 voter_calls로 fallback.
        if total_cache_misses:
            rpm_calls = total_cache_misses
            rpm_basis = "cache_misses (실 API)"
        elif total_pool_calls:
            rpm_calls = total_pool_calls
            rpm_basis = "pool_stats.total_calls"
        else:
            rpm_calls = total_voter_calls
            rpm_basis = "voter_stats.calls"
        effective_rpm = (
            (rpm_calls / total_wall_seconds * 60.0) if total_wall_seconds > 0 else 0.0
        )
        st.markdown("**Throughput** (Σ over live regions)")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric(
            "abstain rate",
            f"{abstain_rate*100:.1f}%",
            delta=f"{total_abstain}/{total_voter_calls}",
            delta_color="off",
        )
        g2.metric(
            "parse fail rate",
            f"{parse_fail_rate*100:.2f}%",
            delta=f"{total_parse_fail}/{total_voter_calls}",
            delta_color="off",
        )
        g3.metric(
            "mean latency",
            f"{mean_latency_ms:,.0f} ms",
            delta=f"wall {total_wall_seconds:,.0f}s",
            delta_color="off",
        )
        if effective_rpm >= 60:
            rpm_band = "✅ 가설 A: separated GCP, multi-key aggregate"
        elif effective_rpm >= 30:
            rpm_band = "⚠️ shared GCP 또는 transient throttling"
        elif effective_rpm > 0:
            rpm_band = "🚨 single-key thrash 가능"
        else:
            rpm_band = ""
        g4.metric(
            "effective RPM",
            f"{effective_rpm:.1f}",
            delta=(f"429 ×{total_429}" if total_429 else (rpm_band or None)),
            delta_color=(
                "inverse" if total_429 else
                ("normal" if effective_rpm >= 60 else
                 "off" if effective_rpm >= 30 else
                 "inverse" if effective_rpm > 0 else "off")
            ),
        )

        # Auxiliary line: cache hit rate + concurrency (config provenance).
        cache_total = total_cache_hits + total_cache_misses
        cache_hit_rate = (total_cache_hits / cache_total) if cache_total else 0.0

        # Cache-artifact caveat — sim-engineer 04:35 보고: cache_hit_rate ≥ 0.90
        # 이면 cached prompt 동일 응답 재사용으로 sweep(vote_share=1.0)이
        # 정성적 baseline엔 정합이지만 정량값은 신뢰 못함.
        sweep_count = 0
        for r in live_results:
            fo = r.get("final_outcome") or {}
            shares = fo.get("vote_share_by_candidate") or fo.get("vote_shares")
            if isinstance(shares, dict):
                vals = [v for v in shares.values() if isinstance(v, (int, float))]
                if vals and max(vals) >= 0.999:
                    sweep_count += 1
            elif isinstance(fo.get("vote_share"), (int, float)) and fo["vote_share"] >= 0.999:
                sweep_count += 1
        if cache_hit_rate >= 0.90 or sweep_count:
            st.warning(
                f"⚠ **캐시 재사용률 {cache_hit_rate*100:.1f}%** "
                f"({total_cache_hits:,} / {cache_total:,}) — 동일 prompt cached 응답이 "
                f"여러 페르소나에 반복 적용되었을 가능성. "
                f"vote_share 100% sweep {sweep_count}건 감지. "
                f"**정성적 ideology baseline은 정합**하나 정량값은 caveat 적용 (paper Limitations 박제 권고).",
                icon="🧊",
            )
        if concurrency_values:
            conc_unique = sorted(set(concurrency_values))
            conc_label = (
                f"concurrency ×{conc_unique[0]}"
                if len(conc_unique) == 1
                else f"concurrency mix [{', '.join(str(c) for c in conc_unique)}]"
            )
        else:
            conc_label = "concurrency —"
        rpm_band_caption = f" · **RPM band**: {rpm_band}" if rpm_band else ""
        # Theoretical capacity = actual_keys × per-key RPM (Gemini-3.1-flash-lite
        # preview = 46 RPM per capacity_evidence.v3_realistic_probe). When
        # measured > 1.5× theoretical, cache reuse is the most likely cause —
        # raise a 🚨 mismatch flag.
        per_key_rpm = 46  # capacity_evidence baseline; could be policy.capacity_evidence-driven later
        max_keys = max(actual_keys_values) if actual_keys_values else 1
        theoretical_rpm = max_keys * per_key_rpm
        if effective_rpm > 1.5 * theoretical_rpm and theoretical_rpm > 0:
            cap_caption = (
                f" · 이론 capacity = {max_keys}-key × {per_key_rpm} = **{theoretical_rpm} RPM** "
                f"vs 측정 {effective_rpm:.1f} RPM → 🚨 cache 의심 ({effective_rpm/theoretical_rpm:.1f}× 초과)"
            )
        elif theoretical_rpm > 0:
            cap_caption = (
                f" · 이론 capacity = {max_keys}-key × {per_key_rpm} = **{theoretical_rpm} RPM** "
                f"(측정 {effective_rpm:.1f} RPM)"
            )
        else:
            cap_caption = ""
        st.caption(
            f"abstain·parse_fail은 voter_stats(JSON 파싱/판단 실패), "
            f"effective RPM = Σ {rpm_basis} / Σ wall_seconds × 60. "
            f"429는 pool per-key total_429 합산 (rate-limit 충돌). · "
            f"**cache hit rate** {cache_hit_rate*100:.1f}% ({total_cache_hits:,} / {cache_total:,}) · "
            f"**{conc_label}** (`POLITIKAST_CONCURRENCY` op override).{rpm_band_caption}{cap_caption}"
        )

    st.caption(f"LLM source: `{llm['source']}` · LiteLLM 라우팅 — provider 슬러그(`gemini/`, `openai/`, `anthropic/`, `azure/`, `vertex_ai/`, `bedrock/`, `groq/`, `openrouter/`)로 자동 라우팅됩니다.")

    # ---- v1.4 artifact evidence pointers (expander) ----------------------
    # Surfaces the audit trail (research/* + _archived/*) so a viewer can
    # follow the same evidence chain that paper §5 cites. Only shown when
    # there is at least one classified artifact (active or just-archived).
    artifact_evidence_paths = [
        ("H1 REJECTED — cache audit (14:10)", "_workspace/research/cache_audit_v14.md", "summary: cache rows 6,977 / 6,971 distinct (99.9% unique) → phantom hit; cache hit rate signal misled v13:42 attribution."),
        ("H1 REJECTED — cache audit (raw)", "_workspace/research/cache_audit_v14.json", "machine-readable companion to the .md."),
        ("H2 REJECTED — persona prompt diversity (14:10)", "_workspace/research/persona_prompt_diversity.json", "summary: persona collision_rate = 0.0 across 5 region samples; persona_text uniqueness 100%."),
        ("H3 PROVISIONAL — LLMPool 3-key bug + Fix A/B/C", "_workspace/research/llmpool_3key_bug.md", "single-key fire root cause + remediation menu."),
        ("v1.4 fire archive (5 region results + MANIFEST)", "_workspace/snapshots/_archived/v14_run_20260426T050040Z/MANIFEST.md", "per-region winner / wall / cache_hit_rate table; preserved for paper §5."),
    ]
    # Always show once the audit trail exists — even if the active index
    # has no artifact rows (post-archive state).
    from pathlib import Path as _Path
    _repo = _Path(__file__).resolve().parents[2]
    existing = [
        (label, rel, note)
        for label, rel, note in artifact_evidence_paths
        if (_repo / rel).exists()
    ]
    if existing:
        with st.expander(
            f"🔎 v1.4 artifact evidence trail · {len(existing)} pointer(s)",
            expanded=False,
        ):
            st.caption(
                "paper §5 Limitations / scratchpad / dashboard 모두 동일 evidence pointer를 사용합니다. "
                "각 항목은 read-only — 클릭 시 raw 파일을 컨테이너에서 직접 확인하세요."
            )
            for label, rel, note in existing:
                st.markdown(f"**{label}** — `{rel}`  \n{note}")

    # ---- policy v1.2 regions + feature flags ----------------------------
    if policy.get("regions") or feature_flags:
        with st.expander("policy v1.2 — regions + feature flags", expanded=False):
            regions_cfg = policy.get("regions") or {}
            if isinstance(regions_cfg, dict) and regions_cfg:
                rows = ["| region | persona_n | T | interview | weight | educated |", "|---|---|---|---|---|---|"]
                for rid, cfg in regions_cfg.items():
                    if not isinstance(cfg, dict):
                        continue
                    rows.append(
                        f"| `{rid}` | {cfg.get('persona_n','—')} | {cfg.get('timesteps','—')} | "
                        f"{cfg.get('interview_n','—')} | {cfg.get('weight','—')} | "
                        f"{cfg.get('educated_ratio','—')} |"
                    )
                st.markdown("\n".join(rows))
            if isinstance(feature_flags, dict) and feature_flags:
                ff_line = " · ".join(
                    f"`{k}`={'✅' if v else '❌'}" for k, v in feature_flags.items()
                )
                st.caption(f"feature flags: {ff_line}")
    st.caption(
        "결과가 박제되면 사이드바의 ‘5초 자동 갱신’이 켜진 동안 자동으로 실 데이터로 전환됩니다."
    )
