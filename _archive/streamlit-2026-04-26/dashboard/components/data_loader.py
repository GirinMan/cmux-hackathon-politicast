"""Data loading utilities for the PolitiKAST dashboard.

Strategy:
1. Try real results from `_workspace/snapshots/results_index.json`.
2. Fall back to bundled placeholder JSON in `ui/dashboard/_placeholder/`.

Caching: 5s TTL — fast enough for live polling, slow enough not to thrash.
The dashboard never crashes due to missing files; it always shows *something*.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_DIR = REPO_ROOT / "_workspace" / "snapshots"
RESULTS_INDEX = SNAPSHOT_DIR / "results_index.json"
KG_PRIMARY = SNAPSHOT_DIR / "kg_export.json"
CONTRACTS_DIR = REPO_ROOT / "_workspace" / "contracts"
PLACEHOLDER_DIR = Path(__file__).resolve().parents[1] / "_placeholder"
VALIDATION_DIR = SNAPSHOT_DIR / "validation"
HISTORICAL_DIR = REPO_ROOT / "_workspace" / "data" / "scenarios" / "historical_outcomes"

# Default Validation Gate thresholds (paper redesign §rolling-origin gate).
# Mirrors `8_Validation_Gate.py` proposed criteria; can be overridden by a
# `_workspace/contracts/validation_schema.json` contract once Codex publishes one.
DEFAULT_VALIDATION_THRESHOLDS: dict[str, float] = {
    "mae_max": 0.05,            # ≤ 5pp mean absolute error vs poll consensus
    "rmse_max": 0.07,            # ≤ 7pp RMSE
    "margin_error_max": 0.05,    # ≤ 5pp on contest margin
    "leader_match_required": 1.0,  # leader must match
    "backtest_rmse_max": 0.05,
    "backtest_lead_pp_max": 0.05,
}

# Region 메타 SoT — `_workspace/contracts/data_paths.json`. 컨트랙트 부재/손상 시
# 보수적 fallback 사용 (대시보드는 어떤 경우에도 화면을 살려야 한다).
_REGION_FALLBACK_ORDER = [
    "seoul_mayor",
    "gwangju_mayor",
    "daegu_mayor",
    "busan_buk_gap",
    "daegu_dalseo_gap",
]
_REGION_FALLBACK_LABELS = {
    "seoul_mayor": "서울시장",
    "gwangju_mayor": "광주시장",
    "daegu_mayor": "대구시장",
    "busan_buk_gap": "부산 북구 갑",
    "daegu_dalseo_gap": "대구 달서구 갑",
}


def _load_region_meta() -> tuple[list[str], dict[str, str]]:
    contract_path = CONTRACTS_DIR / "data_paths.json"
    try:
        with contract_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        regions = data.get("regions") or []
        order = [r["id"] for r in regions if isinstance(r, dict) and r.get("id")]
        labels = {
            r["id"]: r.get("label") or r["id"]
            for r in regions
            if isinstance(r, dict) and r.get("id")
        }
        if order:
            return order, labels
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        pass
    return list(_REGION_FALLBACK_ORDER), dict(_REGION_FALLBACK_LABELS)


REGION_ORDER, REGION_LABELS = _load_region_meta()

# Regions to highlight on the landing page (마이크로 시연 포인트).
HIGHLIGHT_REGIONS = ["busan_buk_gap"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_read_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError):
        # Don't blow up the page; let caller decide how to surface.
        return None


def _resolve_result_path(rel_path: str) -> Path:
    """Resolve a result path that may be relative to repo root."""
    p = Path(rel_path)
    if not p.is_absolute():
        # Try repo root, then placeholder dir
        candidate = REPO_ROOT / p
        if candidate.exists():
            return candidate
        candidate = Path(rel_path)
        if candidate.exists():
            return candidate
        return REPO_ROOT / p  # may not exist; caller checks
    return p


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _normalize_index(raw: Any) -> dict[str, Any] | None:
    """Accept both `[...]` and `{"results": [...]}` shapes; return canonical dict."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return {"results": raw}
    if isinstance(raw, dict):
        # Common keys we accept
        if "results" in raw and isinstance(raw["results"], list):
            return raw
        # Some sim writers may dump a single result object — wrap it.
        if "scenario_id" in raw and "region_id" in raw:
            return {"results": [raw]}
    return None


