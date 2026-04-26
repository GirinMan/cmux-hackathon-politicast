# Capacity Probe v3 — `gemini-3.1-flash-lite-preview` (thinking off)

**Date:** 2026-04-26 (Phase 1 후속, ~12:35 KST)
**Author:** data-engineer (재측정 — 정책팀 요청)
**Trigger:** `.env` GEMINI_MODEL을 `gemini-3-flash-preview` → `gemini-3.1-flash-lite-preview`로 교체.
이전 모델은 thinking-on이라 합성 probe(48 RPM) 대비 실 sim throughput(10 RPM) 5x 갭 발생.
새 모델은 thinking 자체가 없어 실 RPM 회복 가능성 → 풀스펙(또는 Gemini-only) 옵션 재검토.

---

## 1. 측정 요약

| 측정 | v2 (gemini-3-flash-preview, thinking on) | v3 (gemini-3.1-flash-lite-preview, thinking off) | Δ |
|---|---|---|---|
| **합성 probe** (`{"ok": true}`, 32 tokens) | **48.0 RPM** | **36.0 RPM** | -25% |
| **실 sim payload** (system+persona+JSON, 2048 tokens) | **10 RPM** (sustained, sim-engineer 실측) | **46.0 RPM** | **+360%** (4.6x) |
| **실/합성 비율** | 0.21 (5x 과대평가) | **1.28** (합성보다 오히려 더 빠름) | — |
| **avg latency** (실 payload, conc=2) | ~5000 ms | **2712 ms** | -46% |
| **p50 latency** (실 payload) | n/a | 2294 ms | — |
| **429 / errors** | n/a | 0 / 0 | — |

> 핵심: thinking 토큰 제거로 실 워크로드 throughput이 **4.6배** 증가. 합성/실 갭 소멸 → 합성 probe가 다시 신뢰 가능.

### v3 합성 (1 키, conc=2, 60s)
- file: `_workspace/checkpoints/capacity_probe_v3_synthetic.json`
- 33 ok / 0 429 / 0 err → 36 RPM
- 합성 RPM이 v2보다 떨어진 이유: lite 모델은 raw token 처리량은 비슷해도 latency 자체가 구조적으로 약간 높을 수 있음. 그러나 실 워크로드에선 관계 없음(아래 참고).

### v3 실 sim payload (1 키, conc=2, 60s, max_tokens=2048)
- file: `_workspace/checkpoints/capacity_probe_v3_realistic.json`
- 46 ok / 0 429 / 0 err → **46 RPM**
- system prompt 1068자, user prompt 321자 — `voter_agent.py` 실제 prompt와 동등.
- 모든 호출 성공, 429 없음.
- 실 RPM > 합성 RPM 인 이유: 합성은 max_tokens=32 short responses, 실 payload는 max_tokens=2048이지만 JSON 응답이 보통 200~400 토큰이라 generation latency가 비슷. 합성과 실 간 latency 차이가 거의 없어진 결과.

### Cross-provider latency (spot, n=2 each)
| Model | avg latency (ms) | failures |
|---|---|---|
| `openai/gpt-5.4-nano` | 3333 | 0 |
| `openai/gpt-5.4-mini` | 2875 | 0 |
| `anthropic/claude-sonnet-4-6` | 4530 | 0 |
| `gemini/gemini-3.1-flash-lite-preview` | **2712** | 0 |

> Gemini lite가 가장 빠르고 실패 없음. OpenAI nano는 첫 호출 cold start(5s)가 있으나 second call은 1.7s. Anthropic은 가장 느리고 비싸지만 인터뷰(품질 우선) 용으로 적합.

---

## 2. 영향 분석 — 정책팀 권고 입력

v2 (RPM=10) 기준 정책 v1.1: 2040 calls / 240 min × safety 0.85 → 816 voter slots.
v3 (RPM=46) 기준 재계산:

```
budget = 46 RPM × 240 min × 0.85 (safety) = 9,384 calls
calls_per_voter_avg = 2.5  (poll + ballot + 0.5 KG)
voter_slots = 9384 / 2.5 = 3,754
```

v1.1 대비 **4.6배의 voter capacity** — 5 region × 700+ persona/region 가능 (v1.0 풀스펙 800/region 근접).

### Threshold 분류 (사용자 요청 기준)
- 실 RPM **30+** → v1.2 풀스펙 가능 (Gemini-only 폴백 시도) → **충족 (46 RPM)**
- 실 RPM **50+** → OpenAI 안 쓰고 Gemini만으로도 충분 (비용 절감) → **턱걸이 미달 (46 RPM)** but 매우 근접
- 실 RPM **50-** → OpenAI primary 그대로 → 현재 구간

### 권고 (policy-engineer 앞)
1. **`v1.2_recovery` 정책 생성 권고**: rpm_real_sustained=46으로 갱신, voter_slots 3,754로 확장. region별 persona n을 v1.0 풀스펙 baseline의 80~100%로 복원.
2. **Gemini-only 옵션 보류**: 46 RPM은 50 미달. 단일 키·단일 모델에 5 region × 1.5h 의존하는 risk(키 정지/모델 outage) 고려 시 OpenAI primary 유지가 안전. **단, 비용 부담이 핵심 제약이면** (사용자 USD 임계 LLM_COST_THRESHOLD_OPENAI_USD=50) Gemini-only 시도가 합리적 — 단일 키 quota burst 시 즉시 OpenAI fallback 가능하도록 LLMPool 라우팅을 health-check 기반으로 유지.
3. **Phase 3 budgeting 재산정**: 5 region × 800 persona × T=2 (full trajectory) = 8,000 voter calls × 2.5 = 20,000 LLM calls. 46 RPM × 240 min = 11,040 capacity → **여전히 부족하므로** T=2 풀스펙은 어려움. 권고: 4 region T=2 + 1 region T=1, 또는 5 region × 600 persona × T=2.
4. **Concurrency 상향 시도**: 현재 conc=2에서 0 errors. conc=4로 60s 추가 probe 시 실 RPM 80+ 가능성 — 하지만 이번 빌드 동결 시간 고려해 폴리시 재산정 우선, 추가 probe는 14:30 체크포인트 이후로.

### 사용자 escalate 포인트
- v3 RPM이 v2 대비 **4.6배** 증가 → v1.1(816 slot) 폐기, **v1.2(3,754 slot) 신규 박제 필요**.
- 사용자가 "Gemini-only로 절감하고 싶다"고 의사 표현하면 즉시 OPTION으로 제시 (46 RPM은 quota margin 작지만 5 region × 600 persona는 가능).
- **모델 안정성**: gemini-3.1-flash-lite-**preview**는 preview tier — 빌드 freeze까지 4시간 동안 outage 가능성 무시 못 함. 풀스펙은 OpenAI fallback 있는 정책 + Gemini primary로 가는 것이 합리적.

---

## 3. 산출물

| 파일 | 내용 |
|---|---|
| `_workspace/checkpoints/capacity_probe_v3_synthetic.json` | 합성 probe v3 결과 (36 RPM) |
| `_workspace/checkpoints/capacity_probe_v3_realistic.json` | 실 sim payload probe v3 결과 (46 RPM) |
| `_workspace/research/capacity_probe_realistic.py` | 재사용 가능한 realistic probe 스크립트 |
| `_workspace/research/capacity_probe_v3_report.md` | 이 보고서 |

`_workspace/checkpoints/capacity_probe.json` (v2)는 미수정 — 정책 비교 용도로 보존.
