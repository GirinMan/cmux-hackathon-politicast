"""Persona sample service — DuckDB region view 위주.

`src/data/queries.py:sample_personas` 를 호출. db-postgres rewrite 가 완료되면
SQLAlchemy AsyncSession 으로 이식.
"""
from __future__ import annotations

import logging
from typing import Optional

from ..schemas.public_dto import PersonaSampleDTO

logger = logging.getLogger("backend.persona")


class PersonaService:
    def sample(
        self, region_id: str, n: int = 30, seed: Optional[int] = None
    ) -> list[PersonaSampleDTO]:
        try:
            from src.data.queries import sample_personas  # type: ignore
        except Exception as e:
            logger.warning("persona service degraded — sample_personas import: %s", e)
            return []
        try:
            records = sample_personas(region_id=region_id, n=n, seed=seed)  # type: ignore[call-arg]
        except Exception as e:
            logger.warning("persona service degraded — query failed: %s", e)
            return []

        out: list[PersonaSampleDTO] = []
        for r in records:
            d = r if isinstance(r, dict) else getattr(r, "__dict__", {})
            out.append(
                PersonaSampleDTO(
                    persona_id=str(d.get("persona_id") or d.get("id") or ""),
                    age=d.get("age"),
                    gender=d.get("gender"),
                    education=d.get("education"),
                    province=d.get("province"),
                    district=d.get("district") or d.get("province_district"),
                    summary=str(d.get("persona_summary") or d.get("summary") or ""),
                )
            )
        return out


persona_service = PersonaService()

__all__ = ["persona_service", "PersonaService"]