@st.cache_data(ttl=5, show_spinner=False)
def load_results_index() -> tuple[dict[str, Any], bool]:
    """Return (index_dict, is_placeholder).

    Tries `_workspace/snapshots/results_index.json` first; falls back to bundled
    placeholder so screen always renders. Accepts both list-shaped and
    `{"results": [...]}`-shaped indices.
    """
    real = _normalize_index(_safe_read_json(RESULTS_INDEX))
    if real and real.get("results"):
        return real, False
    placeholder = _normalize_index(_safe_read_json(PLACEHOLDER_DIR / "results_index.json")) or {"results": []}
    return placeholder, True


@st.cache_data(ttl=5, show_spinner=False)
def load_all_results() -> tuple[dict[str, dict[str, Any]], bool]:
    """Return ({region_id: result_dict}, is_any_real_loaded_flag).

    Returns the freshest entry per region_id (by `wrote_at`, falling back to
    file mtime). Missing regions are filled from bundled placeholder JSON so
    the dashboard *always* renders all 5 regions.

    Second tuple element is `is_placeholder` — True iff zero real results
    were loaded.
    """
    index, _placeholder_index = load_results_index()
    entries = index.get("results", [])

    # Pick the best entry per region.
    # Priority: (1) live (is_mock=false, is_archive=false) over mock/archive,
    # (2) within same tier, freshest wrote_at wins.
    # This prevents a later-written mock smoke from masking an earlier real
    # live run for the same region.
    def _tier(e: dict[str, Any]) -> int:
        # 0 = live, 1 = archive (v1.1 early validation), 2 = mock
        if e.get("is_mock"):
            return 2
        if e.get("is_archive") or (e.get("meta") or {}).get("is_archive"):
            return 1
        return 0

    def _is_better(cand: dict[str, Any], prev: dict[str, Any]) -> bool:
        ct, pt = _tier(cand), _tier(prev)
        if ct != pt:
            return ct < pt  # lower tier wins (live > archive > mock)
        return (cand.get("wrote_at") or "") > (prev.get("wrote_at") or "")

    best: dict[str, dict[str, Any]] = {}
    for entry in entries:
        rid = entry.get("region_id")
        if not rid:
            continue
        prev = best.get(rid)
        if prev is None or _is_better(entry, prev):
            best[rid] = entry

    out: dict[str, dict[str, Any]] = {}
    real_loaded = 0
    for rid, entry in best.items():
        # Try canonical path, then mirror_path (sim-engineer convenience copy).
        candidates_paths = [
            entry.get("path"),
            entry.get("mirror_path"),
            f"_workspace/snapshots/{rid}_result.json",  # mirror naming convention
        ]
        data = None
        for rel_path in candidates_paths:
            if not rel_path:
                continue
            path = _resolve_result_path(rel_path)
            data = _safe_read_json(path)
            if data is not None:
                break
        if data is not None:
            # Propagate index-level signals onto the result dict if absent.
            if "is_mock" in entry and "is_mock" not in data:
                data["is_mock"] = entry["is_mock"]
            out[rid] = data
            if not data.get("_placeholder"):
                real_loaded += 1

    # Fill missing regions from placeholder JSON
    for rid in REGION_ORDER:
        if rid in out:
            continue
        fallback = PLACEHOLDER_DIR / f"{rid}.json"
        data = _safe_read_json(fallback)
        if data is not None:
            out[rid] = data

    is_placeholder = real_loaded == 0
    return out, is_placeholder


@st.cache_data(ttl=5, show_spinner=False)
def list_kg_snapshots() -> list[dict[str, Any]]:
    """Return metadata about every `kg_*.json` snapshot on disk.

    Each entry: `{path, region_id, timestep, mtime, scenario_id}`.
    Names like `kg_seoul_mayor_t2.json` are parsed for region+timestep.
    """
    out: list[dict[str, Any]] = []
    if not SNAPSHOT_DIR.exists():
        return out
    for p in SNAPSHOT_DIR.glob("kg_*.json"):
        # Read just enough to get region/timestep
        data = _safe_read_json(p) or {}
        region_id = data.get("region_id")
        timestep = data.get("timestep")
        # Name fallback parsing: kg_<region>_t<N>.json
        if region_id is None or timestep is None:
            stem = p.stem  # kg_seoul_mayor_t2
            parts = stem.split("_")
            if parts and parts[0] == "kg":
                # last token like "t2"
                last = parts[-1]
                if last.startswith("t") and last[1:].isdigit():
                    timestep = timestep if timestep is not None else int(last[1:])
                    region_id = region_id or "_".join(parts[1:-1]) or None
        out.append({
            "path": str(p),
            "region_id": region_id,
            "timestep": timestep,
            "scenario_id": data.get("scenario_id"),
            "mtime": p.stat().st_mtime,
            "is_placeholder": bool(data.get("_placeholder")),
        })
    return out


