# LLMPool E2E 검증 리포트 (prod fire 직전)

- **시각:** 2026-04-26 (해커톤 Day)
- **컨테이너:** `politikast:dev` (python 3.11.15, litellm `unknown` 버전 — `__version__` 미노출, but >=1.50 설치됨)
- **검증 스크립트:** `/Users/girinman/repos/cmux-hackathon-politicast/_workspace/research/llmpool_e2e_validation.py`
- **결론:** 🔴 **prod fire 금지** — `LLMPool.chat()`에 **2건 critical 버그**.
  버그 1은 monkey-patch 없이 모든 호출이 `UnboundLocalError`로 실패. 버그 2는
  per-call model override 시 잘못된 provider의 API 키를 사용해서 401.

---

## 요약 표

| # | 검증 항목 | 결과 | 비고 |
|---|-----------|------|------|
| Dev-1 | dev override (OpenAI 명시 → Gemini 라우팅) | 🟡 **PASS w/ patch** | `서울` 응답, init_provider=openai로 stats가 표시되지만 실제 호출은 Gemini (모니터 OK). 버그 1 패치 후. |
| Prod-a | OpenAI gpt-5.4-nano | 🟡 **PASS w/ patch** | `{"answer":"서울"}`, 26.7s (cold start). `max_tokens` → `max_completion_tokens` 자동 변환 OK. reasoning 토큰 없이 정상 응답. |
| Prod-b | OpenAI gpt-5.4-mini (per-call override on OpenAI pool) | 🟡 **PASS w/ patch** | `{"answer":"도쿄"}`, 1.75s. **단 동일 provider 한정**. |
| Prod-c | Anthropic claude-sonnet-4-6 | 🟡 **PASS w/ patch** | `\`\`\`json {"answer":"파리"} \`\`\``, 4.0s. **응답이 markdown fence로 감싸져 있음** — JSON 파싱 시 strip 필요. |
| Prod-d | Gemini gemini-3.1-flash-lite-preview | 🟡 **PASS w/ patch** | `{"answer": "런던"}`, 2.5s. thinking 비활성 OK. |
| Prod-e | per-call override **across providers** (Gemini pool → OpenAI 모델) | 🔴 **FAIL** | `AuthenticationError: OpenAIException - Incorrect API key provided: AIzaSyDT***...QMqk` — Gemini 키가 OpenAI 호출에 잘못 사용됨. |
| Prod-f | Cache hit (동일 prompt 2회) | 🟢 **PASS** | `cache_hits 0→1` 증가 확인, 응답 일치. |

---

## 발견된 버그

### 버그 1 (CRITICAL, 모든 호출 실패): `UnboundLocalError`

`src/llm/llm_pool.py` `chat()` 메서드(361~407라인)에서 `cache_extra` 빌드 시
`effective_provider`/`effective_model` 참조가 정의보다 위에 있음.

```python
# 현재 (버그): cache_extra가 effective_* 정의 전에 사용됨
cache_extra = {..., "provider": effective_provider, ...}    # line 364
cache_key = _SqliteCache.make_key(chat_msgs, effective_model, cache_extra)  # line 367
...
effective_model = model or self.model                       # line 382 (defined here)
effective_provider = _derive_provider(effective_model)
```

**증상:** patch 없이 dev 모드 첫 호출에서 `UnboundLocalError: cannot access local
variable 'effective_provider' where it is not associated with a value`. **prod 도
완전히 동일하게 실패**.

**수정 권고 (보고만):** `effective_model`/`effective_provider` 정의 블록을
`cache_extra` 빌드 직전으로 이동. 검증 스크립트 `_apply_unbound_local_patch()` 가
참고 구현. 순서만 바꾸면 됨.

### 버그 2 (CRITICAL, per-call model override 깨짐): provider mismatch 시 키 미스매치

`_call_with_retry()`에서 `state.api_key`는 `self.provider` 기준으로 수집된 키지만,
per-call override로 다른 provider 모델을 호출해도 `state.api_key` 그대로 전달됨
(`kwargs["api_key"] = state.api_key`). 결과: Gemini 키(`AIzaSy...`)가 OpenAI 엔드포인트로
넘어가 `Incorrect API key provided` 401.

