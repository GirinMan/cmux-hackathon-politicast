#!/usr/bin/env python3
"""
Refetch reference URLs listed in docs/references/manifests/*.txt.

Designed to run on a host with normal network access. Updates raw files in
docs/references/raw/<category>/ and writes a report to
docs/references/refetch-report.md.

Usage:
  python scripts/refs/refetch_references.py                       # all categories
  python scripts/refs/refetch_references.py --category tooling    # one category
  python scripts/refs/refetch_references.py --only-failed         # skip raw files that look fresh
  python scripts/refs/refetch_references.py --dry-run             # list URLs only, no fetch

Dependencies (auto-installed into repo-local .venv on first run if missing):
  requests, markdownify, beautifulsoup4, pypdf
"""
from __future__ import annotations

import argparse
import importlib
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO_ROOT / "docs/references/manifests"
RAW_DIR = REPO_ROOT / "docs/references/raw"
REPORT_PATH = REPO_ROOT / "docs/references/refetch-report.md"
CATEGORIES = ["academic", "mirofish", "korean-data", "tooling"]
LOCAL_VENV = REPO_ROOT / ".venv"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 30
DOMAIN_DELAY_SEC = 1.5
PER_CATEGORY_WORKERS = 4

FAIL_HEURISTIC_PATTERNS = [
    re.compile(r"<!--\s*FETCH (FAILED|ERROR)", re.IGNORECASE),
    re.compile(r"DNS (resolution|lookup) failed", re.IGNORECASE),
    re.compile(r"Could not resolve host", re.IGNORECASE),
    re.compile(r"^\s*# Source:.*\n\s*$", re.MULTILINE),  # only header, blank body
]
MIN_BODY_BYTES_FOR_FRESH = 800  # below this we treat the raw file as suspect


# ---------- dependency bootstrap ----------

REQUIRED = {
    "requests": "requests",
    "markdownify": "markdownify",
    "bs4": "beautifulsoup4",
    "pypdf": "pypdf",
}


def missing_deps() -> list[str]:
    missing = []
    for mod, pkg in REQUIRED.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    return missing


def in_virtualenv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def local_venv_python() -> Path:
    if os.name == "nt":
        return LOCAL_VENV / "Scripts" / "python.exe"
    return LOCAL_VENV / "bin" / "python"


def ensure_local_venv() -> Path:
    python = local_venv_python()
    if python.exists():
        return python
    print(f"[deps] creating local virtualenv: {LOCAL_VENV}", file=sys.stderr)
    subprocess.check_call([sys.executable, "-m", "venv", str(LOCAL_VENV)])
    return python


def missing_deps_for_python(python: Path) -> list[str]:
    code = (
        "import importlib.util\n"
        f"required = {REQUIRED!r}\n"
        "missing = [pkg for mod, pkg in required.items() "
        "if importlib.util.find_spec(mod) is None]\n"
        "print('\\n'.join(missing))\n"
    )
    result = subprocess.run(
        [str(python), "-c", code],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def ensure_deps() -> None:
    missing = missing_deps()
    if not missing:
        return

    if not in_virtualenv():
        python = ensure_local_venv()
        missing_in_venv = missing_deps_for_python(python)
        if missing_in_venv:
            print(
                f"[deps] installing into {LOCAL_VENV}: {', '.join(missing_in_venv)}",
                file=sys.stderr,
            )
            subprocess.check_call(
                [str(python), "-m", "pip", "install", "--quiet", *missing_in_venv]
            )
        print(f"[deps] re-running with {python}", file=sys.stderr)
        os.execv(str(python), [str(python), *sys.argv])

    print(f"[deps] installing: {', '.join(missing)}", file=sys.stderr)
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *missing])
    importlib.invalidate_caches()


# ---------- core ----------

@dataclass
class FetchResult:
    url: str
    category: str
    slug: str
    status: str  # ok | failed | skipped
    detail: str
    content_type: str = ""
    bytes_written: int = 0


def slugify(url: str, max_len: int = 60) -> str:
    stripped = re.sub(r"^https?://", "", url)
    slug = re.sub(r"[/:?#&=.]", "-", stripped)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:max_len] or "untitled"


def read_manifest(category: str) -> list[str]:
    path = MANIFEST_DIR / f"{category}.txt"
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def looks_failed(raw_path: Path) -> bool:
    if not raw_path.exists():
        return True
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    if len(text.encode("utf-8")) < MIN_BODY_BYTES_FOR_FRESH:
        return True
    return any(p.search(text) for p in FAIL_HEURISTIC_PATTERNS)


def html_to_markdown(html: str) -> str:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    body = soup.body or soup
    return md(str(body), heading_style="ATX")