@st.cache_data(ttl=5, show_spinner=False)
def load_kg(region_id: str | None = None, timestep: int | None = None) -> tuple[dict[str, Any], bool]:
    """Return (kg_dict, is_placeholder).

    Resolution order:
      1. Match `region_id` + `timestep` (largest timestep ≤ requested if requested).
      2. Match `region_id` only — newest mtime.
      3. Any `kg_*.json` — newest mtime.
      4. `kg_export.json` (legacy single-file).
      5. Bundled placeholder.
    """
    snaps = list_kg_snapshots()
    real = [s for s in snaps if not s["is_placeholder"]]

    def _try(pred):
        cands = [s for s in real if pred(s)]
        if not cands:
            return None
        cands.sort(key=lambda s: (s.get("timestep") or -1, s["mtime"]), reverse=True)
        data = _safe_read_json(Path(cands[0]["path"]))
        return data

    # 1. region + timestep
    if region_id is not None and timestep is not None:
        chosen = _try(lambda s: s["region_id"] == region_id and (s["timestep"] is None or s["timestep"] <= timestep))
        if chosen:
            return chosen, False
    # 2. region only
    if region_id is not None:
        chosen = _try(lambda s: s["region_id"] == region_id)
        if chosen:
            return chosen, False
    # 3. anything real
    chosen = _try(lambda s: True)
    if chosen:
        return chosen, False

    # 4. legacy single export
    legacy = _safe_read_json(KG_PRIMARY)
    if legacy:
        return legacy, bool(legacy.get("_placeholder"))

    # 5. placeholder
    placeholder = _safe_read_json(PLACEHOLDER_DIR / "kg_export.json") or {"nodes": [], "edges": []}
    return placeholder, True


@st.cache_data(ttl=30, show_spinner=False)
def load_contracts() -> dict[str, Any]:
    """Return merged contracts dict — never raises."""
    out: dict[str, Any] = {}
    for name in ("data_paths", "api_contract", "result_schema", "llm_strategy"):
        data = _safe_read_json(CONTRACTS_DIR / f"{name}.json")
        if data is not None:
            out[name] = data
    return out


@st.cache_data(ttl=30, show_spinner=False)
def load_policy() -> dict[str, Any] | None:
    return _safe_read_json(REPO_ROOT / "_workspace" / "checkpoints" / "policy.json")


# ---------------------------------------------------------------------------
# Cost guard alerts — append to JSONL log when a provider crosses a
# threshold ratio (70% / 90% / 100%) for the first time. State file
# tracks the last-emitted level per provider so we don't spam alerts on
# every 5s refresh.
# ---------------------------------------------------------------------------
_COST_ALERT_LOG = REPO_ROOT / "_workspace" / "checkpoints" / "cost_alerts.log"
_COST_ALERT_STATE = REPO_ROOT / "_workspace" / "checkpoints" / "cost_alerts_state.json"
_COST_ALERT_LEVELS = (("warn70", 0.70), ("warn90", 0.90), ("breach100", 1.00))


