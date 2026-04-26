# LLMPool Cost Guard — 설계 결정 + 검증 결과

**작성:** 2026-04-26 (PolitiKAST 해커톤 Phase 2)
**범위:** `src/llm/llm_pool.py` 비용 추적 + 임계 throw 가드
**목적:** prod fire 직후 비용 폭주 방지 — provider별 누적 비용이 임계 도달 시 즉시 abort.

---

## 1. 설계 결정

### 1.1 신규 예외 — `LLMCostThresholdError`
- `LLMPoolError`의 서브클래스.
- **retry 대상이 아님** (tenacity의 `retry_if_exception_type=(RateLimitError, NetworkError)` 리스트에 포함되지 않음).
- 한 번 throw하면 즉시 abort — 호출자가 캐치해서 fallback 또는 명시적 종료 처리.

### 1.2 비용 추적 위치 — `_call_with_retry` 직후 + 사전 가드
- **사전 가드** (`_enforce_cost_threshold`): `chat()` 진입부에서 누적 비용을 검사해 임계 초과 시 즉시 throw. 캐시 hit/miss 모두 동일하게 차단(이미 위험한 호출자가 추가 시도하는 것을 막기 위함).
- **사후 누적** (`_record_cost`): `litellm.completion()` 응답 직후 `litellm.completion_cost(completion_response=resp)` 호출하여 비용 적립. 다음 호출에서 사전 가드가 throw.
- 이 패턴의 결과: 임계 직전 1회는 통과, 직후 2회차에서 abort. ($0.001 임계라면 최악의 경우 $0.001 + (1회 max cost)까지 청구 가능 — 운영상 충분히 보수적.)

### 1.3 dev 모드 — 추적 자체 skip
- `POLITIKAST_ENV=dev`이면 `_record_cost`/`_enforce_cost_threshold` 모두 즉시 return.
- 이유: dev에선 Gemini Flash Lite preview tier (무료) 사용. 누적 카운터가 의미 없음.
- `stats()`의 `cost_tracking_enabled: False`로 노출.

### 1.4 Provider별 임계 — 환경변수
| 변수 | 기본값(.env) | 사용자 예산 | 임계 비율 |
|------|--------------|-------------|-----------|
| `LLM_COST_THRESHOLD_OPENAI_USD`     | `50` | $300 | 17% (다소 낮음 — 첫 가드) |
| `LLM_COST_THRESHOLD_ANTHROPIC_USD`  | `20` | $25  | 80% (긴급 알림성) |
| `LLM_COST_THRESHOLD_GEMINI_USD`     | `5`  | 무료 | preview tier 청구 발생 시 즉시 abort |

env 미설정 시 `inf` (가드 비활성화) — 기존 코드 호환성 유지.

### 1.5 LiteLLM `completion_cost()` 인식 실패 fallback
- 신규 모델 (예: `gpt-5.4-nano`, `gpt-5.4-mini`)이 LiteLLM 가격표에 없을 수 있음.
- 인식 실패 시 `try/except`로 캐치 → `0.0` 적립 + `logger.warning`.
- 실측 결과 (LiteLLM 1.50+):
  - `gpt-5.4-nano` (150 토큰): `$0.000082` **인식 OK**
  - `gpt-5.4-mini` (150 토큰): `$0.000300` **인식 OK**
  - `gpt-4o-mini` (150 토큰): `$0.000045` **인식 OK**
- 결론: 현재 모델 전부 정상 인식. 향후 신규 모델 등장 시 자동 0 fallback로 안전.

### 1.6 사전 가드 위치 — 캐시 hit도 차단
- 캐시 hit는 자체 비용 0이지만, 이미 임계를 넘은 상태라면 호출자가 후속 비용 호출을 만들 가능성이 높음. 시스템적으로 차단해 cascade 방지.
- 동시에 cost 가드 자체가 `pool.chat()` API의 hard contract 임을 명확히 함.

---

