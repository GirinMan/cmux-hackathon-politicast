"""Election / Position type controlled vocabulary.

PolitiKAST 5 region 시나리오에서 등장하는 두 종류 (광역단체장 / 국회의원
보궐) 를 박제한다. KG ontology, scenario JSON, paper appendix 가 모두
이 단일 vocab 을 참조한다.

Vocab 확장 시 본 파일 + 시나리오 + KG ontology + paper 부록을 함께 갱신한다.
"""
from __future__ import annotations

from typing import Literal, Optional, get_args

from pydantic import BaseModel, ConfigDict


# Position-type vocab — `Literal` 로 IDE/타입체커가 catch.
# 5 region 시나리오 합집합:
#   - metropolitan_mayor      서울/광주/대구 광역시장
#   - national_assembly_by_election  부산 북구갑·대구 달서갑 보궐
# 잠재 확장:
#   - basic_mayor             기초자치단체장
#   - regional_council        지방의회
#   - presidential            대선
PositionType = Literal[
    "metropolitan_mayor",
    "basic_mayor",
    "national_assembly_by_election",
    "regional_council",
    "presidential",
]

# Election-type 은 Position 보다 상위 분류 (사이클·법적 카테고리).
ElectionType = Literal[
    "local",        # 지방선거 일반
    "by_election",  # 보궐
    "general",      # 총선
    "presidential", # 대선
]


def position_type_values() -> tuple[str, ...]:
    return get_args(PositionType)


def election_type_values() -> tuple[str, ...]:
    return get_args(ElectionType)


def is_valid_position_type(value: object) -> bool:
    return isinstance(value, str) and value in position_type_values()


def is_valid_election_type(value: object) -> bool:
    return isinstance(value, str) and value in election_type_values()


class TypologyEntry(BaseModel):
    """Position 또는 Election 키-라벨 매핑."""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    description: Optional[str] = None


# 5 region 라벨 (한국어). 논문/대시보드 표에서 사용.
POSITION_TYPE_LABELS: dict[str, str] = {
    "metropolitan_mayor": "광역단체장",
    "basic_mayor": "기초단체장",
    "national_assembly_by_election": "국회의원 보궐",
    "regional_council": "지방의회",
    "presidential": "대통령",
}

ELECTION_TYPE_LABELS: dict[str, str] = {
    "local": "지방선거",
    "by_election": "보궐선거",
    "general": "총선",
    "presidential": "대선",
}


__all__ = [
    "ELECTION_TYPE_LABELS",
    "ElectionType",
    "POSITION_TYPE_LABELS",
    "PositionType",
    "TypologyEntry",
    "election_type_values",
    "is_valid_election_type",
    "is_valid_position_type",
    "position_type_values",
]