def pdf_to_text(data: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def fetch_one(url: str, category: str, out_dir: Path) -> FetchResult:
    import requests

    slug = slugify(url)
    out_path = out_dir / f"{slug}.md"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
        "Accept-Language": "ko,en;q=0.8",
    }
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=True,
            stream=False,
        )
    except requests.RequestException as exc:
        return FetchResult(url, category, slug, "failed", f"request error: {exc}")

    ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if not resp.ok:
        return FetchResult(
            url, category, slug, "failed", f"HTTP {resp.status_code}", content_type=ct
        )

    try:
        if "pdf" in ct or url.lower().endswith(".pdf"):
            body = pdf_to_text(resp.content)
        elif "html" in ct or "xml" in ct:
            body = html_to_markdown(resp.text)
        else:
            body = resp.text
    except Exception as exc:  # noqa: BLE001
        return FetchResult(
            url, category, slug, "failed", f"convert error: {exc}", content_type=ct
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final_url = resp.url
    header = f"# Source: {url}\n"
    if final_url and final_url != url:
        header += f"<!-- final URL: {final_url} -->\n"
    header += f"<!-- fetched: {time.strftime('%Y-%m-%d %H:%M:%S %z')} -->\n\n"
    payload = header + body.strip() + "\n"
    out_path.write_text(payload, encoding="utf-8")
    return FetchResult(
        url,
        category,
        slug,
        "ok",
        "",
        content_type=ct,
        bytes_written=len(payload.encode("utf-8")),
    )


def domain_of(url: str) -> str:
    return urlparse(url).netloc


def fetch_category(
    category: str, urls: Iterable[str], only_failed: bool, dry_run: bool
) -> list[FetchResult]:
    out_dir = RAW_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)

    todo: list[str] = []
    skipped: list[FetchResult] = []
    for url in urls:
        slug = slugify(url)
        out_path = out_dir / f"{slug}.md"
        if only_failed and not looks_failed(out_path):
            skipped.append(
                FetchResult(url, category, slug, "skipped", "raw looks fresh")
            )
            continue
        todo.append(url)

    if dry_run:
        for url in todo:
            print(f"[dry-run] {category}: {url}")
        return skipped + [
            FetchResult(u, category, slugify(u), "skipped", "dry-run") for u in todo
        ]

    # Group by domain so we can rate-limit per domain but parallel across domains.
    by_domain: dict[str, list[str]] = {}
    for u in todo:
        by_domain.setdefault(domain_of(u), []).append(u)

    results: list[FetchResult] = list(skipped)

    def run_domain(domain: str, urls: list[str]) -> list[FetchResult]:
        out: list[FetchResult] = []
        for i, url in enumerate(urls):
            if i:
                time.sleep(DOMAIN_DELAY_SEC)
            r = fetch_one(url, category, out_dir)
            print(f"[{category}] {r.status:7s} {url}", flush=True)
            out.append(r)
        return out

    with ThreadPoolExecutor(max_workers=PER_CATEGORY_WORKERS) as pool:
        futures = [pool.submit(run_domain, d, us) for d, us in by_domain.items()]
        for fut in as_completed(futures):
            results.extend(fut.result())
    return results


def write_report(all_results: list[FetchResult]) -> None:
    by_cat: dict[str, list[FetchResult]] = {}
    for r in all_results:
        by_cat.setdefault(r.category, []).append(r)

    lines = [
        "# Reference refetch report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "",
        "| Category | Total | OK | Failed | Skipped |",
        "|---|---:|---:|---:|---:|",
    ]
    grand = {"total": 0, "ok": 0, "failed": 0, "skipped": 0}
    for cat in sorted(by_cat):
        items = by_cat[cat]
        ok = sum(1 for r in items if r.status == "ok")
        failed = sum(1 for r in items if r.status == "failed")
        skipped = sum(1 for r in items if r.status == "skipped")
        total = len(items)
        grand["total"] += total
        grand["ok"] += ok
        grand["failed"] += failed
        grand["skipped"] += skipped
        lines.append(f"| {cat} | {total} | {ok} | {failed} | {skipped} |")
    lines.append(
        f"| **TOTAL** | **{grand['total']}** | **{grand['ok']}** "
        f"| **{grand['failed']}** | **{grand['skipped']}** |"
    )
    lines.append("")

    for cat in sorted(by_cat):
        failures = [r for r in by_cat[cat] if r.status == "failed"]
        if not failures:
            continue
        lines.append(f"## {cat} — failed URLs ({len(failures)})")
        lines.append("")
        for r in failures:
            lines.append(f"- `{r.url}`  \n  → {r.detail}")
        lines.append("")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[report] {REPORT_PATH}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--category",
        choices=CATEGORIES,
        action="append",
        help="Category to refetch (repeatable). Default: all.",
    )
    ap.add_argument(
        "--only-failed",
        action="store_true",
        help="Skip URLs whose raw file already looks fresh (size + heuristics).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="List target URLs without fetching.",
    )
    ap.add_argument(
        "--no-install",
        action="store_true",
        help="Skip auto pip install of dependencies.",
    )
    args = ap.parse_args()

    if not args.no_install:
        ensure_deps()

    cats = args.category or CATEGORIES
    print(f"[refetch] repo={REPO_ROOT} categories={cats}", file=sys.stderr)
    if shutil.which("curl") is None:
        print("[warn] curl not in PATH (only used for diagnostics).", file=sys.stderr)

    all_results: list[FetchResult] = []
    for cat in cats:
        urls = read_manifest(cat)
        print(
            f"[refetch] {cat}: {len(urls)} URLs in manifest",
            file=sys.stderr,
        )
        all_results.extend(
            fetch_category(cat, urls, args.only_failed, args.dry_run)
        )

    write_report(all_results)
    failed = sum(1 for r in all_results if r.status == "failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
