"""FastAPI OpenAPI 명세 export — frontend codegen 입력.

출력: _workspace/contracts/openapi.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "_workspace" / "contracts" / "openapi.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    args.out.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.out.relative_to(REPO_ROOT)}  ({len(schema.get('paths') or {})} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
