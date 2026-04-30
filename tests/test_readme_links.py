"""Phase 5 (#106) — README + docs link gate.

Walks every Markdown link target referenced from ``README.md`` and the
``docs/`` set. Local file links must resolve; absolute http(s) URLs are
accepted as-is (no network calls — keeps tests offline + deterministic).

Why a regression gate? README ↔ docs 분리 (#103/#104) 이후 링크 깨짐이 가장
잦은 회귀 패턴입니다. 이 테스트 한 개로 차단합니다.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent

# Inline link form: [text](target)  — strip URL fragments / query strings.
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
# Image references: ![alt](src) — handled identically.
_MD_IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")

_FILES_TO_CHECK: tuple[Path, ...] = (
    _REPO_ROOT / "README.md",
    _REPO_ROOT / "docs" / "research-summary.md",
    _REPO_ROOT / "docs" / "architecture.md",
    _REPO_ROOT / "docs" / "deploy.md",
)


def _extract_targets(md_path: Path) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    text = md_path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _MD_LINK_RE.finditer(line):
            out.append((lineno, match.group(1)))
        for match in _MD_IMG_RE.finditer(line):
            out.append((lineno, match.group(1)))
    return out


def _is_external(target: str) -> bool:
    return (
        target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
    )


def _strip_fragment(target: str) -> str:
    # Drop ``#section`` and ``?query`` so we resolve the bare path.
    for sep in ("#", "?"):
        if sep in target:
            target = target.split(sep, 1)[0]
    return target


@pytest.mark.parametrize("md_path", _FILES_TO_CHECK, ids=lambda p: p.name)
def test_markdown_local_links_resolve(md_path: Path):
    if not md_path.exists():
        pytest.fail(f"expected doc not found: {md_path.relative_to(_REPO_ROOT)}")

    failures: list[str] = []
    base_dir = md_path.parent

    for lineno, target in _extract_targets(md_path):
        if _is_external(target):
            continue
        bare = _strip_fragment(target)
        if not bare:
            # Pure-fragment link (e.g. "#section") — same-page anchor, accept.
            continue
        candidate = (base_dir / bare).resolve()
        if not candidate.exists():
            failures.append(
                f"  {md_path.relative_to(_REPO_ROOT)}:{lineno} → "
                f"{target!r} (resolved to {candidate})"
            )

    if failures:
        pytest.fail(
            "Broken local links found — README/docs gate (#106):\n"
            + "\n".join(failures)
        )


def test_readme_points_to_three_doc_subpages():
    """README must link to research-summary, architecture, and deploy in
    its top navigation block (post-#103 service-tone redesign)."""
    readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for needle in (
        "docs/research-summary.md",
        "docs/architecture.md",
        "docs/deploy.md",
    ):
        assert needle in readme, f"README missing nav link to {needle!r}"


def test_no_legacy_streamlit_url_in_readme():
    """Streamlit was removed in Phase 4; the React frontend (port 5173)
    is the live UI surface. Guard prevents accidental re-advertisement."""
    readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for forbidden in ("streamlit run", ":8501", "streamlit"):
        assert forbidden not in readme.lower(), (
            f"README references removed Streamlit surface: {forbidden!r}"
        )
