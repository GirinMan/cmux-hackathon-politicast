"""Demo seed export — data-engineer 시나리오 박제 전 dashboard/sim 이 개발할 수
있도록 합성 시나리오로 KG snapshot을 ``_workspace/snapshots/`` 에 떨어뜨린다.

data-engineer 가 실제 scenario JSON 을 박제하면 이 데모는 자동으로 무시됨
(``build_kg_from_scenarios`` 가 실제 scenarios/*.json 을 읽기 시작).

실행:
    docker compose run --rm app python -m src.kg.seed_demo
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from src.kg.builder import build_kg_from_dicts, _summary
from src.kg.export_d3 import export_all
from src.kg.firewall import _make_synthetic_scenario

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    G, index = build_kg_from_dicts([_make_synthetic_scenario()])
    summary = _summary(G, index)
    print("[seed-demo] KG summary:")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    paths = export_all(G, index)
    for p in paths:
        print(f"[seed-demo] wrote {p.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
