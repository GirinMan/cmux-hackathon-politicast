"""Nemotron-Personas-Korea 페르소나 스키마.

기존 src/data/ingest.py:21-43 에 흩어져 있던 컬럼 화이트리스트를 모듈 상수로
끌어올렸다. ingest 코드는 이 상수들을 import 해서 사용한다 — 새 컬럼/지역
추가 시 단일 위치만 갱신하면 된다.

PersonaCore/PersonaText 는 DuckDB persona_core / persona_text 테이블 row
shape 를 그대로 반영한다. parquet 원본의 모든 컬럼을 받지 않고, 시뮬에서
실제 사용하는 코어만 검증한다 — 그 외 필드는 `extra="allow"` 로 보존.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


PERSONA_TEXT_SUFFIX = "_persona"

PERSONA_CORE_COLUMNS: tuple[str, ...] = (
    "uuid",
    "sex",
    "age",
    "marital_status",
    "education_level",
    "occupation",
    "department",
    "job_title",
    "city",
    "country",
    "household_income",
    "skills_and_expertise",
    "hobbies_and_interests",
    "religion",
)

# province / district 컬럼은 데이터셋마다 표기가 다르므로 후보 리스트.
# 첫 번째 매칭이 채택된다 (src/data/ingest.py::pick_first_existing).
PERSONA_PROVINCE_CANDIDATES: tuple[str, ...] = (
    "province", "region", "state", "do", "sido",
)
PERSONA_DISTRICT_CANDIDATES: tuple[str, ...] = (
    "district", "city", "sigungu", "county",
)


class PersonaCore(BaseModel):
    """persona_core 테이블 row — 시뮬에서 사용하는 코어 필드만 검증."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    uuid: str
    sex: Optional[str] = None
    age: Optional[int] = None
    marital_status: Optional[str] = None
    education_level: Optional[str] = None
    occupation: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    household_income: Optional[str] = None
    skills_and_expertise: Optional[str] = None
    hobbies_and_interests: Optional[str] = None
    religion: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None


class PersonaText(BaseModel):
    """persona_text 테이블 row — *_persona suffix 텍스트 컬럼 모음."""

    model_config = ConfigDict(extra="allow")

    uuid: str
    persona: Optional[str] = None
    professional_persona: Optional[str] = None
    sports_persona: Optional[str] = None
    arts_persona: Optional[str] = None
    travel_persona: Optional[str] = None
    culinary_persona: Optional[str] = None
    family_persona: Optional[str] = None