## 2. 검증 결과 (`scripts/verify_llmpool_cost_guard.py`)

도커 컨테이너 (`politikast-app`)에서 실행:

```bash
docker compose exec app python scripts/verify_llmpool_cost_guard.py
```

| # | 시나리오 | 결과 |
|---|---------|------|
| 1 | low-threshold ($0.001) + mock cost $0.005 → 2회차 throw | OK — `LLMCostThresholdError` 발생 |
| 2 | 정상 (env unset → inf threshold) → 5회 모두 통과 | OK — 누적 $0.000500 |
| 3 | dev 모드 — cost_tracking_enabled=False, 누적 0 | OK |
| 4 | `completion_cost()` 예외 → 0 fallback + warn | OK |
| 5 | `stats()` 스키마 (`cost_usd` / `cost_thresholds` / `cost_tracking_enabled` 키) | OK |
| 6 | 실제 LiteLLM `completion_cost()` — gpt-5.4-nano/mini/4o-mini 인식 | **3/3 인식 OK** |

**전체:** ALL OK.

---

## 3. 사용 권고

### prod 운영 (`POLITIKAST_ENV=prod` 또는 unset)
- 자동 활성. 별도 코드 변경 불필요.
- `pool.chat()` 호출 도중 `LLMCostThresholdError` 발생 가능 — **반드시 catch하여 graceful shutdown 처리**.
- 권장 처리:
  ```python
  try:
      out = pool.chat(...)
  except LLMCostThresholdError as e:
      logger.error("Cost guard fired: %s", e)
      # 1) 시뮬레이션 즉시 freeze
      # 2) checkpoint 저장
      # 3) 사용자에게 escalate (정책 결정 필요)
      raise SystemExit(2)
  ```

### dev 운영 (`POLITIKAST_ENV=dev`)
- 비용 추적 자체 skip. 기존 동작 그대로.
- Gemini Flash Lite preview tier 사용 가정 — preview 종료 시점에 prod 모드 + 적절한 임계로 전환.

### 임계 조정
- 단계적 권고 (사용자 예산 기준):
  - **OpenAI** $300 예산 → 첫 가드 $50 (17%), 후속 단계 $150 / $250로 ladder 가능.
  - **Anthropic** $25 예산 → 첫 가드 $20 (80% — 긴급).
  - **Gemini** 무료 → $5 (preview tier 청구 발생 즉시 알림성 abort).

### 모니터링
- `pool.stats()`에 다음 키 노출:
  - `cost_usd: {provider: float}`
  - `cost_thresholds: {provider: float}`
  - `cost_tracking_enabled: bool`
- 대시보드(`ui/dashboard/`)에서 폴링하여 실시간 게이지 표시 권장.

---

## 4. 부수 효과 — 기존 버그 수정

`chat()` 메서드에서 `effective_provider` / `effective_model` 변수가 **선언 전에 사용**되던 버그를 함께 수정 (캐시 키 생성부에서 `NameError` 발생 위험).

수정 전 (line 364):
```python
cache_extra = { ..., "provider": effective_provider, ... }  # NameError
...
effective_model = model or self.model  # 뒤에 선언
```

수정 후: `effective_*` 선언을 캐시 키 생성보다 먼저로 이동.

---

## 5. 변경 라인 수 요약

`src/llm/llm_pool.py`:
- **추가:** `LLMCostThresholdError` 클래스, `_load_cost_thresholds()`, `_enforce_cost_threshold()`, `_record_cost()`, stats() 확장
- **수정:** `chat()` — 변수 선언 순서 + 사전 가드 호출 추가
- **수정:** `_call_with_retry()` — 응답 직후 `_record_cost(eff_provider, resp)` 호출
- 총 변경: 약 **+90 라인** (신규), **~10 라인** 재배치/수정

`scripts/verify_llmpool_cost_guard.py`: **신규 (~250 라인, 6 시나리오)**.

`_workspace/research/llmpool_cost_guard.md`: **신규 (이 문서)**.
