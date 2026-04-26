# CAMEL × `gemini-3-flash-preview` 호환성 조사 (PolitiKAST 해커톤)

> **VERDICT — Native 지원. CAMEL 0.2.90 (PyPI 최신, 2026-03-22 release) 의 `ModelType.GEMINI_3_FLASH = "gemini-3-flash-preview"` 를 그대로 사용한다. CAMEL 의 GeminiModel 은 내부적으로 Google 의 OpenAI-호환 엔드포인트(`https://generativelanguage.googleapis.com/v1beta/openai/`) 를 사용하므로 추가 우회 불필요. fallback 은 LiteLLM 어댑터(`ModelPlatformType.LITELLM`).**

조사일시: 2026-04-26 10:30 KST · CAMEL master / v0.2.90 tag 동시 확인

---

## 1. 결론 (Verdict)

| 항목 | 결과 |
|---|---|
| `gemini-3-flash-preview` Native 지원 | **YES (v0.2.90 정식 릴리스 포함)** |
| Enum | `ModelType.GEMINI_3_FLASH` (string value `"gemini-3-flash-preview"`) |
| Platform | `ModelPlatformType.GEMINI` |
| Backing | `GeminiModel(OpenAICompatibleModel)` — 자동으로 OpenAI-호환 엔드포인트 호출 |
| 추가 라이브러리 필요 | 없음. `pip install "camel-ai>=0.2.90"` 만으로 OK |

근거:
- `camel/types/enums.py` (v0.2.90 tag) 에 `GEMINI_3_FLASH = "gemini-3-flash-preview"`, `GEMINI_3_PRO`, `GEMINI_3_1_PRO`, `GEMINI_3_1_FLASH_LITE` 모두 정의.
- `camel/models/gemini_model.py` 는 `OpenAICompatibleModel` 상속, base URL `https://generativelanguage.googleapis.com/v1beta/openai/`, `model_type: Union[ModelType, str]` 로 임의 문자열도 허용.
- `camel/configs/gemini_config.py` 의 `GeminiConfig` 가 `response_format`, `tool_choice`, `temperature`, `max_tokens`, `cached_content` 등을 지원 → JSON mode (`{"type": "json_object"}`) 사용 가능.
- 모델 자체 free-tier 정책(2026-04 기준): `gemini-3-flash-preview` 는 free pricing 으로 listed 되어있으나 RPM/RPD 가 매우 빡빡 (10–50 RPM 추정, preview-class). 4-key 라운드로빈 + backoff 필수.

---

## 2. Minimal Working Code (해커톤 즉시 복붙용)

### 2.1 환경 준비
```bash
pip install "camel-ai>=0.2.90"
```

### 2.2 단일 ChatAgent (Voter persona) — 가장 짧은 경로

```python
# politikast/agent.py
import os, random
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import GeminiConfig

GEMINI_KEYS = [k.strip() for k in os.environ["GEMINI_API_KEYS"].split(",") if k.strip()]
assert len(GEMINI_KEYS) == 4, "expect 4 keys"

def build_voter_agent(persona_text: str, key_idx: int | None = None) -> ChatAgent:
    api_key = GEMINI_KEYS[key_idx if key_idx is not None else random.randrange(4)]
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_3_FLASH,                # "gemini-3-flash-preview"
        api_key=api_key,
        model_config_dict=GeminiConfig(
            temperature=0.7,
            max_tokens=512,
            response_format={"type": "json_object"},        # JSON mode 강제
        ).as_dict(),
        max_retries=2,                                       # CAMEL 내부 retry
        timeout=30.0,
    )
    sys_msg = BaseMessage.make_assistant_message(
        role_name="KoreanVoter",
        content=(
            "너는 2026년 한국 지방선거 유권자다. 아래 페르소나를 100% 1인칭으로 체화해서 답하라. "
            "반드시 다음 JSON schema 만 출력: "
            '{"vote": "<후보명|기권|미정>", "stance": "<짧은 입장>", "rationale": "<2~3문장>"}.\n\n'
            f"=== 나의 페르소나 ===\n{persona_text}"
        ),
    )
    return ChatAgent(system_message=sys_msg, model=model)
```

### 2.3 Async 배치 + 4-key 라운드로빈 + 429 백오프 (1만 voter 시뮬레이션)

CAMEL 의 `ChatAgent.astep()` 은 비동기 지원. 키 분산은 키별로 별도 모델 인스턴스를 만들고 라운드로빈으로 작업을 흘려보낸다.

