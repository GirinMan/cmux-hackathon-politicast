#!/usr/bin/env python
"""스냅샷 v0 → v1 migration.

`_workspace/snapshots/results/*.json` 의 파일들을:
  1. ScenarioResult Pydantic 모델로 round-trip
  2. `schema_version: "v1"` 필드 박제
  3. 같은 위치에 덮어쓰기 (idempotent)

실패한 파일은 `_workspace/snapshots/results/_quarantine/` 로 격리한다.
`--dry-run` 모드에서는 실제 쓰기 없이 결과만 출력한다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from pydantic import ValidationError

from src.schemas import SCHEMA_VERSION, ScenarioResult

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = REPO_ROOT / "_workspace" / "snapshots" / "results"
QUARANTINE_NAME = "_quarantine"


def migrate_one(path: Path, *, dry_run: bool) -> tuple[str, str]:
    """Returns (status, detail) where status ∈ {ok, skip, fail}."""
    try:
        raw = json.loads(path.read_text())
    except Exception as e:
        return "fail", f"unreadable JSON: {e}"
    if raw.get("schema_version") == SCHEMA_VERSION:
        return "skip", "already v1"
    try:
        model = ScenarioResult.model_validate(raw)
    except ValidationError as e:
        return "fail", f"validation error: {str(e)[:200]}"
    out = model.model_dump(mode="json", exclude_none=False)
    out["schema_version"] = SCHEMA_VERSION
    if not dry_run:
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return "ok", "migrated"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dir.exists():
        print(f"[migrate] dir not found: {args.dir}", file=sys.stderr)
        return 2

    files = sorted(p for p in args.dir.glob("*.json") if p.is_file())
    quarantine = args.dir / QUARANTINE_NAME

    counts = {"ok": 0, "skip": 0, "fail": 0}
    failures: list[tuple[Path, str]] = []
    for f in files:
        status, detail = migrate_one(f, dry_run=args.dry_run)
        counts[status] += 1
        marker = {"ok": "✔", "skip": "·", "fail": "✗"}[status]
        print(f"  {marker} {f.name}: {detail}")
        if status == "fail":
            failures.append((f, detail))

    if failures and not args.dry_run:
        quarantine.mkdir(exist_ok=True)
        for f, _ in failures:
            shutil.move(str(f), str(quarantine / f.name))
            print(f"    quarantined → {quarantine / f.name}")

    print(
        f"\n[migrate] dir={args.dir} dry_run={args.dry_run} "
        f"ok={counts['ok']} skip={counts['skip']} fail={counts['fail']}"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
