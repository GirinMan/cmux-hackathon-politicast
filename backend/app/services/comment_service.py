"""Comment service — scope_type ∈ {region, scenario, board_topic, scenario_tree}."""
from __future__ import annotations

from typing import Optional

from . import _community_store as cs

MAX_BODY_LEN = 2000
ALLOWED_SCOPES = ("region", "scenario", "board_topic", "scenario_tree")


def _validate_body(body: str) -> str:
    body = (body or "").strip()
    if not body:
        raise ValueError("body must be non-empty")
    if len(body) > MAX_BODY_LEN:
        raise ValueError(f"body too long (>{MAX_BODY_LEN})")
    return body


def list_for_scope(
    scope_type: str, scope_id: str, *, page: int = 1, page_size: int = 50,
    include_deleted: bool = False,
) -> tuple[list[cs.Comment], int]:
    if scope_type not in ALLOWED_SCOPES:
        raise ValueError(f"invalid scope_type={scope_type!r}")
    return cs.get_store().list_comments_for_scope(
        scope_type, scope_id, page=page, page_size=page_size,
        include_deleted=include_deleted,
    )


def get(comment_id: str) -> Optional[cs.Comment]:
    return cs.get_store().get_comment(comment_id)


def create(
    user: cs.AnonUser, *, scope_type: str, scope_id: str, body: str,
    parent_id: Optional[str] = None,
) -> cs.Comment:
    if scope_type not in ALLOWED_SCOPES:
        raise ValueError(f"invalid scope_type={scope_type!r}")
    body = _validate_body(body)
    if parent_id is not None:
        parent = cs.get_store().get_comment(parent_id)
        if parent is None:
            raise ValueError(f"parent_id={parent_id!r} not found")
        if parent.scope_type != scope_type or parent.scope_id != scope_id:
            raise ValueError("parent comment in different scope")
    return cs.get_store().create_comment(
        user_id=user.id, scope_type=scope_type, scope_id=scope_id,
        body=body, parent_id=parent_id,
    )


def update(user: cs.AnonUser, comment_id: str, body: str) -> cs.Comment:
    c = cs.get_store().get_comment(comment_id)
    if c is None or c.deleted_at is not None:
        raise KeyError(comment_id)
    if c.user_id != user.id:
        raise PermissionError("only author can edit")
    body = _validate_body(body)
    return cs.get_store().update_comment_body(comment_id, body)


def soft_delete(actor: cs.AnonUser, comment_id: str, *, is_admin: bool = False) -> cs.Comment:
    c = cs.get_store().get_comment(comment_id)
    if c is None:
        raise KeyError(comment_id)
    if not is_admin and c.user_id != actor.id:
        raise PermissionError("only author or admin can delete")
    return cs.get_store().soft_delete_comment(comment_id, by="admin" if is_admin else "user")


def admin_soft_delete(comment_id: str) -> cs.Comment:
    c = cs.get_store().get_comment(comment_id)
    if c is None:
        raise KeyError(comment_id)
    return cs.get_store().soft_delete_comment(comment_id, by="admin")


def report(user: cs.AnonUser, comment_id: str, reason: str) -> cs.CommentReport:
    c = cs.get_store().get_comment(comment_id)
    if c is None or c.deleted_at is not None:
        raise KeyError(comment_id)
    reason = (reason or "").strip()
    if not (1 <= len(reason) <= 500):
        raise ValueError("reason length must be 1..500")
    return cs.get_store().create_report(
        target_kind="comment", target_id=comment_id,
        reporter_user_id=user.id, reason=reason,
    )


__all__ = [
    "list_for_scope",
    "get",
    "create",
    "update",
    "soft_delete",
    "admin_soft_delete",
    "report",
    "ALLOWED_SCOPES",
    "MAX_BODY_LEN",
]