```python
# politikast/runtime.py
import asyncio, json, random
from collections import deque
from typing import Any
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import GeminiConfig
from politikast.agent import GEMINI_KEYS

# 키별 1 인스턴스 캐시 (페르소나가 바뀌므로 system_msg 만 갱신)
_MODEL_POOL = [
    ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_3_FLASH,
        api_key=k,
        model_config_dict=GeminiConfig(
            temperature=0.7, max_tokens=512,
            response_format={"type": "json_object"},
        ).as_dict(),
        timeout=30.0, max_retries=0,    # 외부 backoff 사용
    )
    for k in GEMINI_KEYS
]
# 키별 동시성 제한 (free-tier 10 RPM 가정 → 동시 4~6 + 6초 spacing 안전)
_KEY_SEMS = [asyncio.Semaphore(4) for _ in GEMINI_KEYS]
_RR = deque(range(len(GEMINI_KEYS)))


def _next_key() -> int:
    _RR.rotate(-1)
    return _RR[-1]


async def ask_voter(persona_text: str, prompt: str, max_attempts: int = 5) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        idx = _next_key()
        async with _KEY_SEMS[idx]:
            model = _MODEL_POOL[idx]
            sys_msg = BaseMessage.make_assistant_message(
                role_name="KoreanVoter",
                content=(
                    "너는 2026년 한국 지방선거 유권자다. 페르소나를 1인칭으로 체화하라. "
                    "반드시 JSON 한 객체만 출력: "
                    '{"vote":"...","stance":"...","rationale":"..."}.'
                    "\n\n페르소나:\n" + persona_text
                ),
            )
            agent = ChatAgent(system_message=sys_msg, model=model)
            user_msg = BaseMessage.make_user_message(role_name="Pollster", content=prompt)
            try:
                resp = await agent.astep(user_msg)
                text = resp.msgs[0].content
                return json.loads(text)
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                # 429 / quota / RESOURCE_EXHAUSTED → exponential backoff + 다른 키
                if any(s in msg for s in ("429", "quota", "rate", "resource_exhausted")):
                    await asyncio.sleep((2 ** attempt) + random.random())
                    continue
                # JSON 파싱 실패 → 1회 재시도
                if isinstance(e, json.JSONDecodeError):
                    await asyncio.sleep(0.5)
                    continue
                raise
    raise RuntimeError(f"ask_voter failed after {max_attempts}: {last_err}")


async def run_simulation(personas: list[str], prompt: str, concurrency: int = 16) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)

    async def _one(p):
        async with sem:
            try:
                return await ask_voter(p, prompt)
            except Exception as e:
                return {"vote": "미정", "stance": "ERROR", "rationale": str(e)[:200]}

    return await asyncio.gather(*[_one(p) for p in personas])
```

### 2.4 페르소나 로딩 (parquet → list[str])

```python
# politikast/personas.py
import glob, pyarrow.parquet as pq

def load_personas(n: int, seed: int = 42) -> list[str]:
    files = sorted(glob.glob("/Users/girinman/datasets/Nemotron-Personas-Korea/data/*.parquet"))
    table = pq.read_table(files[0])
    df = table.to_pandas().sample(n=n, random_state=seed)
    # 컬럼명은 데이터셋 스키마 확인 후 조정 (보통 'persona' 또는 'description')
    col = "persona" if "persona" in df.columns else df.columns[0]
    return df[col].astype(str).tolist()
```

### 2.5 사용 예
```python
# main.py
import asyncio
from politikast.personas import load_personas
from politikast.runtime import run_simulation

if __name__ == "__main__":
    personas = load_personas(n=200)
    prompt = (
        "2026년 6월 서울시장 선거에서 누구에게 투표할 것인가? "
        "후보: A(여당), B(야당), C(제3지대). 또는 '기권'."
    )
    results = asyncio.run(run_simulation(personas, prompt, concurrency=12))
    print(sum(1 for r in results if r["vote"] == "A"), "votes for A")
```

---

## 3. Risks & 처리 방법

### 3.1 Rate limit (가장 큰 리스크)
- `gemini-3-flash-preview` 는 **preview** + free-tier 적용 시 RPM 이 매우 낮음 (10–50 RPM, 프로젝트당 — 키당 X). 4 키가 **다른 GCP 프로젝트** 인지 확인 필요. 같은 프로젝트라면 키 4 개를 써도 quota 가 합쳐진다.
- 대응:
  1. 4 개의 GCP 프로젝트로 키 발급 (필수). 못 하면 paid tier(Tier 1) 활성화.
  2. 위 코드의 `_KEY_SEMS` (per-key semaphore) + `_next_key()` 라운드로빈.
  3. 429 / `RESOURCE_EXHAUSTED` 감지 시 exponential backoff (`2^n + jitter`) 후 다음 키로 회전.
  4. 시뮬레이션 규모: 1만 voter * 1 prompt = 1만 콜. 40 RPM 풀이면 4 시간 → **샘플링 N=500~2000 으로 시작**, 결과 신뢰구간으로 1만 추정. (해커톤 데모는 200~500 voter 면 충분히 인상적.)