**수정 권고 (보고만):**
- `_call_with_retry`에서 `eff_provider != self.provider`이면 `eff_provider`용 키를
  env에서 즉석 fetch (single key, no rotation), 또는
- `LLMPool`을 provider별로 1개씩 둬서 per-call override 자체를 multi-pool 디스패처로 변경.
- 빠른 해결: chat에서 effective_provider 추론한 직후 해당 env 키를 직접 kwargs에 박는 helper 추가.

### 관찰 1 (NON-BLOCK): Anthropic JSON 응답 fence

claude-sonnet-4-6은 `response_format={"type": "json_object"}`를 LiteLLM 경유 시
지원하지 않거나 무시됨 → 출력이 ```` ```json ... ``` ```` markdown fence로 감싸짐.
다운스트림 파서에서 fence strip + `json.loads` 필요 (또는 LiteLLM의
`anthropic_force_json_via_tool_use` 옵션 검토).

### 관찰 2 (NON-BLOCK): `max_tokens` → `max_completion_tokens` 자동 변환

OpenAI gpt-5.x는 `max_completion_tokens`만 지원하지만, LiteLLM 1.50+이 자동
변환해서 정상 응답 (`{"answer":"서울"}`). 추가 패치 **불필요**. reasoning 토큰
없이 즉시 답변 — `reasoning_effort="none"` 효과 확인됨.

### 관찰 3 (NON-BLOCK): Stats가 init_model 기준으로만 표시됨

`LLMPool.stats()`의 `provider`/`model`이 `__init__` 시점 값 — dev override나
per-call override 시 effective 값이 보이지 않음. 디버깅에는 미흡하나 동작에는
영향 없음.

### 관찰 4 (NON-BLOCK): `litellm.__version__` 미노출

`getattr(litellm, "__version__", "unknown")` → `unknown`. requirements.txt에
`litellm>=1.50.0` 명시되어 있고 OpenAI gpt-5 자동 변환이 동작하므로 1.50+ 설치
확정. 단순 정보 부족.

---

## 다운스트림 영향 평가 (prod fire 시)

- **VoterAgent**: prod에서 OpenAI gpt-5.4-nano를 voter conditional model로 쓸
  계획이라면, **버그 1 패치는 필수**. 단일 provider pool이라면 버그 2는 영향 없음.
- **Multi-provider 배치 (interview는 Claude, voter는 Gemini, 등)**: 별도
  `LLMPool` 인스턴스 per provider 권장. per-call override는 버그 2 수정 전까지
  **사용 금지**.
- **Cache 동작**: 정상. 동일 prompt 재호출 비용 0. 시뮬 timestep 반복에서 안전.

---

## 권고 액션 (사용자 결정 필요)

1. 🔴 **버그 1 패치** — `effective_model`/`effective_provider` 정의 라인 이동.
   소요 5분. **prod fire 전 필수**.
2. 🔴 **버그 2 패치 또는 운영 가드** — per-call cross-provider override 금지하거나
   `_call_with_retry`에 effective_provider별 키 fetch 로직 추가. 소요 10~15분.
3. 🟡 **Claude 응답 fence strip 유틸** 다운스트림 파서에 추가 (한 줄).
4. 🟢 (선택) `LLMPool.stats()`에 `effective_model_last` 필드 추가하여 디버깅 향상.

---

## 박제 파일

- 스크립트: `/Users/girinman/repos/cmux-hackathon-politicast/_workspace/research/llmpool_e2e_validation.py`
- 리포트: `/Users/girinman/repos/cmux-hackathon-politicast/_workspace/research/llmpool_e2e_validation_report.md`
- 재실행:
  ```bash
  cd /Users/girinman/repos/cmux-hackathon-politicast
  docker compose run --rm -e POLITIKAST_ENV=dev  -e LLMPOOL_PATCH=1 app \
      python _workspace/research/llmpool_e2e_validation.py dev
  docker compose run --rm -e POLITIKAST_ENV=prod -e LLMPOOL_PATCH=1 app \
      python _workspace/research/llmpool_e2e_validation.py prod
  ```
  `LLMPOOL_PATCH=1` 빼면 버그 1 재현 가능 (모든 체크 UnboundLocalError).

총 API 호출 비용: ~ $0.005 (5건 prod 호출 + Gemini cache hit 1건). 가드레일 준수.
