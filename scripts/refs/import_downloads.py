#!/usr/bin/env python3
"""
Import manually downloaded files from docs/downloads/ into docs/references/raw/
using the mapping in docs/references/manifests/manual-downloads.tsv.

When a URL refuses to be fetched programmatically (auth wall, 403, expired
cert), download the file by hand into docs/downloads/, register it in the TSV,
and run this script. The file is converted (PDF → text, HTML → markdown) and
written to the same slug path that refetch_references.py would have produced,
so the rest of the pipeline (KB rebuild, refetch report) finds it transparently.

Usage:
  python scripts/refs/import_downloads.py                  # promote everything in TSV
  python scripts/refs/import_downloads.py --dry-run        # show what would happen
  python scripts/refs/import_downloads.py --keep-source    # do not delete docs/downloads file
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# reuse helpers from the sibling refetch script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from refetch_references import (  # type: ignore  # noqa: E402
    REPO_ROOT,
    RAW_DIR,
    MANIFEST_DIR,
    ensure_deps,
    html_to_markdown,
    pdf_to_text,
    slugify,
)

DOWNLOADS_DIR = REPO_ROOT / "docs/downloads"
MAPPING_PATH = MANIFEST_DIR / "manual-downloads.tsv"


def read_mapping() -> list[tuple[str, str, str]]:
    if not MAPPING_PATH.exists():
        return []
    rows: list[tuple[str, str, str]] = []
    for lineno, raw in enumerate(
        MAPPING_PATH.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            print(
                f"[warn] {MAPPING_PATH.name}:{lineno}: expected 3 tab-separated "
                f"fields, got {len(parts)}: {line!r}",
                file=sys.stderr,
            )
            continue
        rows.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return rows


def convert(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return pdf_to_text(file_path.read_bytes())
    if suffix in {".html", ".htm", ".xhtml"}:
        return html_to_markdown(file_path.read_text(encoding="utf-8", errors="replace"))
    if suffix in {".md", ".txt"}:
        return file_path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"unsupported extension {suffix!r} for {file_path.name}")


def import_one(
    fname: str,
    category: str,
    url: str,
    *,
    dry_run: bool,
    keep_source: bool,
) -> dict[str, str]:
    src = DOWNLOADS_DIR / fname
    if not src.exists():
        return {"file": fname, "status": "missing", "detail": f"not in {DOWNLOADS_DIR}"}

    slug = slugify(url)
    out_path = RAW_DIR / category / f"{slug}.md"
    rel_out = out_path.relative_to(REPO_ROOT)
    if dry_run:
        return {
            "file": fname,
            "status": "would-import",
            "detail": f"→ {rel_out}",
        }

    try:
        body = convert(src)
    except Exception as exc:  # noqa: BLE001
        return {"file": fname, "status": "convert-error", "detail": str(exc)}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# Source: {url}\n"
        f"<!-- imported from: docs/downloads/{fname} -->\n"
        f"<!-- imported at: {time.strftime('%Y-%m-%d %H:%M:%S %z')} -->\n\n"
    )
    out_path.write_text(header + body.strip() + "\n", encoding="utf-8")

    if not keep_source:
        src.unlink()

    return {
        "file": fname,
        "status": "ok",
        "detail": f"→ {rel_out} ({out_path.stat().st_size:,} bytes)",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--keep-source",
        action="store_true",
        help="Do not delete docs/downloads/<file> after import.",
    )
    ap.add_argument(
        "--no-install",
        action="store_true",
        help="Skip auto pip install of dependencies.",
    )
    args = ap.parse_args()

    if not args.no_install:
        ensure_deps()

    rows = read_mapping()
    if not rows:
        print(f"[import] no entries in {MAPPING_PATH}", file=sys.stderr)
        return 0

    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[import] {len(rows)} mappings, dry_run={args.dry_run}", file=sys.stderr)

    failed = 0
    for fname, category, url in rows:
        result = import_one(
            fname,
            category,
            url,
            dry_run=args.dry_run,
            keep_source=args.keep_source,
        )
        flag = "✓" if result["status"] in {"ok", "would-import"} else "✗"
        print(f"  {flag} {result['status']:14s} {fname}  {result['detail']}")
        if result["status"] not in {"ok", "would-import"}:
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