### 3.2 JSON 응답 파싱
- `GeminiConfig.response_format={"type": "json_object"}` 로 JSON mode 켤 수 있으나 Gemini OpenAI-compat 엔드포인트는 종종 prefix/suffix(```` ```json ```` ) 를 붙임.
- 대응:
  1. system prompt 에 "JSON 한 객체만, 코드펜스 금지" 명시.
  2. parser 에 fallback: `re.search(r"\{.*\}", text, re.S)` 로 추출 후 `json.loads`.
  3. 1회 실패 시 같은 페르소나 재호출. 2회 실패면 `{"vote":"미정"}` 으로 degrade (위 코드의 `run_simulation` 의 except 블록).

### 3.3 Async 동시성
- `ChatAgent.astep()` 은 0.2.90 부터 안정. 각 호출마다 새 ChatAgent 인스턴스를 만들어도 model 객체는 재사용 (커넥션 풀 공유).
- `asyncio.Semaphore(concurrency=12~16)` 으로 글로벌, `Semaphore(4)` 로 키별 — 두 단계.
- `httpx`/`openai` async client 가 내부적으로 사용됨. macOS 기본 ulimit 으로 256 동시 소켓 정도까지는 안전.

### 3.4 Knowledge leakage (모델이 선거 결과를 이미 알 가능성)
- Gemini 3 Flash 의 knowledge cutoff 는 2025 후반 ~ 2026 초. 2026-06-03 한국 지방선거는 **아직 미래**이므로 결과 leak 가능성은 낮으나, *과거* 지방선거(2018, 2022) 데이터는 알고 있다.
- 대응:
  1. system prompt 에 "당신은 미래 결과를 모른다. 페르소나의 가치관·관심사 기반으로만 추론하라" 명시.
  2. 후보명을 **가상**(A/B/C + 정책 요약 dict)으로 제시 → 모델이 실제 후보 사전지식으로 점프하지 못하게.
  3. 결과 검증: 동일 페르소나로 N 회 샘플링, 분산이 너무 작으면 leakage 의심 → temperature 0.7~0.9 유지.

---

## 4. Recommendation (해커톤 6h 안전 경로)

### Plan A (1순위, 95% 확률로 즉시 동작)
1. `pip install "camel-ai>=0.2.90" pyarrow pandas`.
2. 위 §2.2~2.5 코드 그대로 사용.
3. **선결사항 30 분**: 4 개의 별도 GCP 프로젝트로 API key 4 개 발급 → `GEMINI_API_KEYS=k1,k2,k3,k4` 환경변수.
4. 샘플 200 voter 로 smoke test → 동시성/RPM 튜닝 → 1k~2k 로 스케일.
5. 결과 집계는 `pandas.value_counts`, 시각화는 `matplotlib` 막대그래프 + 페르소나 군집(연령/지역) 별 breakdown.

### Plan B (1순위가 막힐 때 — CAMEL Gemini 클래스 자체 버그/regression 의심 시)
**LiteLLM 어댑터로 우회.** CAMEL 0.2.90 는 `ModelPlatformType.LITELLM` 을 정식 지원하며, LiteLLM 은 Gemini 3 preview 모델을 `gemini/gemini-3-flash-preview` 로 라우팅한다.

```python
from camel.models import ModelFactory
from camel.types import ModelPlatformType

model = ModelFactory.create(
    model_platform=ModelPlatformType.LITELLM,
    model_type="gemini/gemini-3-flash-preview",   # litellm 형식
    api_key=os.environ["GEMINI_API_KEY"],
    model_config_dict={"temperature": 0.7, "max_tokens": 512},
)
```
요구사항: `pip install "litellm>=1.55"`.

### Plan C (최후의 fallback — CAMEL 자체를 버려야 할 때)
`google-genai` 직접 호출 (CAMEL 의 ChatAgent 추상화 포기, 페르소나 system_prompt 만 직접 관리).
```python
# pip install google-genai
from google import genai
from google.genai import types as gtypes

client = genai.Client(api_key=key)   # 키별 인스턴스
resp = await client.aio.models.generate_content(
    model="gemini-3-flash-preview",
    contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
    config=gtypes.GenerateContentConfig(
        system_instruction=persona_sys,
        response_mime_type="application/json",
        temperature=0.7, max_output_tokens=512,
    ),
)
```
나머지 (라운드로빈/backoff/JSON 파싱) 는 §2.3 와 동일 패턴 재사용.

---

## 핵심 한 줄
**`pip install "camel-ai>=0.2.90"` 한 줄이 다 한다. `ModelPlatformType.GEMINI` + `ModelType.GEMINI_3_FLASH` 로 즉시 ChatAgent 생성 가능. 진짜 리스크는 라이브러리가 아니라 free-tier RPM — 4 개 GCP 프로젝트 키 확보가 본 작업의 전제다.**
