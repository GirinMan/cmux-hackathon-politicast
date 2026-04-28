"""In-memory thread-safe community store (anon users / comments / board / reports).

ORM (#90) 도착 전 임시 저장소. 인터페이스는 ORM repo 의 수퍼셋 — 도착 시 동일
서비스 코드를 유지한 채 본 모듈만 SQLAlchemy 구현으로 교체. 모든 메서드는
sync (services 가 sync 함수에서 호출). 실 ORM swap 시 await 추가.

테스트가 동일 process 내에서 격리될 수 있도록 `reset_for_test()` 도 제공.
"""
from __future__ import annotations

import datetime as dt
import threading
import uuid
from dataclasses import dataclass, field, asdict
from typing import Iterable, Literal, Optional

ScopeType = Literal["region", "scenario", "board_topic", "scenario_tree"]
ReportTargetKind = Literal["comment", "board_topic"]
ReportStatus = Literal["open", "resolved"]
ReportResolution = Literal["dismissed", "soft_deleted", "banned_user"]


def _utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Models (lightweight, no SQLAlchemy)
# ---------------------------------------------------------------------------
@dataclass
class AnonUser:
    id: str
    display_name: str
    created_at: str = field(default_factory=_utcnow_iso)
    banned: bool = False
    banned_at: Optional[str] = None
    banned_reason: Optional[str] = None


@dataclass
class Comment:
    id: str
    user_id: str
    scope_type: ScopeType
    scope_id: str
    body: str
    parent_id: Optional[str] = None
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: Optional[str] = None
    edited_count: int = 0
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None  # "user"|"admin"


@dataclass
class BoardTopic:
    id: str
    user_id: str
    region_id: Optional[str]
    title: str
    body: str
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: Optional[str] = None
    deleted_at: Optional[str] = None
    deleted_by: Optional[str] = None
    pinned: bool = False
    pinned_at: Optional[str] = None
    comment_count: int = 0


@dataclass
class CommentReport:
    id: str
    target_kind: ReportTargetKind
    target_id: str
    reporter_user_id: str
    reason: str
    status: ReportStatus = "open"
    resolution: Optional[ReportResolution] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None  # admin username
    created_at: str = field(default_factory=_utcnow_iso)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------
class CommunityStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.users: dict[str, AnonUser] = {}
        self.comments: dict[str, Comment] = {}
        self.topics: dict[str, BoardTopic] = {}
        self.reports: dict[str, CommentReport] = {}

    # ---- users ----
    def get_user(self, user_id: str) -> Optional[AnonUser]:
        with self._lock:
            return self.users.get(user_id)

    def create_user(self, display_name: str, *, user_id: Optional[str] = None) -> AnonUser:
        with self._lock:
            uid = user_id or f"u_{uuid.uuid4().hex[:12]}"
            u = AnonUser(id=uid, display_name=display_name)
            self.users[uid] = u
            return u

    def upsert_user(self, user_id: str, display_name: str) -> AnonUser:
        """cookie politikast_uid 가 들고 온 id 로 멱등 생성."""
        with self._lock:
            if user_id in self.users:
                return self.users[user_id]
            return self.create_user(display_name, user_id=user_id)

    def update_user_nickname(self, user_id: str, new_name: str) -> AnonUser:
        with self._lock:
            u = self.users[user_id]
            u.display_name = new_name
            return u

    def ban_user(self, user_id: str, reason: Optional[str] = None) -> AnonUser:
        with self._lock:
            u = self.users[user_id]
            u.banned = True
            u.banned_at = _utcnow_iso()
            u.banned_reason = reason
            return u

    # ---- comments ----
    def create_comment(self, **kw) -> Comment:
        with self._lock:
            cid = f"c_{uuid.uuid4().hex[:12]}"
            c = Comment(id=cid, **kw)
            self.comments[cid] = c
            if c.scope_type == "board_topic" and c.scope_id in self.topics and c.deleted_at is None:
                self.topics[c.scope_id].comment_count += 1
            return c

    def get_comment(self, cid: str) -> Optional[Comment]:
        with self._lock:
            return self.comments.get(cid)

    def list_comments_for_scope(
        self, scope_type: ScopeType, scope_id: str,
        *, page: int = 1, page_size: int = 50, include_deleted: bool = False,
    ) -> tuple[list[Comment], int]:
        with self._lock:
            rows = [
                c for c in self.comments.values()
                if c.scope_type == scope_type and c.scope_id == scope_id
                and (include_deleted or c.deleted_at is None)
            ]
        rows.sort(key=lambda c: c.created_at)
        total = len(rows)
        page = max(1, page)
        start = (page - 1) * page_size
        return rows[start:start + page_size], total

    def update_comment_body(self, cid: str, body: str) -> Comment:
        with self._lock:
            c = self.comments[cid]
            c.body = body
            c.edited_count += 1
            c.updated_at = _utcnow_iso()
            return c

    def soft_delete_comment(self, cid: str, *, by: str) -> Comment:
        with self._lock:
            c = self.comments[cid]
            if c.deleted_at is None:
                c.deleted_at = _utcnow_iso()
                c.deleted_by = by
                if c.scope_type == "board_topic" and c.scope_id in self.topics:
                    t = self.topics[c.scope_id]
                    t.comment_count = max(0, t.comment_count - 1)
            return c

    # ---- topics ----
    def create_topic(self, **kw) -> BoardTopic:
        with self._lock:
            tid = f"t_{uuid.uuid4().hex[:12]}"
            t = BoardTopic(id=tid, **kw)
            self.topics[tid] = t
            return t

    def get_topic(self, tid: str) -> Optional[BoardTopic]:
        with self._lock:
            return self.topics.get(tid)

    def list_topics(
        self, *, region_id: Optional[str] = None,
        page: int = 1, page_size: int = 20, include_deleted: bool = False,
    ) -> tuple[list[BoardTopic], int]:
        with self._lock:
            rows = [
                t for t in self.topics.values()
                if (region_id is None or t.region_id == region_id)
                and (include_deleted or t.deleted_at is None)
            ]
        # pinned first, then newest
        rows.sort(key=lambda t: (0 if t.pinned else 1, -dt.datetime.fromisoformat(t.created_at).timestamp()))
        total = len(rows)
        page = max(1, page)
        start = (page - 1) * page_size
        return rows[start:start + page_size], total

    def update_topic(self, tid: str, *, title: Optional[str] = None,
                     body: Optional[str] = None) -> BoardTopic:
        with self._lock:
            t = self.topics[tid]
            if title is not None:
                t.title = title
            if body is not None:
                t.body = body
            t.updated_at = _utcnow_iso()
            return t

    def soft_delete_topic(self, tid: str, *, by: str) -> BoardTopic:
        with self._lock:
            t = self.topics[tid]
            if t.deleted_at is None:
                t.deleted_at = _utcnow_iso()
                t.deleted_by = by
            return t

    def pin_topic(self, tid: str, *, pinned: bool = True) -> BoardTopic:
        with self._lock:
            t = self.topics[tid]
            t.pinned = pinned
            t.pinned_at = _utcnow_iso() if pinned else None
            return t

    # ---- reports ----
    def create_report(self, **kw) -> CommentReport:
        with self._lock:
            rid = f"r_{uuid.uuid4().hex[:12]}"
            r = CommentReport(id=rid, **kw)
            self.reports[rid] = r
            return r

    def list_reports(self, *, status: Optional[ReportStatus] = None) -> list[CommentReport]:
        with self._lock:
            rows = list(self.reports.values())
        if status is not None:
            rows = [r for r in rows if r.status == status]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows

    def get_report(self, rid: str) -> Optional[CommentReport]:
        with self._lock:
            return self.reports.get(rid)

    def resolve_report(
        self, rid: str, *, resolution: ReportResolution, by: str
    ) -> CommentReport:
        with self._lock:
            r = self.reports[rid]
            r.status = "resolved"
            r.resolution = resolution
            r.resolved_at = _utcnow_iso()
            r.resolved_by = by
            return r

    # ---- test helper ----
    def reset_for_test(self) -> None:
        with self._lock:
            self.users.clear()
            self.comments.clear()
            self.topics.clear()
            self.reports.clear()


# Global singleton (process-level). ORM swap 시 본 함수가 SQLAlchemy 세션
# 기반 Repository 객체로 교체.
_STORE = CommunityStore()


def get_store() -> CommunityStore:
    return _STORE


__all__ = [
    "AnonUser",
    "Comment",
    "BoardTopic",
    "CommentReport",
    "CommunityStore",
    "ScopeType",
    "ReportTargetKind",
    "ReportStatus",
    "ReportResolution",
    "get_store",
]
