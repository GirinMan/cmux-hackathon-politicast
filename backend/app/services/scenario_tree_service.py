"""Phase 6 — ScenarioTree service.

Loads beam-search artifacts (`_workspace/snapshots/scenario_trees/{tree_id}.json`)
and surfaces them as Sankey-friendly DTOs. Admin operations (build / delete /
list) talk to the ORM in `backend/app/db/models.py`.

Build is a long-running job — exposed as a BackgroundTask in the router; this
service simply records a `building` row + spawns the worker (as a thin
subprocess shim, so the FastAPI process stays responsive).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.scenario_tree import ScenarioTree

from ..db.models import ScenarioTree as ScenarioTreeORM
from ..schemas.admin_dto import (
    ScenarioTreeBuildRequestDTO,
    ScenarioTreeBuildResponseDTO,
    ScenarioTreeListResponseDTO,
    ScenarioTreeMetadataDTO,
)
from ..schemas.public_dto import (
    BeamNodeDetailDTO,
    PollPointDTO,
    ScenarioTreeDTO,
    ScenarioTreeNodeDTO,
)
from ..settings import REPO_ROOT

logger = logging.getLogger("backend.scenario_tree")

ARTIFACTS_DIR = REPO_ROOT / "_workspace" / "snapshots" / "scenario_trees"

DEFAULT_BEAM_WIDTH = 3
DEFAULT_BEAM_DEPTH = 4
DEFAULT_K_PROPOSE = 3


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------
def _resolve_artifact_path(artifact_path: str) -> Path:
    p = Path(artifact_path)
    if not p.is_absolute():
        p = REPO_ROOT / artifact_path
    return p


def _load_artifact(artifact_path: str) -> Optional[ScenarioTree]:
    p = _resolve_artifact_path(artifact_path)
    if not p.exists():
        logger.warning("scenario tree artifact missing: %s", p)
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return ScenarioTree.model_validate(raw)
    except Exception:  # noqa: BLE001
        logger.exception("failed to parse scenario tree artifact %s", p)
        return None


def _root_label(as_of: dt.date) -> str:
    return f"현재 ({as_of.isoformat()})"


def _node_to_dto(node, *, root_label: str) -> ScenarioTreeNodeDTO:
    label = node.event.description if node.event else root_label
    source = node.event.source if node.event else None
    prior_p = node.event.prior_p if node.event else None
    occurs_at = node.event.occurs_at.isoformat() if node.event else None
    return ScenarioTreeNodeDTO(
        node_id=node.node_id,
        parent_id=node.parent_id,
        depth=node.depth,
        label=label,
        source=source,
        prior_p=prior_p,
        cumulative_p=node.cumulative_p,
        leader_candidate_id=node.leader_candidate_id,
        predicted_shares=dict(node.predicted_shares),
        children=list(node.children),
        occurs_at=occurs_at,
    )


def _tree_to_dto(orm: ScenarioTreeORM, tree: ScenarioTree) -> ScenarioTreeDTO:
    root_label = _root_label(tree.as_of)
    nodes = [_node_to_dto(n, root_label=root_label) for n in tree.nodes.values()]
    nodes.sort(key=lambda n: (n.depth, n.node_id))
    return ScenarioTreeDTO(
        tree_id=str(orm.id),
        region_id=tree.region_id,
        contest_id=tree.contest_id,
        as_of=tree.as_of.isoformat(),
        election_date=tree.election_date.isoformat(),
        root_id=tree.root_id,
        nodes=nodes,
        mlflow_run_id=tree.mlflow_run_id or orm.mlflow_run_id,
        built_at=orm.built_at.isoformat() if orm.built_at else None,
    )


# ---------------------------------------------------------------------------
# Public API operations
# ---------------------------------------------------------------------------
async def get_scenario_tree(
    session: AsyncSession,
    region_id: str,
    *,
    as_of: Optional[dt.date] = None,
) -> Optional[ScenarioTreeDTO]:
    """Return the latest complete tree for region (optionally pinned to as_of)."""
    stmt = (
        select(ScenarioTreeORM)
        .where(ScenarioTreeORM.region_id == region_id)
        .where(ScenarioTreeORM.status == "complete")
        .order_by(ScenarioTreeORM.as_of.desc(), ScenarioTreeORM.built_at.desc())
        .limit(1)
    )
    if as_of is not None:
        stmt = (
            select(ScenarioTreeORM)
            .where(ScenarioTreeORM.region_id == region_id)
            .where(ScenarioTreeORM.as_of == as_of)
            .where(ScenarioTreeORM.status == "complete")
            .order_by(ScenarioTreeORM.built_at.desc())
            .limit(1)
        )
    res = await session.execute(stmt)
    orm = res.scalar_one_or_none()
    if orm is None:
        return None
    tree = _load_artifact(orm.artifact_path)
    if tree is None:
        return None
    return _tree_to_dto(orm, tree)


async def get_node_detail(
    session: AsyncSession, region_id: str, tree_id: str, node_id: str
) -> Optional[BeamNodeDetailDTO]:
    try:
        tid = uuid.UUID(tree_id)
    except ValueError:
        return None
    stmt = select(ScenarioTreeORM).where(ScenarioTreeORM.id == tid)
    orm = (await session.execute(stmt)).scalar_one_or_none()
    if orm is None or orm.region_id != region_id:
        return None
    tree = _load_artifact(orm.artifact_path)
    if tree is None or node_id not in tree.nodes:
        return None
    node = tree.nodes[node_id]
    label = node.event.description if node.event else _root_label(tree.as_of)
    poll_pts: list[PollPointDTO] = []
    interview_excerpts: list[str] = []
    sim_ref = node.sim_result_ref or None
    if sim_ref:
        sim_path = _resolve_artifact_path(sim_ref)
        if sim_path.exists():
            try:
                sim_raw = json.loads(sim_path.read_text(encoding="utf-8"))
                for pt in (sim_raw.get("poll_trajectory") or [])[:64]:
                    poll_pts.append(
                        PollPointDTO(
                            timestep=int(pt.get("timestep", 0)),
                            date=pt.get("date"),
                            support_by_candidate=dict(
                                pt.get("support_by_candidate") or {}
                            ),
                            turnout_intent=pt.get("turnout_intent"),
                            consensus_var=pt.get("consensus_var"),
                        )
                    )
                for vi in (sim_raw.get("virtual_interviews") or [])[:5]:
                    excerpt = (vi.get("response") or vi.get("text") or "")[:280]
                    if excerpt:
                        interview_excerpts.append(excerpt)
            except Exception:  # noqa: BLE001
                logger.warning("failed to load sim result %s", sim_path)
    event_meta: dict[str, Optional[str]] = {}
    if node.event is not None:
        for k, v in (node.event.metadata or {}).items():
            event_meta[str(k)] = None if v is None else str(v)
    return BeamNodeDetailDTO(
        tree_id=str(orm.id),
        node_id=node.node_id,
        region_id=orm.region_id,
        parent_id=node.parent_id,
        depth=node.depth,
        label=label,
        source=node.event.source if node.event else None,
        prior_p=node.event.prior_p if node.event else None,
        cumulative_p=node.cumulative_p,
        leader_candidate_id=node.leader_candidate_id,
        predicted_shares=dict(node.predicted_shares),
        sim_result_ref=sim_ref,
        poll_trajectory=poll_pts,
        virtual_interview_excerpts=interview_excerpts,
        event_metadata=event_meta,
    )


# ---------------------------------------------------------------------------
# Admin operations
# ---------------------------------------------------------------------------
def _orm_to_metadata(orm: ScenarioTreeORM) -> ScenarioTreeMetadataDTO:
    return ScenarioTreeMetadataDTO(
        id=str(orm.id),
        region_id=orm.region_id,
        contest_id=orm.contest_id,
        as_of=orm.as_of.isoformat() if orm.as_of else "",
        election_date=orm.election_date.isoformat() if orm.election_date else "",
        beam_width=int(orm.beam_width),
        beam_depth=int(orm.beam_depth),
        artifact_path=orm.artifact_path,
        mlflow_run_id=orm.mlflow_run_id,
        built_at=orm.built_at.isoformat() if orm.built_at else "",
        built_by=orm.built_by,
        status=orm.status,
    )


async def list_trees(
    session: AsyncSession,
    *,
    region_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> ScenarioTreeListResponseDTO:
    page = max(1, page)
    page_size = max(1, min(200, page_size))
    base = select(ScenarioTreeORM)
    if region_id:
        base = base.where(ScenarioTreeORM.region_id == region_id)
    total_res = await session.execute(
        select(ScenarioTreeORM.id).where(base.whereclause) if base.whereclause is not None
        else select(ScenarioTreeORM.id)
    )
    total = len(total_res.scalars().all())
    rows = (
        await session.execute(
            base.order_by(ScenarioTreeORM.built_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return ScenarioTreeListResponseDTO(
        data=[_orm_to_metadata(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


async def delete_tree(session: AsyncSession, tree_id: str) -> bool:
    try:
        tid = uuid.UUID(tree_id)
    except ValueError:
        return False
    orm = (
        await session.execute(select(ScenarioTreeORM).where(ScenarioTreeORM.id == tid))
    ).scalar_one_or_none()
    if orm is None:
        return False
    artifact = _resolve_artifact_path(orm.artifact_path)
    if artifact.exists():
        try:
            artifact.unlink()
        except OSError:
            logger.warning("failed to unlink artifact %s", artifact)
    await session.execute(delete(ScenarioTreeORM).where(ScenarioTreeORM.id == tid))
    await session.commit()
    return True


async def request_build(
    session: AsyncSession,
    payload: ScenarioTreeBuildRequestDTO,
    *,
    requested_by: Optional[str] = None,
) -> ScenarioTreeBuildResponseDTO:
    """Insert a `building` row and spawn the worker subprocess (fire-and-forget).

    The worker (`python -m src.sim.scenario_tree`) writes to
    `_workspace/snapshots/scenario_trees/{tree_id}.json` and is expected to
    flip the row to `complete` (or `failed`) when finished. Until then the
    public `GET` endpoint sees no `complete` row and returns 404.
    """
    as_of = dt.date.fromisoformat(payload.as_of)
    beam_width = payload.beam_width or DEFAULT_BEAM_WIDTH
    beam_depth = payload.beam_depth or DEFAULT_BEAM_DEPTH
    k_propose = payload.k_propose or DEFAULT_K_PROPOSE
    proposer = payload.proposer or "composite"

    tree_id = uuid.uuid4()
    artifact_path = (
        f"_workspace/snapshots/scenario_trees/{tree_id}.json"
    )
    config: dict[str, Any] = {
        "beam_width": beam_width,
        "beam_depth": beam_depth,
        "k_propose": k_propose,
        "proposer": proposer,
        "seed": payload.seed if payload.seed is not None else 11,
    }

    # Replace any existing row for the same (region, as_of) — UNIQUE constraint
    # on (region_id, contest_id, as_of) — drop first, idempotent build.
    await session.execute(
        delete(ScenarioTreeORM)
        .where(ScenarioTreeORM.region_id == payload.region_id)
        .where(ScenarioTreeORM.as_of == as_of)
    )
    orm = ScenarioTreeORM(
        id=tree_id,
        region_id=payload.region_id,
        contest_id=payload.region_id,  # default — worker may overwrite
        as_of=as_of,
        election_date=as_of,  # placeholder, real value set by worker artifact
        beam_width=beam_width,
        beam_depth=beam_depth,
        config=config,
        artifact_path=artifact_path,
        built_by=requested_by,
        status="building",
    )
    session.add(orm)
    await session.commit()

    # Spawn the build subprocess. We do not await — the FastAPI BackgroundTask
    # wrapper invokes us; subprocess inherits env (incl. MLFLOW_TRACKING_URI).
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "src.sim.scenario_tree",
        "--region", payload.region_id,
        "--as-of", as_of.isoformat(),
        "--beam-width", str(beam_width),
        "--beam-depth", str(beam_depth),
        "--k-propose", str(k_propose),
        "--tree-id", str(tree_id),
        "--artifact", str((REPO_ROOT / artifact_path).resolve()),
    ]
    try:
        env = os.environ.copy()
        env.setdefault("PYTHONPATH", str(REPO_ROOT))
        subprocess.Popen(  # noqa: S603 — controlled args
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            close_fds=True,
        )
    except FileNotFoundError:
        # `src.sim.scenario_tree` not yet present (pipeline-model wip) — leave
        # the row in `building` so admin sees the request but we don't crash.
        logger.warning("scenario_tree builder not available; row kept as 'building'")

    return ScenarioTreeBuildResponseDTO(
        tree_id=str(tree_id),
        region_id=payload.region_id,
        as_of=as_of.isoformat(),
        status="building",
        mlflow_run_id=None,
    )


# Sync helper used by FastAPI BackgroundTask wrappers (which want a coroutine).
async def request_build_bg(
    session_factory,
    payload: ScenarioTreeBuildRequestDTO,
    requested_by: Optional[str],
) -> None:
    async with session_factory() as session:
        await request_build(session, payload, requested_by=requested_by)


__all__ = [
    "ARTIFACTS_DIR",
    "delete_tree",
    "get_node_detail",
    "get_scenario_tree",
    "list_trees",
    "request_build",
    "request_build_bg",
]
