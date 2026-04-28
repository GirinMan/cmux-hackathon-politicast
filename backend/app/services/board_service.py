"""Board topic service — region 별 자유 게시판."""
from __future__ import annotations

from typing import Optional

from . import _community_store as cs
from . import comment_service

MAX_TITLE_LEN = 120
MAX_BODY_LEN = 5000


def _validate_text(value: str, *, field: str, maxlen: int) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{field} must be non-empty")
    if len(value) > maxlen:
        raise ValueError(f"{field} too long (>{maxlen})")
    return value


def list_topics(
    region_id: Optional[str] = None, *, page: int = 1, page_size: int = 20,
) -> tuple[list[cs.BoardTopic], int]:
    return cs.get_store().list_topics(
        region_id=region_id, page=page, page_size=page_size
    )


def get_topic(tid: str) -> Optional[cs.BoardTopic]:
    return cs.get_store().get_topic(tid)


def get_topic_with_first_comments(
    tid: str, n: int = 20
) -> tuple[Optional[cs.BoardTopic], list[cs.Comment]]:
    t = cs.get_store().get_topic(tid)
    if t is None or t.deleted_at is not None:
        return None, []
    rows, _ = cs.get_store().list_comments_for_scope(
        "board_topic", tid, page=1, page_size=n
    )
    return t, rows


def create_topic(
    user: cs.AnonUser, *, region_id: Optional[str], title: str, body: str,
) -> cs.BoardTopic:
    title = _validate_text(title, field="title", maxlen=MAX_TITLE_LEN)
    body = _validate_text(body, field="body", maxlen=MAX_BODY_LEN)
    return cs.get_store().create_topic(
        user_id=user.id, region_id=region_id, title=title, body=body,
    )


def update_topic(
    user: cs.AnonUser, tid: str, *, title: Optional[str] = None,
    body: Optional[str] = None,
) -> cs.BoardTopic:
    t = cs.get_store().get_topic(tid)
    if t is None or t.deleted_at is not None:
        raise KeyError(tid)
    if t.user_id != user.id:
        raise PermissionError("only author can edit")
    if title is not None:
        title = _validate_text(title, field="title", maxlen=MAX_TITLE_LEN)
    if body is not None:
        body = _validate_text(body, field="body", maxlen=MAX_BODY_LEN)
    return cs.get_store().update_topic(tid, title=title, body=body)


def soft_delete_topic(actor: cs.AnonUser, tid: str, *, is_admin: bool = False) -> cs.BoardTopic:
    t = cs.get_store().get_topic(tid)
    if t is None:
        raise KeyError(tid)
    if not is_admin and t.user_id != actor.id:
        raise PermissionError("only author or admin can delete")
    return cs.get_store().soft_delete_topic(tid, by="admin" if is_admin else "user")


def pin_topic(tid: str, *, pinned: bool = True) -> cs.BoardTopic:
    t = cs.get_store().get_topic(tid)
    if t is None:
        raise KeyError(tid)
    return cs.get_store().pin_topic(tid, pinned=pinned)


def report_topic(user: cs.AnonUser, tid: str, reason: str) -> cs.CommentReport:
    t = cs.get_store().get_topic(tid)
    if t is None or t.deleted_at is not None:
        raise KeyError(tid)
    reason = (reason or "").strip()
    if not (1 <= len(reason) <= 500):
        raise ValueError("reason length must be 1..500")
    return cs.get_store().create_report(
        target_kind="board_topic", target_id=tid,
        reporter_user_id=user.id, reason=reason,
    )


__all__ = [
    "list_topics",
    "get_topic",
    "get_topic_with_first_comments",
    "create_topic",
    "update_topic",
    "soft_delete_topic",
    "pin_topic",
    "report_topic",
    "MAX_TITLE_LEN",
    "MAX_BODY_LEN",
]
