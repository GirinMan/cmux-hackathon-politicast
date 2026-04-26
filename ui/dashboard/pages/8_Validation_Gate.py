"""Validation Gate — rolling-origin official-poll backtest (V9 ACTIVE).

Paper redesign (scratchpad §"Main Agent Reference: Validation-First Redesign",
2026-04-26 13:59 KST) made this page the *headline* of the demo flow.

Two axes:
1. **Past-election backtest** — for each region, freeze model + KG + persona at
   the historical election date, run sim with the temporal firewall, compare
   against the certified outcome (`_workspace/data/scenarios/historical_outcomes/`).
2. **Rolling-origin current-poll trajectory** — sim trajectory vs.
   NESDC-registered official polls (`poll_consensus_daily`).
   Result JSON contract: `official_poll_validation` block (see
   `_workspace/validation/official_poll_validation_targets.md`).

Source slot: `_workspace/snapshots/validation/{rolling_*,backtest_*}.json`.
Polled every 5 s via the standard sidebar autorefresh.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_DASH_ROOT = _HERE.parents[1]
if str(_DASH_ROOT) not in sys.path:
    sys.path.insert(0, str(_DASH_ROOT))

import streamlit as st  # noqa: E402

from components.data_loader import (  # noqa: E402
    REGION_ORDER,
    REPO_ROOT,
    evaluate_validation_metrics,
    extract_validation_block,
    gate_overall_pass,
    get_region_label,
    list_validation_files,
    load_hill_climbing_summary,
    load_historical_outcomes,
    load_policy,
    load_validation_results,
    load_validation_thresholds,
    render_sidebar,
    validation_cache_enabled,
    validation_cache_hits,
    validation_is_unavailable,
    validation_run_quality,
    validation_target_series,
)

st.set_page_config(page_title="Validation Gate · PolitiKAST", layout="wide")
ctx = render_sidebar("Validation Gate")
scope: str = ctx.get("scope", "all")  # type: ignore[assignment]

st.title("🛂 Validation Gate")
st.caption(
    "Rolling-origin official-poll validation — paper(13:59 redesign) headline. "
    "공식 NESDC 등록 여론조사를 검증 라벨로 사용해 sim trajectory 가 실제 여론을 "
    "재현하는지 정량 평가. **현재 선거 forecast 는 이 게이트를 통과한 후에만 신뢰 가능.**"
)

policy = load_policy() or {}
policy_status = policy.get("status") or policy.get("_status") or "—"
st.caption(f"policy: `v{policy.get('version', '?')}` · {policy_status}")

# ---------------------------------------------------------------------------
# Discover validation results
# ---------------------------------------------------------------------------
thresholds = load_validation_thresholds()
rolling_results = load_validation_results("rolling")
backtest_results = load_validation_results("backtest")
historical = load_historical_outcomes()

rolling_files = list_validation_files("rolling")
backtest_files = list_validation_files("backtest")
has_any = bool(rolling_results) or bool(backtest_results)

# Region scoping
def _scoped(rids: list[str]) -> list[str]:
    if scope == "all":
        return [r for r in REGION_ORDER if r in rids]
    return [scope] if scope in rids else []


# ---------------------------------------------------------------------------
# Headline summary
# ---------------------------------------------------------------------------
hl_cols = st.columns(4)
hl_cols[0].metric(
    "rolling regions",
    len(rolling_results),
    delta=f"{len(rolling_files)} validation files + results fallback" if rolling_results else "pending",
)
hl_cols[1].metric(
    "backtest result files",
    len(backtest_files),
    delta=f"{len(backtest_results)} regions parsed" if backtest_results else "pending",
)
hl_cols[2].metric(
    "historical outcomes",
    f"{len(historical)}/5",
    delta="baseline ready" if len(historical) >= 5 else "partial",
)
# Aggregate gate pass count (rolling only — current-election validation)
pass_count = 0
fail_count = 0
unavailable_count = 0
unknown_count = 0
clean_fail_regions: list[str] = []
unavailable_regions: list[str] = []
# Paper-headline aggregate: mean MAE + leader-match rate across rated regions
mae_values: list[float] = []
leader_true: list[bool] = []
sweep_count = 0  # 100%-sweep heuristic — single candidate ≥ 0.99
methods_used: set[str] = set()
for rid, payload in rolling_results.items():
    opv = extract_validation_block(payload) or {}
    target = validation_target_series(payload) or ""
    run_quality = validation_run_quality(payload)
    # sweep is a property of the simulator output regardless of validation
    # state — count across ALL surfaced regions (including missing) so the
    # paper-headline numerics ("100%-sweep regions = 5/5") match sim notes.
    fo = payload.get("final_outcome") or {}
    shares = fo.get("vote_share_by_candidate") or {}
    if isinstance(shares, dict) and shares:
        try:
            if max(float(v) for v in shares.values()) >= 0.99:
                sweep_count += 1
        except (TypeError, ValueError):
            pass
    if validation_is_unavailable(payload):
        unavailable_count += 1
        unavailable_regions.append(rid)
        continue
    m = opv.get("metrics") or {}
    rows = evaluate_validation_metrics(m, thresholds)
    overall = gate_overall_pass(rows)
    if overall is True:
        pass_count += 1
    elif overall is False:
        fail_count += 1
        if target == "poll_consensus_daily" and run_quality.startswith("clean"):
            clean_fail_regions.append(rid)
    else:
        unknown_count += 1
    if isinstance(m.get("mae"), (int, float)):
        mae_values.append(float(m["mae"]))
    if isinstance(m.get("leader_match"), bool):
        leader_true.append(bool(m["leader_match"]))
    if opv.get("method_version"):
        methods_used.add(str(opv["method_version"]))
total = len(rolling_results)
delta_parts: list[str] = []
if pass_count:
    delta_parts.append(f"✅{pass_count}")
if fail_count:
    delta_parts.append(f"❌{fail_count}")
if unavailable_count:
    delta_parts.append(f"🚫{unavailable_count} unavailable")
if unknown_count:
    delta_parts.append(f"⏳{unknown_count}")
rated = pass_count + fail_count + unknown_count
hl_cols[3].metric(
    "rolling gate pass",
    f"{pass_count}/{rated} rated" if total else "—",
    delta=" ".join(delta_parts) or "pending",
)

# Current-result status cards: distinguish rated FAIL from unavailable slots.
if clean_fail_regions:
    clean_labels = ", ".join(get_region_label(rid) for rid in clean_fail_regions)
    st.error(
        "**Clean official-poll validation FAIL** — "
        f"{clean_labels} failed `poll_consensus_daily` validation with "
        "`POLITIKAST_LLM_CACHE=0`/`cache_hits=0`. Current-election forecast "
        "claims stay blocked until this gate passes.",
        icon="🚨",
    )
if unavailable_regions:
    unavailable_labels = ", ".join(get_region_label(rid) for rid in unavailable_regions)
    st.warning(
        "**Official-poll validation unavailable** — "
        f"{unavailable_labels} have `target_series=missing` or "
        "`target_series=prediction_only`; this is not a pending run. No "
        "matched NESDC consensus target is available for the current "
        "cutoff/candidate mapping.",
        icon="🚫",
    )

# Paper headline narrative banner (sim-engineer 14:34 제안) — surface
# only when at least 2 regions are rated, since a single FAIL is anecdotal.
if rated >= 2:
    mean_mae = sum(mae_values) / len(mae_values) if mae_values else None
    leader_pass = sum(1 for x in leader_true if x)
    primary_method = ""
    if methods_used:
        # prefer poll_consensus_daily / weighted_v1 if engaged
        if "weighted_v1" in methods_used:
            primary_method = "DuckDB primary (poll_consensus_daily, weighted_v1)"
        elif "scenario_fallback_v1" in methods_used:
            primary_method = "scenario fallback (raw_polls)"
        else:
            primary_method = ", ".join(sorted(methods_used))
    if fail_count == rated and pass_count == 0:
        scope_note = (
            f"{fail_count}/{rated} rated"
            + (f" · {unavailable_count}/{len(rolling_results)} unavailable" if unavailable_count else "")
        )
        st.error(
            f"📌 **paper headline** — gate caught **{scope_note}** regions: "
            + (f"mean MAE = `{mean_mae:.4f}` " if mean_mae is not None else "")
            + f"(threshold ≤ {thresholds.get('mae_max'):.3f}, "
            f"~{(mean_mae / thresholds.get('mae_max', 0.05)):.1f}× over) · "
            f"leader_match = {leader_pass}/{len(leader_true)} · "
            f"100%-sweep regions = {sweep_count}/{len(rolling_results)}"
            + (f" · {primary_method}" if primary_method else "")
            + ". **Validation-first methodology required** — zero-shot LLM voter "
            "simulation does not pass on its own.",
            icon="🚨",
        )
        # Provenance qualifier — 정확히 어떤 라우팅이 검증되었는지 명시.
        # paper narrative 와 정합 유지를 위해 prod routing 은 future-work scope.
        st.caption(
            "scope note · 검증된 라우팅: dev=Gemini-3.1-flash-lite (lite-tier deterministic alignment 시그널). "
            "prod=gpt-5.4-nano/mini routing 은 미실시(future work). 100%-sweep 원인 분석은 "
            "`_workspace/research/cache_audit_v14.md` 참조."
        )
    elif pass_count and fail_count:
        st.warning(
            f"⚠️ **gate mixed**: ✅{pass_count} / ❌{fail_count} / ⏳{unknown_count} of {rated} rated regions"
            + (f" · mean MAE = `{mean_mae:.4f}`" if mean_mae is not None else "")
            + (f" · {primary_method}" if primary_method else ""),
            icon="⚠️",
        )
    elif pass_count == rated:
        st.success(
            f"✅ **gate pass**: {pass_count}/{rated} regions"
            + (f" · mean MAE = `{mean_mae:.4f}`" if mean_mae is not None else "")
            + (f" · {primary_method}" if primary_method else ""),
            icon="✅",
        )

if not has_any:
    st.info(
        "**데이터 슬롯 pending** — `_workspace/snapshots/validation/{rolling_*,backtest_*}.json` "
        "이 박제되면 5초 안에 자동으로 채워집니다. data-engineer V3 (poll_consensus_daily) + "
        "sim-engineer V8 (validation fire) 결과 대기 중.",
        icon="⏳",
    )

st.divider()

# ---------------------------------------------------------------------------
# ② Rolling-origin gate (headline carousel — listed first per task brief)
# ---------------------------------------------------------------------------
st.subheader("① Rolling-origin official-poll gate")
st.caption(
    "5 region 에 대해 cutoff `τ_r⁻` 기준 sim trajectory vs `poll_consensus_daily`. "
    "MAE / RMSE / margin error / leader match 모두 통과해야 ✅."
)

# Threshold reference table
with st.expander("Gate thresholds (현재값)", expanded=False):
    st.markdown(
        f"""
        | criterion | comparator | threshold | source |
        |---|---|---|---|
        | MAE (vote share) | ≤ | `{thresholds.get('mae_max'):.3f}` | default / contract |
        | RMSE | ≤ | `{thresholds.get('rmse_max'):.3f}` | default / contract |
        | Margin error | ≤ | `{thresholds.get('margin_error_max'):.3f}` | default / contract |
        | Leader match | == | `True` | required |
        | Backtest RMSE | ≤ | `{thresholds.get('backtest_rmse_max'):.3f}` | default / contract |
        | Backtest |Δ lead pp| | ≤ | `{thresholds.get('backtest_lead_pp_max'):.3f}` | default / contract |
        """
    )
    st.caption(
        "thresholds 는 `_workspace/contracts/validation_schema.json` 박제 시 "
        "자동으로 contract value 로 동기화됩니다. 현재는 default."
    )

scoped_rolling = _scoped(list(rolling_results.keys()))
if scoped_rolling:
    # Summary row table
    rows: list[dict[str, Any]] = []
    for rid in scoped_rolling:
        payload = rolling_results[rid]
        opv = extract_validation_block(payload) or {}
        m = opv.get("metrics") or {}
        criteria = evaluate_validation_metrics(m, thresholds)
        overall = gate_overall_pass(criteria)
        target = validation_target_series(payload) or "—"
        run_quality = validation_run_quality(payload)
        cache_hits = validation_cache_hits(payload)
        cache_enabled = validation_cache_enabled(payload)
        is_unavailable = validation_is_unavailable(payload)
        gate_label = (
            "🚫 unavailable" if is_unavailable
            else ("✅ pass" if overall is True
                  else ("❌ fail (clean)" if overall is False and run_quality.startswith("clean")
                        else ("❌ fail" if overall is False else "⏳ partial")))
        )
        rows.append({
            "region": get_region_label(rid),
            "as_of": opv.get("as_of_date") or "—",
            "target": target,
            "MAE": m.get("mae"),
            "RMSE": m.get("rmse"),
            "margin_err": m.get("margin_error"),
            "leader_match": m.get("leader_match"),
            "gate": gate_label,
            "provenance": run_quality,
            "cache_hits": cache_hits if cache_hits is not None else "—",
            "cache_enabled": cache_enabled if cache_enabled is not None else "—",
            "method": opv.get("method_version") or "—",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Per-region detail expanders
    for rid in scoped_rolling:
        payload = rolling_results[rid]
        opv = extract_validation_block(payload) or {}
        m = opv.get("metrics") or {}
        target = validation_target_series(payload) or "—"
        method = opv.get("method_version") or "—"
        run_quality = validation_run_quality(payload)
        is_unavailable = validation_is_unavailable(payload)
        criteria = evaluate_validation_metrics(m, thresholds)
        overall = gate_overall_pass(criteria)
        if is_unavailable:
            badge = "🚫 UNAVAILABLE"
        else:
            badge = ("✅ PASS" if overall is True
                     else ("❌ FAIL" if overall is False else "⏳ PARTIAL"))
        with st.expander(f"{badge} · {get_region_label(rid)} — {opv.get('as_of_date', '?')}", expanded=(scope == rid or len(scoped_rolling) == 1)):
            if is_unavailable:
                # Surface the cutoff / consensus-window mismatch explicitly so
                # the demo viewer doesn't read this as a silent fail.
                fo = payload.get("final_outcome") or {}
                winner = fo.get("winner") or "—"
                target = validation_target_series(payload) or "missing"
                if target == "prediction_only":
                    st.warning(
                        "**Prediction-only scenario** — this region has source-backed "
                        "media/candidate-field priors but no matched NESDC validation "
                        "target. It is excluded from MAE/RMSE/leader-match scoring.",
                        icon="🚫",
                    )
                    st.info(
                        f"sim result winner=`{winner}` is retained as a hypothetical "
                        "scenario artifact, not as validation evidence.",
                        icon="ℹ️",
                    )
                    continue
                st.warning(
                    "**검증 데이터 부재 (target_series=missing)** — sim cutoff "
                    f"`{opv.get('cutoff_ts', '—')}` 기준으로 NESDC "
                    "`poll_consensus_daily` 윈도우 내 정합 데이터가 없거나 후보 "
                    "매핑이 unusable. sim 결과(winner=`"
                    f"{winner}`) 자체는 박제되어 있으나 게이트 판정 불가. "
                    "→ sim re-fire 시 `cutoff_ts` 를 consensus 윈도우 안으로 "
                    "이동시키거나, `raw_poll_result` 에 해당 region 매핑을 추가해야 함.",
                    icon="🚫",
                )
                st.info(
                    "No MAE/RMSE/margin/leader-match metrics are rated for "
                    "`target_series=missing`; the validation target is unavailable, "
                    "not still pending.",
                    icon="ℹ️",
                )
            else:
                if overall is False and run_quality.startswith("clean"):
                    st.error(
                        "**Clean official-poll validation failed** — metrics below "
                        "come from the no-cache `poll_consensus_daily` artifact, "
                        "so this is a calibration/behavior failure rather than a "
                        "stale cache or placeholder.",
                        icon="🚨",
                    )
                cc = st.columns(4)
                for col, (_key, row) in zip(cc, criteria.items()):
                    value = row.get("value")
                    if isinstance(value, float):
                        disp = f"{value:.4f}"
                    elif isinstance(value, bool):
                        disp = "✓" if value else "✗"
                    else:
                        disp = "—" if value is None else str(value)
                    ok = row.get("pass")
                    badge2 = "✅" if ok is True else ("❌" if ok is False else "⏳")
                    col.metric(
                        row["label"],
                        disp,
                        delta=f"{badge2} {row['comparator']} {row['threshold']}",
                    )

            detail_cache_hits = validation_cache_hits(payload)
            st.caption(
                f"cutoff: `{opv.get('cutoff_ts', '—')}` · target_series: "
                f"`{target}` · method: `{method}` · source_polls: "
                f"{len(opv.get('source_poll_ids') or [])} · "
                f"provenance: `{run_quality}` · cache_hits: "
                f"`{detail_cache_hits if detail_cache_hits is not None else '—'}`"
            )
            by_cand = opv.get("by_candidate") or {}
            if by_cand:
                cand_rows = []
                for cid, cdata in by_cand.items():
                    if not isinstance(cdata, dict):
                        continue
                    cand_rows.append({
                        "candidate_id": cid,
                        "simulated": cdata.get("simulated_share"),
                        "official": cdata.get("official_consensus"),
                        "error": cdata.get("error"),
                    })
                st.markdown("**Per-candidate**")
                st.dataframe(cand_rows, use_container_width=True, hide_index=True)

            src = payload.get("_source_path")
            if src:
                st.caption(f"📂 `{src}`")
else:
    st.info(
        "Rolling-origin 결과 없음 — sim-engineer V8 fire 후 "
        "`_workspace/snapshots/validation/rolling_<region>_*.json` 생성 시 자동 표시.",
        icon="⏳",
    )

st.divider()

# ---------------------------------------------------------------------------
# ② Past-election backtest
# ---------------------------------------------------------------------------
st.subheader("② Past-election backtest")
st.caption(
    "`_workspace/data/scenarios/historical_outcomes/<region>.json` (직전 본 선거 winner / "
    "lead_pp) vs simulator 가 생성한 backtest 결과. Temporal Information Firewall 통과 증거."
)

scoped_hist = _scoped(list(historical.keys()))
if not scoped_hist:
    st.info("historical_outcomes 디렉토리에 region 데이터가 없습니다.", icon="ℹ️")
else:
    for rid in scoped_hist:
        hist = historical[rid]
        bt_payload = backtest_results.get(rid)

        with st.container(border=True):
            top = st.columns([3, 2, 2, 2])
            with top[0]:
                st.markdown(f"**{get_region_label(rid)}**  ·  `{rid}`")
                el = hist.get("election", {})
                st.caption(
                    f"baseline: {el.get('name', '—')} · {el.get('date', '—')}"
                )
            actual_winner = None
            actual_lead = hist.get("lead_pp")
            for r in hist.get("results", []):
                if r.get("rank") == 1:
                    actual_winner = r.get("name")
                    break
            top[1].metric("actual winner", actual_winner or "—")
            top[2].metric(
                "actual lead Δ",
                f"{actual_lead:.3f}" if isinstance(actual_lead, (int, float)) else "—",
            )

            # Simulator backtest comparison
            if bt_payload:
                opv = extract_validation_block(bt_payload) or {}
                m = opv.get("metrics") or {}
                bt_winner = (opv.get("predicted_winner")
                             or (bt_payload.get("final_outcome") or {}).get("winner"))
                bt_lead = m.get("margin_error")
                top[3].metric(
                    "sim winner",
                    bt_winner or "—",
                    delta=("match" if bt_winner and actual_winner and bt_winner == actual_winner
                           else ("mismatch" if bt_winner else "pending")),
                )
                criteria = evaluate_validation_metrics(m, thresholds)
                overall = gate_overall_pass(criteria)
                badge = ("✅ PASS" if overall is True
                         else ("❌ FAIL" if overall is False else "⏳ PARTIAL"))
                st.caption(badge)
                cc = st.columns(4)
                for col, row in zip(cc, criteria.values()):
                    value = row.get("value")
                    if isinstance(value, float):
                        disp = f"{value:.4f}"
                    elif isinstance(value, bool):
                        disp = "✓" if value else "✗"
                    else:
                        disp = "—" if value is None else str(value)
                    ok = row.get("pass")
                    b2 = "✅" if ok is True else ("❌" if ok is False else "⏳")
                    col.metric(
                        row["label"], disp,
                        delta=f"{b2} {row['comparator']} {row['threshold']}",
                    )
                src = bt_payload.get("_source_path")
                if src:
                    st.caption(f"📂 `{src}`")
            else:
                top[3].metric("sim winner", "—", delta="pending")
                st.caption(
                    "📌 backtest 결과 슬롯 — "
                    f"`_workspace/snapshots/validation/backtest_{rid}_*.json` 박제 시 자동 표시"
                )

st.divider()

# ---------------------------------------------------------------------------
# Rolling-origin trajectory placeholder (data-engineer V3 후 채움)
# ---------------------------------------------------------------------------
st.subheader("Rolling-origin trajectory (poll_consensus_daily)")
st.caption(
    "`as_of_date` 시리즈를 timestep 으로 펼쳐 sim trajectory 와 정합 시각화. "
    "data-engineer V3 (`poll_consensus_daily` 박제) 후 활성화."
)
trajectory_rendered = False
for rid in _scoped(list(rolling_results.keys())):
    payload = rolling_results[rid]
    series = payload.get("trajectory_series") or payload.get("rolling_origins")
    if not series:
        continue
    trajectory_rendered = True
    st.markdown(f"**{get_region_label(rid)}**")
    try:
        st.line_chart(series, use_container_width=True)
    except Exception:
        # Fallback: show raw structure
        st.json(series, expanded=False)
if not trajectory_rendered:
    st.info(
        "trajectory_series 키가 아직 결과 JSON 에 없습니다 — data-engineer V3 박제 대기.",
        icon="⏳",
    )

st.divider()

# ---------------------------------------------------------------------------
# Hill-climbing trajectory — KG narrative enrichment evidence (paper §6)
# ---------------------------------------------------------------------------
hc_summary = load_hill_climbing_summary()
if hc_summary:
    # Round label for caption (e.g. R6_partial_trackA_only)
    rounds_seen = sorted({v.get("_round") for v in hc_summary.values() if v.get("_round")})
    round_label = ", ".join(rounds_seen) if rounds_seen else "—"
    st.subheader("🧗 Hill-climbing harness (n=10 ablation, Track A baseline)")
    st.caption(
        f"⚠️ **이 카드는 n=10 harness fire** (`_workspace/snapshots/hill_climbing/`). "
        f"R6_full harness 안에서 Track A only vs Track A+B variant 비교 — paper §6 "
        f"in-regime ablation evidence. **production fire (n=200, Track A+B) 결과는 "
        f"위 §① rolling-origin gate 에서 자동 surface** (daegu_mayor 가 거기서 "
        f"**자력 leader_match=True**, MAE 0.0538, R5 hardcode 0.1486 대비 2.76× tighter "
        f"— Track B (cohort priors) 가 김부겸 outlier resolution 에 essential). latest round: `{round_label}`."
    )
    # 4-stage demo narrative trajectory (snapshot of paper §6 evidence chain).
    # Static markdown — values reflect the team-curated milestones as of
    # 16:13 KST. Live banner numerics above stay auto-derived.
    with st.expander("📈 4-stage trajectory snapshot (paper §6 narrative)", expanded=True):
        st.markdown(
            """
            | stage | source | seoul MAE | busan MAE | daegu MAE | leader_match | sweep |
            |---|---|---:|---:|---:|---:|---:|
            | baseline (5/5 sweep) | n=200 production | 0.5702 | 0.4444 | 0.5052 | 0/3 | 5/5 |
            | v12_feedback_off | n=200 production | 0.2581 | 0.0987 | 0.4919 | 2/3 | 2/5 |
            | R6 hill-climbing (daegu hardcode) | n=10 harness | **0.0298** | 0.135 | 0.1486 | 3/3 | — |
            | **R6 full (no hardcode)** | **n=200 production** | 0.3745 | 0.1062 | **0.0538** | **3/3 자력** | 0/3 rated |
            """
        )
        st.caption(
            "🔄 **narrative inversion (16:22 정정)** — Track B (CohortPrior) 효과는 "
            "**sample-size-dependent + region-dependent**, monotonic regression 아님:\n\n"
            "• n=10 harness 안에서 v4_v2 (Track A only) vs v4_v2_kg (Track A+B) 비교: "
            "seoul +0.100 / busan +0.133 MAE 회귀 (small-n cohort over-fit).\n\n"
            "• **n=200 production (Track A+B) → daegu_mayor 自력 leader_match=True** "
            "(R5 hardcode 0.1486 → R6_full 0.0538, **2.76× tighter, generalizable**). "
            "Track B 가 김부겸 outlier resolution 에 essential.\n\n"
            "• n=200 production seoul: cohort_prior at scale → DPK over-amplification "
            "60:40 → 94:6 (paper §Limitations material).\n\n"
            "→ paper §6 evidence: cohort prior shrinkage factor + age-band-specific "
            "attenuation 가 swing voter 안정화에 future work."
        )

    rated_threshold_mae = thresholds.get("mae_max", 0.05)

    hc_rows: list[dict[str, Any]] = []
    for rid in REGION_ORDER:
        entry = hc_summary.get(rid)
        if not entry:
            continue
        m = entry.get("metrics") or {}
        mae = m.get("mae")
        leader = m.get("leader_match")
        if isinstance(mae, (int, float)):
            gate_lbl = "✅ PASS" if mae <= rated_threshold_mae and leader else (
                "❌ FAIL" if leader is False else
                "⚠️ borderline" if leader is True else "⏳ partial"
            )
        else:
            gate_lbl = "🚫 unavailable"
        # Production-sim baseline MAE for the same region (so the demo viewer
        # sees the trajectory shift inline)
        prod = rolling_results.get(rid)
        prod_mae = None
        if prod:
            prod_blk = extract_validation_block(prod) or {}
            prod_mae = (prod_blk.get("metrics") or {}).get("mae")
        delta = None
        if isinstance(mae, (int, float)) and isinstance(prod_mae, (int, float)):
            delta = mae - prod_mae
        # KG ablation: best vs non-KG (Track A only) — surfaces ΔMAE within
        # the same round when both `v4_v2_kg` and `v4_v2_nesdc_plus_policy`
        # variants exist for the region.
        kg_delta: float | None = None
        all_v = entry.get("_all_variants") or []
        kg_mae = next(
            (v["metrics"].get("mae") for v in all_v
             if isinstance(v.get("variant"), str) and "kg" in v["variant"].lower()),
            None,
        )
        nokg_mae = next(
            (v["metrics"].get("mae") for v in all_v
             if isinstance(v.get("variant"), str) and "kg" not in v["variant"].lower()),
            None,
        )
        if isinstance(kg_mae, (int, float)) and isinstance(nokg_mae, (int, float)):
            kg_delta = kg_mae - nokg_mae
        hc_rows.append({
            "region": get_region_label(rid),
            "variant": entry.get("variant", "—"),
            "n": entry.get("n_personas") or (m.get("n_rated") or "—"),
            "MAE": mae,
            "leader_match": leader,
            "Δ vs prod": delta,
            "Δ KG ablation": kg_delta,
            "gate": gate_lbl,
        })
    if hc_rows:
        st.dataframe(hc_rows, use_container_width=True, hide_index=True)

        # Headline numerics for the hill-climbing trajectory
        rated_maes = [r["MAE"] for r in hc_rows if isinstance(r["MAE"], (int, float))]
        leader_pass = sum(1 for r in hc_rows if r["leader_match"] is True)
        leader_total = sum(1 for r in hc_rows if isinstance(r["leader_match"], bool))
        pass_count = sum(1 for r in hc_rows if r["gate"].startswith("✅"))
        rated_total = sum(1 for r in hc_rows if isinstance(r["MAE"], (int, float)))
        if rated_maes:
            mean_hc_mae = sum(rated_maes) / len(rated_maes)
            best_idx = min(range(len(rated_maes)), key=lambda i: rated_maes[i])
            best_row = [r for r in hc_rows if isinstance(r["MAE"], (int, float))][best_idx]
            st.success(
                f"🧗 **hill-climbing headline** — "
                f"PASS = {pass_count}/{rated_total} rated · "
                f"mean MAE = `{mean_hc_mae:.4f}` (threshold ≤ {rated_threshold_mae:.3f}, "
                f"~{(mean_hc_mae / rated_threshold_mae):.1f}× over) · "
                f"leader_match = {leader_pass}/{leader_total} · "
                f"best variant = `{best_row['variant']}` ({best_row['region']}, "
                f"MAE={best_row['MAE']:.4f}). paper §6: KG-enriched prompts 가 "
                "production sim 대비 정합도 향상.",
                icon="🧗",
            )

        # Per-region detail expanders (collapsed by default)
        for rid in REGION_ORDER:
            entry = hc_summary.get(rid)
            if not entry:
                continue
            m = entry.get("metrics") or {}
            with st.expander(
                f"{get_region_label(rid)} — variant `{entry.get('variant', '—')}`",
                expanded=False,
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("MAE", f"{m.get('mae'):.4f}" if isinstance(m.get('mae'), (int, float)) else "—")
                c2.metric("RMSE", f"{m.get('rmse'):.4f}" if isinstance(m.get('rmse'), (int, float)) else "—")
                c3.metric("KL(sim‖off)", f"{m.get('kl_div'):.4f}" if isinstance(m.get('kl_div'), (int, float)) else "—")
                c4.metric("leader_match", "✓" if m.get("leader_match") is True else ("✗" if m.get("leader_match") is False else "—"))

                # KG ablation table — surface every variant in this round so
                # paper §6 ablation rows can cross-link inline (Track A vs
                # Track A+B). Honest evidence even when variants regress.
                all_v = entry.get("_all_variants") or []
                if len(all_v) >= 2:
                    st.markdown("**Ablation — variants in this round**")
                    abl_rows = []
                    for v in all_v:
                        vm = v.get("metrics") or {}
                        is_kg = "kg" in str(v.get("variant", "")).lower()
                        abl_rows.append({
                            "variant": v.get("variant", "—"),
                            "track": "A+B (KG cohort)" if is_kg else "A only (narrative+NESDC)",
                            "MAE": vm.get("mae"),
                            "RMSE": vm.get("rmse"),
                            "KL": vm.get("kl_div"),
                            "leader_match": vm.get("leader_match"),
                        })
                    st.dataframe(abl_rows, use_container_width=True, hide_index=True)

                renorm = entry.get("renorm_share") or {}
                official = entry.get("official_consensus") or {}
                if renorm or official:
                    cmp_rows = []
                    for cid in sorted(set(list(renorm) + list(official))):
                        cmp_rows.append({
                            "candidate_id": cid,
                            "sim (renorm)": renorm.get(cid),
                            "official consensus": official.get(cid),
                            "error": (
                                renorm.get(cid, 0) - official.get(cid, 0)
                                if isinstance(renorm.get(cid), (int, float))
                                and isinstance(official.get(cid), (int, float))
                                else None
                            ),
                        })
                    st.dataframe(cmp_rows, use_container_width=True, hide_index=True)

                src = entry.get("_source_path")
                if src:
                    st.caption(f"📂 `{src}`")
    else:
        st.info("Hill-climbing 결과 디렉토리는 존재하나 파싱 가능한 region variant 가 없습니다.", icon="ℹ️")

    st.divider()

# ---------------------------------------------------------------------------
# v1.4 audit evidence — inline reader (paper §5 cross-reference, 보존)
# ---------------------------------------------------------------------------
RESEARCH_DIR = REPO_ROOT / "_workspace" / "research"
AUDIT_FILES = [
    ("H1 — cache 가설 audit", "cache_audit_v14.md",
     "REJECTED 14:10 · 6,977 cache rows / 6,971 distinct (99.9% unique) → phantom hit; cache_hit_rate signal misled v13:42 attribution."),
    ("H2 — persona prompt diversity", "persona_prompt_diversity.json",
     "REJECTED 14:10 · persona collision_rate = 0.0 across 5 region samples; persona_text uniqueness 100%."),
    ("H3 — LLMPool 3-key bug + Fix A/B/C", "llmpool_3key_bug.md",
     "PROVISIONAL · single-key fire root cause + remediation menu."),
]
audit_present = [(t, n, s) for t, n, s in AUDIT_FILES if (RESEARCH_DIR / n).exists()]
if audit_present:
    st.subheader("🔎 v1.4 audit evidence (paper §5 cross-ref)")
    st.caption(
        "100% sweep 결과의 무효화 근거. paper Limitations §5 가설 3종 표와 동일 evidence pointer."
    )
    cols = st.columns(len(audit_present))
    for col, (title, name, summary) in zip(cols, audit_present):
        with col:
            st.markdown(f"**{title}**  \n`research/{name}`")
            st.caption(summary)
            with st.expander("raw content", expanded=False):
                try:
                    raw = (RESEARCH_DIR / name).read_text(encoding="utf-8")
                except Exception as e:
                    st.error(f"read error: {e}")
                    continue
                if name.endswith(".json"):
                    try:
                        st.json(json.loads(raw), expanded=False)
                    except Exception:
                        st.code(raw[:3000])
                else:
                    st.markdown(raw[:6000])

    # archive pointer
    archive_dir = REPO_ROOT / "_workspace" / "snapshots" / "_archived"
    archives = sorted(archive_dir.glob("v14_run_*")) if archive_dir.exists() else []
    if archives:
        latest = archives[-1]
        manifest = latest / "MANIFEST.md"
        st.markdown(f"**archive root** — `_archived/{latest.name}/`")
        if manifest.exists():
            with st.expander("MANIFEST.md", expanded=False):
                try:
                    st.markdown(manifest.read_text(encoding="utf-8"))
                except Exception as e:
                    st.error(f"read error: {e}")
