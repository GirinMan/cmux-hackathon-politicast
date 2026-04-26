"""Result, KG snapshot, and policy BFF endpoints for the React dashboard."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

import db
from models import (
    KgSnapshotInfo,
    KgSnapshotResponse,
    PolicyRegionPlan,
    PolicySummaryResponse,
    ResultDetailResponse,
    ResultRegionSummary,
    ResultSummaryResponse,
    ResultTotals,
)

router = APIRouter(tags=["results"])

PROJECT_ROOT = db.PROJECT_ROOT
SNAPSHOT_DIR = PROJECT_ROOT / "_workspace" / "snapshots"
RESULTS_INDEX = SNAPSHOT_DIR / "results_index.json"
RESULTS_DIR = SNAPSHOT_DIR / "results"
CHECKPOINTS_DIR = PROJECT_ROOT / "_workspace" / "checkpoints"
POLICY_PATH = CHECKPOINTS_DIR / "policy.json"
CAPACITY_PROBE_PATH = CHECKPOINTS_DIR / "capacity_probe.json"
PLACEHOLDER_DIR = PROJECT_ROOT / "ui" / "dashboard" / "_placeholder"

REGION_ORDER = list(db.FIVE_REGIONS.keys())


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _safe_read_json(path: Path) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _normalize_index(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        if isinstance(raw.get("results"), list):
            return [x for x in raw["results"] if isinstance(x, dict)]
        if raw.get("scenario_id") and raw.get("region_id"):
            return [raw]
    return []


def _resolve_result_path(rel_path: str | None) -> Path | None:
    if not rel_path:
        return None
    path = Path(rel_path)
    if path.is_absolute():
        return path
    candidate = PROJECT_ROOT / path
    if candidate.exists():
        return candidate
    return PROJECT_ROOT / path


def _mtime_iso(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _region_label(region_id: str) -> str:
    info = db.FIVE_REGIONS.get(region_id) or {}
    return str(info.get("label_ko") or region_id)


def _candidate_maps(result: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    labels: dict[str, str] = {}
    parties: dict[str, str] = {}
    for c in result.get("candidates") or []:
        cid = str(c.get("id") or "")
        if not cid:
            continue
        name = str(c.get("name") or cid)
        party = str(c.get("party") or "")
        labels[cid] = f"{name} ({party})" if party else name
        parties[cid] = party
    labels["abstain"] = "기권"
    parties["abstain"] = "p_none"
    return labels, parties


def _artifact_status(entry: dict[str, Any], result: dict[str, Any] | None) -> tuple[str, bool]:
    scenario_id = str((result or {}).get("scenario_id") or entry.get("scenario_id") or "")
    is_mock = bool(entry.get("is_mock") or (result or {}).get("is_mock") or scenario_id.endswith("__mock"))
    is_placeholder = bool((result or {}).get("_placeholder"))
    if is_placeholder:
        return "placeholder", is_mock
    if "smoke" in scenario_id:
        return "smoke", is_mock
    if is_mock:
        return "mock", True
    if result:
        return "live", False
    return "missing", False


def _status_rank(status: str) -> int:
    return {"live": 4, "smoke": 3, "mock": 2, "placeholder": 1}.get(status, 0)


def _load_result_from_entry(entry: dict[str, Any]) -> tuple[dict[str, Any] | None, Path | None]:
    for rel_path in (
        entry.get("path"),
        entry.get("mirror_path"),
        f"_workspace/snapshots/{entry.get('region_id')}_result.json",
    ):
        path = _resolve_result_path(rel_path)
        if path is None:
            continue
        data = _safe_read_json(path)
        if isinstance(data, dict):
            if "is_mock" in entry and "is_mock" not in data:
                data["is_mock"] = entry["is_mock"]
            return data, path
    return None, None


def _placeholder_entry(region_id: str) -> dict[str, Any]:
    path = PLACEHOLDER_DIR / f"{region_id}.json"
    data = _safe_read_json(path)
    if isinstance(data, dict):
        data["_placeholder"] = True
    return {
        "region_id": region_id,
        "scenario_id": data.get("scenario_id") if isinstance(data, dict) else None,
        "path": _rel(path),
        "_loaded_result": data,
        "_loaded_path": path if isinstance(data, dict) else None,
    }


def _freshest_entries() -> dict[str, dict[str, Any]]:
    raw = _normalize_index(_safe_read_json(RESULTS_INDEX))
    by_region: dict[str, dict[str, Any]] = {}
    for entry in raw:
        rid = entry.get("region_id")
        if rid not in db.FIVE_REGIONS:
            continue
        loaded, path = _load_result_from_entry(entry)
        enriched = dict(entry)
        enriched["_loaded_result"] = loaded
        enriched["_loaded_path"] = path
        enriched["_sort_time"] = entry.get("wrote_at") or _mtime_iso(path) or ""
        enriched["_status"] = _artifact_status(enriched, loaded)[0]
        prev = by_region.get(str(rid))
        prev_key = (_status_rank(prev.get("_status", "missing")), prev.get("_sort_time", "")) if prev else None
        next_key = (_status_rank(enriched["_status"]), enriched["_sort_time"])
        if prev is None or next_key > prev_key:
            by_region[str(rid)] = enriched

    for rid in REGION_ORDER:
        if rid not in by_region:
            by_region[rid] = _placeholder_entry(rid)
    return by_region


def _summary_for(region_id: str, entry: dict[str, Any]) -> ResultRegionSummary:
    result = entry.get("_loaded_result")
    if not isinstance(result, dict):
        result = None
    path = entry.get("_loaded_path")
    status, is_mock = _artifact_status(entry, result)
    labels, _parties = _candidate_maps(result or {})
    meta = (result or {}).get("meta") or {}
    voter_stats = meta.get("voter_stats") or {}
    pool_stats = meta.get("pool_stats") or {}
    final = (result or {}).get("final_outcome") or {}
    winner = final.get("winner")
    parse_fail = int(voter_stats.get("parse_fail") or meta.get("parse_fail") or 0)
    abstain = int(voter_stats.get("abstain") or final.get("n_abstain") or 0)
    warning = None
    if status == "mock":
        warning = "dry-run mock artifact"
    elif status == "smoke":
        warning = "smoke harness check, not a calibrated forecast"
    elif parse_fail > 0:
        warning = "parse failures present"
    elif status == "placeholder":
        warning = "placeholder fallback"
    elif status == "missing":
        warning = "missing result artifact"

    return ResultRegionSummary(
        region_id=region_id,
        label=_region_label(region_id),
        scenario_id=(result or {}).get("scenario_id") or entry.get("scenario_id"),
        status=status,
        is_mock=is_mock,
        persona_n=int((result or {}).get("persona_n") or entry.get("persona_n") or 0),
        timestep_count=int((result or {}).get("timestep_count") or entry.get("timestep_count") or 0),
        winner=winner,
        winner_label=labels.get(str(winner)) if winner else None,
        turnout=final.get("turnout"),
        parse_fail=parse_fail,
        abstain=abstain,
        total_calls=int(voter_stats.get("calls") or pool_stats.get("total_calls") or 0),
        mean_latency_ms=voter_stats.get("mean_latency_ms"),
        wall_seconds=meta.get("wall_seconds"),
        provider=pool_stats.get("provider"),
        model=pool_stats.get("model"),
        wrote_at=entry.get("wrote_at") or _mtime_iso(path),
        path=_rel(path),
        warning=warning,
    )


@router.get("/api/results", response_model=ResultSummaryResponse)
def results_summary() -> ResultSummaryResponse:
    """Freshest five-region result summary with explicit artifact status."""
    entries = _freshest_entries()
    regions = [_summary_for(rid, entries[rid]) for rid in REGION_ORDER]
    live = [r for r in regions if r.status == "live"]
    all_latency = [r.mean_latency_ms for r in regions if r.mean_latency_ms is not None]
    totals = ResultTotals(
        regions_total=len(regions),
        live_count=sum(1 for r in regions if r.status == "live"),
        mock_count=sum(1 for r in regions if r.status == "mock"),
        smoke_count=sum(1 for r in regions if r.status == "smoke"),
        placeholder_count=sum(1 for r in regions if r.status == "placeholder"),
        persona_n=sum(r.persona_n for r in regions),
        parse_fail=sum(r.parse_fail for r in regions),
        abstain=sum(r.abstain for r in regions),
        total_calls=sum(r.total_calls for r in regions),
        wall_seconds=round(sum(float(r.wall_seconds or 0) for r in regions), 3),
        mean_latency_ms=round(sum(all_latency) / len(all_latency), 3) if all_latency else None,
    )
    warnings = [
        "Current paper section treats these outputs as local harness diagnostics, not calibrated forecasts.",
    ]
    if len(live) < len(regions):
        warnings.append("Some regions are mock/smoke/placeholder artifacts; headline forecast claims should exclude them.")
    if totals.parse_fail > 0:
        warnings.append("At least one indexed artifact contains parse failures.")

    return ResultSummaryResponse(
        regions=regions,
        totals=totals,
        warnings=warnings,
        source_files={
            "results_index": _rel(RESULTS_INDEX) or "",
            "results_dir": _rel(RESULTS_DIR) or "",
        },
    )


@router.get("/api/results/{region_id}", response_model=ResultDetailResponse)
def result_detail(region_id: str) -> ResultDetailResponse:
    """Full freshest result artifact for one contract region."""
    if region_id not in db.FIVE_REGIONS:
        raise HTTPException(status_code=400, detail=f"unknown region key: {region_id}")
    entries = _freshest_entries()
    entry = entries.get(region_id) or _placeholder_entry(region_id)
    result = entry.get("_loaded_result")
    if not isinstance(result, dict):
        raise HTTPException(status_code=404, detail=f"result artifact not found: {region_id}")
    path = entry.get("_loaded_path")
    status, is_mock = _artifact_status(entry, result)
    labels, parties = _candidate_maps(result)
    return ResultDetailResponse(
        region_id=region_id,
        label=_region_label(region_id),
        scenario_id=result.get("scenario_id") or entry.get("scenario_id"),
        status=status,
        is_mock=is_mock,
        candidate_labels=labels,
        candidate_parties=parties,
        artifact={
            "path": _rel(path),
            "wrote_at": entry.get("wrote_at") or _mtime_iso(path),
            "status": status,
            "is_mock": is_mock,
        },
        result=result,
        paper_note=(
            "Local harness artifact only; the current paper explicitly warns that "
            "these values are not calibrated election forecasts."
        ),
    )


def _kg_snapshot_meta(path: Path) -> dict[str, Any]:
    data = _safe_read_json(path)
    if not isinstance(data, dict):
        data = {}
    region_id = data.get("region_id")
    timestep = data.get("timestep")
    if region_id is None or timestep is None:
        stem = path.stem
        parts = stem.split("_")
        if parts and parts[0] == "kg":
            last = parts[-1]
            if last.startswith("t") and last[1:].isdigit():
                timestep = int(last[1:]) if timestep is None else timestep
                region_id = "_".join(parts[1:-1]) if region_id is None else region_id
    return {
        "path": path,
        "region_id": region_id,
        "timestep": timestep,
        "scenario_id": data.get("scenario_id"),
        "mtime": path.stat().st_mtime,
        "is_placeholder": bool(data.get("_placeholder")),
    }


def _kg_snapshots() -> list[dict[str, Any]]:
    if not SNAPSHOT_DIR.exists():
        return []
    return [_kg_snapshot_meta(p) for p in sorted(SNAPSHOT_DIR.glob("kg_*.json"))]


@router.get("/api/kg", response_model=KgSnapshotResponse)
def kg_snapshot(
    region: str | None = Query(default=None),
    timestep: int | None = Query(default=None, ge=0),
) -> KgSnapshotResponse:
    """Return the best KG snapshot for region/timestep plus snapshot metadata."""
    if region is not None and region not in db.FIVE_REGIONS:
        raise HTTPException(status_code=400, detail=f"unknown region key: {region}")
    snaps = [s for s in _kg_snapshots() if not s["is_placeholder"]]
    available_timesteps = sorted(
        {
            int(s["timestep"])
            for s in snaps
            if s.get("region_id") == region and s.get("timestep") is not None
        }
    )

    candidates = snaps
    if region is not None:
        candidates = [s for s in candidates if s.get("region_id") == region]
    if timestep is not None:
        candidates = [
            s
            for s in candidates
            if s.get("timestep") is None or int(s.get("timestep") or 0) <= timestep
        ]
    candidates.sort(key=lambda s: (int(s.get("timestep") or -1), float(s["mtime"])), reverse=True)

    chosen = candidates[0] if candidates else None
    data = _safe_read_json(chosen["path"]) if chosen else None
    status = "live"
    if not isinstance(data, dict):
        data = _safe_read_json(PLACEHOLDER_DIR / "kg_export.json") or {"nodes": [], "edges": []}
        chosen = {
            "path": PLACEHOLDER_DIR / "kg_export.json",
            "region_id": data.get("region_id"),
            "timestep": data.get("timestep"),
            "scenario_id": data.get("scenario_id"),
            "is_placeholder": True,
        }
        status = "placeholder" if data.get("nodes") else "missing"

    snapshot_infos = [
        KgSnapshotInfo(
            region_id=s.get("region_id"),
            timestep=s.get("timestep"),
            scenario_id=s.get("scenario_id"),
            path=_rel(s["path"]) or "",
            is_placeholder=bool(s.get("is_placeholder")),
        )
        for s in snaps
    ]
    return KgSnapshotResponse(
        region_id=data.get("region_id") or chosen.get("region_id"),
        timestep=data.get("timestep") if data.get("timestep") is not None else chosen.get("timestep"),
        available_timesteps=available_timesteps,
        cutoff_ts=data.get("cutoff_ts"),
        scenario_id=data.get("scenario_id") or chosen.get("scenario_id"),
        status=status,
        source_path=_rel(chosen.get("path")),
        nodes=list(data.get("nodes") or []),
        edges=list(data.get("edges") or []),
        snapshots=snapshot_infos,
    )


@router.get("/api/policy", response_model=PolicySummaryResponse)
def policy_summary() -> PolicySummaryResponse:
    """Policy/capacity summary used by the experiment diagnostics UI."""
    policy = _safe_read_json(POLICY_PATH)
    capacity = _safe_read_json(CAPACITY_PROBE_PATH)
    if not isinstance(policy, dict):
        policy = {}
    if not isinstance(capacity, dict):
        capacity = None

    regions: list[PolicyRegionPlan] = []
    raw_regions = policy.get("regions") if isinstance(policy.get("regions"), dict) else {}
    for rid in REGION_ORDER:
        cfg = raw_regions.get(rid) if isinstance(raw_regions, dict) else None
        cfg = cfg if isinstance(cfg, dict) else {}
        regions.append(
            PolicyRegionPlan(
                region_id=rid,
                label=_region_label(rid),
                persona_n=cfg.get("persona_n"),
                timesteps=cfg.get("timesteps"),
                interview_n=cfg.get("interview_n"),
                weight=cfg.get("weight"),
            )
        )

    downscale = policy.get("downscale_ladder_v11")
    if not isinstance(downscale, list):
        downscale = []

    provider = policy.get("provider") or (capacity or {}).get("provider")
    model = policy.get("model") or (capacity or {}).get("model")
    warnings = []
    if not policy:
        warnings.append("policy.json is missing or unreadable")
    if not capacity:
        warnings.append("capacity_probe.json is missing or unreadable")

    return PolicySummaryResponse(
        provider=provider,
        model=model,
        regions=regions,
        capacity_probe=capacity,
        downscale_ladder=[x for x in downscale if isinstance(x, dict)],
        warnings=warnings,
        source_files={
            "policy": _rel(POLICY_PATH) or "",
            "capacity_probe": _rel(CAPACITY_PROBE_PATH) or "",
        },
    )
