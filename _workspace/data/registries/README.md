# `_workspace/data/registries/`

PolitiKAST 의 controlled-vocabulary / config registry 모음. 모든 파일은 git-tracked 이며, **각 JSON 파일별로 src/schemas 하위의 Pydantic 모델이 SoT(Single Source of Truth)** 다. JSON 은 schema-validated config 일 뿐이며, 코드는 항상 schema 모델을 통해서만 읽는다.

| Registry JSON | Pydantic SoT (src/schemas/) | Owner stream | Loader |
|---|---|---|---|
| `election_calendar.json` | `calendar.ElectionCalendar` | cal-stream | `load_election_calendar()` |
| `parties.json` | `party.PartyRegistry` | vocab-stream | `load_party_registry()` |
| `age_buckets.json` | `cohort.AgeBuckets` | vocab-stream | `load_age_buckets()` |
| `pollsters.json` | `pollster.PollsterRegistry` | infra-tidy | `load_pollster_registry()` |
| `persona_axes.json` | `persona_axis.PersonaAxisRegistry` | vocab-stream | `load_persona_axes()` |
| `candidates.json` | `candidate_registry.CandidateRegistry` | adapter-structured | `load_candidate_registry()` |
| `issues.json` | `issue_registry.IssueRegistry` | adapter-llm | `load_issue_registry()` |
| `persons.json` | `person_registry.PersonRegistry` | adapter-llm | `load_person_registry()` |
| `data_sources.json` | `data_source.DataSourceRegistry` | orchestrator | `load_data_source_registry()` |

## 새 registry 추가 절차

1. `src/schemas/<name>.py` 에 Pydantic 모델 + `load_<name>()` 함수 작성 (`@lru_cache`).
2. `src/schemas/__init__.py` 에 re-export.
3. `_workspace/data/registries/<name>.json` 작성. `version: "v1"` 필드 박제.
4. `scripts/export_jsonschema.py` 의 `EXPORTS` dict 에 추가 (논문/외부 도구용 JSON Schema 내보내기).
5. 본 README 표에 한 줄 추가.
6. `make schema-export && make test` 통과 확인.

## 환경 변수 override

`POLITIKAST_REGISTRY_DIR=/abs/path` 를 설정하면 본 디렉토리 대신 해당 경로의 동일 파일명을 우선 로드한다 (현재는 `pollsters.json` 만 지원, 다른 registry 도 같은 패턴으로 확장 가능). 미설정 시 기본 경로 사용.

## Backward compatibility

- 구 `_workspace/data/poll_priors.json` 위치는 deprecated. `pollsters.json` 가 없을 때만 fallback 로드된다 (`PollsterRegistry._coerce_legacy`). 신규 작업은 `registries/pollsters.json` 만 사용.
