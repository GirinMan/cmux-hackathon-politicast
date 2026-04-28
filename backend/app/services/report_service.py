"""Report moderation service — admin 전용 처리."""
from __future__ import annotations

from typing import Optional

from . import _community_store as cs
from . import anon_user_service


def list_reports(status: Optional[str] = None) -> list[cs.CommentReport]:
    if status not in (None, "open", "resolved"):
        raise ValueError(f"invalid status={status!r}")
    return cs.get_store().list_reports(status=status)  # type: ignore[arg-type]


def get_report(rid: str) -> Optional[cs.CommentReport]:
    return cs.get_store().get_report(rid)


def resolve(
    rid: str, *, resolution: str, admin_username: str,
) -> cs.CommentReport:
    if resolution not in ("dismissed", "soft_deleted", "banned_user"):
        raise ValueError(f"invalid resolution={resolution!r}")
    store = cs.get_store()
    r = store.get_report(rid)
    if r is None:
        raise KeyError(rid)
    if r.status == "resolved":
        return r  # idempotent — return existing resolution

    # Apply side-effects depending on resolution
    if resolution in ("soft_deleted", "banned_user"):
        if r.target_kind == "comment":
            target = store.get_comment(r.target_id)
            if target is not None and target.deleted_at is None:
                store.soft_delete_comment(target.id, by="admin")
        elif r.target_kind == "board_topic":
            target_t = store.get_topic(r.target_id)
            if target_t is not None and target_t.deleted_at is None:
                store.soft_delete_topic(target_t.id, by="admin")

    if resolution == "banned_user":
        author_id = _resolve_target_author(r)
        if author_id is not None:
            anon_user_service.ban_user(author_id, reason=f"report:{rid}")

    return store.resolve_report(rid, resolution=resolution, by=admin_username)  # type: ignore[arg-type]


def ban_user_directly(user_id: str, *, admin_username: str, reason: Optional[str] = None) -> cs.AnonUser:
    return anon_user_service.ban_user(
        user_id, reason=reason or f"admin:{admin_username}",
    )


# ---- internals ----
def _resolve_target_author(r: cs.CommentReport) -> Optional[str]:
    store = cs.get_store()
    if r.target_kind == "comment":
        c = store.get_comment(r.target_id)
        return c.user_id if c else None
    if r.target_kind == "board_topic":
        t = store.get_topic(r.target_id)
        return t.user_id if t else None
    return None


__all__ = [
    "list_reports",
    "get_report",
    "resolve",
    "ban_user_directly",
]