def emit_cost_alerts(
    cost_by_provider: dict[str, float],
    thresholds_by_provider: dict[str, float],
    *,
    source: str = "dashboard",
) -> list[dict[str, Any]]:
    """Append a JSONL alert when a provider first crosses 70/90/100% of its
    cost threshold. Returns the list of alerts emitted on this call (typically
    empty). Safe to call on every refresh — state file dedupes.
    """
    if not cost_by_provider or not thresholds_by_provider:
        return []
    state: dict[str, str] = {}
    if _COST_ALERT_STATE.exists():
        try:
            state = json.loads(_COST_ALERT_STATE.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                state = {}
        except Exception:
            state = {}

    emitted: list[dict[str, Any]] = []
    from datetime import datetime, timezone

    for prov, thr in thresholds_by_provider.items():
        if not isinstance(thr, (int, float)) or thr <= 0:
            continue
        spent = float(cost_by_provider.get(prov, 0.0))
        ratio = spent / float(thr)
        last_level = state.get(prov, "")
        last_idx = -1
        for i, (lvl, _) in enumerate(_COST_ALERT_LEVELS):
            if lvl == last_level:
                last_idx = i
                break
        for i, (lvl, threshold_ratio) in enumerate(_COST_ALERT_LEVELS):
            if i <= last_idx:
                continue
            if ratio >= threshold_ratio:
                event = {
                    "ts": datetime.now(tz=timezone.utc).isoformat(),
                    "level": lvl,
                    "provider": prov,
                    "spent_usd": round(spent, 6),
                    "threshold_usd": float(thr),
                    "ratio": round(ratio, 4),
                    "source": source,
                }
                emitted.append(event)
                state[prov] = lvl

    if emitted:
        try:
            _COST_ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
            with _COST_ALERT_LOG.open("a", encoding="utf-8") as fh:
                for ev in emitted:
                    fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
            _COST_ALERT_STATE.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            # Never let alert IO crash the dashboard — logs are best-effort.
            pass
    return emitted


@st.cache_data(ttl=30, show_spinner=False)
def get_llm_info() -> dict[str, str | None]:
    """Resolve current LLM provider/model for build provenance.

    Priority:
      1. `LITELLM_MODEL` env var (live runtime)
      2. `llm_strategy.json` → `primary_path.default_model`
      3. `policy.json` → `provider`/`model` (legacy keys, if present)
    Returns: `{provider, model, decision, source}`
    """
    contracts = load_contracts()
    strat = contracts.get("llm_strategy") or {}
    policy = load_policy() or {}

    model = os.environ.get("LITELLM_MODEL")
    source = "env LITELLM_MODEL"
    if not model:
        model = (strat.get("primary_path") or {}).get("default_model")
        source = "llm_strategy.primary_path.default_model"
    if not model:
        model = policy.get("model")
        source = "policy.json"

    # Provider from prefix; fall back to policy.provider
    provider: str | None = None
    if isinstance(model, str) and "/" in model:
        provider = model.split("/", 1)[0]
    elif isinstance(model, str) and model.startswith(("gpt-", "o1", "o3", "o4")):
        provider = "openai"
    elif isinstance(model, str) and model.startswith("claude"):
        provider = "anthropic"
    if not provider:
        provider = policy.get("provider") or "unknown"

    return {
        "provider": provider,
        "model": model or "unknown",
        "decision": strat.get("decision"),
        "source": source,
    }


def get_region_label(region_id: str) -> str:
    return REGION_LABELS.get(region_id, region_id)


# ---------------------------------------------------------------------------
# Hill-climbing trajectory loader (paper §6 evidence — narrative augment)
# ---------------------------------------------------------------------------
HILL_CLIMBING_DIR = REPO_ROOT / "_workspace" / "snapshots" / "hill_climbing"


@st.cache_data(ttl=10, show_spinner=False)
def load_hill_climbing_summary() -> dict[str, dict[str, Any]]:
    """Return `{region_id: best_variant_dict}` from the latest available
    hill-climbing round (prefer R6 partial Track A; fall back to R5 / R3a).

    Each value carries: `variant`, `metrics{mae,rmse,leader_match,kl_div,
    n_rated}`, `renorm_share`, `official_consensus`, `_source_path`.
    Used by the Validation Gate "Hill-climbing trajectory" card to surface
    KG-narrative-enrichment evidence (paper §6).
    """
    if not HILL_CLIMBING_DIR.exists():
        return {}

    # Round preference: R6_full > R6_partial > R5 > R4 > R3a > R3b.
    # team-lead 16:09 정합: R6_full 박제 시 자동 surface 우선.
    candidate_roots = [
        HILL_CLIMBING_DIR / "R6_full",
        HILL_CLIMBING_DIR / "R6_partial_trackA_only",
        HILL_CLIMBING_DIR / "R5",
        HILL_CLIMBING_DIR / "R4",
        HILL_CLIMBING_DIR / "R3a",
        HILL_CLIMBING_DIR / "R3b",
    ]

    def _pick_best_variant(sub: Path) -> dict[str, Any] | None:
        """Among variant JSONs in `sub/`, pick the one with the lowest MAE
        (ties broken by alphabetical name). If all variants have None MAE,
        return the alphabetically last one as the canonical unavailable
        evidence.

        Also stamps `_all_variants: [{variant, metrics, renorm_share,
        _source_path}, ...]` so the UI can render a Track A vs Track A+B
        ablation comparison (paper §6 cross-ref).
        """
        variant_files = sorted(sub.glob("R*_v*.json"))
        if not variant_files:
            return None
        best_payload: dict[str, Any] | None = None
        best_path: Path | None = None
        best_mae: float | None = None
        fallback_payload: dict[str, Any] | None = None
        fallback_path: Path | None = None
        all_variants: list[dict[str, Any]] = []
        for vp in variant_files:
            data = _safe_read_json(vp)
            if not isinstance(data, dict):
                continue
            mae = (data.get("metrics") or {}).get("mae")
            fallback_payload, fallback_path = data, vp
            if isinstance(mae, (int, float)):
                if best_mae is None or mae < best_mae:
                    best_mae = float(mae)
                    best_payload = data
                    best_path = vp
            all_variants.append({
                "variant": data.get("variant", vp.stem),
                "metrics": data.get("metrics") or {},
                "renorm_share": data.get("renorm_share") or {},
                "official_consensus": data.get("official_consensus") or {},
                "_source_path": str(vp.relative_to(REPO_ROOT)),
            })
        chosen_payload = best_payload if best_payload is not None else fallback_payload
        chosen_path = best_path if best_path is not None else fallback_path
        if chosen_payload is None or chosen_path is None:
            return None
        out = dict(chosen_payload)
        out["_source_path"] = str(chosen_path.relative_to(REPO_ROOT))
        out["_n_variants"] = len(variant_files)
        out["_all_variants"] = all_variants
        return out

    out: dict[str, dict[str, Any]] = {}
    chosen_root: Path | None = None
    for root in candidate_roots:
        if not root.exists():
            continue
        chosen_root = root
        for sub in sorted(root.iterdir()):
            if not sub.is_dir():
                continue
            rid = sub.name
            if rid not in REGION_ORDER:
                continue
            entry = _pick_best_variant(sub)
            if entry is None:
                continue
            entry["_round"] = root.name
            out[rid] = entry
        if out:
            break  # use first non-empty round
    if chosen_root:
        for v in out.values():
            v["_round_root"] = str(chosen_root.relative_to(REPO_ROOT))
    return out


# ---------------------------------------------------------------------------
# Validation Gate loaders (V9 — Phase B/C)
# ---------------------------------------------------------------------------
def _infer_region_from_filename(stem: str) -> str | None:
    """rolling_seoul_mayor_2026-04-26 → seoul_mayor."""
    for rid in REGION_ORDER:
        if rid in stem:
            return rid
    return None


@st.cache_data(ttl=5, show_spinner=False)
def load_validation_thresholds() -> dict[str, float]:
    """Resolve Validation Gate thresholds. Prefer contract if present."""
    contract = _safe_read_json(CONTRACTS_DIR / "validation_schema.json") or {}
    thresholds = contract.get("thresholds") or {}
    out = dict(DEFAULT_VALIDATION_THRESHOLDS)
    for k, v in thresholds.items():
        if isinstance(v, (int, float)):
            out[k] = float(v)
    return out


@st.cache_data(ttl=5, show_spinner=False)
def list_validation_files(kind: str) -> list[Path]:
    """kind in {"rolling", "backtest"} — return sorted Paths under
    `_workspace/snapshots/validation/`. Newest mtime last.
    """
    if not VALIDATION_DIR.exists():
        return []
    paths = list(VALIDATION_DIR.glob(f"{kind}_*.json"))
    paths.sort(key=lambda p: p.stat().st_mtime)
    return paths


def extract_validation_block(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Pull `official_poll_validation` from a result dict.

    Sim writes the block under `meta.official_poll_validation` (V6/V11 in the
    election_env._inject_validation_metrics path). For forward compatibility
    the gate also accepts a top-level `official_poll_validation` key.
    """
    if not isinstance(payload, dict):
        return None
    top = payload.get("official_poll_validation")
    if isinstance(top, dict):
        return top
    meta = payload.get("meta") or {}
    if isinstance(meta, dict):
        nested = meta.get("official_poll_validation")
        if isinstance(nested, dict):
            return nested
    return None


def validation_target_series(payload: dict[str, Any]) -> str | None:
    """Return the validation target series, if present."""
    opv = extract_validation_block(payload) or {}
    target = opv.get("target_series")
    return str(target) if target is not None else None


def validation_cache_enabled(payload: dict[str, Any]) -> bool | None:
    """Return whether the sim run had the LLM cache enabled, if recorded."""
    if not isinstance(payload, dict):
        return None
    meta = payload.get("meta") or {}
    if isinstance(meta, dict) and isinstance(meta.get("llm_cache_enabled"), bool):
        return bool(meta["llm_cache_enabled"])
    if isinstance(payload.get("llm_cache_enabled"), bool):
        return bool(payload["llm_cache_enabled"])
    return None


def validation_cache_hits(payload: dict[str, Any]) -> int | None:
    """Return pool cache hits for provenance display and result selection."""
    if not isinstance(payload, dict):
        return None
    meta = payload.get("meta") or {}
    if not isinstance(meta, dict):
        return None
    pool_stats = meta.get("pool_stats") or {}
    if not isinstance(pool_stats, dict):
        return None
    hits = pool_stats.get("cache_hits")
    if isinstance(hits, bool):
        return None
    if isinstance(hits, int):
        return hits
    return None


def validation_run_quality(payload: dict[str, Any]) -> str:
    """Human-readable provenance label for the Validation Gate."""
    target = validation_target_series(payload)
    if target == "missing":
        return "unavailable"
    if target == "prediction_only":
        return "prediction-only"
    if target == "poll_consensus_daily":
        cache_enabled = validation_cache_enabled(payload)
        cache_hits = validation_cache_hits(payload)
        if cache_enabled is False and cache_hits == 0:
            return "clean no-cache official poll"
        if cache_hits == 0 and cache_enabled is not True:
            return "clean official poll"
        if isinstance(cache_hits, int) and cache_hits > 0:
            return f"cached official poll ({cache_hits} hits)"
        return "official poll"
    if target:
        return "fallback validation"
    return "unknown"


def validation_is_unavailable(payload: dict[str, Any]) -> bool:
    """True when the result explicitly declares no official-poll target."""
    return validation_target_series(payload) in {"missing", "prediction_only"}


def _validation_selection_key(payload: dict[str, Any], mtime: float, kind: str) -> tuple[int, int, int, int, float]:
    """Prefer clean official-poll validation over stale fallback/missing slots.

    Current rolling validation may be present both as dedicated rolling files
    and as regular result files. For a region, pick the strongest validation
    evidence first, then newest mtime inside the same evidence class.
    """
    if kind != "rolling":
        return (0, 0, 0, 0, mtime)

    opv = extract_validation_block(payload) or {}
    metrics = opv.get("metrics") if isinstance(opv.get("metrics"), dict) else {}
    target = validation_target_series(payload)
    quality = validation_run_quality(payload)
    cache_hits = validation_cache_hits(payload)

    if target == "poll_consensus_daily":
        target_score = 4
    elif target and target != "missing":
        target_score = 2
    elif target in {"missing", "prediction_only"}:
        target_score = 1
    else:
        target_score = 0

    clean_score = 2 if quality.startswith("clean") else 0
    metric_score = 1 if any(v is not None for v in metrics.values()) else 0
    cache_score = 0
    if cache_hits is None:
        cache_score = -1
    elif cache_hits > 0:
        cache_score = -cache_hits

    return (target_score, clean_score, metric_score, cache_score, mtime)


@st.cache_data(ttl=5, show_spinner=False)
def load_validation_results(kind: str = "rolling") -> dict[str, dict[str, Any]]:
    """Return {region_id: result_dict} — newest per region.

    Resolution order (per region):
      1. `_workspace/snapshots/validation/{kind}_*.json` (canonical V9 slot —
         dedicated rolling-origin / backtest snapshots).
      2. Fallback for kind=="rolling": regular result files in
         `_workspace/snapshots/results/*.json` that already carry an
         `official_poll_validation` block via sim's
         `_inject_validation_metrics`. Surfaces V8 fire results immediately
         even before sim duplicates them into the validation slot.

    Each surfaced dict gets `_source_path` and `_mtime` for the UI to display.
    """
    out: dict[str, dict[str, Any]] = {}
    priorities: dict[str, tuple[int, int, int, int, float]] = {}

    def _consider(p: Path, data: dict[str, Any]) -> None:
        rid = data.get("region_id") or _infer_region_from_filename(p.stem)
        if not rid:
            return
        if extract_validation_block(data) is None:
            # For canonical kind dir we still surface placeholders, but for
            # the results-fallback we filter to only files that actually
            # carry the validation block.
            return
        data = dict(data)  # avoid mutating cache value
        data.setdefault("_source_path", str(p.relative_to(REPO_ROOT)))
        data.setdefault("_mtime", p.stat().st_mtime)
        priority = _validation_selection_key(data, data["_mtime"], kind)
        prev = out.get(rid)
        if prev is None or priority > priorities.get(rid, (0, 0, 0, 0, 0.0)):
            out[rid] = data
            priorities[rid] = priority

    # 1. Canonical validation snapshots
    for p in list_validation_files(kind):
        data = _safe_read_json(p)
        if isinstance(data, dict):
            _consider(p, data)

    # 2. Fallback: regular results with embedded validation block
    if kind == "rolling":
        results_dir = SNAPSHOT_DIR / "results"
        if results_dir.exists():
            for p in results_dir.glob("*.json"):
                data = _safe_read_json(p)
                if not isinstance(data, dict):
                    continue
                if data.get("is_mock") or data.get("_placeholder"):
                    continue
                _consider(p, data)
    return out


@st.cache_data(ttl=30, show_spinner=False)
def load_historical_outcomes() -> dict[str, dict[str, Any]]:
    """Return {region_id: outcome_dict} from
    `_workspace/data/scenarios/historical_outcomes/*.json`. Used for
    past-election backtest cards (winner / lead_pp baseline)."""
    out: dict[str, dict[str, Any]] = {}
    if not HISTORICAL_DIR.exists():
        return out
    for p in HISTORICAL_DIR.glob("*.json"):
        data = _safe_read_json(p)
        if not isinstance(data, dict):
            continue
        rid = data.get("region_id") or p.stem
        out[rid] = data
    return out


def evaluate_validation_metrics(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, dict[str, Any]]:
    """Per-criterion pass/fail evaluation.

    Returns mapping `criterion → {value, threshold, pass, label}` so the UI
    can render the threshold table consistently across rolling and backtest
    result dicts.
    """
    out: dict[str, dict[str, Any]] = {}

    def _row(label: str, value: Any, thr: float, comparator: str) -> dict[str, Any]:
        ok: bool | None = None
        if isinstance(value, (int, float)):
            if comparator == "<=":
                ok = float(value) <= float(thr)
            elif comparator == ">=":
                ok = float(value) >= float(thr)
            elif comparator == "==":
                ok = float(value) == float(thr)
        elif isinstance(value, bool) and comparator == "==":
            ok = bool(value) == bool(thr)
        return {
            "label": label,
            "value": value,
            "threshold": thr,
            "comparator": comparator,
            "pass": ok,
        }

    mae = metrics.get("mae")
    rmse = metrics.get("rmse")
    me = metrics.get("margin_error")
    lm = metrics.get("leader_match")

    out["mae"] = _row("MAE (vote share)", mae, thresholds.get("mae_max", 0.05), "<=")
    out["rmse"] = _row("RMSE", rmse, thresholds.get("rmse_max", 0.07), "<=")
    out["margin_error"] = _row(
        "Margin error", me, thresholds.get("margin_error_max", 0.05), "<="
    )
    if isinstance(lm, bool):
        out["leader_match"] = {
            "label": "Leader match",
            "value": lm,
            "threshold": True,
            "comparator": "==",
            "pass": lm is True,
        }
    else:
        out["leader_match"] = {
            "label": "Leader match",
            "value": lm,
            "threshold": True,
            "comparator": "==",
            "pass": None,
        }
    return out


def gate_overall_pass(rows: dict[str, dict[str, Any]]) -> bool | None:
    """Aggregate pass: all known criteria must pass. None if any is unknown."""
    statuses = [r["pass"] for r in rows.values()]
    if any(s is None for s in statuses):
        return None
    return all(bool(s) for s in statuses)


def is_cache_artifact(result: dict[str, Any]) -> bool:
    """Detect a v1.4-style cache-artifact result — either via explicit flag
    (`meta.is_cache_artifact` or `meta.policy_version == 'v1.4_invalid'`) or
    heuristically (cache_hit_rate ≥ 0.9 + actual_keys_used == 1 + at least one
    candidate at vote_share ≥ 99.9%).

    Per policy v1.4 INVALIDATION (13:42): such results are kept for paper
    Limitations but excluded from the headline live count and outcome charts.
    """
    meta = result.get("meta") or {}
    if meta.get("is_cache_artifact") or result.get("is_cache_artifact"):
        return True
    if meta.get("policy_version") in ("v1.4_invalid", "1.4_invalid"):
        return True
    ps = meta.get("pool_stats") or {}
    chr_ = ps.get("cache_hit_rate")
    aku = meta.get("actual_keys_used")
    fo = result.get("final_outcome") or {}
    shares = fo.get("vote_share_by_candidate") or fo.get("vote_shares")
    sweep = False
    # 0.98 catches near-sweeps (e.g. seoul 0.995). Below this, vote split is
    # plausible.
    if isinstance(shares, dict):
        vals = [v for v in shares.values() if isinstance(v, (int, float))]
        if vals and max(vals) >= 0.98:
            sweep = True
    elif isinstance(fo.get("vote_share"), (int, float)) and fo["vote_share"] >= 0.98:
        sweep = True
    # Heuristic per policy v1.4 INVALIDATION (13:42) — refined 14:10:
    # root cause is **Gemini lite-tier model determinism** producing 100%
    # sweep votes when persona context aligns with regional ideology.
    # Cache hypothesis was withdrawn (cache rows 99.9% unique → phantom
    # hit, persona collision_rate = 0.0; evidence:
    # `_workspace/research/cache_audit_v14.md`). The signal we still trust
    # for classification is single-pool-key (capacity not met) + sweep —
    # those two together indicate v1.4-class invalidity regardless of root
    # cause naming.
    if isinstance(aku, int) and aku == 1 and sweep:
        return True
    return False


def result_status_badge(result: dict[str, Any]) -> str:
    """Return a short markdown badge for a result's provenance.

    Order of precedence:
      • placeholder (bundled JSON)  → 🛰️ placeholder
      • is_mock (sim-engineer dry-run)  → 🧪 DRY RUN (mock)
      • is_archive (v1.1 early validation, archived under _archived/)  → 📦 v1.1 archive
      • is_cache_artifact (v1.4 model-determinism — Gemini lite-tier alignment; H1 fallback REJECTED 14:05; cache hypothesis withdrawn 14:10 — `research/cache_audit_v14.md`)  → 🚨 v1.4 model-determinism artifact (lite-tier alignment)
      • else  → ✅ live
    """
    if result.get("_placeholder"):
        return "🛰️ placeholder"
    if result.get("is_mock"):
        return "🧪 DRY RUN (mock)"
    if result.get("is_archive") or (result.get("meta") or {}).get("is_archive"):
        return "📦 v1.1 archive (early validation)"
    if is_cache_artifact(result):
        return "🚨 v1.4 model-determinism artifact (lite-tier alignment)"
    return "✅ live"


def is_real_live(result: dict[str, Any]) -> bool:
    """True iff result is a real LLM run AND not a v1.4 cache artifact.

    Cache-artifact results are kept on disk for paper Limitations but are
    excluded from the headline live count, throughput aggregation, and
    outcome charts so the demo doesn't surface invalid quantitative claims.
    """
    if result.get("_placeholder") or result.get("is_mock"):
        return False
    if result.get("is_archive") or (result.get("meta") or {}).get("is_archive"):
        return False
    if is_cache_artifact(result):
        return False
    return True


def selected_regions(scope: str, all_regions: list[str]) -> list[str]:
    """Translate sidebar scope toggle to a region list."""
    if scope == "all":
        return [r for r in REGION_ORDER if r in all_regions]
    return [scope] if scope in all_regions else []


def render_placeholder_banner() -> None:
    """Standard banner shown at the top of every page when no real results yet."""
    st.info(
        "**Placeholder mode** — 시뮬레이션 결과가 아직 박제되지 않았습니다. "
        "결과가 `_workspace/snapshots/results_index.json`에 박제되면 5초 안에 자동 갱신됩니다.",
        icon="🛰️",
    )


def render_sidebar(page_label: str) -> dict[str, Any]:
    """Render the shared sidebar (region scope, refresh, freshness).

    Returns dict with: scope, autorefresh, regions_present.
    """
    results, is_placeholder = load_all_results()
    regions_present = list(results.keys())

    st.sidebar.header("PolitiKAST")
    st.sidebar.caption(f"Page · {page_label}")

    scope_options = ["all"] + [r for r in REGION_ORDER if r in regions_present]
    scope_labels = {r: get_region_label(r) for r in regions_present}
    scope_labels["all"] = "5 region 비교"

    scope = st.sidebar.selectbox(
        "Region 범위",
        options=scope_options,
        format_func=lambda x: scope_labels.get(x, x),
        index=0,
        key=f"_scope_{page_label}",
    )

    st.sidebar.divider()
    autorefresh = st.sidebar.checkbox("5초 자동 갱신", value=True, key=f"_auto_{page_label}")
    if st.sidebar.button("🔄 즉시 새로고침", use_container_width=True, key=f"_refresh_{page_label}"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.divider()
    if is_placeholder:
        st.sidebar.warning("Placeholder 데이터", icon="🛰️")
    else:
        st.sidebar.success(f"Live · {len(regions_present)} regions", icon="✅")

    # Build provenance
    policy = load_policy()
    if policy:
        st.sidebar.caption(f"policy: {policy.get('_status', 'unknown')}")
    snapshot_mtime = None
    if RESULTS_INDEX.exists():
        snapshot_mtime = RESULTS_INDEX.stat().st_mtime
    if snapshot_mtime:
        from datetime import datetime
        st.sidebar.caption(f"snapshot mtime: {datetime.fromtimestamp(snapshot_mtime).strftime('%H:%M:%S')}")

    # Auto-refresh via meta refresh hack (no streamlit-extras dependency)
    if autorefresh:
        st.markdown(
            "<meta http-equiv='refresh' content='5'>",
            unsafe_allow_html=True,
        )

    return {
        "scope": scope,
        "autorefresh": autorefresh,
        "regions_present": regions_present,
        "is_placeholder": is_placeholder,
    }
