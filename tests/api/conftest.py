"""Common test scaffolding for backend API tests.

Backend의 origin_guard middleware (POST/PUT/PATCH/DELETE 에 Origin 또는
Referer 가 cors_origin_list 에 속해야 통과) 때문에, 기존 TestClient 호출이
모두 403 으로 떨어진다. 모든 ``TestClient`` 인스턴스에 default
``Origin: http://localhost:5173`` 헤더를 박아 production-like 호출 패턴을
시뮬레이션한다.

CSRF guard 자체를 검증하는 테스트 (test_origin_guard.py) 는 fixture 안에서
``client.headers.pop("origin", None)`` 으로 default 를 명시 reset.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

_orig_init = TestClient.__init__


def _patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
    _orig_init(self, *args, **kwargs)
    self.headers.setdefault("Origin", "http://localhost:5173")


TestClient.__init__ = _patched_init  # type: ignore[method-assign]
